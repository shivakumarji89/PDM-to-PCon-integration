# 17 — Images

**Module prefix:** BR-IMG
**Primary legacy source:** `GetImage.cs` (~209), `ValidateImages.cs`, `ValidateImageThread.cs`; secondary callers: `CADMaintenance.cs` (image validation / archive menu items), `ProductDescriptions.cs`, `MainMenu.cs`, `Global.cs`, `DataQuery.cs`, `ExportDPSDB.cs`.
**Status:** Verified from source unless marked `UNKNOWN`.

---

## 1. Purpose

This module covers two related concerns:

1. **Image path resolution / loading** — how the application turns a stored `ImageFile` string (or a hard‑coded relative token such as `"Images\Application\small_catalogue.jpg"`) into a real bitmap, by prepending one of several base paths (local UNC share, EOS folder, or an HTTP URL) and probing each until a file is found. Implemented in [GetImage.cs](../../../Users/siaoca/Desktop/PDM/PDMMaintenance/GetImage.cs).
2. **Image validation** — batch checks that verify the `ImageFile` / `WFImageFile` references stored in the database still point at existing files on the PDM network share, and either report or auto‑null the broken references. Implemented in [ValidateImages.cs](../../../Users/siaoca/Desktop/PDM/PDMMaintenance/ValidateImages.cs) (silent, used at publish time) and [ValidateImageThread.cs](../../../Users/siaoca/Desktop/PDM/PDMMaintenance/ValidateImageThread.cs) (interactive, launched from the query dialog).

`ImageFile`‑style columns exist on many entities (Product, AttributeValue, OptionValue, ProductRange, Catalogue, CatalogueProductCategories, HandbookProducts). The same `GetImage` resolver is reused across all of them.

---

## 2. Entry Points

| Entry point | Trigger | Source |
|---|---|---|
| `GetImage.GetImage(imageFile, materialpath, safeload, noscale)` | Any UI needing a bitmap for an icon, product photo, attribute/option swatch, etc. | `GetImage.cs:108` |
| `GetImage.SafeImageFromFile(path, noscale)` | Called internally by `GetImage` when `safeload = true`; also directly usable. `public static`. | `GetImage.cs:57` |
| `GetImage.GetImageFromURL(url)` | Called internally by `GetImage` when a base path starts with `http`. `private`. | `GetImage.cs:35` |
| `GetImage.URLExists(url)` | `public static` reachability probe. | `GetImage.cs:13` |
| `ValidateImages.validateImages()` | Called during DPS DB publish. `ExportDPSDB.cs:215` (`new ValidateImages().validateImages()`). | `ValidateImages.cs:12` |
| `ValidateImageThread.ExecThread()` | Background thread started from the **DataQuery** dialog when its title starts with `"Unresolved"` (query menu items "Unresolved Product Images" / "Unresolved … EOS Cloud"). | `DataQuery.cs:2428`; thread body `ValidateImageThread.cs:33` |
| CADMaintenance menu: **Validate Product Images**, **Validate Attribute/Option Images**, **Validate Image File References**, **Archive Legacy Product Images** | Tools menu inside CAD Maintenance form. | `CADMaintenance.cs:16982 / 17221 / 24511 / 22088` (documented here as image‑related maintenance; the form itself is module 11). |

**Representative resolver call sites** (all use `new GetImage().GetImage(...)`):

- `MainMenu.cs:2618-2621+` — toolbar icons (`Images\Application\small_catalogue.jpg`, `small_notepad.jpg`, `small_currencies.jpg`, `small_syteline.jpg`, …).
- `ProductDescriptions.cs:7937 / 7959 / 7981` — product primary image (`ImageFile`), wireframe (`WFImageFile`), dimension image (`DimImageFile`).
- `CADMaintenance.cs:9678`, `12275-12277` (zoom icons, `safeload:false`).
- `HandbookDesigner.cs:2948`, `FinancialMaintenance.cs:1657`, `PhysicalMaintenance.cs:1850`, `PriceMaintenance.cs:4288`, `SIFImport.cs:7063`, `UserAdmin.cs:2246` (`Images\Other\skype.gif`).

---

## 3. Call Hierarchy

