# Porting conventions: ExportThread.cs -> Python

Source of truth: `C:\Users\siaoca\Desktop\PDM\PDMMaintenance\ExportThread.cs` (+ `SytelineExport.cs`,
`SytelineBOMExport.cs`, `SytelineCSIExport.cs` where called). This is a **mechanical transliteration** of
decompiled C#: preserve control flow, variable names and evaluation order exactly. Do not "clean up" logic,
merge branches, or re-derive rules; correctness is judged by equivalence to the C# line by line.

## Where things live
* `services/syteline_export/pipeline/run_base.py` — `ExportRunBase` (fields `self._x`, `self.v`, `self.db`,
  `self.q/self.x`, `msgbox`, `report_swallowed`, `Flow`, `ExportAborted`). READ IT FIRST.
* `netsem.py` — .NET semantics: `tostr`, `net_int`, `net_double`, `net_bool`, `substring`, `index_of`,
  `list_index_of`, `list_contains`, `list_remove`, `remove_non_alphanumeric`, `is_knoll_catalogue`,
  `debug_feature_pos`, `debug_feature_template`, `debug_post_processed_feature_pos`.
* `db.py` — `ExportDb` protocol and `ScriptedExportDb` (test double: maps a SQL *substring* to rows).
* Each chunk you own is a mixin class in its own module `services/syteline_export/pipeline/<module>.py`,
  composed later into `ExportRun(ExportRunBase, <all mixins>)` by the integrator. Do NOT edit `run_base.py`,
  `netsem.py`, `db.py` or other agents' modules; if you need something added, say so in your final report and
  work around it locally.

## Variables
* `self._name` for C# class fields (`_siteId`, `_convertedList`, `materialstr`, `ConvCount`...), exactly as in
  `ExportRunBase` (use the same attribute names; no renaming). Fields that exist in C# but are missing from
  `ExportRunBase` must be reported to the integrator (state which, and initial value).
* Decompiled locals of `execThread` (`text38`, `arrayList66`, `num30`, `flag4`, `sqlDataReader`...) live in the
  flat namespace `self.v` (`v = self.v` at the top of your method; then `v.text38`). Every local name is unique in
  the method and always assigned at its declaration, so a flat namespace is equivalent.
  * You MAY use a plain Python local for a variable only if `grep`-ing the whole C# file shows that every use is
    inside your line range. Anything referenced outside your range MUST be `v.<name>`.
  * Keep the decompiled names even though they are ugly (the integrator and other agents rely on them). Add a
    short trailing comment with the meaning once you know it.
* `sqlDataReader` (current item row, a dict) is `v.sqlDataReader` inside the per-item loop. Other readers
  (`sqlDataReader2..5`) become `for row in <list of dict rows>`; remember `reader.Read()` loops iterate rows, and
  that after a loop the reader is exhausted/closed. Reading a column: `row["Col"]` (KeyError if the column is
  absent — keep it so mismatches surface); `x.ToString()` -> `tostr(x)`; `!= DBNull.Value` -> `is not None`.

## Types and .NET semantics (do not use bare Python equivalents where behaviour differs)
* `int.Parse(s.ToString())` -> `net_int(s)`; `double.Parse` -> `net_double`; `bool.Parse` -> `net_bool`;
  `Conversions.ToString(n)` on int -> `str(n)`; on double -> `tostr(n)`; `Conversions.ToInteger(o)` -> `int(o)`
  for ints already, else `net_int(o)`.
