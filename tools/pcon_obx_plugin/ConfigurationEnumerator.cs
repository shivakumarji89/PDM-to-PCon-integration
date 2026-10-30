using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using X3g.Plugin;

namespace MKObxGenerator
{
    internal sealed class PropertyRule
    {
        public string Key;
        public string Mode;      // default | fixed | vary
        public string ValueKey;
    }

    internal sealed class ArticleRequest
    {
        public string ArticleNumber;
        public string VariantCode;
        public string PackageName;
    }

    internal sealed class GenerationRequest
    {
        public string ManufacturerId;
        public string SeriesId;
        public string CatalogPackage;
        public List<ArticleRequest> Articles = new List<ArticleRequest>();
        public List<PropertyRule> Rules = new List<PropertyRule>();
        public int MaxConfigurations = 500;
        public string Language = "";
        public DateTime? PriceDate;
        /// <summary>Automatic mode: vary every visible, editable choice property not pinned or excluded by a rule.</summary>
        public bool VaryAll = true;
        /// <summary>Drop configurations whose final article number was already produced.</summary>
        public bool Deduplicate = true;
    }

    /// <summary>
    /// Automatic valid-SKU enumeration on top of the SDK's configuration validation.
    ///
    /// The SDK has no permutation API. What it does offer is a live
    /// IProperty.ValueSet that pCon.planner recomputes after every SetValue -
    /// the same mechanism the pCon.planner property editor uses. The enumerator
    /// therefore never multiplies value lists blindly: for every prefix of applied
    /// values it inserts a fresh probe article, re-applies the prefix in order and
    /// reads, from that live probe, which property comes next and which values it
    /// offers. Values withdrawn by relations are never visited; properties that
    /// only appear after an earlier choice (nested dependencies) are discovered
    /// because the property list itself is re-read at every node.
    ///
    /// Leaves stay in the planning as real article entities; the OBX export then
    /// serialises them with pCon's own basket generator. Duplicate final article
    /// numbers are removed before export.
    /// </summary>
    internal sealed class ConfigurationEnumerator
    {
        private readonly ArticleConfigurator _configurator;
        private readonly IArticleManager _articles;
        private readonly Logger _log;
        private readonly Action<int, int, string> _progress;
        private readonly Func<bool> _cancelRequested;

        public List<Dictionary<string, object>> Configurations = new List<Dictionary<string, object>>();
        public List<string> Warnings = new List<string>();
        public int Skipped;
        public int Duplicates;
        public int Visited;
        public bool Truncated;
        public bool Cancelled;

        private int _estimatedTotal;
        private List<PropertyRule> _fixedRules = new List<PropertyRule>();
        private HashSet<string> _excluded = new HashSet<string>(StringComparer.Ordinal);
        private List<string> _varyOrder = new List<string>();
        private bool _varyAll;
        private readonly HashSet<string> _seenFinals = new HashSet<string>(StringComparer.Ordinal);

        public ConfigurationEnumerator(ArticleConfigurator configurator, IArticleManager articles,
                                       Logger log, Action<int, int, string> progress, Func<bool> cancelRequested)
        {
            _configurator = configurator;
            _articles = articles;
            _log = log;
            _progress = progress;
            _cancelRequested = cancelRequested ?? (() => false);
        }

        public void Run(GenerationRequest request)
        {
            _estimatedTotal = request.MaxConfigurations;
            _varyAll = request.VaryAll;
            _fixedRules = new List<PropertyRule>();
            _varyOrder = new List<string>();
            _excluded = new HashSet<string>(StringComparer.Ordinal);
            foreach (PropertyRule rule in request.Rules)
            {
                if (rule.Mode == JobProtocol.ModeFixed) { _fixedRules.Add(rule); _excluded.Add(rule.Key); }
                else if (rule.Mode == JobProtocol.ModeVary) _varyOrder.Add(rule.Key);
                else _excluded.Add(rule.Key); // "default": keep pCon's value, never vary
            }

            foreach (ArticleRequest article in request.Articles)
            {
                if (Truncated || Cancelled) break;
                _seenFinals.Clear();
                var prefix = new List<KeyValuePair<string, string>>();
                foreach (PropertyRule rule in _fixedRules)
                    prefix.Add(new KeyValuePair<string, string>(rule.Key, rule.ValueKey));
                Enumerate(request, article, prefix);
            }
        }

