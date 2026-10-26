# Legacy VARCOND bridge pilot

This isolated bridge exposes the Maintenance **Price Relation / VARCOND**
generator for comparison. It does not replace the Python UI and does not write
to the pCon MDB.

## Design and build

`MK Product Workbench (Python)` sends JSON on stdin to an x86 .NET Framework
4.8 helper. The helper loads `PDMMaintenance.exe`, reflects
`PDMMaintenance.VarCondThread`, captures its `UpdateStatus` events, and writes
JSON on stdout. The Python adapter is
[`services/legacy_varcond_bridge.py`](../../services/legacy_varcond_bridge.py).

Build on Windows with the .NET Framework 4.8 targeting pack and MSBuild:

```powershell
msbuild .\LegacyVarCondBridge.csproj /restore /p:Configuration=Release
```

Verified in this workspace: VS MSBuild 18.4, .NET Framework 4.8 targeting
support, x86 Release build, and database-free reflection binding against
`PDMMaintenance.exe` version `1.0.9686.24988`. The legacy `ExprEvaluator.dll`
must be beside the assembly. The assembly and its runtime files should be
copied to an isolated directory for bridge execution.

The database-free request is `{"dryRun": true, "legacyAssemblyPath": "..."}`.
It verifies the worker methods, initializer parameter types, event delegate,
and required static fields. It does not configure the fields, create the worker,
or connect to SQL.

## Generation request and safety

Required JSON fields:

- `legacyAssemblyPath`: absolute path to the legacy executable.
- `itemCodes`: non-empty article-code array, in the order to process.
- `categoryId`: legacy PDM category ID.
- `server` and `database`: explicitly approved and verified non-production
  SQL target.
- `filter`: non-empty group filter; empty input triggers a legacy confirmation.
- `confirmNonProduction`: explicit operator attestation.

Optional fields: `pConPath`, `prefix`, `propertySubstitutions`, and
`propertyExclusions`. The database-name tripwire requires `test`, `dev`, `uat`,
`prototype`, or `sandbox`, and refuses names containing `live` or `prod`. This
is not an allowlist or proof that the target is safe.

The bridge sets `Global.connectedServer` and `Global.connectedDB` on the loaded
legacy assembly and fails if those fields are absent or not strings. The
legacy `ConnectionFactory` still applies its server-name-based connection and
authentication policy. Only the compiled legacy install is available here;
its source checkout/configuration files and the operator-approved target were
not supplied. No credentials are read, emitted, or passed through the bridge.
Do not run generation until the exact server, database, and test article group
have been approved.

The response contains `ok`, `generatedText`, `statuses`, and the assembly
version, or an `error`. The helper treats a legacy abort or absent `VARCOND:`
output as failure. A legacy modal dialog can still block until timeout.

## Capturing and comparing results

The bridge currently returns generated text, not the SQL input rows. Capture
the Python result and its snapshot inputs from a serialized Workbench snapshot
with the existing parity runner:

```powershell
python -m scripts.varcond_parity.run_python --snapshot snapshot.json `
    --category-id 42 --article-code PARENT.1 --mode default --out python.json
```

Repeat `--article-code` to record the selected parent scope in the manifest.
The default `--mode default` captures normal Workbench behavior and retains
snapshot ordering. Select `--mode legacy_exact` only when comparing the
source-shaped opt-in Python mode, which follows the requested article order.
Use `--fixture` for deterministic synthetic regression cases. The generated
artifact contains exact `text` and the `inputs` manifest, including selected
parents, ordered component/term rows, prefix lengths, and only the relevant
option-increment prefixes.

Compare the Python artifact to the bridge response with:

```powershell
python -m scripts.varcond_parity.compare --legacy legacy.json `
    --python python.json --legacy-inputs legacy-inputs.json --out report.json
```

`legacy-inputs.json` must contain the legacy rows in the same manifest schema as
the Python artifact's `inputs`. The comparison reports a unified exact-text
diff, missing/extra and duplicate rules, ordering and formatting differences,
option-suffix differences, pricing-factor quantities, and field-level input
differences. If legacy inputs are absent, input equivalence and attribution
remain explicitly unverified. Synthetic comparator tests and static helper
outputs are not generated-output parity evidence. See
[`PARITY_REVIEW.md`](./PARITY_REVIEW.md) for verified behavior and remaining
gates.

## Limitations

- No real `VarCondThread` generation has been run; no approved non-production
  SQL server/database and known test article group were supplied.
- The PDM generator writes text via its status event. This bridge does not call
  the separate MDB export handler, delete existing relations, or modify MDB.
- PDM's `getOptionIncrementSuffixes` reads the legacy stored-procedure result
  with an `ItemOptionValues` fallback. Snapshot option increments have not been
  proven equivalent to those live inputs.
- The normal Workbench generator and UI remain unchanged. Do not switch a
  production workflow to the bridge before real output and input comparison.