* `s.Substring(a)`, `s.Substring(a, b)` -> `substring(s, a, b)` (raises `LegacyRangeError`);
  `s.IndexOf(t)` -> `index_of`; `ArrayList.IndexOf/Contains/Remove` -> `list_index_of/list_contains/list_remove`;
  `ArrayList.Add` -> `.append`; `.Count` -> `len`; `.Insert(i,x)` -> `.insert`; `.RemoveAt` -> `del`;
  `string.Replace` -> `.replace`; `.StartsWith/.EndsWith` -> `.startswith/.endswith` (ordinal; C# is culture
  sensitive, accepted deviation); `.Length` -> `len`; `.ToLower()` -> `.lower()`; `.Trim()` -> `.strip()`
  (C# trims Unicode whitespace; fine).
* VB helpers: `Operators.CompareString(a, b, false) == 0` -> `a == b`; `Operators.ConcatenateObject` -> `tostr(a) + tostr(b)`;
  `Operators.AddObject(a,b)` numeric add; `Operators.CompareObjectEqual/NotEqual(obj, 292, false)` -> compare
  with `int` after converting DB value with `net_int` only when the C# would; late-bound calls
  (`NewLateBinding.LateGet(arrayListX[i], null, "Substring", ...)`) -> plain method calls on the element.
  Python `bool`/`int` confusion: never rely on `True == 1`.
* C# `checked { }` arithmetic overflow cannot occur on realistic data; ignore. Integer division: use `//` when
  both operands are ints in C#.
* Unguarded `int.Parse`/`Substring` that throw on bad data: keep the throw (the integrator wraps the run, reports the
  exception with the stage, and marks the export failed). Do not add silent fallbacks.

## Control flow
* Chunk methods for the per-item loop (`continue`/`break` of `while (sqlDataReader.Read() && !_abortThread)`)
  return `Flow.NEXT_ITEM` for `continue`, `Flow.BREAK_ITEMS` for `break`, `Flow.RETURN` for `return;` from
  execThread, else `None`. `continue`/`break` of loops *inside* your range stay as Python `continue`/`break`.
* `SytelineExport.threadStage = "17.2a";` -> `self.threadStage = "17.2a"` (keep every assignment; used for diagnostics).
* `_abortThread` checks stay where they are (`if self._abortThread:`).
* `UpdateStatusLabel?.Invoke(this, t)` -> `self.update_status_label(t)`; `UpdateExportTimer` ->
  `self.update_export_timer`.
* `Interaction.MsgBox(...)` and `catch (Exception) { ...MsgBox(ex.ToString()) }` -> `self.report_swallowed("<where>", exc)`
  (the run then continues exactly as legacy does but the error is recorded and the run is reported as
  "completed with errors"). `debug_form.ShowDialog()` blocks and is developer-only: replace by recording the text
  with `self.warnings.append(...)` (or drop if purely debug).
* **All `SytelineExport.debug*` flags default to false** and are never set at runtime: drop every
  `if (SytelineExport.debugXxx) {...}` block entirely (and the `logOutput`/`logSql` blocks). Calls to
  `SytelineExport.debugFeaturePos/debugFeatureTemplate/debugPostProcessedFeaturePos` -> the netsem identity helpers.
  Debug-only string accumulators (`text8 = text8 + ...` that are only written under a debug flag) are dropped.
  Note each dropped block in a comment `# debug-only block omitted (flag default false)` — nothing else.
* Developer-machine hacks (`Environment.UserName == "dbacw8"`, `C:\Downloads\...`) -> omit, with a comment.

## SQL
* Every `NewSqlCommand(sql, sqlConnectionN, stage)` + `ExecuteReader()` -> `rows = self.q("cN", sql, params)`;
  non-query -> `self.x("cN", ...)`. Connection names: `sqlConnection`=`c1`, `sqlConnection2`=`c2`, ... `c5`.
  Temp tables (`#temptable`) are session scoped: keep them on the same connection name as legacy.
* **Bind values, do not concatenate.** Replace every concatenated data value (strings, ids, dates) with a `?`
  placeholder and a params tuple, in textual order. Keep the SQL text otherwise identical (spacing may change).
  Concatenated *structure* (e.g. building an `IN (...)` list) -> generate `?` placeholders. Only numeric ids that
  originate from an int column may remain inline if binding would change semantics; say why in a comment.
  Preserve `CommandTimeout` intent via the Db (default 900s) — no per-command code needed.
* Sorting/deduping that SQL Server did stays in SQL; ordering that relied on reader order stays as returned.

## Tests (mandatory, `tests/test_syteline_pipeline_<module>.py`)
* Build a harness: `class H(<YourMixin>, ExportRunBase): pass`, `h = H(ScriptedExportDb({...}))`.
* Cover every branch of the C# you can reach with small, **synthetic** fixtures (name the file's fixtures as
  synthetic in a comment). Expected values must be derived by reading the C# (cite the line number in the test or
  a comment), not by running your port and pasting the output.
* Also test: each place where legacy would throw on malformed data (assert the exception type), cancellation
  via `_abortThread` where the C# checks it, and that SQL is parameterised (`db.calls` params; no data value
  appears in the SQL text).
* Run tests with `C:\Users\siaoca\AppData\Local\Programs\Python\Python312\python.exe -m pytest <file> -q`
  (never `.venv`, never bare `python`). Do not run the full suite; do not touch other tests.

## Deliverable per agent
1. Your mixin module(s) + test file(s) (no other repo files). 2. A final report with: the exact C# line range ported;
the list of `v.` variables your range **assigns** that other ranges read (name -> meaning) and **reads** that are
assigned elsewhere (name -> meaning); every ExportRunBase field/method you used that does not exist; every deviation
from the C# (what, why); any C# you could not port and why (never leave a TODO that silently skips behaviour —
raise `NotImplementedError("<legacy line>: <why>")` instead and list it); anything you suspect is a legacy defect
(do not fix it; list it).
Do NOT commit, stage, or use git beyond read-only commands. Do NOT connect to any real database.
