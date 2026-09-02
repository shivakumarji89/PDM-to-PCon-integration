# OEX Export (EAIWS Plugin) 1.6.0

Source: https://docs.pcon-solutions.com/eaiws/plugins/oex/release/1.6.0/index.html
Category: pCon.configurator online Plugin – OEX Export (cat=105)
Updated: 23.04.2026

EAIWS plugin that generates OEX (OFML Business Data Exchange) exports — XML-based order/quote documents, optionally with embedded OBX and PDF.

Base URL: `http://<eaiws-server>/EAIWS/plugins/oex/`
Example: `https://s1.eaiws.pcon-solutions.com/4.18.2-001/EAIWS/plugins/oex/export`

---

## API Endpoints

### GET `/config.json` — Default OEX Config

Returns the default OEX configuration to use with the export endpoint.

#### Key Config Fields

| Field | Type | Default | Notes |
|---|---|---|---|
| `documentType` | string | `"ORDERS"` | `"ORDERS"` or `"QUOTES"` |
| `oexVersion` | string | `"3.0"` | `"3.1"`, `"3.0"`, or `"2.3"` |
| `attachOBX` | boolean | `true` | Attach OBX file to archive |
| `attachOEX` | boolean | `true` | Attach OEX XML to archive |
| `attachPDF` | boolean | `false` | Attach PDF report to archive |
| `calculationPurchase` | boolean | `true` | Include purchase calculation |
| `calculationSales` | boolean | `true` | Include sales calculation |
| `exportAlternativeArticles` | boolean | `true` | Include alternative articles |
| `exportFolders` | boolean | `true` | Include folder structure |
| `exportImages` | boolean | `false` | Embed images as Base64 in OEX |
| `exportInvisibleFeatures` | boolean | `true` | Include invisible features |
| `exportRoomInformation` | boolean | `true` | Include room information |
| `exportSetArticle` | boolean | `true` | Include set articles |
| `exportTextArticles` | boolean | `true` | Include text articles |
| `featureInARTL` | boolean | `false` | Export features in ARTL node |
| `hideDiscounts` | boolean | `false` | Hide all discounts |
| `splitDocumentByManufacturers` | boolean | `false` | Split document per manufacturer (requires `manufacturerId`) |
| `structuralInformation` | boolean | `true` | Include structural information |
| `manufacturerIds` | string[] | `[]` | Filter by manufacturer IDs |
| `addresses` | AddressData[] | `[]` | Address overrides (see below) |

#### AddressData Object

```typescript
{
  addressType: "SoldTo" | "ShipTo" | "BillTo" | "Payer" | "Carrier" | "Supplier"
             | "EndUser" | "InstallationCompany" | "InstallationLocation"
             | "Branch" | "InCharge";
  addressNumber?: string;
  addressId?: string;
  title?: string;
  name1?: string;
  name2?: string;
  name3?: string;
  name4?: string;
  street?: string;
  street2?: string;
  countryCode?: string;
  postalCode?: string;
  location?: string;
  district?: string;
  regionCode?: string;
  poBox?: string;
  taxCode?: string;
  taxCodeEU?: string;
  taxCodeUSA?: string;
  commAddresses?: CommAddress[];
  contacts?: ContactData[];
}
```

> **Note:** Addresses without a valid OEX address type are excluded from the export (e.g. `InCharge` type is not exported).

#### CommAddress Object
```typescript
{ value: string; type: "Phone" | "Fax" | "Mobile" | "WWW" | "EMail"; scope: "Business" | "Private"; }
```

#### ContactData Object
```typescript
{
  contactNumber?: string; title?: string; firstName?: string; lastName?: string;
  commAddresses?: CommAddress[];
  id: number;
  contactType?: "Sale" | "Warehouse" | "Installer" | "Support" | "Employee" | "Client";
}
```

---

### POST `/export` — Generate OEX

Generates OEX export. May include OBX, PDF etc. depending on config.

#### Request Body (application/json)

| Field | Type | Default | Description |
|---|---|---|---|
| `sessionId` | string (uuid) | **required** | UUID of the current session |
| `calculationScheme` | string | `"STDB2B_WBK"` | Price calculation scheme |
| `preferredImageColumn` | string | `"73bd68f4-..."` | UUID of user-defined image column |
| `imageOptions` | string[] | — | Override image generation params (use sparingly — defaults use cached images) |
| `config` | object | — | OEX config (see `/config.json` above) |