```
UI form (MainMenu / ProductDescriptions / CADMaintenance / …)
  └─ new GetImage().GetImage(imageFile, materialpath="", safeload=true, noscale=false)
       ├─ imageFile.Replace("\\","")           // only when materialpath == ""
       ├─ token expansion loop (ImagesProducts → Images\Products\, …)
       ├─ for each Global.filePaths[i]:
       │     ├─ if base starts "http": GetImageFromURL(text)  → WebClient.OpenRead → Image.FromStream
       │     └─ else:                 File.Exists(text) ? (safeload ? SafeImageFromFile : Image.FromFile)
       └─ fallback: image = Global.imageUnavailable   // NEVER assigned ⇒ null

DataQuery ("Unresolved…" query)
  └─ new ValidateImageThread().InitThread(catalogueId, cloud) → Thread(ExecThread).Start()
       ├─ SELECT products / catalogues / attribute-value images
       ├─ File.Exists("\\wechip01v\HMEURONET\PDM\" + ImageFile)  (+ "\na.jpg" placeholder check)
       └─ debug_form.ShowDialog()  // report of unresolved images

ExportDPSDB (publish)
  └─ new ValidateImages().validateImages()
       ├─ SELECT ProductId, WFImageFile FROM Product WHERE WFImageFile IS NOT NULL
       ├─ File.Exists("\\wechip01v\wwwroot\PDM\" + WFImageFile)?
       └─ UPDATE Product SET WFImageFile = NULL WHERE ProductId = …   // auto-clean broken refs
```

---

## 4. SQL Analysis

### ValidateImages.validateImages() — `ValidateImages.cs`

**Q-IMG-001** (`ValidateImages.cs:28`)
```sql
SELECT ProductId, WFImageFile FROM Product WHERE WFImageFile IS NOT NULL
```
*WHY:* Enumerate every product that has a **wireframe** image reference, so each can be checked for physical existence on the share. Only `WFImageFile` is validated here (not `ImageFile` / `DimImageFile`).

**Q-IMG-002** (`ValidateImages.cs:49`, executed once per broken reference)
```sql
UPDATE Product SET WFImageFile = NULL WHERE ProductId = <id>
```
*WHY:* Auto‑repair — when the referenced wireframe file no longer exists under `\\wechip01v\wwwroot\PDM\`, the DB reference is cleared to `NULL` so downstream consumers don't point at a missing file. Built by string concat of the `ProductId`.

### ValidateImageThread.ExecThread() — `ValidateImageThread.cs`

**Q-IMG-003** — cloud mode, catalogue images (`ValidateImageThread.cs:51`)
```sql
SELECT CatalogueId, Name, ImageFile FROM Catalogue WHERE Status < 2 [AND CatalogueId = <id>] ORDER BY Name
```
*WHY:* In "EOS Cloud" mode, catalogue tile images are also validated. `Status < 2` = only Unreleased(0)/Active(1) catalogues (excludes Obsolete≥2). Optional `CatalogueId` filter restricts to the selected catalogue. CatalogueId is stored negated (`-1 * CatalogueId`) in the result list to distinguish it from product/attribute rows.

**Q-IMG-004** — cloud mode, first‑attribute swatch images (`ValidateImageThread.cs:71`)
```sql
SELECT pc.Name AS pc_name, atval.AttributeValueId, atval.Name AS atval_name, Product.Product, atval.ImageFile
FROM Product
INNER JOIN ProductAttributeValues pav ON Product.ProductId = pav.ProductId
INNER JOIN AttributeValue atval ON pav.AttributeValueId = atval.AttributeValueId
INNER JOIN Attribute attr ON atval.AttributeId = attr.AttributeId AND attr.DisplayOrder = 1
INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId
INNER JOIN ProductCategory pc ON pr.ProductCategoryId = pc.ProductCategoryId
[INNER JOIN Item ON Product.ProductId = Item.ProductId
 INNER JOIN CatalogueItems ci ON Item.ItemId = ci.ItemId AND ci.CatalogueId = <id>]
WHERE atval.Status < 2 AND Product.Status < 2 AND pr.Status < 2
  AND Product.ProductRangeId <> 999 AND Product.ProductRangeId <> 1000
