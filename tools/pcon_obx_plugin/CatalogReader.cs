using System;
using System.Collections.Generic;
using System.Globalization;
using X3g.Plugin;
using X3g.Plugin.Articles;

namespace MKObxGenerator
{
    /// <summary>
    /// Catalogue discovery through the SDK:
    ///   Articles.Package.GetAll()                -> manufacturers / programs
    ///   Articles.Catalog.Get(package).GetAllItems() -> insertable articles
    /// </summary>
    internal sealed class CatalogReader
    {
        private readonly Logger _log;

        public CatalogReader(Logger log)
        {
            _log = log;
        }

        public List<Dictionary<string, object>> ListPackages()
        {
            var rows = new List<Dictionary<string, object>>();
            IList<Package> packages = Package.GetAll();
            if (packages == null)
                return rows;
            foreach (Package package in packages)
            {
                if (package == null)
                    continue;
                bool hasCatalog = package.Type == PackageType.ProductWithCatalog || package.Type == PackageType.Catalog;
                rows.Add(new Dictionary<string, object>
                {
                    { "packageName", package.VersionedName ?? "" },
                    { "manufacturerId", package.ManufacturerId ?? "" },
                    { "manufacturer", package.Manufacturer ?? "" },
                    { "manufacturerName", SafeName(() => package.GetManufacturerName(null)) },
                    { "programIds", package.ProgramIds ?? "" },
                    { "program", package.Program ?? "" },
                    { "programName", SafeName(() => package.GetProgramName(null)) },
                    { "type", package.Type.ToString() },
                    { "version", package.Version == null ? "" : package.Version.ToString() },
                    { "distributionRegion", package.DistributionRegion ?? "" },
                    { "hasCatalog", hasCatalog },
                });
            }
            return rows;
        }

        /// <summary>Resolve by VersionedName (the value we report as packageName).</summary>
        public Package FindPackage(string packageName)
        {
            if (string.IsNullOrEmpty(packageName))
                return null;
            IList<Package> packages = Package.GetAll();
            if (packages != null)
            {
                foreach (Package package in packages)
                {
                    if (package != null && string.Equals(package.VersionedName, packageName, StringComparison.Ordinal))
                        return package;
                }
            }
            // Package.Get expects a registered package name; try it as a fallback.
            try { return Package.Get(packageName); }
            catch (Exception ex)
            {
                _log.WriteToLog("MKObxGenerator: Package.Get failed for " + packageName + ": " + ex.Message);
                return null;
            }
        }

        public List<Dictionary<string, object>> ListArticles(Package package)
        {
            var rows = new List<Dictionary<string, object>>();
            using (Catalog catalog = Catalog.Get(package))
            {
                if (catalog == null)
                    throw new InvalidOperationException("Package " + package.VersionedName + " has no catalog.");
                IList<CatalogItem> items = catalog.GetAllItems();
                if (items == null)
                    return rows;
                foreach (CatalogItem item in items)
                {
                    if (item == null || item.Type != CatalogItemType.Article)
                        continue;
                    if (string.IsNullOrEmpty(item.ArticleNumber))
                        continue;
                    rows.Add(new Dictionary<string, object>
                    {
                        { "articleNumber", item.ArticleNumber ?? "" },
                        { "variantCode", item.VariantCode ?? "" },
                        { "variantKey", item.VariantKey ?? "" },
                        { "packageName", item.PackageName ?? "" },
                        { "label", SafeName(() => item.GetText(CatalogTextPurpose.Label)) },
                        { "description", SafeName(() => item.GetText(CatalogTextPurpose.Description)) },
                        { "inCatalogTree", item.InCatalogTree },
                    });
                }
            }
            return rows;
        }

        private static string SafeName(Func<string> getter)
        {
            try { return getter() ?? ""; }
            catch (Exception) { return ""; }
        }
    }
}
