using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;
using X3g.Plugin;
using X3g.Plugin.Articles;

namespace MKObxGenerator
{
    /// <summary>One inserted, instantiated article and its live property provider.</summary>
    internal sealed class ConfiguredArticle : IDisposable
    {
        public IArticleEntity Entity;
        public IArticleInstance Instance;
        public string EntityId;
        private bool _closed;

        /// <summary>Apply pending property changes and release the instance; the entity stays in the planning.</summary>
        public void Close()
        {
            if (_closed) return;
            _closed = true;
            try
            {
                if (Instance != null && Instance.IsValid)
                    Instance.Close();
            }
            catch (Exception) { /* closing an already-invalid instance is harmless */ }
        }

        /// <summary>Close and remove the entity from the planning (used for enumeration probes).</summary>
        public void Discard()
        {
            Close();
            try
            {
                DbEntity entity = DbEntity.FromId(EntityId);
                if (entity != null && entity.Valid)
                    entity.Delete();
            }
            catch (Exception) { /* entity may already be gone */ }
        }

        public void Dispose()
        {
            Close();
        }
    }

    /// <summary>Property snapshot returned to the Workbench.</summary>
    internal sealed class PropertyRow
    {
        public string Key;
        public string Name;
        public string Description;
        public string Type;
        public string State;
        public string ValueKey;
        public string ValueText;
        public bool Editable;
        public bool Hidden;
        public List<KeyValuePair<string, string>> Choices = new List<KeyValuePair<string, string>>();

        public Dictionary<string, object> ToDictionary()
        {
            var choices = new List<Dictionary<string, object>>();
            foreach (var choice in Choices)
                choices.Add(new Dictionary<string, object> { { "key", choice.Key }, { "text", choice.Value } });
            return new Dictionary<string, object>
            {
                { "key", Key ?? "" }, { "name", Name ?? "" }, { "description", Description ?? "" },
                { "type", Type ?? "" }, { "state", State ?? "" },
                { "valueKey", ValueKey ?? "" }, { "valueText", ValueText ?? "" },
                { "editable", Editable }, { "hidden", Hidden }, { "choices", choices },
            };
        }
    }

    /// <summary>
    /// Wraps the SDK article lifecycle:
    ///   IArticleManager.InsertArticle / InsertArticleByPackage  (create)
    ///   IArticleManager.InstantiateArticle                       (open for configuration)
    ///   IArticleInstance.PropertyProvider.GetProperties()         (read, re-read after every change)
    ///   IProperty.SetValue(new ChoicePropertyValue(key), false)    (configure; pCon applies relations)
    ///   IArticleInstance.getArticleInformation(false)             (basket identity + price)
    /// </summary>
    internal sealed class ArticleConfigurator
    {
        private readonly IArticleManager _articles;
        private readonly Logger _log;

        public ArticleConfigurator(IArticleManager articles, Logger log)
        {
            _articles = articles;
            _log = log;
        }

        public ConfiguredArticle Insert(string manufacturerId, string seriesId, string catalogPackage,
                                        string articlePackage, string articleNumber, string variantCode)
        {
            IArticleEntity entity = null;
            string lastError = "";
            if (!string.IsNullOrEmpty(seriesId))
            {
                try { entity = _articles.InsertArticle(manufacturerId, seriesId, articleNumber, variantCode ?? "", true); }
                catch (Exception ex) { lastError = ex.Message; }
            }
            if (entity == null && !string.IsNullOrEmpty(catalogPackage))
            {
                try
                {
                    ArticleEntity byPackage = _articles.InsertArticleByPackage(
                        catalogPackage, string.IsNullOrEmpty(articlePackage) ? catalogPackage : articlePackage,
                        articleNumber, variantCode ?? "", true, ArticleGeometryMode.Undefined);
                    if (byPackage != null && byPackage.Entity != null)
                    {
                        _articles.PrepareArticleEntities();
                        entity = _articles.GetArticleEntity(byPackage.Entity.Id);
                    }
                }
                catch (Exception ex) { lastError = ex.Message; }
            }
            if (entity == null)
                throw new InvalidOperationException(
                    "pCon.planner could not insert article " + articleNumber +
                    (string.IsNullOrEmpty(lastError) ? "" : ": " + lastError));

            IArticleInstance instance = _articles.InstantiateArticle(entity, null);
            if (instance == null || !instance.IsValid)
                throw new InvalidOperationException("pCon.planner could not instantiate article " + articleNumber);
            return new ConfiguredArticle { Entity = entity, Instance = instance, EntityId = entity.Id };
        }