ORDER BY Product.Product
```
*WHY:* Validates the swatch image of the **primary** attribute value (`attr.DisplayOrder = 1`) for each active product. `Status < 2` filters everywhere (product, range, attribute value). Product ranges `999` (SP Components) and `1000` are excluded. The optional catalogue join scopes validation to a catalogue's items. De‑duplicated in code via `arrayList.Contains(AttributeValueId)`.

**Q-IMG-005** — non‑cloud mode, product images (`ValidateImageThread.cs:99`)
```sql
SELECT pc.Name AS pc_name, Product.ProductId, Product.Name AS prod_name, Product.Product, Product.ImageFile
FROM Product
INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId
INNER JOIN ProductCategory pc ON pr.ProductCategoryID = pc.ProductCategoryId
[INNER JOIN Item ON Product.ProductId = Item.ProductId
 INNER JOIN CatalogueItems ci ON Item.ItemId = ci.ItemId AND ci.CatalogueId = <id>]
WHERE Product.Status < 2 AND pr.Status < 2
  AND Product.ProductRangeId <> 999 AND Product.ProductRangeId <> 1000
ORDER BY Product.Product
```
*WHY:* Standard product‑image validation set. Same active/range filters as Q‑IMG‑004; validates `Product.ImageFile`.

### CADMaintenance "Validate Product Images" — `CADMaintenance.cs:16982`

**Q-IMG-006** (`CADMaintenance.cs:17001`)
```sql
SELECT DISTINCT Product.ProductId, Product.Product, Product.ImageFile, pr.ProductCategoryId, Product.ProductCodeId
FROM Product INNER JOIN ProductRange pr ON Product.ProductRangeId = pr.ProductRangeId
[INNER JOIN Item ON Product.ProductId = Item.ProductId
 INNER JOIN CatalogueItems ci ON Item.ItemId = ci.ItemId AND ci.CatalogueId = <selectedCatalogueId>]
WHERE Product.Product LIKE '<prefix>%' AND Product.ImageFile NOT LIKE '%StemShell%'
ORDER BY Product.Product
```
*WHY:* Loads products matching an operator‑entered prefix (blank ⇒ whole selected catalogue via the Item/CatalogueItems join). `NOT LIKE '%StemShell%'` excludes a special image family that must not be auto‑renamed. Category id and product‑code id are needed for the file‑naming special cases (BR‑IMG‑040/041).

**Q-IMG-007..013** — after computing corrected paths, the handler rewrites references across every entity that can hold an `ImageFile` (`CADMaintenance.cs:17125-17155`), one `UPDATE` per entity per changed row:
```sql
UPDATE Product SET ImageFile = '<new>' WHERE ProductId = <id>
UPDATE AttributeValue SET ImageFile = '<new>' WHERE ImageFile = '<old>'
UPDATE OptionValue SET ImageFile = '<new>' WHERE ImageFile = '<old>'
UPDATE CatalogueProductCategories SET ImageFile = '<new>' WHERE ImageFile = '<old>'
UPDATE Catalogue SET ImageFile = '<new>' WHERE ImageFile = '<old>'
UPDATE ProductRange SET ImageFile = '<new>' WHERE ImageFile = '<old>'
UPDATE HandbookProducts SET AlternateImageFile = '<new>' WHERE AlternateImageFile = '<old>'
```
*WHY:* When a product image is physically moved/renamed to the canonical path, every table that referenced the old relative path is updated to keep references consistent. `AlternateImageFile` is the handbook‑specific override column.

> The full‑text of the CAD `Validate Attribute/Option Images`, `Validate Image File References`, and `Archive Legacy Product Images` handlers was not fully read; their SQL beyond the above is `UNKNOWN` and belongs primarily to module 11 (CAD Maintenance).

---

## 5. Data Model

| Column | Table | Meaning |
|---|---|---|
| `ImageFile` | Product | Primary product photo (relative path under a base, e.g. `Images\Products\<Product>.jpg`). |
| `WFImageFile` | Product | Wireframe image (validated/nulled by `ValidateImages`). |
| `DimImageFile` | Product | Dimension diagram image. |
| `ImageFile` | AttributeValue | Swatch/thumbnail for an attribute value. |
| `ImageFile` | OptionValue | Swatch/thumbnail for an option value (fabric/finish). |
| `ImageFile` | ProductRange | Range‑level image. |
| `ImageFile` | Catalogue | Catalogue tile image (cloud mode). |
| `ImageFile` | CatalogueProductCategories | Per‑catalogue category image. |
| `AlternateImageFile` | HandbookProducts | Handbook override image. |

**Base paths** — `Global.filePaths` (`Global.cs:13`), a `string[4]`:

| Index | Value | Notes |
|---|---|---|
| 0 | `C:\Projects\DPS\bin\` | Local dev/DPS bin. **Skipped at runtime** because it contains `C:\` (see BR‑IMG‑006). |
| 1 | `\\<PDMServer>\HMEURONET\PDM\` where `PDMServer = "wechip01v"` ⇒ `\\wechip01v\HMEURONET\PDM\` | The primary network image share. |
| 2 | `C:\Program Files\HermanMiller\EOS\` | EOS install. **Skipped at runtime** (contains `C:\`). |
| 3 | `http://www.hmeuronet.com/PDM/` | Public HTTP fallback. |

