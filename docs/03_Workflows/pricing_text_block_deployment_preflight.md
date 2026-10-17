# Pricing export - live MDB deployment preflight (text-block release)

**Status: STOPPED before the first live write. Nothing in this document has been executed against the live MDB.**
Live file: `C:\HermanMillerOFMLSVN\Staging\HermanMiller\WS\Tables\Tables\Layout_Studio\pcr_data_com_ocd.mdb`

## Checked now (read-only)

| Item | Result |
|---|---|
| Backup | A byte copy was made before any testing; SHA-256 of live file and copy are identical: `332704027690729f6b60d25213431beec3e928dd131dbf16d2e8bcac4352b7d5` (95,916,032 bytes, last modified 2026-10-16 21:51 - not touched by this work). The copy lives in the session scratchpad and is **not** committed; make a fresh dated backup immediately before the live write. |
| Lock status | No `.ldb` / `.laccdb` beside the file; the file opens for read/write exclusively, so no process holds it. Re-check right before writing (pCon / PDM must be closed). |
| Package / lists | 1 package (375). EUR list 21 `EURO_2026_2` (region 6, 5) and GBP list 22 `GBP_2026_2` (regions 7, 5) are the region-linked targets. Orphan lists 23 / 24 are **not** touched and **not** deleted. |
| Schema | `tCOMd_Text` has `com_Text_1_en/de/fr/nl`; 3,341 `price` texts, no duplicate name; no global price has a dangling `com_TextID`; every global row in lists 21 / 22 is linked. |

## Counts - to be produced from your computed prices

The row counts depend on the prices computed in the Pricing page (not cached anywhere). Produce them with no write:
**Pricing -> Compute**, then **Preview Export...**, pick the *backup copy*, review/rename the target lists, and read the
preview (computation date, EUR/GBP target list names, ids, validity, reuse/create, updates, inserts, text reuse/create,
blocked rows). Paste the totals here before approving. The write button inside the preview is bound to that exact plan.
Expected for the intended run (comp. date 2026-10-16): EUR -> `EURO_2026_2` id 21 reuse, GBP -> `GBP_2026_2` id 22 reuse
(look-alikes 24 / 23 ignored and untouched); *missing or ambiguous* 0; *rows blocked* 0.

Rehearsals on copies of the real MDB are in `pricing_pdm_parity.md` (scenarios A and B).

## Expected changes to existing data

* `tCOMd_GlobalPrice` / `tCOMd_Price`: `com_PriceValue` only, on rows whose value differs. `com_TextID` of existing rows is never written.
* New rows: global at level `X`, type `S`, the list's validity, `com_TextID` set; article rows with the article's existing validity and no text.
* `tCOMd_Text`: **inserts only**, type `price`; no existing text is modified.
* No deletes anywhere; no price-list or region-link changes.

## Unrelated-record preservation checks (run after the write)

Per-list aggregates (`COUNT`, `SUM(com_PriceValue)`, `SUM(com_TextID)`) of every list other than 21 / 22 unchanged;
orphan lists 23 / 24 unchanged; `tCOMd_Article`, `tCOMd_PriceList2`, `tCOMd_DistributionRegionPriceList`, `tCOMd_Package`
row counts unchanged; every pre-existing `tCOMd_Text` row byte-identical; zero dangling `com_TextID`; no new duplicate
text names. The exporter's own read-back covers the written rows and text links; the aggregate checks are the
independent ones used in the rehearsal.

## Rollback

1. The whole export is a single ADODB transaction: if any insert/update fails nothing is committed (verified: a forced
   failure left the file's contents unchanged).
2. After a *successful* but unwanted write: close pCon/PDM and restore the pre-write backup over the live file
   (`copy /Y <backup>.mdb <live>.mdb`); verify the SHA-256 equals the backup's.
3. There is no row-level undo script; the inserted ids are all above the pre-run maxima (`tCOMd_Text` > 161,278,
   `tCOMd_GlobalPrice` > 404,621, `tCOMd_Price` > 90), so rows could be deleted by id range if a restore is not possible.

## Approval needed

To proceed, please confirm explicitly: (1) preview totals accepted, (2) pCon/PDM closed, (3) fresh backup taken.
Until then the live MDB is not written.

## Live-write gate (all must be true; each is re-checked, never assumed)

1. **Fresh preview of the intended run.** Recompute prices for the intended date, then *Export to MDB...* -> select the
   **backup copy** -> review the EUR/GBP target lists (reuse / create, ids, validity) -> read the preview: price rows to
   update / insert, already current, zero / unmapped / blocked rows (and the reason of each blocked row, including
   "upcharge has no base price row"), text blocks to reuse / create, rows blocked for a missing `Product_Code`, duplicate
   matches. Record the totals here. The write button is bound to that exact plan (`plan_digest`) and refuses if the MDB or
   inputs changed.
2. **Current verified backup** of the live MDB taken immediately before the write, SHA-256 recorded and re-verified
   against the file about to be written; no `.ldb`/`.laccdb`; PDM and pCon Creator closed (a shared reader does not block
   the write, an exclusive holder does - the export then fails with nothing written).
3. **Reviewed counts and an unchanged scope**: orphan lists 23 / 24 and unrelated region links untouched, no deletes.
4. **Explicit approval of the final, refreshed write scope** by the owner. Nothing in this repository writes the live MDB
   on its own.

Evidence for what the export does and where it differs from PDM: `pricing_pdm_parity.md` (*Actual PDM differential*) and
`pdm_differential_report.json`. pCon rendering of the written prices and texts has **not** been verified.
