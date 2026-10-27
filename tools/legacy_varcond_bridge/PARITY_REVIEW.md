# Legacy VARCOND parity review

Status: **bridge binding verified and compiled legacy behavior inspected;
end-to-end runtime parity is not proven**.

## Evidence collected

- The local legacy install has `PDMMaintenance.exe` version `1.0.9686.24988`,
  `ExprEvaluator.dll`, and the other runtime binaries, but no legacy source
  checkout or `.config` / `.ini` files.
- The x86 bridge's database-free reflection check loaded the real executable
  and verified `VarCondThread`, `UpdateStatus`, `initThread(ArrayList, int,
  string, string, string, string)`, `execThread()`, and the required global
  fields. The bridge build and helper invocation are verified; generation was
  not run.
- The pure legacy helper vector script was run against an isolated copy of the
  real assembly. Its complete output matched
  `scripts/varcond_parity/fixtures/helper_legacy_results.json` for version
  `1.0.9686.24988`.
- `VarCondThread.execThread` and `PriceMaintenance.getOptionIncrementSuffixes`
  were inspected from the compiled assembly's IL. The repository's
  `docs/02_Domain/PDM/Legacy_PDM_Business_Logic/05_Products.md` inventory also
  documents the Maintenance form and its SQL/MDB paths.

These are not generated-output comparisons against live PDM data.

## Legacy worker behavior established from the compiled method

1. The caller-supplied article list drives the parent-item loop. An empty
   filter enters a confirmation path; the bridge rejects it to avoid a modal
   dialog. The worker obtains a SQL connection through
   `ConnectionFactory.CreateNewConnection`.
2. For each parent, it selects BOM sub-items and quantities ordered by numeric
   `ComponentSequence`. It then queries distinct parent attributes ordered by
   `DisplayOrder`. The IF expression is built once per parent and reused for
   every BOM component; there is no component-head-attribute filter.
3. Parametric codes use `SUBSTRING` with the article prefix length and the sum
   of preceding qualifying attributes' absolute `HasDependentOptions` widths.
   Ordinary attributes use `OrderCodeValue`. Property normalization, exclusions,
   substitutions, and dot removal happen before emission.
4. Component rows are emitted in sequence, without final identical-rule
   de-duplication. An integer quantity greater than one also emits
   `$SET_PRICING_FACTOR`.
5. Option suffixes use `PriceMaintenance.getOptionIncrementSuffixes`, which
   calls `PDMOptionDataReportWithIncBase` and contains an `ItemOptionValues`
   fallback query. The Python snapshot currently supplies
   `ItemOptionValues`; equality with the stored-procedure results is not
   established.
6. Family behavior visible in the compiled method:
   - HZ13 / HZ14 fabric names map to `Upper_Front_Fabric_Type` /
     `Lower_Front_Fabric_Type`.
   - RYMPSH maps to `Panel_Finish`; RY3VNN items ending in `HW` map to
     `Screen_Finish`; RYT maps to `Worktop_Finish`; RY2U maps to
     `Hardware_Pack_Finish`.
   - RY3VNN...HW and RY2U suffixes use the ordinary
     `'<component> <optionId>=' + <property>` form. The IL-derived synthetic
     fixture now checks their full emitted rules; it is not a captured
     `VarCondThread` runtime result.
   - RYMPSH and RYT use the alternate
     `'<optionId>=<component>_' + <property>` suffix form.
7. The worker reports its assembled text through `UpdateStatus` with the
   `VARCOND:` prefix. It does not itself perform the separate form's MDB
   export/delete/link operations.

## Workbench comparison and implementation

`VarCondService.generate(..., legacy_exact=True)` now follows the worker's
confirmed ordering and formatting behavior: shared parent IF, numeric BOM
sequence, duplicate preservation, quantity factors, no automatic removal of
unresolved parametric terms, and the family suffix mappings above. Focused
regression tests cover those cases. This mode is deliberately opt-in: the
normal Workbench generator and UI remain unchanged pending real parity evidence.

The default Workbench path still applies component-head-property filtering,
deduplicates identical rules, and drops unresolved parametric properties.
These are known behavioral differences from the compiled worker. Whether those
differences explain a real relation mismatch has not been checked against a
legacy run.

The separate non-super-product `PricingRelationService` algorithm has not been
changed or compared; the bridge invokes the super-product `VarCondThread`.

## Repeatable result comparison

The committed parity harness is authoritative:
`scripts/varcond_parity/run_python.py` captures a fixture or serialized
Workbench snapshot, `inputs.py` builds the input manifest, and `compare.py`
compares legacy and Python outputs. For a Workbench snapshot:

```powershell
python -m scripts.varcond_parity.run_python --snapshot snapshot.json `
    --category-id 42 --article-code PARENT.1 --mode default --out python.json
```

Repeat `--article-code` to record the selected parent scope in the manifest.
The default generator retains snapshot order; `--mode legacy_exact` follows the
requested article order. Use `--mode legacy_exact` only to compare the opt-in
source-shaped port; the default generator remains the normal Workbench
workflow. Relevant option increments are selected by component item prefix and
included deterministically in `python.json` under `inputs`.

Compare with a real bridge response plus a legacy input manifest from the same
source scope:

```powershell
python -m scripts.varcond_parity.compare --legacy legacy.json `
    --python python.json --legacy-inputs legacy-inputs.json --out report.json
```

The legacy manifest must use the same shape as `python.json`'s `inputs`. The
report contains a unified exact-text diff, missing/extra and duplicate rules,
ordering and formatting differences, option-suffix differences,
pricing-factor quantity differences, and field-level input differences. If
legacy inputs are missing, the report marks attribution unverified rather
than claiming algorithm parity. No legacy-generator output fixture has been
fabricated.

## Runtime configuration and remaining gate

The actual assembly has `Global.connectedServer` and `Global.connectedDB`;
`CADMaintenance.pConPath` is also present. The bridge now requires and sets the
two connection fields instead of silently skipping missing fields. The
repository's legacy architecture inventory says `ConnectionFactory` uses those
globals and selects authentication behavior from the server-name policy. The
source checkout/configuration files needed to independently verify that
selection are unavailable here. No credentials are read, emitted, or passed
through the bridge.

Do not invoke generation until an operator supplies and verifies an explicitly
approved non-production SQL server/database and a known test article group.
Those inputs are not available in this task context. Runtime output comparison,
same-source input confirmation, and full behavioral parity remain unverified.
