using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Reflection;
using System.Windows.Forms;
using X3g.Plugin;

namespace MKObxGenerator
{
    /// <summary>
    /// MK OBX Generator: lets MK Product Workbench drive pCon.planner through the
    /// official Plugin SDK. The plugin polls a job directory (shared with the
    /// Workbench) on the planner UI thread and answers each request with the
    /// SDK calls documented in docs/04_Reference/pCon/SDK_Article_OBX_Generator.md.
    ///
    /// Registration: pCon.planner only loads plugins whose XML hash was issued by
    /// EasternGraphics, or any plugin with hash "0" on a machine holding a Plugin
    /// SDK developer licence (Getting Started, section 3). Keep res/MKObxGenerator.xml
    /// and X3gGetGlobalIdentifier() in sync.
    /// </summary>
    public class MKObxGeneratorPlugin : Plugin
    {
        public const string PluginVersion = "0.1.0";
        private const string ActionRunJobs = "mk::MKObxGenerator::RunPendingJobs";
        private const string ActionShowFolder = "mk::MKObxGenerator::ShowJobFolder";
        private const string JobDirEnvironment = "MK_PCON_OBX_JOBS";

        private Timer _timer;
        private string _jobDir;
        private bool _ready;
        private bool _busy;
        private DateTime _lastHeartbeat = DateTime.MinValue;

        public override string X3gGetGlobalIdentifier() { return "0"; }
        public override string X3gGetName() { return "MKObxGenerator"; }
        public override string X3gGetVendor() { return "MillerKnoll"; }
        public override string X3gGetDescription() { return "Generates configured articles and OBX files for MK Product Workbench QA."; }
        public override string X3gGetVersion() { return PluginVersion; }

        public override bool X3gInitialize(string pPluginPath)
        {
            X3gActions.RegisterAction(ActionRunJobs);
            X3gActions.RegisterAction(ActionShowFolder);
            _jobDir = ResolveJobDir();
            return true;
        }

        public override void X3gFinalize()
        {
            if (_timer != null)
            {
                _timer.Stop();
                _timer.Dispose();
                _timer = null;
            }
            _ready = false;
            WriteHeartbeat();
        }

        public override void X3gEvent(EventType pEventType, object pParameter)
        {
            if (pEventType == EventType.ApplicationReady)
            {
                _ready = true;
                StartTimer();
                WriteHeartbeat();
            }
            else if (pEventType == EventType.ApplicationWillTerminate)
            {
                _ready = false;
                WriteHeartbeat();
            }
        }

        public override void X3gAction(string pActionKey, string pArguments)
        {
            if (pActionKey == ActionRunJobs)
                Poll();
            else if (pActionKey == ActionShowFolder)
                X3g.Plugin.MessageBox.Show("MK OBX Generator job folder:\n" + _jobDir);
        }

        private static string ResolveJobDir()
        {
            string dir = Environment.GetEnvironmentVariable(JobDirEnvironment);
            if (string.IsNullOrEmpty(dir))
            {
                string local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
                dir = Path.Combine(Path.Combine(local, "MKProductWorkbench"), "pcon_obx_jobs");
            }
            try { Directory.CreateDirectory(dir); }
            catch (Exception) { /* heartbeat will simply be missing */ }
            return dir;
        }

        private void StartTimer()
        {
            if (_timer != null) return;
            // WinForms timer: fires on the planner UI thread, which is the only
            // thread allowed to call the plugin interface (Plugin.Invoke docs).
            _timer = new Timer { Interval = 500 };
            _timer.Tick += (sender, args) => Poll();
            _timer.Start();
        }