Related globals: `Global.defaultFilePathIndex = 1` (`Global.cs:21`), `Global.imageUnavailable` (declared `Global.cs:23`, **never assigned**), `Global.testMode = false` (`Global.cs:65`), `Global.InvalidId = -1`.

---

## 6. Business Rules

**Path resolution — `GetImage.GetImage`**

- **BR-IMG-001** — Default signature is `GetImage(imageFile, materialpath = "", safeload = true, noscale = false)`. Most callers pass only `imageFile`. (`GetImage.cs:108`)
- **BR-IMG-002** — When `materialpath == ""`, all backslashes are first stripped from `imageFile` (`imageFile.Replace("\\","")`). This is why callers may pass a "collapsed" token like `ImagesProducts` OR a real relative path — both are normalised. (`GetImage.cs:118-120`)
- **BR-IMG-003** — Token expansion: a fixed ordered set of `Replace` calls converts collapsed tokens back into real sub‑paths. The order matters (longer/more specific tokens first). Verified mappings (`GetImage.cs:127-148`):
  - `ImagesApplication` → `Images\Application\`
  - `ImagesAttributes` → `Images\Attributes\`
  - `ImagesDimensions` → `Images\Dimensions\`
  - `ImagesLogo` → `Images\Logo\`
  - `ImagesOptionsFabricsKnoll` → `Images\Options\Fabrics\Knoll\`
  - `ImagesOptionsFabrics` → `Images\Options\Fabrics\`
  - `ImagesOptionsFinishKnoll` → `Images\Options\Finish\Knoll\`
  - `ImagesOptionsFinishPellicle` → `Images\Options\Finish\Pellicle\`
  - `ImagesOptionsFinish` → `Images\Options\Finish\`
  - `ImagesOther` → `Images\Other\`
  - `ImagesProducts` → `Images\Products\`
  - `ImagesTemp` → `Images\Temp\`
  - `ImagesWireframes` → `Images\Wireframes\`
  - `ImagesUSProducts` → `Images\USProducts\`
  - `ImagesParts` → `Images\Parts\`
- **BR-IMG-004** — Candidate path is built as `Global.filePaths[i] + imageFile` for each base index `i`. (`GetImage.cs:157`)
- **BR-IMG-005** — If the current base starts with `"http"`, backslashes in the full candidate are converted to forward slashes (`text.Replace("\\","/")`). (`GetImage.cs:158-161`)
- **BR-IMG-006** — Any candidate whose text contains `"C:\"` is **skipped** unless `Global.testMode` is true: `if (!((text.IndexOf("C:\\") == -1) | Global.testMode)) continue;`. Because `testMode = false`, filePaths[0] and filePaths[2] (both under `C:\`) are effectively never used in production; resolution falls to the UNC share (index 1) then HTTP (index 3). (`GetImage.cs:172-175`)
- **BR-IMG-007** — For a non‑http base: if `File.Exists(text)`, the image is loaded via `SafeImageFromFile(text, noscale)` when `safeload` (default), else via `Image.FromFile(text)`; then `GC.Collect()` is called and the loop breaks with success. (`GetImage.cs:176-186`)
- **BR-IMG-008** — For an http base: `GetImageFromURL(text)` is called; if it returns non‑null, success and break. (`GetImage.cs:188-195`)
- **BR-IMG-009** — When `materialpath != ""` the candidate is overridden to `materialpath + imageFile` (the base‑path array is bypassed), and only the first iteration is used — the inner loop breaks once `i > 0` while `materialpath != ""`. This is the CAD/material‑library image lookup path. (`GetImage.cs:130`, `162-165`)
- **BR-IMG-010** — Fallback on total failure: `image = Global.imageUnavailable`. **Because `Global.imageUnavailable` is never assigned anywhere in the codebase, the fallback is always `null`.** Callers therefore receive `null` for an unresolved image and must null‑check. (`GetImage.cs:196-199`; `Global.cs:23`)
- **BR-IMG-011** — There is an outer `do … while (num2 <= 2)` re‑index loop guarded by `flag`, entered only if `Global.filePaths.Length` changed mid‑iteration (`num != Global.filePaths.Length && num2 == 1`). In normal operation the array length is constant, so this loop runs once. (`GetImage.cs:122-206`)
- **BR-IMG-012** — Exceptions are swallowed. "Out of memory" errors are silently ignored; any other exception pops a `MsgBox` dumping `filePaths.Length`, the loop index, and the exception (developer diagnostics leaking to end users). (`GetImage.cs:202-210`)

