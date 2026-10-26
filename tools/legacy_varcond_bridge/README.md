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

Build from this directory on Windows:

```powershell
msbuild .\LegacyVarCondBridge.csproj /p:Configuration=Release
```

## Example request

The helper accepts one JSON object on stdin. Required fields:

- `legacyAssemblyPath`: absolute path to `PDMMaintenance.exe`
- `itemCodes`: non-empty array of article codes
- `categoryId`: legacy PDM category ID
- `filter`: non-empty group filter. An empty filter triggers a legacy confirmation dialog, so the bridge rejects it.

Optional fields: `server`, `database`, `pConPath`, `prefix`, `propertySubstitutions`, `propertyExclusions`.

The response is JSON containing `ok`, `generatedText`, `statuses`, or `error`.

## Important limitations before UI integration

1. The legacy generator may display modal Visual Basic message boxes on internal errors; those code paths have not yet been made headless.
2. It reads live SQL data and uses legacy static configuration. Only run with a non-production test database and a known article group.
3. This pilot returns generated text only. It does not call the old form's MDB export handler, delete existing relations, or write to MDB.
4. The legacy implementation performs repeated SQL calls. This pilot deliberately preserves behavior; later performance work should replace data access behind a stable generation boundary and compare results before enabling batching.
5. The helper cannot be considered build-verified until compiled and run in the user's Windows environment with the missing legacy dependencies available.

The normal Workbench generator remains unchanged. Enable no production path until the bridge's output is compared against the current Python generator for representative super-products and edge cases.
