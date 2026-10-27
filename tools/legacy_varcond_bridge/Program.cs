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

        [STAThread]
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

                // dryRun never configures legacy statics, never creates the worker and never
                // connects: it only proves the reflection contract against the real assembly.
                if (OptionalBool(request, "dryRun"))
                {
                    response["ok"] = true;
                    response["dryRun"] = VerifyBinding(assemblyPath);
                    Console.Out.WriteLine(Json.Serialize(response));
                    return 0;
                }

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
                if (databaseLower.Contains("live") || databaseLower.Contains("prod"))
                    throw new ArgumentException("Database name looks like a live/production database.");
                // A name check is only a tripwire. The operator must separately attest that the
                // server/database pair was verified as non-production.
                if (!OptionalBool(request, "confirmNonProduction"))
                    throw new ArgumentException("confirmNonProduction must be true: the operator has to attest the server/database is a verified non-production target.");

                Assembly legacy = Assembly.LoadFrom(Path.GetFullPath(assemblyPath));
                ConfigureLegacy(legacy, request);

                Type workerType = legacy.GetType("PDMMaintenance.VarCondThread", true);
                object worker = Activator.CreateInstance(workerType);
                var statuses = new List<string>();
                var generated = new StringBuilder();
                response["statuses"] = statuses;
                response["legacyAssemblyVersion"] = legacy.GetName().Version.ToString();

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
                        new ArrayList(items), categoryId, filter, OptionalString(request, "prefix"),
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

                // execThread swallows its own exceptions (modal MsgBox + status), so a normal return
                // does not mean success. Treat an abort or an absent result as failure.
                if (statuses.Contains("GENERATE_VARCOND_ABORTED"))
                    throw new InvalidOperationException("Legacy worker reported GENERATE_VARCOND_ABORTED; its output is not valid.");
                if (!statuses.Exists(s => s.StartsWith("VARCOND:", StringComparison.Ordinal)))
                    throw new InvalidOperationException("Legacy worker produced no VARCOND output.");

                response["ok"] = true;
                response["generatedText"] = generated.ToString();
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

        private static Dictionary<string, object> VerifyBinding(string assemblyPath)
        {
            Assembly legacy = Assembly.LoadFrom(Path.GetFullPath(assemblyPath));
            Type worker = legacy.GetType("PDMMaintenance.VarCondThread", true);
            EventInfo statusEvent = worker.GetEvent("UpdateStatus");
            if (statusEvent == null) throw new MissingMemberException(worker.FullName, "UpdateStatus");
            MethodInfo handlerMethod = typeof(Program).GetMethod("OnLegacyStatus", BindingFlags.Static | BindingFlags.NonPublic);
            Delegate.CreateDelegate(statusEvent.EventHandlerType, handlerMethod); // throws if the signature differs

            MethodInfo init = worker.GetMethod("initThread", BindingFlags.Instance | BindingFlags.NonPublic);
            MethodInfo execute = worker.GetMethod("execThread", BindingFlags.Instance | BindingFlags.NonPublic);
            if (init == null || execute == null)
                throw new MissingMethodException("Legacy worker initThread/execThread methods were not found.");
            Type[] expected = { typeof(ArrayList), typeof(int), typeof(string), typeof(string), typeof(string), typeof(string) };
            ParameterInfo[] actual = init.GetParameters();
            if (actual.Length != expected.Length) throw new MissingMethodException("initThread has an unexpected parameter count.");
            var parameterNames = new List<string>();
            for (int i = 0; i < expected.Length; i++)
            {
                if (actual[i].ParameterType != expected[i])
                    throw new MissingMethodException("initThread parameter " + i + " is " + actual[i].ParameterType + ", expected " + expected[i] + ".");
                parameterNames.Add(actual[i].ParameterType.Name + " " + actual[i].Name);
            }
            if (execute.GetParameters().Length != 0) throw new MissingMethodException("execThread must take no parameters.");

            var info = new Dictionary<string, object>();
            info["assemblyVersion"] = legacy.GetName().Version.ToString();
            info["processIs64Bit"] = Environment.Is64BitProcess;
            info["initThreadParameters"] = parameterNames;
            info["statusEventHandlerType"] = statusEvent.EventHandlerType.FullName;
            info["globalHasConnectedServer"] = HasStaticString(legacy, "PDMMaintenance.Global", "connectedServer");
            info["globalHasConnectedDB"] = HasStaticString(legacy, "PDMMaintenance.Global", "connectedDB");
            info["cadHasPConPath"] = HasStaticString(legacy, "PDMMaintenance.CADMaintenance", "pConPath");
            return info;
        }

        private static bool HasStaticString(Assembly legacy, string typeName, string field)
        {
            Type type = legacy.GetType(typeName, false);
            if (type == null) return false;
            FieldInfo f = type.GetField(field, BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic);
            return f != null && f.FieldType == typeof(string);
        }

        private static bool OptionalBool(IDictionary<string, object> values, string key)
        {
            object value;
            return values.TryGetValue(key, out value) && value is bool && (bool)value;
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
            Type global = legacy.GetType("PDMMaintenance.Global", true);
            SetRequiredStaticField(global, "connectedServer", RequiredString(request, "server"));
            SetRequiredStaticField(global, "connectedDB", RequiredString(request, "database"));

            string pConPath = OptionalString(request, "pConPath");
            if (!String.IsNullOrWhiteSpace(pConPath))
            {
                Type cad = legacy.GetType("PDMMaintenance.CADMaintenance", true);
                SetRequiredStaticField(cad, "pConPath", pConPath);
            }
        }

        private static void SetRequiredStaticField(Type type, string name, string value)
        {
            FieldInfo field = type.GetField(name, BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic);
            if (field == null)
                throw new MissingFieldException(type.FullName, name);
            if (field.FieldType != typeof(string))
                throw new InvalidOperationException(type.FullName + "." + name + " is not a string field.");
            field.SetValue(null, value);
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