        private void Poll()
        {
            if (_busy) return;
            _busy = true;
            try
            {
                if ((DateTime.UtcNow - _lastHeartbeat).TotalSeconds >= 2)
                    WriteHeartbeat();
                if (!_ready) return;
                string[] requests;
                try { requests = Directory.GetFiles(_jobDir, "*" + JobProtocol.RequestSuffix); }
                catch (Exception) { return; }
                Array.Sort(requests, StringComparer.Ordinal);
                foreach (string request in requests)
                    Handle(request);
            }
            finally
            {
                _busy = false;
            }
        }

        private void WriteHeartbeat()
        {
            _lastHeartbeat = DateTime.UtcNow;
            try
            {
                var body = new Dictionary<string, object>
                {
                    { "pluginVersion", PluginVersion },
                    { "protocolVersion", JobProtocol.ProtocolVersion },
                    { "plannerReady", _ready },
                    { "timestamp", (DateTime.UtcNow - new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc)).TotalSeconds },
                    { "jobDir", _jobDir },
                    { "plannerVersion", PlannerVersion() },
                };
                JobProtocol.WriteAtomic(Path.Combine(_jobDir, JobProtocol.HeartbeatFile), body);
            }
            catch (Exception ex)
            {
                Log.WriteToLog("MKObxGenerator: heartbeat failed: " + ex.Message);
            }
        }

        private static string PlannerVersion()
        {
            try
            {
                Assembly assembly = typeof(Plugin).Assembly;
                return assembly.GetName().Version.ToString();
            }
            catch (Exception) { return ""; }
        }

        private void Handle(string requestPath)
        {
            string id = Path.GetFileName(requestPath);
            id = id.Substring(0, id.Length - JobProtocol.RequestSuffix.Length);
            string resultPath = Path.Combine(_jobDir, id + JobProtocol.ResultSuffix);
            string progressPath = Path.Combine(_jobDir, id + JobProtocol.ProgressSuffix);
            string cancelPath = Path.Combine(_jobDir, id + JobProtocol.CancelSuffix);
            string kind = "";
            Dictionary<string, object> result;
            try
            {
                string text = ReadWithRetry(requestPath);
                if (text == null)
                    return; // still being renamed by the Workbench; next poll will pick it up
                Dictionary<string, object> request = JobProtocol.Parse(text);
                kind = JobProtocol.GetString(request, "kind");
                int version = JobProtocol.GetInt(request, "protocolVersion", 0);
                if (version != JobProtocol.ProtocolVersion)
                    throw new InvalidDataException("Unsupported protocol version " + version + "; plugin expects " + JobProtocol.ProtocolVersion + ".");
                if (JobProtocol.GetString(request, "id") != id)
                    throw new InvalidDataException("Request id does not match file name.");
                result = Dispatch(kind, request, progressPath, cancelPath);
                result["protocolVersion"] = JobProtocol.ProtocolVersion;
                result["id"] = id;
                result["kind"] = kind;
                result["ok"] = true;
                result["error"] = "";
            }
            catch (Exception ex)
            {
                Log.WriteToLog("MKObxGenerator: request " + id + " failed: " + ex);
                result = JobProtocol.Envelope(id, kind, false, ex.Message);
            }
            try { File.Delete(requestPath); } catch (Exception) { }
            try { File.Delete(cancelPath); } catch (Exception) { }
            try { JobProtocol.WriteAtomic(resultPath, result); }
            catch (Exception ex) { Log.WriteToLog("MKObxGenerator: cannot write result " + id + ": " + ex.Message); }
        }

        /// <summary>
        /// The Workbench renames ".pending" to ".request.json"; Windows may report a
        /// sharing violation while the rename completes. Retry briefly, then give up
        /// for this poll cycle.
        /// </summary>
        private static string ReadWithRetry(string path)
        {
            for (int attempt = 0; attempt < 20; attempt++)
            {
                try { return File.ReadAllText(path); }
                catch (IOException) { System.Threading.Thread.Sleep(10); }
                catch (UnauthorizedAccessException) { System.Threading.Thread.Sleep(10); }
            }
            return null;
        }