**Image scaling — `SafeImageFromFile`**

- **BR-IMG-020** — Loads via a `FileStream` + `new Bitmap(stream)` (avoids locking the source file the way `Image.FromFile` would). (`GetImage.cs:63-65`)
- **BR-IMG-021** — Target display width is **180 px**; a fixed aspect factor `num = 1.3` and reference height `160` are used. If `bitmap.Width != 180` and `!noscale`, the image is rescaled. (`GetImage.cs:62`, `66-90`)
- **BR-IMG-022** — Scaling picks the dominant ratio: `num2 = Width/180`, `num3 = Height*1.3/160`; if `num2 > num3 && Width > 180` it scales by width ratio, else by height ratio. Uses `InterpolationMode.HighQualityBilinear`. (`GetImage.cs:72-92`)
- **BR-IMG-023** — `noscale = true` bypasses all resizing and returns the image at native size. (`GetImage.cs:66`)
- **BR-IMG-024** — On any exception the error text is shown in a `MsgBox` and `null` is returned. (`GetImage.cs:98-104`)

**URL probe — `URLExists`**

- **BR-IMG-030** — `HttpWebRequest.Timeout = 100` ms — an extremely short timeout; slow/remote servers will frequently be reported unreachable. (`GetImage.cs:16`)
- **BR-IMG-031** — Returns `true` by default; only a `WebException` whose `.ToString()` is non‑empty sets the result to `false`. (Effectively any web exception ⇒ `false`; success or empty exception ⇒ `true`.) (`GetImage.cs:13-32`)

**Wireframe validation — `ValidateImages`**

- **BR-IMG-040** — No‑op guard: if `\\<PDMServer>\wwwroot\PDM\Images` does not exist, the method returns immediately (no network ⇒ skip). Note this uses the **`wwwroot`** share, not `HMEURONET`. (`ValidateImages.cs:14`)
- **BR-IMG-041** — Only `Product.WFImageFile` is checked (Q‑IMG‑001), against `\\<PDMServer>\wwwroot\PDM\<WFImageFile>`. (`ValidateImages.cs:37`)
- **BR-IMG-042** — Broken references are **silently auto‑nulled** (Q‑IMG‑002) — no confirmation, no report. This runs as part of DPS DB publish. (`ValidateImages.cs:47-53`)
- **BR-IMG-043** — Errors surface via `MsgBox`; connection always closed in `finally`. (`ValidateImages.cs:56-66`)

**Interactive validation — `ValidateImageThread`**