#### Request Sample
```json
{
  "sessionId": "7c57526d-d1ea-406d-8b87-f61b7263788c",
  "calculationScheme": "STDB2B_WBK",
  "config": {
    "documentType": "QUOTES",
    "oexVersion": "3.1",
    "exportImages": true,
    "attachOBX": true,
    "attachOEX": true,
    "exportFolders": true,
    "attachPDF": true
  }
}
```

#### Response (200)
```json
{
  "archive": { "name": "oex-orders_v3-0_..._20260116-102327.zip", "url": "https://..." },
  "oex":     { "name": "oex-orders_v3-0_....xml", "url": "https://..." },
  "obx":     { "name": "oex-orders_v3-0_....obx", "url": "https://..." },
  "pdf":     { "name": "oex-orders_v3-0_....pdf", "url": "https://..." },
  "items":   ["uuid1", "uuid2", "..."],
  "name":    "oex-orders_v3-0_...",
  "errors":  []
}
```

#### Response Codes
| Code | Meaning |
|---|---|
| 200 | Success |
| 400 | `request-bad-request` – Invalid request parameters |
| 422 | Session not found |
| 500 | Internal error |

---

### POST `/manufacturers.json` — List of Manufacturers

Returns the manufacturers included in the OEX for the current project. Use to filter which manufacturers are exported.

#### Request Body
```json
{ "sessionId": "7c57526d-d1ea-406d-8b87-f61b7263788c" }
```

#### Response (200)
```json
[
  { "manufacturerId": "AM", "manufacturerName": "ASSMANN BÜROMÖBEL GMBH & CO. KG" },
  { "manufacturerId": "GS", "manufacturerName": "Sedus office furniture" }
]
```

---

## OEX Version Behaviour Notes

| Version | OBX Handling |
|---|---|
| `2.3` / `3.0` | OBX attached as separate file in archive |
| `3.1` | OBX embedded inline per article in OEX XML; `attachOBX` embeds instead of attaching |

- OEX 3.1: article OBX references do not contain pricing; quantity always set to 1
- OEX 3.1: user descriptions removed from embedded OBX
- Filename pattern includes OEX version: e.g. `oex-orders_v3-1_...`
- Articles with negative quantity are excluded from export
- User texts not exported for `ORDERS` type exports

---

## Changelog

### 1.6.0 – 23.04.2026
- Updated to EAIWS 4.19 and latest `commons-exports`
- Fixed Pseudo-Articles causing export failures
- Fixed calculation error in `compact` view for Pseudo-Articles
- Added statistics event for OEX export
- Invalid address fields excluded instead of dropping entire address
- User articles now contain OBX reference when exported via OEX 3.1 with `attachOBX`

### 1.5.0 – 16.10.2025
- Added `fileStoragePath` to plugin config
- Updated to Java 21
- Removed user descriptions from embedded OBX in OEX 3.1
- `itmOrgData` of type `POS` always exports original article list position
- Added `TTNE` (Tax Net Total) as reference for `TTAX` line
- Added `aTaxCode` and `aCondRef` attributes to `TTAX` line

### 1.4.0 – 22.04.2025
- OEX 3.1: `docCalculationChanges` node removed from item OBX
- OEX 3.1: quantity node never included in OBX
- Article OBX references no longer export pricing; quantity = 1
- Added `SNEH`/`TNEH` `itmPricing` values (net value after header discounts)
- User texts no longer exported for `ORDERS` exports

### 1.3.0 – 15.10.2024
- OEX 3.1: OBX now embedded inline per article (no longer separate file)
- Filename now includes OEX version separated with `-` (e.g. `v3-1`)
- Fixed `TopLevelNumber` missing when view filtered one item in hierarchy
- Always exports quote number from header as `hdrDocNo` of type `QUO`

### 1.2.0 – 17.05.2024
- `vVendorArticleNo` always set to BASE article number
- Added `commission`, `additionalAgreement`, `dispatchNotes` to OEXConfig
- Excluded articles with negative quantity
- Addresses without OEX address type no longer exported

### 1.1.0 – 17.10.2023
- Added OEX 3.1 export
- Added `TNET` for purchase calculation
- Added `pdfLogoImage` to OEXConfig for standard-order report logo
- `attachOBX` now supported in config

### 1.0.0 – 26.05.2023
- Initial release; OEX versions 2.3, 3.0, 3.1 supported