        private Dictionary<string, object> Dispatch(string kind, Dictionary<string, object> request,
                                                    string progressPath, string cancelPath)
        {
            var catalog = new CatalogReader(Log);
            switch (kind)
            {
                case JobProtocol.KindPing:
                    return new Dictionary<string, object>
                    {
                        { "pluginVersion", PluginVersion },
                        { "plannerVersion", PlannerVersion() },
                        { "languages", new List<string>(X3gArticles.GetEffectiveArticleLanguages() ?? new List<string>()) },
                        { "documentModified", Document.Modified },
                    };
                case JobProtocol.KindCatalog:
                    return new Dictionary<string, object> { { "packages", catalog.ListPackages() } };
                case JobProtocol.KindArticles:
                {
                    string packageName = JobProtocol.GetString(request, "packageName");
                    X3g.Plugin.Articles.Package package = catalog.FindPackage(packageName);
                    if (package == null)
                        throw new InvalidDataException("Package not registered in pCon.planner: " + packageName);
                    return new Dictionary<string, object> { { "articles", catalog.ListArticles(package) } };
                }
                case JobProtocol.KindProperties:
                    return DescribeProperties(request);
                case JobProtocol.KindGenerate:
                    return Generate(request, progressPath, cancelPath);
                default:
                    throw new InvalidDataException("Unknown request kind: " + kind);
            }
        }

        private string PrimaryLanguage()
        {
            try
            {
                IList<string> languages = X3gArticles.GetEffectiveArticleLanguages();
                return languages != null && languages.Count > 0 ? languages[0] : "";
            }
            catch (Exception) { return ""; }
        }

        private Dictionary<string, object> DescribeProperties(Dictionary<string, object> request)
        {
            var configurator = new ArticleConfigurator(X3gArticles, Log);
            ConfiguredArticle article = configurator.Insert(
                JobProtocol.GetString(request, "manufacturerId"),
                JobProtocol.GetString(request, "seriesId"),
                JobProtocol.GetString(request, "catalogPackage"),
                JobProtocol.GetString(request, "articlePackage"),
                JobProtocol.GetString(request, "articleNumber"),
                JobProtocol.GetString(request, "variantCode"));
            try
            {
                var applied = new List<Dictionary<string, object>>();
                foreach (Dictionary<string, object> assignment in JobProtocol.GetObjectList(request, "assignments"))
                {
                    string error;
                    string key = JobProtocol.GetString(assignment, "key");
                    string value = JobProtocol.GetString(assignment, "valueKey");
                    bool ok = configurator.Apply(article, key, value, out error);
                    applied.Add(new Dictionary<string, object> { { "key", key }, { "valueKey", value }, { "ok", ok }, { "error", error } });
                }
                return new Dictionary<string, object>
                {
                    { "article", configurator.Information(article, PrimaryLanguage()) },
                    { "properties", configurator.DescribeAll(article) },
                    { "applied", applied },
                };
            }
            finally
            {
                // Inspection must leave the planning as it was.
                article.Discard();
            }
        }

