# Spreadsheet Export (EAIWS Plugin) 1.6.0

Source: https://docs.pcon-solutions.com/eaiws/plugins/spreadsheet/1.6.0/index.html
Category: pCon.configurator online Plugin – Spreadsheet Export (cat=104)
Updated: 23.04.2026

EAIWS plugin that generates Excel (.xlsx) and CSV exports from a basket/configurator session.

Base URL: `http://<eaiws-server>/EAIWS/plugins/excel/`
Example: `https://s1.eaiws.pcon-solutions.com/4.18.2-001/EAIWS/plugins/excel/v1/export`

---

## API Endpoints

### Errors

Two categories:
- **Aborted** – returns HTTP error code + JSON or text body
- **Suppressed** – appended to a successful (200) response

Aborted error example:
```json
{
  "additionalInformation": {},
  "cause": [],
  "code": 422,
  "id": "request-session-not-found",
  "message": "No active session was found for the specified session id.",
  "scopes": [],
  "type": "request"
}
```

Suppressed error example (inside response body):
```json
{
  "errors": [
    {
      "additionalInformation": {},
      "cause": ["Some exception..."],
      "id": "item-text-error",
      "message": "Failed to get item app data!",
      "scopes": ["ERROR"],
      "type": "item"
    }
  ],
  "name": "somecustomname.xlsx",
  "url": "https://..."
}
```

---

### POST `/v1/export` — Project Excel Export

Generates an Excel project workbook (.xlsx).

#### Request Body (application/json)

| Field | Type | Default | Description |
|---|---|---|---|
| `sessionId` | string (uuid) | **required** | UUID of the current session |
| `calculationScheme` | string | `"STDB2B_WBK"` | Price calculation scheme |
| `preferredImageColumn` | string | `"73bd68f4-da62-11d8-b9d6-00e081513ada"` | UUID of user-defined image column |
| `externalRefColumn` | string | — | UUID of basket column containing external reference number |
| `sheetSettings` | object | — | Starting points: `articleStartRow`, `articleStartColumn`, `calcStartRow`, `calcStartColumn`, `reportStartRow`, `reportStartColumn` |
| `items` | string[] | — | Selected article UUIDs (filter) |
| `matchBasketItemIds` | boolean | `false` | Match against basket item IDs instead of view item IDs |
| `viewId` | string | — | UUID of the view to use |
| `imageOptions` | string[] | — | Override default image generation parameters |
| `filename` | string | — | Custom filename (e.g. `somecustomname.xlsx`) |
| `hideMargins` | boolean | `false` | Hide margin calculation |
| `hideTaxes` | boolean | `false` | Hide tax calculation |
| `hideDiscounts` | boolean | `false` | Hide all discounts |
| `hideHeaderDiscounts` | boolean | `false` | Hide header discounts |
| `hidePurchaseDiscounts` | boolean | `false` | Hide purchase discounts |
| `hideSalesDiscounts` | boolean | `false` | Hide sales discounts |
| `hideFinalTotal` | boolean | `false` | Hide final total |
| `showVariantText` | boolean | `false` | Show variant text in Report Sheet |
| `hideLineTags` | string[] | — | Hide calculation lines matching any of these tags |
| `hideConditionTypes` | string[] | — | Hide calculation lines matching any of these condition types |
| `hideAccessMethods` | string[] | — | Hide calculation lines matching any of these access methods |

#### Request Sample
```json
{
  "sessionId": "39d105c0-5254-4860-9865-935aba7cc78a",
  "calculationScheme": "STDB2B_WBK",
  "preferredImageColumn": "cc080d73-88f4-4bfc-8ec1-e7e2ad30739a",
  "externalRefColumn": "c962203c-7e83-4a2f-8060-acaa4a06c921",
  "sheetSettings": {
    "articleStartRow": 1,
    "articleStartColumn": 2,
    "calcStartRow": 2,
    "calcStartColumn": 1,
    "reportStartRow": 3,
    "reportStartColumn": 3
  },
  "filename": "somecustomname.xlsx"
}
```

