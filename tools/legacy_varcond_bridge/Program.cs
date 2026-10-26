using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Text;
using System.Web.Script.Serialization;

namespace LegacyVarCondBridge
{
    internal static class Program
    {
        private static readonly JavaScriptSerializer Json = new JavaScriptSerializer();

        private static int Main()
        {
            var response = new Dictionary<string, object>();
            try
            {
                string input = Console.In.ReadToEnd();
                var request = Json.Deserialize<Dictionary<string, object>>(input);
                if (request == null) throw new ArgumentException("Request JSON must be an object.");

                string assemblyPath = RequiredString(request, "legacyAssemblyPath");
                if (!File.Exists(assemblyPath))
                    throw new FileNotFoundException("Legacy PDMMaintenance assembly was not found.", assemblyPath);

                var items = GetStringList(request, "itemCodes");
                if (items.Count == 0) throw new ArgumentException("itemCodes must contain at least one article.");
                string filter = OptionalString(request, "filter");
                if (String.IsNullOrWhiteSpace(filter))
                    throw new ArgumentException("filter must be non-empty to prevent the legacy all-items confirmation dialog.");
                int categoryId = RequiredInt(request, "categoryId");
                string server = RequiredString(request, "server");
                string database = RequiredString(request, "database");
                string databaseLower = database.ToLowerInvariant();
                if (!(databaseLower.Contains("test") || databaseLower.Contains("dev") ||
                      databaseLower.Contains("uat") || databaseLower.Contains("prototype") ||
                      databaseLower.Contains("sandbox")))
                    throw new ArgumentException("Database name must clearly identify a test/dev/UAT/prototype/sandbox database.");

                Assembly legacy = Assembly.LoadFrom(Path.GetFullPath(assemblyPath));
                ConfigureLegacy(legacy, request);

                Type workerType = legacy.GetType("PDMMaintenance.VarCondThread", true);
                object worker = Activator.CreateInstance(workerType);
                var statuses = new List<string>();
                var generated = new StringBuilder();

                EventInfo statusEvent = workerType.GetEvent("UpdateStatus");
                if (statusEvent == null) throw new MissingMemberException(workerType.FullName, "UpdateStatus");
                MethodInfo handlerMethod = typeof(Program).GetMethod("OnLegacyStatus", BindingFlags.Static | BindingFlags.NonPublic);
                Delegate handler = Delegate.CreateDelegate(statusEvent.EventHandlerType, handlerMethod);
                statusEvent.AddEventHandler(worker, handler);
                _activeStatuses = statuses;
                _activeGenerated = generated;

                try
                {
                    MethodInfo init = workerType.GetMethod("initThread", BindingFlags.Instance | BindingFlags.NonPublic);
                    MethodInfo execute = workerType.GetMethod("execThread", BindingFlags.Instance | BindingFlags.NonPublic);
                    if (init == null || execute == null)
                        throw new MissingMethodException("Legacy worker initThread/execThread methods were not found.");

                    init.Invoke(worker, new object[] {
                        items, categoryId, filter, OptionalString(request, "prefix"),
                        OptionalString(request, "propertySubstitutions"),
                        OptionalString(request, "propertyExclusions")
                    });
                    execute.Invoke(worker, null);
                }
                finally
                {
                    statusEvent.RemoveEventHandler(worker, handler);
                    _activeStatuses = null;
                    _activeGenerated = null;
                }

                response["ok"] = true;
                response["generatedText"] = generated.ToString();
                response["statuses"] = statuses;
            }
            catch (TargetInvocationException ex)
            {
                response["ok"] = false;
                response["error"] = (ex.InnerException ?? ex).ToString();
            }
            catch (Exception ex)
            {
                response["ok"] = false;
                response["error"] = ex.ToString();
            }

            Console.Out.WriteLine(Json.Serialize(response));
            return response.ContainsKey("ok") && (bool)response["ok"] ? 0 : 1;
        }

        private static List<string> _activeStatuses;
        private static StringBuilder _activeGenerated;

        private static void OnLegacyStatus(object sender, string status)
        {
            if (_activeStatuses == null || status == null) return;
            _activeStatuses.Add(status);
            if (status.StartsWith("VARCOND:", StringComparison.Ordinal))
                _activeGenerated.Append(status.Substring("VARCOND:".Length));
        }

        private static void ConfigureLegacy(Assembly legacy, IDictionary<string, object> request)
        {
            Type global = legacy.GetType("PDMMaintenance.Global", false);
            if (global != null)
            {
                SetStaticField(global, "connectedServer", OptionalString(request, "server"));
                SetStaticField(global, "connectedDB", OptionalString(request, "database"));
            }

            Type cad = legacy.GetType("PDMMaintenance.CADMaintenance", false);
            if (cad != null)
                SetStaticField(cad, "pConPath", OptionalString(request, "pConPath"));
        }

        private static void SetStaticField(Type type, string name, string value)
        {
            if (String.IsNullOrWhiteSpace(value)) return;
            FieldInfo field = type.GetField(name, BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic);
            if (field != null && field.FieldType == typeof(string)) field.SetValue(null, value);
        }

        private static string RequiredString(IDictionary<string, object> values, string key)
        {
            string value = OptionalString(values, key);
            if (String.IsNullOrWhiteSpace(value)) throw new ArgumentException(key + " is required.");
            return value;
        }

        private static string OptionalString(IDictionary<string, object> values, string key)
        {
            object value;
            return values.TryGetValue(key, out value) && value != null ? Convert.ToString(value) : "";
        }

        private static int RequiredInt(IDictionary<string, object> values, string key)
        {
            object value;
            if (!values.TryGetValue(key, out value) || value == null)
                throw new ArgumentException(key + " is required.");
            int parsed;
            if (!Int32.TryParse(Convert.ToString(value), out parsed))
                throw new ArgumentException(key + " must be an integer.");
            return parsed;
        }

        private static List<string> GetStringList(IDictionary<string, object> values, string key)
        {
            object value;
            var result = new List<string>();
            if (!values.TryGetValue(key, out value) || value == null) return result;
            var list = value as ArrayList;
            if (list == null)
            {
                var objectList = value as object[];
                if (objectList == null) throw new ArgumentException(key + " must be a JSON array.");
                foreach (object item in objectList)
                    if (!String.IsNullOrWhiteSpace(Convert.ToString(item))) result.Add(Convert.ToString(item));
                return result;
            }
            foreach (object item in list)
                if (!String.IsNullOrWhiteSpace(Convert.ToString(item))) result.Add(Convert.ToString(item));
            return result;
        }
    }
}