- **BR-IMG-050** — Two modes selected by the `_cloud` flag (set from whether the DataQuery title contains "EOS Cloud"): cloud mode validates catalogue + primary‑attribute images (Q‑IMG‑003/004); standard mode validates product images (Q‑IMG‑005). (`ValidateImageThread.cs:49`; `DataQuery.cs:2416-2418`)
- **BR-IMG-051** — Optional scope: `_catalogueId > 0` adds the Item/CatalogueItems join to restrict to a catalogue's items; `= 0` validates all active products/catalogues. (`ValidateImageThread.cs:56,71,101`)
- **BR-IMG-052** — Active filter everywhere: `Status < 2` on catalogue/product/range/attribute value. (`ValidateImageThread.cs`)
- **BR-IMG-053** — Product ranges `999` and `1000` are excluded from image validation. (`ValidateImageThread.cs:76,105`)
- **BR-IMG-054** — Existence check uses the **`HMEURONET`** share: `File.Exists("\\wechip01v\HMEURONET\PDM\" + ImageFile)`. (Contrast with `ValidateImages`, which uses `wwwroot`.) (`ValidateImageThread.cs:123`)
- **BR-IMG-055** — A reference is flagged as unresolved if the file is missing **OR** the path ends (case‑insensitively) with `"\na.jpg"` — i.e. `na.jpg` is treated as a "not‑available" placeholder, not a real image. (`ValidateImageThread.cs:123`)
- **BR-IMG-056** — Catalogue rows are stored as `-1 * CatalogueId` in the working list so they can be distinguished from product/attribute ids; catalogue rows carry the literal label `"<Catalogue Image>"`. (`ValidateImageThread.cs:62-64`)
- **BR-IMG-057** — Duplicate attribute values are skipped via `arrayList.Contains(AttributeValueId)` (each swatch validated once). (`ValidateImageThread.cs:85`)
- **BR-IMG-058** — Cancellable: the `terminate` flag (set true by DataQuery on close/cancel) breaks the loop; on terminate the method returns without reporting. (`ValidateImageThread.cs:120,146`; `DataQuery.cs:1301-1303`)
- **BR-IMG-059** — If any unresolved references are found, a `debug_form` lists them with a `"<count> missing / unresolved image(s) in total"` footer; if none, a `MsgBox` confirms "All active/The selected products/catalogues … have images assigned correctly". Progress is streamed via the `UpdateStatus` event ("(i of N)"). (`ValidateImageThread.cs:150-176`)

**Product‑image auto‑naming — CADMaintenance "Validate Product Images"**

- **BR-IMG-070** — Canonical product image path is `Images\Products\<sanitized-product>.jpg` under base `\\wechip01v\HMEURONET\PDM\`. (`CADMaintenance.cs:16999,17020`)
- **BR-IMG-071** — Product‑code sanitisation for the filename: trailing `/` removed; `/` → `-`; `.` → `-`; leading/trailing `-` trimmed. (`CADMaintenance.cs:17011-17017`)
- **BR-IMG-072** — Special case: if `ProductCategoryId == 615` **or** `ProductCodeId == 805` **or** `ProductCodeId == 1009` (and the code doesn't already end with `.`), the product code is truncated to everything up to and including the first `.`; filename becomes `Images\Products\<trunc>jpg`. (`CADMaintenance.cs:17022-17027`)
- **BR-IMG-073** — Special case: product codes starting `SFAB` / `SFSA` / `SFSB` containing `-` are truncated at the first `-` (fabric families share one image). (`CADMaintenance.cs:17028-17031`)
- **BR-IMG-074** — `Images\Temp\na.jpg` is the recognised placeholder; a product still pointing at it (and with no real file) is reported as missing. (`CADMaintenance.cs:17038`)
- **BR-IMG-075** — When the real file exists at a non‑canonical name, it is physically moved to the canonical name; if a file already occupies the canonical name it is first renamed to `<name>_prev[N].jpg` (N up to 5). IO failures are collected and reported. (`CADMaintenance.cs:17040-17095`)
- **BR-IMG-076** — After moves, all `ImageFile` references are rewritten (Q‑IMG‑007..013) and a per‑entity update count is reported. (`CADMaintenance.cs:17110-17170`)

**Placeholder / "na.jpg" handling (cross‑module, image‑related)**

- **BR-IMG-080** — The HTTP form of the placeholder is `http://www.hmeuronet.com/PDM/Images/Temp/na.jpg` (used by `ClippingsExport.cs:1153`). (`ClippingsExport.cs`)
- **BR-IMG-081** — Layout export strips the placeholder: `Replace("Images\Temp\na.jpg","")` (`ExportLayoutStyleThread.cs:173`). OFDA export compares against literal `"na.jpg"` (`OFDAExport.cs:4027`). ProductDescriptions treats an `openFileDialog` selection containing `na.jpg` as "no image chosen" (`ProductDescriptions.cs:9995`). These confirm `na.jpg` is the app‑wide "no image" sentinel.

---

## 7. Hidden Logic

