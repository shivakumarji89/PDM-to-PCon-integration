# Article OBX Generator - catalogue refresh

The page shows a catalogue (manufacturer -> program -> series -> articles) scanned from the OCD repository root. The catalogue is
loaded, and the progress popup shown, **only when the repository content differs from the catalogue now displayed**.

## Why the popup used to repeat

* The page is constructed once with the main window, so its 60-second timer ran for the whole session, whichever workflow was open.
* Every tick, and the page start, called `_load_catalogue`, which always went through the shared progress popup and a full `scan()`.
* The "up to date" comparison happened only *after* the popup and the scan (`previous.programs == scan.programs`, which also compares
  absolute `db_dir` paths), so it could never prevent the popup.
* A second page instance started with no memory of what was already loaded.

## Sequence now

1. Page start / show / visible-page poll -> `_check_catalogue` (silent background task, no popup).
2. It computes `OcdCatalogueService.fingerprint()` and compares `(root, fingerprint)` with the key of the catalogue shown.
3. Equal -> status "Catalogue up to date"; nothing is loaded, no popup.
4. Different, or nothing shown yet -> `_load_catalogue` (popup + scan). On success the new `(root, fingerprint)` is recorded and kept
   process-wide (`remember_loaded`); a page instance created later for the same root starts from it and loads nothing.
5. A failed or cancelled load records nothing, so the next check detects the same difference and retries.
6. The poll does nothing while the page is not the visible workflow; showing the page performs the check. A changed catalogue also
   discards the page's cached per-program datasets.

## Fingerprint

`sha256` over, for every range folder in sorted name order, the line `<folder name>|<parts>` where parts are the sha256 of each of
`ocd_article.csv`, `pdata.ocd_article.inp_descr`, `ocd_artshorttext.csv`, `pdata.ocd_artshorttext.inp_descr` in the range's chosen
`db` folder (`-` when a file is absent; a range without OCD data contributes `-`). These are exactly the files the catalogue is read
from (article rows, labels, column layouts). It contains no absolute path, timestamp or object identity. File content is hashed once
and re-hashed only when size or mtime changes, so a repeated check is a directory listing plus `stat` calls.

Not covered: the other `ocd_*` tables (properties, values, relations, prices). They do not affect the catalogue listing; the page's
cached generator datasets are only dropped when the catalogue fingerprint changes.
