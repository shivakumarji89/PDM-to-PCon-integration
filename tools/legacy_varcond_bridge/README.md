# Legacy VARCOND bridge pilot

This is an isolated proof-of-concept bridge for the Maintenance **Price Relation / VARCOND** workflow. It does not replace the current Python UI and it does not write to the pCon MDB.

## Design

`MK Product Workbench (Python)` -> JSON on stdin -> x86 `.NET Framework 4.8` helper -> reflection call to the existing `PDMMaintenance.VarCondThread` -> JSON on stdout.

The Python adapter is `services/legacy_varcond_bridge.py`. It is opt-in and is not called by the standard workflow yet.

## Build requirements

- Windows with the .NET Framework 4.8 targeting/developer pack and MSBuild or Visual Studio Build Tools.
- x86 build.
- A compatible, already-built `PDMMaintenance.exe` and all of its runtime dependencies, including the legacy `ExprEvaluator.dll` dependency where required.
- Access to the intended PDM SQL Server/database using the legacy connection policy.
- A test environment and a known test article group. Do not point the first run at production.

Build from this directory on Windows (`/restore` is required; without it MSBuild fails with `NETSDK1004`):

```powershell
& "C:\Program Files\Microsoft Visual Studio8\Community\MSBuild\Current\Bin\MSBuild.exe" `
  .\LegacyVarCondBridge.csproj /restore /p:Configuration=Release
```

**Verified here:** .NET SDK 10.0.200, VS 18 MSBuild 18.4, .NET Framework 4.8 targeting pack present; the Release build succeeds
and produces an x86 `bin\Release
et48\LegacyVarCondBridge.exe`.

### Database-free binding check (safe)

`{"dryRun": true, "legacyAssemblyPath": "<COPY of PDMMaintenance.exe>"}` loads the real assembly and verifies the
`initThread(ArrayList,int,string,string,string,string)` / `execThread()` signatures, the `UpdateStatus` delegate and the
`Global`/`CADMaintenance` static fields. It never configures statics, creates the worker or connects. From Python:
`services.legacy_varcond_bridge.verify_legacy_binding(helper, assembly)`. Verified against PDMMaintenance 1.0.9686.24988
(x86 process). Always point at a **copy** of the legacy folder (it needs `ExprEvaluator.dll` beside it).

## Example request

The helper accepts one JSON object on stdin. Required fields:

- `legacyAssemblyPath`: absolute path to `PDMMaintenance.exe`
- `itemCodes`: non-empty array of article codes
- `categoryId`: legacy PDM category ID
- `server` and `database`: explicit SQL target; database name must contain `test`, `dev`, `uat`, `prototype`, or `sandbox`
- `filter`: non-empty group filter. An empty filter triggers a legacy confirmation dialog, so the bridge rejects it.
- `confirmNonProduction`: must be `true`. Operator attestation that server/database were verified as non-production. Names containing `live` or `prod` are always refused.

Optional fields: `server`, `database`, `pConPath`, `prefix`, `propertySubstitutions`, `propertyExclusions`.

The response is JSON containing `ok`, `generatedText`, `statuses`, or `error`. The helper refuses to run if the database name does not clearly identify a non-production database; this is a guardrail, not a substitute for verifying the actual server and permissions.

## Important limitations before UI integration

1. The legacy generator may display modal Visual Basic message boxes on internal errors; those code paths have not yet been made headless.
2. It reads live SQL data and uses legacy static configuration. Only run with a non-production test database and a known article group.
3. This pilot returns generated text only. It does not call the old form's MDB export handler, delete existing relations, or write to MDB.
4. The legacy implementation performs repeated SQL calls. This pilot deliberately preserves behavior; later performance work should replace data access behind a stable generation boundary and compare results before enabling batching.
5. The legacy worker swallows its own exceptions (modal message box + `GENERATE_VARCOND_ABORTED`). The bridge now reports an abort, or a run with no `VARCOND:` output, as `ok:false`. A modal dialog still blocks until the Python client's timeout.
6. `ConnectionFactory.CreateNewConnection` contains per-user and per-server branching. The bridge only sets `Global.connectedServer/connectedDB`; it cannot prove where the legacy factory finally connects. **No generation run has been executed** in this work (see PARITY_REVIEW.md). A name check is not proof of a safe database.
7. Build and binding are verified; end-to-end generation against a database is not.

The normal Workbench generator remains unchanged. Enable no production path until the bridge's output is compared against the current Python generator for representative super-products and edge cases.