#### Response (200)
```json
{
  "url": "https://.../somecustomname.xlsx",
  "name": "somecustomname.xlsx",
  "errors": []
}
```

#### Response Codes
| Code | Meaning |
|---|---|
| 200 | Success |
| 400 | `request-bad-request` – Invalid sessionId |
| 422 | Session or view not found |
| 500 | Internal error |

---

### POST `/v1/export/manufacturers` — Management Excel Export

Generates an Excel management workbook per manufacturer.

#### Request Body (application/json)

| Field | Type | Default | Description |
|---|---|---|---|
| `sessionId` | string (uuid) | **required** | UUID of the current session |
| `calculationScheme` | string | `"STDB2B_WBK"` | Price calculation scheme |
| `items` | string[] | — | Selected article UUIDs (filter) |
| `matchBasketItemIds` | boolean | `false` | Match against basket item IDs |
| `viewId` | string | — | UUID of the view |
| `filename` | string | — | Custom filename |

#### Request Sample
```json
{
  "sessionId": "62afce0a-6304-4484-8f52-780c4ae28b3e",
  "calculationScheme": "STDB2B_WBK",
  "viewId": "f6a20aef-8fe4-4fcd-9854-8701b792563f",
  "filename": "somecustomname.xlsx"
}
```

---

### POST `/v1/exportCSV` — CSV Project Export

Generates Excel workbook and exports as ZIP containing:
- `Article_List.csv`
- `Calculation_Scheme.csv`
- `Header_Calculation.csv`
- `Header_Data.csv`

Same request body as `/v1/export`. Response URL points to a `.zip` file.

---

### POST `/v1/exportCSV/articlelist` — CSV Article List Export

Generates article list sheet as a single `.csv` file.

Same request body as `/v1/export`.

---

### POST `/v1/exportCSV/header/calculation` — CSV Header Calculation Export

Generates header calculation sheet as a single `.csv` file.

---

### POST `/v1/exportCSV/header/data` — CSV Header Data Export

Generates header data sheet as a single `.csv` file.

---

## Changelog

### 1.6.0 – 23.04.2026
- Updated translations; updated to EAIWS 4.19
- Fixed alternative set article parts being included in calculation in temp projects
- Fixed Set Article parts marked as alternative not flagged correctly in flat list view
- Internal flags now read from view instead of basket
- Net value for Pseudo Article Items greyed out in Report Sheet
- Added `Net value for item` subtotal for Pseudo Articles
- Added `Rounding Off` calculation lines to report sheet
- Fixed Pseudo-Articles causing certain exports to fail
- Fixed calculation error in `compact` view for Pseudo-Articles
- Added statistics events for excel & CSV exports
- Removed redundant `debug.json` request

### 1.5.1 – 27.10.2025
- Updated Polish translations

### 1.5.0 – 16.10.2025
- Added calculation level & counter to headers as prefix
- Added Calculation Scheme excel sheet to article list workbook and CSV archive
- Added article number column to management excel sheet
- Fixed margin value/percentage being switched in Management Export
- Language files converted from Latin-1 to UTF-8
- Updated to Java 21

### 1.4.0 – 22.04.2025
- Fixed Set-Article parts incorrectly removed in `commons-exports` API
- Added Manufacturer Overview excel workbook as new export
- Accounting format: negative sign no longer aligned to left cell border
- Updated to EAIWS 4.17beta1

### 1.3.0 – 15.10.2024
- Improved performance of large exports with images using multithreading
- Fixed export fail with multiple VAT calculation lines
- Added `showVariantText` option
- Added special condition for `NET_VALUE_ECO` in header calculation sheet

### 1.2.0 – 17.05.2024
- Added individual CSV exports for article list, header calculation, header data
- Added `Currency` columns for all pricing procedures of type Money
- Added `Price Date` column to article list sheet
- Added CSV export; ISO 8601 date format in CSV
- Changed article list sheet to be static instead of dynamic
- Variant prices exported together in a single column

### 1.1.0 – 17.10.2023
- Added `hideLineTags`, `hideConditionTypes`, `hideAccessMethods` options

### 1.0.0 – 26.05.2023
- Initial release