        private Dictionary<string, object> Generate(Dictionary<string, object> request, string progressPath, string cancelPath)
        {
            string outputPath = JobProtocol.GetString(request, "outputPath");
            if (string.IsNullOrEmpty(outputPath))
                throw new InvalidDataException("outputPath is required.");
            bool discard = JobProtocol.GetBool(request, "discardUnsavedPlanning", false);
            if (Document.Modified && !discard)
                throw new InvalidOperationException(
                    "The current pCon.planner planning has unsaved changes. Save it or allow the Workbench to discard it.");
            if (!Document.NewPlanning())
                throw new InvalidOperationException("pCon.planner refused to start a new planning.");

            var generation = new GenerationRequest
            {
                ManufacturerId = JobProtocol.GetString(request, "manufacturerId"),
                SeriesId = JobProtocol.GetString(request, "seriesId"),
                CatalogPackage = JobProtocol.GetString(request, "catalogPackage"),
                MaxConfigurations = Math.Max(1, JobProtocol.GetInt(request, "maxConfigurations", 500)),
                Language = PrimaryLanguage(),
                VaryAll = JobProtocol.GetBool(request, "varyAll", true),
                Deduplicate = JobProtocol.GetBool(request, "deduplicate", true),
            };
            string priceDate = JobProtocol.GetString(request, "priceDate");
            DateTime parsedDate;
            if (!string.IsNullOrEmpty(priceDate) &&
                DateTime.TryParseExact(priceDate, "yyyy-MM-dd", CultureInfo.InvariantCulture, DateTimeStyles.None, out parsedDate))
                generation.PriceDate = parsedDate;
            foreach (Dictionary<string, object> item in JobProtocol.GetObjectList(request, "articles"))
            {
                generation.Articles.Add(new ArticleRequest
                {
                    ArticleNumber = JobProtocol.GetString(item, "articleNumber"),
                    VariantCode = JobProtocol.GetString(item, "variantCode"),
                    PackageName = JobProtocol.GetString(item, "packageName"),
                });
            }
            foreach (Dictionary<string, object> item in JobProtocol.GetObjectList(request, "properties"))
            {
                generation.Rules.Add(new PropertyRule
                {
                    Key = JobProtocol.GetString(item, "key"),
                    Mode = JobProtocol.GetString(item, "mode", JobProtocol.ModeDefault),
                    ValueKey = JobProtocol.GetString(item, "valueKey"),
                });
            }
            if (generation.Articles.Count == 0)
                throw new InvalidDataException("At least one article is required.");

            uint progressId = X3gApp.StartProgress("MK OBX Generator", generation.MaxConfigurations, false);
            Action<int, int, string> progress = (processed, total, message) =>
            {
                try { X3gApp.SetProgress(progressId, Math.Min(processed, total)); } catch (Exception) { }
                try
                {
                    JobProtocol.WriteAtomic(progressPath, new Dictionary<string, object>
                    {
                        { "processed", processed }, { "total", total }, { "message", message ?? "" },
                    });
                }
                catch (Exception) { }
                Application.DoEvents();
            };

            var configurator = new ArticleConfigurator(X3gArticles, Log);
            Func<bool> cancelRequested = () => File.Exists(cancelPath);
            var enumerator = new ConfigurationEnumerator(configurator, X3gArticles, Log, progress, cancelRequested);
            bool exported = false;
            int basketItems = 0;
            bool incomplete = false;
            try
            {
                enumerator.Run(generation);
                var exporter = new ObxExporter(X3gArticles);
                if (enumerator.Cancelled)
                {
                    enumerator.Warnings.Add("Nothing exported because the run was cancelled.");
                }
                else if (enumerator.Configurations.Count > 0)
                {
                    exported = exporter.Export(outputPath);
                    try { exporter.Summarize(out basketItems, out incomplete); }
                    catch (Exception ex) { enumerator.Warnings.Add("Basket summary unavailable: " + ex.Message); }
                }
                else
                {
                    enumerator.Warnings.Add("No configuration could be generated; nothing exported.");
                }
            }
            finally
            {
                try { X3gApp.EndProgress(progressId); } catch (Exception) { }
                try { File.Delete(progressPath); } catch (Exception) { }
            }

            return new Dictionary<string, object>
            {
                { "outputPath", outputPath },
                { "exported", exported },
                { "configurations", enumerator.Configurations },
                { "skipped", enumerator.Skipped },
                { "duplicates", enumerator.Duplicates },
                { "visited", enumerator.Visited },
                { "truncated", enumerator.Truncated },
                { "cancelled", enumerator.Cancelled },
                { "basketItems", basketItems },
                { "basketIncomplete", incomplete },
                { "warnings", enumerator.Warnings },
            };
        }
    }
}
