using System;
using System.Collections.Generic;
using System.IO;
using X3g.Plugin;

namespace MKObxGenerator
{
    /// <summary>
    /// OBX export via IArticleManager.ExportBasketToObx plus a basket summary via
    /// IArticleManager.GenerateBasket (IBasket.RootFolder / IsIncomplete).
    /// </summary>
    internal sealed class ObxExporter
    {
        private readonly IArticleManager _articles;

        public ObxExporter(IArticleManager articles)
        {
            _articles = articles;
        }

        private static BasketGenerationFlags Flags
        {
            get { return BasketGenerationFlags.DirectMode | BasketGenerationFlags.IgnoreEmptyFolders; }
        }

        public bool Export(string path)
        {
            string directory = Path.GetDirectoryName(path);
            if (!string.IsNullOrEmpty(directory) && !Directory.Exists(directory))
                Directory.CreateDirectory(directory);
            return _articles.ExportBasketToObx(Flags, path);
        }

        public void Summarize(out int articleItems, out bool incomplete)
        {
            articleItems = 0;
            incomplete = false;
            IBasket basket = _articles.GenerateBasket(Flags, new List<string>().AsReadOnly());
            if (basket == null)
                return;
            incomplete = basket.IsIncomplete;
            articleItems = Count(basket.RootFolder);
        }

        private static int Count(IBasketItem item)
        {
            if (item == null) return 0;
            int count = item is IBasketArticleItem ? 1 : 0;
            if (item.Children != null)
            {
                foreach (IBasketItem child in item.Children)
                    count += Count(child);
            }
            return count;
        }
    }
}