- **HL-IMG-1** — `Global.imageUnavailable` is declared but never initialised, so the "unavailable" fallback silently yields `null` rather than a placeholder bitmap. Any assumption that `GetImage` always returns a drawable image is wrong. (`Global.cs:23`, `GetImage.cs:196`)
- **HL-IMG-2** — `filePaths[0]` and `filePaths[2]` are dead in production because of the `C:\` skip guard (BR‑IMG‑006); the only live sources are the UNC share (index 1) and the HTTP URL (index 3). `testMode = false` is compiled in.
- **HL-IMG-3** — Two different network shares are used for image existence checks: `ValidateImages` → `\\wechip01v\wwwroot\PDM\`, but `ValidateImageThread` and `GetImage`/CAD → `\\wechip01v\HMEURONET\PDM\`. A file present on one share but not the other will validate inconsistently. (`ValidateImages.cs:37` vs `ValidateImageThread.cs:123`)
- **HL-IMG-4** — The backslash‑stripping in BR‑IMG‑002 followed by token re‑expansion (BR‑IMG‑003) is an obscure encoding scheme: any `ImageFile` value must match one of the 15 hard‑coded tokens to expand correctly, otherwise the folder separators are simply removed and the path resolves incorrectly.
- **HL-IMG-5** — `URLExists` returning `true` on empty/no exception, combined with a 100 ms timeout, means it is optimistic and timing‑sensitive; it is not a reliable reachability test.
- **HL-IMG-6** — `debug_form` (a raw text window) is reused as the "validation report" UI; there is no structured results grid.

---

## 8. UI Behaviour

- `GetImage` is invoked synchronously on the UI thread for icons and thumbnails; a slow share or HTTP fallback (up to the WebClient default timeout) can block the UI.
- `ProductDescriptions` sets `PictureBox.Tag` to the resolved `ImageFile` and, on failure (null image), sets a tooltip `"Unable to load image: <path>"`. (`ProductDescriptions.cs:7941-7948`, `7963-7970`, `7985-7992`)
- Interactive validation (`ValidateImageThread`) runs on a background `Thread`, streaming `UpdateStatus` events ("(i of N)") to the DataQuery status label; results are shown in a modal `debug_form`. Cancelling sets `terminate = true`.
- `ValidateImages` runs silently during publish (no UI beyond error `MsgBox`).

---

## 9. Dependencies

- `Global` — `filePaths`, `defaultFilePathIndex`, `imageUnavailable`, `testMode`, `PDMServer`.
- `ConnectionFactory.CreateNewConnection(autoOpen)` — DB access for both validators.
- `System.Drawing` (`Bitmap`, `Graphics`, `InterpolationMode`), `System.Net` (`HttpWebRequest`, `WebClient`), `System.IO` (`File`, `Directory`, `FileStream`, `FileInfo`).
- `debug_form` — report window (module 24).
- Network shares `\\wechip01v\HMEURONET\PDM\` and `\\wechip01v\wwwroot\PDM\`; public host `www.hmeuronet.com`.
- Consumers: `MainMenu`, `ProductDescriptions`, `CADMaintenance`, `HandbookDesigner`, `FinancialMaintenance`, `PhysicalMaintenance`, `PriceMaintenance`, `SIFImport`, `UserAdmin`, `DataQuery`, `ExportDPSDB`.

---

## 10. Risks

- **SQL injection** — `ValidateImages` Q‑IMG‑002 concatenates `ProductId` (numeric, lower risk). CAD "Validate Product Images" concatenates the operator‑entered product **prefix** directly into a `LIKE` clause (Q‑IMG‑006) and rewrites `ImageFile` values (from disk paths) into `UPDATE … WHERE ImageFile = '<old>'` (Q‑IMG‑007..013) with no parameterisation — a filename containing a quote would break/inject.
- **Silent data mutation** — `ValidateImages` nulls `WFImageFile` with no confirmation or audit trail; a transient network hiccup that makes `File.Exists` fail could wipe valid references.
- **Null fallback** — `imageUnavailable` never being set means missing images propagate as `null`; any caller lacking a null check risks `NullReferenceException`.
- **Share inconsistency** — divergent `wwwroot` vs `HMEURONET` paths (HL‑IMG‑3) can cause false "missing" results and erroneous nulling.
- **UI blocking / short timeouts** — synchronous resolution plus the 100 ms `URLExists` timeout and HTTP fallback can freeze or misbehave on slow networks.
- **Developer diagnostics leakage** — raw exception dumps shown to end users (BR‑IMG‑012, BR‑IMG‑024).
- **Hard‑coded infrastructure** — server names, share names, folder tokens and the public URL are all compile‑time constants; any move requires a rebuild.
- **File moves during validation** — CAD "Validate Product Images" performs live file moves/renames on the production share as a side effect of a "validation" action (surprising, destructive if interrupted).
