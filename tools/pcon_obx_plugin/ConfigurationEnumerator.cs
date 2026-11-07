using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Diagnostics;
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
        public long EnumerationElapsedMs;
        public EnumerationMetrics Metrics { get { return _configurator.Metrics; } }
        public int ProbeInsertions { get { return Metrics.ProbeInsert.Count; } }
        public int PropertyApplications { get { return Metrics.PropertyApply.Count; } }
        public long ProbeInsertElapsedMs { get { return (long)Math.Round(Metrics.ProbeInsert.Milliseconds); } }
        public long PropertyApplyElapsedMs { get { return (long)Math.Round(Metrics.PropertyApply.Milliseconds); } }
        public bool Truncated;
        public bool Cancelled;

        /// <summary>
        /// Hand the parent's already-configured probe to its first child instead of
        /// discarding it, so that child only applies its one new value (no insert,
        /// no prefix replay). Siblings still get a fresh probe plus a full replay:
        /// the SDK has no rollback/clone, and un-setting a value does not undo
        /// pCon's relation cascade. Set false to measure the baseline behaviour.
        /// </summary>
        public bool ReuseParentProbe = true;

        /// <summary>
        /// Benchmark switch (MK_OBX_LEGACY_READS=1): read each chosen property's ValueSet a second
        /// time and always run the offered-check before SetValue, as before the ValueSet-read
        /// optimisation. With ReuseParentProbe=false this reproduces the fe4534e baseline's SDK calls.
        /// </summary>
        public bool LegacyValueSetReads
        {
            get { return _configurator.AlwaysCheckOffered; }
            set { _configurator.AlwaysCheckOffered = value; }
        }

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
            var runClock = Stopwatch.StartNew();
            Metrics.Clock.Restart();
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
                // Reuse the branch state during depth-first traversal. Each child
                // appends one assignment and removes it in a finally block, avoiding
                // a fresh prefix list and assigned-key HashSet for every visited node.
                var prefix = new List<KeyValuePair<string, string>>();
                var assigned = new HashSet<string>(StringComparer.Ordinal);
                foreach (PropertyRule rule in _fixedRules)
                {
                    prefix.Add(new KeyValuePair<string, string>(rule.Key, rule.ValueKey));
                    assigned.Add(rule.Key);
                }
                Enumerate(request, article, prefix, assigned, null);
            }
            runClock.Stop();
            Metrics.Clock.Stop();
            EnumerationElapsedMs = runClock.ElapsedMilliseconds;
        }

        private ConfiguredArticle InsertProbe(GenerationRequest request, ArticleRequest article)
        {
            long begin = CostCounter.Begin();
            try
            {
                return _configurator.Insert(request.ManufacturerId, request.SeriesId, request.CatalogPackage,
                                             article.PackageName, article.ArticleNumber, article.VariantCode);
            }
            finally { Metrics.ProbeInsert.End(begin); }
        }

        private bool ApplyAndCount(ConfiguredArticle probe, string key, string value, out string error,
                                   bool valueJustRead = false)
        {
            long begin = CostCounter.Begin();
            try
            {
                return _configurator.Apply(probe, key, value, out error, valueJustRead);
            }
            finally { Metrics.PropertyApply.End(begin); }
        }

        private void DiscardProbe(ConfiguredArticle probe)
        {
            long begin = CostCounter.Begin();
            try { probe.Discard(); }
            finally { Metrics.ProbeDiscard.End(begin); }
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
        private IProperty NextProperty(ConfiguredArticle probe, HashSet<string> assigned, out List<string> values)
        {
            long begin = CostCounter.Begin();
            try { return SelectNextProperty(probe, assigned, out values); }
            finally { Metrics.NextProperty.End(begin); }
        }

        private IProperty SelectNextProperty(ConfiguredArticle probe, HashSet<string> assigned, out List<string> values)
        {
            values = null;
            if (_varyAll)
            {
                foreach (IProperty property in _configurator.Properties(probe))
                {
                    if (property == null || assigned.Contains(property.Key) || _excluded.Contains(property.Key))
                        continue;
                    if (IsVariable(property, out values))
                        return property;
                }
                return null;
            }
            foreach (string key in _varyOrder)
            {
                if (assigned.Contains(key)) continue;
                IProperty property = _configurator.FindProperty(probe, key);
                if (property != null && IsVariable(property, out values))
                    return property;
            }
            return null;
        }

        /// <summary>The value keys are returned so the caller does not read the ValueSet a second time.</summary>
        private bool IsVariable(IProperty property, out List<string> values)
        {
            values = null;
            if (property.Type != PropertyType.Choice) return false; // only enumerable value sets are varied
            if (ArticleConfigurator.IsHidden(property) || !ArticleConfigurator.IsEditable(property)) return false;
            List<string> keys = _configurator.ChoiceKeys(property);
            if (keys.Count == 0) return false;
            values = keys;
            return true;
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
                if (!ApplyAndCount(probe, rule.Key, rule.ValueKey, out error))
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

        /// <param name="inherited">
        /// A probe whose state is the parent prefix minus its last assignment, handed
        /// down by the parent (null for the root and for later siblings). Ownership
        /// moves to this call, which always releases it.
        /// </param>
        private void Enumerate(GenerationRequest request, ArticleRequest article,
                               List<KeyValuePair<string, string>> prefix, HashSet<string> assigned,
                               ConfiguredArticle inherited)
        {
            ConfiguredArticle probe = inherited;
            bool released = false;
            try
            {
                if (CheckCancelled()) return;
                if (Configurations.Count >= request.MaxConfigurations)
                {
                    Truncated = true;
                    return;
                }
                Visited++;
                int depth = prefix.Count;
                Metrics.Visit(depth, Visited, Configurations.Count, Duplicates);

                if (probe == null)
                {
                    try
                    {
                        Metrics.Inserted(depth);
                        probe = InsertProbe(request, article);
                    }
                    catch (Exception ex)
                    {
                        Skipped++;
                        Warnings.Add(article.ArticleNumber + ": " + ex.Message);
                        return;
                    }

                    // Re-apply the prefix in order. pCon re-evaluates relations after
                    // each SetValue, so a value chosen earlier can legitimately make a
                    // later value unavailable; that branch is skipped, not forced.
                    foreach (KeyValuePair<string, string> assignment in prefix)
                    {
                        string error;
                        Metrics.Replayed(depth);
                        if (!ApplyAndCount(probe, assignment.Key, assignment.Value, out error))
                        {
                            Skipped++;
                            Warnings.Add(article.ArticleNumber + " " + Describe(prefix) + ": " + error);
                            return;
                        }
                    }
                }
                else
                {
                    // The inherited probe already carries the parent prefix; only the
                    // new assignment is applied. The value came from the live ValueSet
                    // of this very probe, so the "is it offered" pre-check is redundant.
                    KeyValuePair<string, string> last = prefix[prefix.Count - 1];
                    string error;
                    Metrics.IncrementalApplications++;
                    if (!ApplyAndCount(probe, last.Key, last.Value, out error, true))
                    {
                        Skipped++;
                        Warnings.Add(article.ArticleNumber + " " + Describe(prefix) + ": " + error);
                        return;
                    }
                }

                List<string> values;
                IProperty next = NextProperty(probe, assigned, out values);
                if (next != null && LegacyValueSetReads)
                    values = _configurator.ChoiceKeys(next); // the second ValueSet read the baseline made
                if (next == null)
                {
                    // Leaf: this probe is the configured article.
                    Metrics.Leaves++;
                    long verifyBegin = CostCounter.Begin();
                    bool verified = VerifyLeaf(probe, article, prefix);
                    Metrics.LeafVerify.End(verifyBegin);
                    if (!verified)
                        return;
                    if (request.PriceDate.HasValue)
                    {
                        long priceBegin = CostCounter.Begin();
                        try { _articles.UpdateArticleToCurrentPD(probe.Entity, request.PriceDate.Value); }
                        catch (Exception ex) { Warnings.Add(article.ArticleNumber + ": price date not applied: " + ex.Message); }
                        Metrics.PriceDateUpdate.End(priceBegin);
                    }
                    long rowBegin = CostCounter.Begin();
                    Dictionary<string, object> row = BuildRow(probe, article, prefix, request.Language);
                    Metrics.RowBuild.End(rowBegin);
                    string finalNumber = JobProtocol.GetString(row, "finalArticle");
                    long dupBegin = CostCounter.Begin();
                    bool duplicate = request.Deduplicate && finalNumber.Length > 0 && !_seenFinals.Add(finalNumber);
                    Metrics.DuplicateCheck.End(dupBegin);
                    if (duplicate)
                    {
                        Duplicates++;
                        return; // probe is discarded in finally: duplicate SKU never reaches the basket
                    }
                    long closeBegin = CostCounter.Begin();
                    probe.Close();
                    Metrics.LeafClose.End(closeBegin);
                    released = true;
                    Configurations.Add(row);
                    long progressBegin = CostCounter.Begin();
                    _progress(Configurations.Count, _estimatedTotal,
                              article.ArticleNumber + " -> " + finalNumber);
                    Metrics.ProgressCallback.End(progressBegin);
                    return;
                }
                Metrics.InternalNodes++;
                Metrics.BranchSum += values.Count;

                string key = next.Key;
                // The probe now holds exactly the state the first child needs. With
                // reuse it is handed to that child; otherwise (baseline) it is dropped
                // and every child inserts and replays on its own.
                ConfiguredArticle carry = null;
                if (ReuseParentProbe)
                    carry = probe;
                else
                    DiscardProbe(probe);
                released = true;
                try
                {
                    foreach (string value in values)
                    {
                        if (CheckCancelled()) return;
                        if (Configurations.Count >= request.MaxConfigurations)
                        {
                            Truncated = true;
                            return;
                        }
                        prefix.Add(new KeyValuePair<string, string>(key, value));
                        assigned.Add(key);
                        ConfiguredArticle handoff = carry;
                        carry = null; // the child owns it from here on, whatever happens
                        try
                        {
                            Enumerate(request, article, prefix, assigned, handoff);
                        }
                        finally
                        {
                            // Restore the parent prefix exactly, including when the
                            // child is cancelled, truncated, or exits through an error.
                            assigned.Remove(key);
                            prefix.RemoveAt(prefix.Count - 1);
                        }
                    }
                }
                finally
                {
                    // Never handed on (cancel/truncate before the first child): remove
                    // the probe so nothing is left behind in the planning.
                    if (carry != null)
                        DiscardProbe(carry);
                }
            }
            finally
            {
                if (!released && probe != null)
                    DiscardProbe(probe);
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
