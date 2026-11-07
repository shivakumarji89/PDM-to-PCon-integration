using System;
using System.Collections.Generic;
using System.Diagnostics;

namespace MKObxGenerator
{
    /// <summary>
    /// Call count and accumulated wall time of one kind of operation. Time is kept in
    /// Stopwatch ticks, so sub-millisecond SDK calls are not rounded away per call.
    /// </summary>
    internal sealed class CostCounter
    {
        public int Count;
        public long Ticks;

        public static long Begin() { return Stopwatch.GetTimestamp(); }

        public void End(long begin)
        {
            Count++;
            Ticks += Stopwatch.GetTimestamp() - begin;
        }

        public double Milliseconds { get { return Ticks * 1000.0 / Stopwatch.Frequency; } }

        public Dictionary<string, object> ToDictionary()
        {
            return new Dictionary<string, object>
            {
                { "count", Count },
                { "ms", Math.Round(Milliseconds, 3) },
                { "usPerCall", Count == 0 ? 0.0 : Math.Round(Milliseconds * 1000.0 / Count, 2) },
            };
        }
    }

    /// <summary>
    /// Counters for the SKU enumeration, reported in the result JSON under "metrics".
    ///
    /// Timers are INCLUSIVE and overlap: propertyApply contains propertyFind, valueSetRead (the
    /// offered-check) and setValue; leafVerify contains propertyFind and propertyApply for fixed
    /// rules; nextProperty contains propertyList and valueSetRead. Do not add them up; compare
    /// each against totalMs. Everything is single-threaded SDK use, so there is no double counting
    /// across threads.
    /// </summary>
    internal sealed class EnumerationMetrics
    {
        public readonly CostCounter ProbeInsert = new CostCounter();
        public readonly CostCounter PropertyApply = new CostCounter();   // FindProperty + offered-check + SetValue
        public readonly CostCounter SetValue = new CostCounter();        // the SDK SetValue call alone
        public readonly CostCounter PropertyFind = new CostCounter();    // IPropertyProvider.GetProperty
        public readonly CostCounter PropertyList = new CostCounter();    // IPropertyProvider.GetProperties (the call, not the walk)
        public readonly CostCounter NextProperty = new CostCounter();    // choosing the next property to vary
        public readonly CostCounter ValueSetRead = new CostCounter();    // IProperty.ValueSet read and walk
        public readonly CostCounter LeafVerify = new CostCounter();
        public readonly CostCounter RowBuild = new CostCounter();        // BuildRow: property names, Information(), prices
        public readonly CostCounter PriceDateUpdate = new CostCounter();
        public readonly CostCounter DuplicateCheck = new CostCounter();
        public readonly CostCounter ProbeDiscard = new CostCounter();    // Close + delete entity
        public readonly CostCounter LeafClose = new CostCounter();       // Close of an accepted leaf
        public readonly CostCounter ProgressCallback = new CostCounter();
        public readonly CostCounter ProgressSetProgress = new CostCounter();
        public readonly CostCounter ProgressWriteFile = new CostCounter();
        public readonly CostCounter ProgressDoEvents = new CostCounter();

        public int ReplayApplications;       // SetValue calls made replaying a prefix on a fresh probe
        public int IncrementalApplications;  // SetValue calls made on a handed-over probe (one value)
        public int Leaves;                   // nodes with no further property to vary
        public int InternalNodes;
        public long BranchSum;               // sum of value counts offered at internal nodes
        public int MaxDepth;
        public readonly List<int> VisitsByDepth = new List<int>();
        public readonly List<int> InsertsByDepth = new List<int>();
        public readonly List<int> ReplayByDepth = new List<int>();

        public readonly Stopwatch Clock = new Stopwatch();
        public const int SampleEveryVisits = 500;
        public const int MaxSamples = 2000;
        public readonly List<Dictionary<string, object>> Samples = new List<Dictionary<string, object>>();

        private static void Bump(List<int> list, int depth, int by = 1)
        {
            while (list.Count <= depth) list.Add(0);
            list[depth] += by;
        }

        public void Visit(int depth, int visited, int configurations, int duplicates)
        {
            Bump(VisitsByDepth, depth);
            if (depth > MaxDepth) MaxDepth = depth;
            if (visited % SampleEveryVisits == 0 && Samples.Count < MaxSamples)
            {
                Samples.Add(new Dictionary<string, object>
                {
                    { "elapsedMs", Clock.ElapsedMilliseconds }, { "visited", visited },
                    { "configurations", configurations }, { "duplicates", duplicates },
                    { "probeInserts", ProbeInsert.Count }, { "setValues", PropertyApply.Count },
                    { "insertMs", Math.Round(ProbeInsert.Milliseconds, 1) },
                    { "applyMs", Math.Round(PropertyApply.Milliseconds, 1) },
                    { "valueSetMs", Math.Round(ValueSetRead.Milliseconds, 1) },
                    { "nextPropertyMs", Math.Round(NextProperty.Milliseconds, 1) },
                });
            }
        }

        public void Inserted(int depth) { Bump(InsertsByDepth, depth); }
        public void Replayed(int depth) { ReplayApplications++; Bump(ReplayByDepth, depth); }

        public Dictionary<string, object> ToDictionary()
        {
            return new Dictionary<string, object>
            {
                { "totalMs", Clock.ElapsedMilliseconds },
                { "probeInsert", ProbeInsert.ToDictionary() },
                { "propertyApply", PropertyApply.ToDictionary() },
                { "setValue", SetValue.ToDictionary() },
                { "propertyFind", PropertyFind.ToDictionary() },
                { "propertyList", PropertyList.ToDictionary() },
                { "nextProperty", NextProperty.ToDictionary() },
                { "valueSetRead", ValueSetRead.ToDictionary() },
                { "leafVerify", LeafVerify.ToDictionary() },
                { "rowBuild", RowBuild.ToDictionary() },
                { "priceDateUpdate", PriceDateUpdate.ToDictionary() },
                { "duplicateCheck", DuplicateCheck.ToDictionary() },
                { "probeDiscard", ProbeDiscard.ToDictionary() },
                { "leafClose", LeafClose.ToDictionary() },
                { "progressCallback", ProgressCallback.ToDictionary() },
                { "progressSetProgress", ProgressSetProgress.ToDictionary() },
                { "progressWriteFile", ProgressWriteFile.ToDictionary() },
                { "progressDoEvents", ProgressDoEvents.ToDictionary() },
                { "replayApplications", ReplayApplications },
                { "incrementalApplications", IncrementalApplications },
                { "leaves", Leaves },
                { "internalNodes", InternalNodes },
                { "averageBranching", InternalNodes == 0 ? 0.0 : Math.Round((double)BranchSum / InternalNodes, 3) },
                { "maxDepth", MaxDepth },
                { "visitsByDepth", VisitsByDepth },
                { "insertsByDepth", InsertsByDepth },
                { "replayApplicationsByDepth", ReplayByDepth },
                { "sampleEveryVisits", SampleEveryVisits },
                { "samples", Samples },
            };
        }
    }
}