        public ReadOnlyCollection<IProperty> Properties(ConfiguredArticle article)
        {
            IPropertyProvider provider = article.Instance.PropertyProvider;
            if (provider == null)
                return new ReadOnlyCollection<IProperty>(new List<IProperty>());
            return provider.GetProperties() ?? new ReadOnlyCollection<IProperty>(new List<IProperty>());
        }

        public IProperty FindProperty(ConfiguredArticle article, string key)
        {
            IPropertyProvider provider = article.Instance.PropertyProvider;
            return provider == null ? null : provider.GetProperty(key);
        }

        /// <summary>
        /// Set one choice value. Returns false when the value is not offered at this
        /// point (dependent properties may have removed it) or pCon rejects it.
        /// </summary>
        public bool Apply(ConfiguredArticle article, string key, string valueKey, out string error)
        {
            error = "";
            IProperty property = FindProperty(article, key);
            if (property == null)
            {
                error = "Property " + key + " is not available for this configuration.";
                return false;
            }
            if (!Offers(property, valueKey))
            {
                error = "Value " + valueKey + " is not offered for " + key + " in this configuration.";
                return false;
            }
            try
            {
                bool ok = property.SetValue(new ChoicePropertyValue(valueKey), false);
                if (!ok)
                    error = "pCon.planner rejected " + key + "=" + valueKey + ".";
                return ok;
            }
            catch (Exception ex)
            {
                error = "pCon.planner failed to set " + key + "=" + valueKey + ": " + ex.Message;
                return false;
            }
        }

        public static bool Offers(IProperty property, string valueKey)
        {
            ReadOnlyCollection<PropertyValue> set = property.ValueSet;
            if (set == null || set.Count == 0)
                return true; // free-form property: let pCon decide
            foreach (PropertyValue value in set)
            {
                var choice = value as ChoicePropertyValue;
                string key = choice != null ? choice.Key : value.ValueAsString;
                if (string.Equals(key, valueKey, StringComparison.Ordinal))
                    return true;
            }
            return false;
        }

        public static List<string> ChoiceKeys(IProperty property)
        {
            var keys = new List<string>();
            ReadOnlyCollection<PropertyValue> set = property.ValueSet;
            if (set == null) return keys;
            foreach (PropertyValue value in set)
            {
                var choice = value as ChoicePropertyValue;
                string key = choice != null ? choice.Key : value.ValueAsString;
                if (!string.IsNullOrEmpty(key) && !keys.Contains(key))
                    keys.Add(key);
            }
            return keys;
        }

        public static bool IsHidden(IProperty property)
        {
            return (property.State & PropertyState.Hidden) == PropertyState.Hidden;
        }

        public static bool IsEditable(IProperty property)
        {
            PropertyState state = property.State;
            if ((state & PropertyState.ReadOnly) == PropertyState.ReadOnly) return false;
            if ((state & PropertyState.Editable) == PropertyState.Editable) return true;
            // Some providers report only Enabled; treat enabled, non-read-only as editable.
            return (state & PropertyState.Enabled) == PropertyState.Enabled;
        }

