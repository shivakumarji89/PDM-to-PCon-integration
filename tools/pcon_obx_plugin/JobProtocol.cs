using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using System.Web.Script.Serialization;

namespace MKObxGenerator
{
    /// <summary>
    /// JSON job protocol shared with services/pcon_sdk_obx/protocol.py.
    /// Uses JavaScriptSerializer (System.Web.Extensions) so the plugin has no
    /// NuGet dependency; pCon.planner ships the .NET Framework 4.8.1 runtime.
    /// </summary>
    internal static class JobProtocol
    {
        public const int ProtocolVersion = 1;

        public const string KindPing = "ping";
        public const string KindCatalog = "catalog";
        public const string KindArticles = "articles";
        public const string KindProperties = "properties";
        public const string KindGenerate = "generate";

        public const string ModeDefault = "default";
        public const string ModeFixed = "fixed";
        public const string ModeVary = "vary";

        public const string HeartbeatFile = "plugin.heartbeat.json";
        public const string RequestSuffix = ".request.json";
        public const string ResultSuffix = ".result.json";
        public const string ProgressSuffix = ".progress.json";
        public const string CancelSuffix = ".cancel";

        private static JavaScriptSerializer NewSerializer()
        {
            return new JavaScriptSerializer { MaxJsonLength = int.MaxValue, RecursionLimit = 64 };
        }

        public static Dictionary<string, object> Parse(string text)
        {
            var data = NewSerializer().DeserializeObject(text) as Dictionary<string, object>;
            if (data == null)
                throw new InvalidDataException("Request is not a JSON object.");
            return data;
        }

        public static string Serialize(object body)
        {
            return NewSerializer().Serialize(body);
        }

        /// <summary>Write atomically: temp file then rename, so readers never see a partial document.</summary>
        public static void WriteAtomic(string path, object body)
        {
            string temp = path + ".tmp";
            File.WriteAllText(temp, Serialize(body), new UTF8Encoding(false));
            // The Workbench may be reading the previous version at this moment;
            // Windows then refuses the delete/rename for a few milliseconds.
            for (int attempt = 0; ; attempt++)
            {
                try
                {
                    if (File.Exists(path))
                        File.Delete(path);
                    File.Move(temp, path);
                    return;
                }
                catch (IOException)
                {
                    if (attempt >= 50) throw;
                    System.Threading.Thread.Sleep(10);
                }
                catch (UnauthorizedAccessException)
                {
                    if (attempt >= 50) throw;
                    System.Threading.Thread.Sleep(10);
                }
            }
        }

        public static string GetString(Dictionary<string, object> data, string key, string fallback = "")
        {
            object value;
            if (data != null && data.TryGetValue(key, out value) && value != null)
                return Convert.ToString(value, CultureInfo.InvariantCulture);
            return fallback;
        }

        public static int GetInt(Dictionary<string, object> data, string key, int fallback)
        {
            object value;
            if (data != null && data.TryGetValue(key, out value) && value != null)
            {
                try { return Convert.ToInt32(value, CultureInfo.InvariantCulture); }
                catch (Exception) { return fallback; }
            }
            return fallback;
        }

        public static bool GetBool(Dictionary<string, object> data, string key, bool fallback)
        {
            object value;
            if (data != null && data.TryGetValue(key, out value) && value != null)
            {
                if (value is bool) return (bool)value;
                bool parsed;
                if (bool.TryParse(Convert.ToString(value, CultureInfo.InvariantCulture), out parsed))
                    return parsed;
            }
            return fallback;
        }

        public static List<Dictionary<string, object>> GetObjectList(Dictionary<string, object> data, string key)
        {
            var result = new List<Dictionary<string, object>>();
            object value;
            if (data == null || !data.TryGetValue(key, out value) || value == null)
                return result;
            var array = value as object[];
            if (array == null)
            {
                var list = value as System.Collections.IEnumerable;
                if (list == null) return result;
                foreach (var item in list)
                {
                    var dict = item as Dictionary<string, object>;
                    if (dict != null) result.Add(dict);
                }
                return result;
            }
            foreach (var item in array)
            {
                var dict = item as Dictionary<string, object>;
                if (dict != null) result.Add(dict);
            }
            return result;
        }

        public static Dictionary<string, object> Envelope(string id, string kind, bool ok, string error)
        {
            return new Dictionary<string, object>
            {
                { "protocolVersion", ProtocolVersion },
                { "id", id },
                { "kind", kind },
                { "ok", ok },
                { "error", error ?? "" },
            };
        }
    }
}