        private bool CheckCancelled()
        {
            if (Cancelled) return true;
            if (_cancelRequested())
            {
                Cancelled = true;
                Warnings.Add("Generation cancelled by the Workbench.");
            }
            return Cancelled;
        }

        /// <summary>
        /// Pick the next property to vary from the live property list of the probe.
        /// Automatic mode walks properties in pCon's own order; explicit mode walks the
        /// requested keys in request order. Either way a candidate must exist now, be
        /// visible, editable, a choice property, and not yet assigned.
        /// </summary>
        private IProperty NextProperty(ConfiguredArticle probe, HashSet<string> assigned)
        {
            if (_varyAll)
            {
                foreach (IProperty property in _configurator.Properties(probe))
                {
                    if (property == null || assigned.Contains(property.Key) || _excluded.Contains(property.Key))
                        continue;
                    if (IsVariable(property))
                        return property;
                }
                return null;
            }
            foreach (string key in _varyOrder)
            {
                if (assigned.Contains(key)) continue;
                IProperty property = _configurator.FindProperty(probe, key);
                if (property != null && IsVariable(property))
                    return property;
            }
            return null;
        }

        private static bool IsVariable(IProperty property)
        {
            if (property.Type != PropertyType.Choice) return false; // only enumerable value sets are varied
            if (ArticleConfigurator.IsHidden(property) || !ArticleConfigurator.IsEditable(property)) return false;
            return ArticleConfigurator.ChoiceKeys(property).Count > 0;
        }

        /// <summary>
        /// A leaf is only accepted when every fixed value can be re-applied and every
        /// assignment in the prefix still holds. pCon's relation cascade may have
        /// changed an earlier value when a later one was set; such a configuration is
        /// not the one requested and is skipped rather than exported.
        /// </summary>
        private bool VerifyLeaf(ConfiguredArticle probe, ArticleRequest article,
                                List<KeyValuePair<string, string>> prefix)
        {
            foreach (PropertyRule rule in _fixedRules)
            {
                string error;
                if (!_configurator.Apply(probe, rule.Key, rule.ValueKey, out error))
                {
                    Skipped++;
                    Warnings.Add(article.ArticleNumber + " " + Describe(prefix) + ": " + error);
                    return false;
                }
            }
            foreach (KeyValuePair<string, string> assignment in prefix)
            {
                IProperty property = _configurator.FindProperty(probe, assignment.Key);
                string current = CurrentKey(property);
                if (property == null || !string.Equals(current, assignment.Value, StringComparison.Ordinal))
                {
                    Skipped++;
                    Warnings.Add(article.ArticleNumber + " " + Describe(prefix) + ": " + assignment.Key + "=" +
                                 assignment.Value + " changed by relations to " + (current ?? "(none)"));
                    return false;
                }
            }
            return true;
        }

        private static string CurrentKey(IProperty property)
        {
            if (property == null || property.Value == null) return null;
            var choice = property.Value as ChoicePropertyValue;
            return choice != null ? choice.Key : property.Value.ValueAsString;
        }

