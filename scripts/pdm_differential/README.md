# PDM differential (real PDM vs Pricing export)

Runs the **actual compiled PDM** price update against an isolated MDB copy and the Pricing export against an
identical copy, then diffs the results. Output of the committed run: `docs/03_Workflows/pdm_differential_report.json`.

## What runs
* `run_pdm_price_update.ps1` (32-bit PowerShell) loads a **copy** of `PDMMaintenance.exe` as a library and starts
  `UpdatePriceThread.execThread` - the method PDM's *Update pCon prices* buttons start - with the same arguments the
  buttons pass (`mydate`, selected price list label / id, catalogue, `variableincs` from
  `PriceMaintenance.programCodeHasVariableIncs`). `CADMaintenance.pConPath` is redirected so the only MDB PDM can
  touch is the scenario copy. PDM.bat and the PDM UI are never started.
* `dialog_watcher.ps1` records and dismisses message boxes PDM raises (equivalent to an operator clicking OK).
* `differential.py` applies identical setup edits to both copies, runs PDM, computes the Pricing records with
  `PricingService` (same SQL functions) and exports them with `PriceMdbExportService`, reads both result states back
  and compares them (autonumber ids and row order are the only things normalised away).
* `build_report.py` classifies each remaining difference; a difference without a recorded, matching explanation fails.

## Safety
* Pass a **backup copy** of the MDB, never the live file. Nothing here opens the live MDB.
* SQL Server is only read: every INSERT/UPDATE in the exercised PDM methods targets `tCOMd_*` Jet tables
  (verified in the PDM source). PDM's own connection logic is used with the current Windows identity; no credentials are
  supplied or bypassed.
* PDM has no transaction, no preview and no read-back, so rollback / stale-plan behaviour cannot be compared against it.

## Run
```
python scripts/pdm_differential/differential.py --backup <backup.mdb> --pdm-dir <dir with PDMMaintenance.exe copy> \
    --work <scratch dir> --out raw.json [--scenarios S1_article_gbp,...]
python scripts/pdm_differential/build_report.py raw.json docs/03_Workflows/pdm_differential_report.json
```
Each scenario needs minutes (full-table state reads through the 32-bit ACE bridge).