        public static PropertyRow Describe(IProperty property)
        {
            var row = new PropertyRow
            {
                Key = property.Key,
                Name = property.Name,
                Description = property.Description,
                Type = property.Type.ToString(),
                State = property.State.ToString(),
                Editable = IsEditable(property),
                Hidden = IsHidden(property),
            };
            PropertyValue current = property.Value;
            if (current != null)
            {
                var choice = current as ChoicePropertyValue;
                row.ValueKey = choice != null ? choice.Key : current.ValueAsString;
                row.ValueText = choice != null ? (choice.Text ?? "") : (current.ValueAsString ?? "");
            }
            ReadOnlyCollection<PropertyValue> set = property.ValueSet;
            if (set != null)
            {
                foreach (PropertyValue value in set)
                {
                    var choice = value as ChoicePropertyValue;
                    if (choice != null)
                        row.Choices.Add(new KeyValuePair<string, string>(choice.Key ?? "", choice.Text ?? ""));
                    else
                        row.Choices.Add(new KeyValuePair<string, string>(value.ValueAsString ?? "", value.ValueAsString ?? ""));
                }
            }
            return row;
        }

        public List<Dictionary<string, object>> DescribeAll(ConfiguredArticle article)
        {
            var rows = new List<Dictionary<string, object>>();
            foreach (IProperty property in Properties(article))
            {
                if (property == null) continue;
                try { rows.Add(Describe(property).ToDictionary()); }
                catch (Exception ex) { _log.WriteToLog("MKObxGenerator: property " + property.Key + " unreadable: " + ex.Message); }
            }
            return rows;
        }

        /// <summary>Identity and prices of the configured article from the basket view.</summary>
        public Dictionary<string, object> Information(ConfiguredArticle article, string language)
        {
            var info = new Dictionary<string, object>();
            IBasketItem item = article.Instance.getArticleInformation(false);
            var basketArticle = item as IBasketArticleItem;
            if (basketArticle == null)
            {
                info["baseNumber"] = "";
                info["finalNumber"] = "";
                return info;
            }
            info["baseNumber"] = Safe(() => basketArticle.GetArticleNumber(BasketArtNumType.Base));
            info["finalNumber"] = Safe(() => basketArticle.GetArticleNumber(BasketArtNumType.Final));
            info["variantCode"] = Safe(() => basketArticle.GetArticleNumber(BasketArtNumType.VariantCode));
            info["ofmlVariantCode"] = Safe(() => basketArticle.GetArticleNumber(BasketArtNumType.OFMLVariantCode));
            info["shortText"] = Safe(() => basketArticle.GetDescription(BasketArtDescrType.Short, language ?? ""));
            info["manufacturerId"] = basketArticle.ManufacturerId ?? "";
            info["seriesId"] = basketArticle.SeriesId ?? "";
            IBasketArticleCalculation calc = basketArticle.Calculation;
            if (calc != null)
            {
                Currency purchase = calc.PurchasePricePD != null ? calc.PurchasePricePD.Single : null;
                Currency sales = calc.SalesPricePD != null ? calc.SalesPricePD.Single : null;
                if (purchase != null)
                {
                    info["purchasePrice"] = Convert.ToDouble(purchase.Value, CultureInfo.InvariantCulture);
                    info["currency"] = purchase.Unit ?? "";
                }
                if (sales != null)
                {
                    info["salesPrice"] = Convert.ToDouble(sales.Value, CultureInfo.InvariantCulture);
                    if (!info.ContainsKey("currency")) info["currency"] = sales.Unit ?? "";
                }
            }
            var features = new List<Dictionary<string, object>>();
            try
            {
                ReadOnlyCollection<IBasketArticleFeature> list = basketArticle.GetFeatures(language ?? "");
                if (list != null)
                {
                    foreach (IBasketArticleFeature feature in list)
                    {
                        features.Add(new Dictionary<string, object>
                        {
                            { "key", feature.NameKey ?? "" }, { "name", feature.NameText ?? "" },
                            { "valueKey", feature.ValueKey ?? "" }, { "valueText", feature.ValueText ?? "" },
                            { "visible", feature.Visible },
                        });
                    }
                }
            }
            catch (Exception ex) { _log.WriteToLog("MKObxGenerator: features unreadable: " + ex.Message); }
            info["features"] = features;
            return info;
        }

        private static string Safe(Func<string> getter)
        {
            try { return getter() ?? ""; }
            catch (Exception) { return ""; }
        }
    }
}