        private void Enumerate(GenerationRequest request, ArticleRequest article,
                               List<KeyValuePair<string, string>> prefix)
        {
            if (CheckCancelled()) return;
            if (Configurations.Count >= request.MaxConfigurations)
            {
                Truncated = true;
                return;
            }
            Visited++;

            ConfiguredArticle probe;
            try
            {
                probe = _configurator.Insert(request.ManufacturerId, request.SeriesId, request.CatalogPackage,
                                             article.PackageName, article.ArticleNumber, article.VariantCode);
            }
            catch (Exception ex)
            {
                Skipped++;
                Warnings.Add(article.ArticleNumber + ": " + ex.Message);
                return;
            }

            bool released = false;
            try
            {
                // Re-apply the prefix in order. pCon re-evaluates relations after
                // each SetValue, so a value chosen earlier can legitimately make a
                // later value unavailable; that branch is skipped, not forced.
                var assigned = new HashSet<string>(StringComparer.Ordinal);
                foreach (KeyValuePair<string, string> assignment in prefix)
                {
                    string error;
                    if (!_configurator.Apply(probe, assignment.Key, assignment.Value, out error))
                    {
                        Skipped++;
                        Warnings.Add(article.ArticleNumber + " " + Describe(prefix) + ": " + error);
                        return;
                    }
                    assigned.Add(assignment.Key);
                }

                IProperty next = NextProperty(probe, assigned);
                if (next == null)
                {
                    // Leaf: this probe is the configured article.
                    if (!VerifyLeaf(probe, article, prefix))
                        return;
                    if (request.PriceDate.HasValue)
                    {
                        try { _articles.UpdateArticleToCurrentPD(probe.Entity, request.PriceDate.Value); }
                        catch (Exception ex) { Warnings.Add(article.ArticleNumber + ": price date not applied: " + ex.Message); }
                    }
                    Dictionary<string, object> row = BuildRow(probe, article, prefix, request.Language);
                    string finalNumber = JobProtocol.GetString(row, "finalArticle");
                    if (request.Deduplicate && finalNumber.Length > 0 && !_seenFinals.Add(finalNumber))
                    {
                        Duplicates++;
                        return; // probe is discarded in finally: duplicate SKU never reaches the basket
                    }
                    probe.Close();
                    released = true;
                    Configurations.Add(row);
                    _progress(Configurations.Count, _estimatedTotal,
                              article.ArticleNumber + " -> " + finalNumber);
                    return;
                }

                List<string> values = ArticleConfigurator.ChoiceKeys(next);
                string key = next.Key;
                probe.Discard();
                released = true;
                foreach (string value in values)
                {
                    if (CheckCancelled()) return;
                    if (Configurations.Count >= request.MaxConfigurations)
                    {
                        Truncated = true;
                        return;
                    }
                    var branch = new List<KeyValuePair<string, string>>(prefix)
                    {
                        new KeyValuePair<string, string>(key, value)
                    };
                    Enumerate(request, article, branch);
                }
            }
            finally
            {
                if (!released)
                    probe.Discard();
            }
        }

        private Dictionary<string, object> BuildRow(ConfiguredArticle probe, ArticleRequest article,
                                                    List<KeyValuePair<string, string>> prefix, string language)
        {
            var assignments = new List<Dictionary<string, object>>();
            foreach (KeyValuePair<string, string> assignment in prefix)
            {
                string name = assignment.Key;
                string text = assignment.Value;
                IProperty property = _configurator.FindProperty(probe, assignment.Key);
                if (property != null)
                {
                    name = property.Name ?? assignment.Key;
                    ReadOnlyCollection<PropertyValue> set = property.ValueSet;
                    if (set != null)
                    {
                        foreach (PropertyValue value in set)
                        {
                            var choice = value as ChoicePropertyValue;
                            if (choice != null && choice.Key == assignment.Value)
                            {
                                text = choice.Text ?? assignment.Value;
                                break;
                            }
                        }
                    }
                }
                assignments.Add(new Dictionary<string, object>
                {
                    { "key", assignment.Key }, { "name", name },
                    { "valueKey", assignment.Value }, { "valueText", text },
                });
            }

            Dictionary<string, object> info;
            string status = "ok";
            string message = "";
            try { info = _configurator.Information(probe, language); }
            catch (Exception ex)
            {
                info = new Dictionary<string, object>();
                status = "error";
                message = "Article information unavailable: " + ex.Message;
            }
            string finalNumber = JobProtocol.GetString(info, "finalNumber");
            if (status == "ok" && string.IsNullOrEmpty(finalNumber))
            {
                status = "error";
                message = "pCon.planner returned no final article number.";
            }
            var row = new Dictionary<string, object>
            {
                { "index", Configurations.Count + 1 },
                { "baseArticle", JobProtocol.GetString(info, "baseNumber", article.ArticleNumber) },
                { "finalArticle", finalNumber },
                { "variantCode", JobProtocol.GetString(info, "variantCode") },
                { "ofmlVariantCode", JobProtocol.GetString(info, "ofmlVariantCode") },
                { "assignments", assignments },
                { "features", info.ContainsKey("features") ? info["features"] : new List<Dictionary<string, object>>() },
                { "currency", JobProtocol.GetString(info, "currency") },
                { "status", status },
                { "message", message },
            };
            object price;
            if (info.TryGetValue("purchasePrice", out price)) row["purchasePrice"] = price;
            if (info.TryGetValue("salesPrice", out price)) row["salesPrice"] = price;
            return row;
        }

        private static string Describe(List<KeyValuePair<string, string>> prefix)
        {
            var parts = new List<string>();
            foreach (KeyValuePair<string, string> item in prefix)
                parts.Add(item.Key + "=" + item.Value);
            return "[" + string.Join("; ", parts.ToArray()) + "]";
        }
    }
}
