## BR-PVAL — Property Values → [doc](../../08_Property_Values.md)

| Rule ID | Short description | Related methods | Related SQL | Related tables | Source doc |
|---|---|---|---|---|---|
| BR-PVAL-003 | Each DTO serializes to exactly one CSV row via `getAllProperties()`, fields `;`-joined in fixed order. | `getAllProperties()` | — | — (DTO) | [08_Property_Values](../../08_Property_Values.md) |
| BR-PVAL-004 | The CSV filename is the DTO's `fileName` (`ocd_propertyclass`/`ocd_property`/`ocd_propertyvalue`), `.csv` appended. | writer loop / `fileName` | — | — (CSV) | [08_Property_Values](../../08_Property_Values.md) |
| BR-PVAL-005 | DTOs do no validation/persistence; all logic is in the `OCDExport` build loop; blank rows skipped. | `OCDExport` build loop | — | — | [08_Property_Values](../../08_Property_Values.md) |
| BR-PVAL-006 | Text/description references are 1-based indices into the description arrays, not inline text. | `addDescription()` | — | — (propertytext/propvaluetext CSV) | [08_Property_Values](../../08_Property_Values.md) |
| BR-PVAL-007 | A property class is emitted once per unique key (`Contains` guard); key = `<article>\|<pos>\|<name>\|\|<rel>`. | `_propertyClassData.Contains` guard | — | — | [08_Property_Values](../../08_Property_Values.md) |
| BR-PVAL-008 | Class `position` increments only when the class key changes from the previous row. | `OCDExport` build loop | — | — | [08_Property_Values](../../08_Property_Values.md) |
| BR-PVAL-009 | Class naming = `<series>_CLS_` + range/category + fabric/option suffixes, with per-item overrides. | `OCDExport` class-naming block | — | ProductRange, ProductCategory | [08_Property_Values](../../08_Property_Values.md) |
| BR-PVAL-010 | Only rows with `Status = 1` are processed for property values. | `OCDExport` build loop | Q-PVAL-001 | OptionValue | [08_Property_Values](../../08_Property_Values.md) |
| BR-PVAL-011 | Rows whose `OrderCodeValue2` contains `#` are ignored entirely. | `OCDExport` build loop | Q-PVAL-001 | — | [08_Property_Values](../../08_Property_Values.md) |
| BR-PVAL-012 | Property description: EN from `Option2`, DE (LanguageId 5), NL (LanguageId 9). | `addDescription()` | Q-PVAL-002 | Option, OtherDescription | [08_Property_Values](../../08_Property_Values.md) |
| BR-PVAL-013 | Property length defaults to `OrderCodeValue2.Length`, overridden by `Option.SLFeatureLength`. | `OCDExport` build loop | Q-PVAL-003 | Option | [08_Property_Values](../../08_Property_Values.md) |
| BR-PVAL-014 | Length hard-overrides: `5` for `FABRICCOLOUR`; `11` for `SAYLVISCHR_SB_U`. | `OCDExport` build loop | Q-PVAL-003 | — | [08_Property_Values](../../08_Property_Values.md) |
| BR-PVAL-015 | Value description = `optval_name + " - " + OrderCodeValue2` (EN), DE/NL from Q-PVAL-004. | `addDescription()` | Q-PVAL-004 | OptionValue, OtherDescription | [08_Property_Values](../../08_Property_Values.md) |
| BR-PVAL-016 | First pass computes distinct non-fabric option count and max `IsFabric` for class naming. | `OCDExport` count pass | Q-PVAL-001 | — | [08_Property_Values](../../08_Property_Values.md) |
| BR-PVAL-017 | Hardcoded value `"C7"` is excluded from property-value emission (rationale UNKNOWN). | `OCDExport` build loop | Q-PVAL-001 | — | [08_Property_Values](../../08_Property_Values.md) |
| BR-PVAL-018 | A value is added only if its `OptionValueId` is in the allowed set (source UNKNOWN in excerpt). | `OCDExport` build loop | Q-PVAL-001 | — | [08_Property_Values](../../08_Property_Values.md) |
| BR-PVAL-019 | Property `position` = `num14*10 + num18`, bumped for specific property-name substrings to force gaps. | `OCDExport` build loop | — | — | [08_Property_Values](../../08_Property_Values.md) |
| BR-PVAL-020 | Post-loop, `ocdPropertyValue.relObjID` is rewritten from `valueFrom` fabric prefixes (`8M25→+3` … `8M24→+8`). | relObjID post-processing | — | — | [08_Property_Values](../../08_Property_Values.md) |
| BR-PVAL-021 | Properties de-duplicated via `_propertyData.Contains(key)` (composite class\|prop\|position\|…). | `_propertyData.Contains` guard | — | — | [08_Property_Values](../../08_Property_Values.md) |
| BR-PVAL-022 | With `_newformat`, each property also generates OFML `SPECIFIED`/`COL_` relation lines. | `OCDExport` build loop | — | — | [08_Property_Values](../../08_Property_Values.md) |
| BR-PVAL-023 | `valueFrom` = `OrderCodeValue2` with spaces→underscores; `opFrom="EQ"`; opTo/valueTo empty. | `OCDExport` build loop | Q-PVAL-001 | — | [08_Property_Values](../../08_Property_Values.md) |
| BR-PVAL-024 | Value `position` is a running counter per (class\|prop) key. | `OCDExport` build loop | — | — | [08_Property_Values](../../08_Property_Values.md) |
| BR-PVAL-025 | `isDefault = 1` for the first value of a newly-encountered option, else 0. | `OCDExport` build loop | Q-PVAL-001 | — | [08_Property_Values](../../08_Property_Values.md) |
| BR-PVAL-026 | Values de-duplicated via `_propertyValueData.Contains(key)`. | `_propertyValueData.Contains` guard | — | — | [08_Property_Values](../../08_Property_Values.md) |
| BR-PVAL-027 | `relObjID = "9999"` when article starts `MQ`/`MR` and `OrderCodeValue2` starts `7Q`. | `OCDExport` build loop | Q-PVAL-001 | — | [08_Property_Values](../../08_Property_Values.md) |
| BR-PVAL-028 | For `UPHB_FABRIC` classes, values not starting `8M` are suppressed. | `OCDExport` build loop | Q-PVAL-001 | — | [08_Property_Values](../../08_Property_Values.md) |
| BR-PVAL-029 | For `_FS` classes, `valueFrom` in {1A701,1A703} sets `relObjID = num58 + 12`. | relObjID post-processing | — | — | [08_Property_Values](../../08_Property_Values.md) |
| BR-PVAL-030 | For `_AS` classes, `valueFrom` in {1A701..1A708} sets `relObjID = num58 + 11`. | relObjID post-processing | — | — | [08_Property_Values](../../08_Property_Values.md) |
| BR-PVAL-031 | A synthetic `LEADTIME` property class is appended per article, de-dup-guarded. | `OCDExport` LEADTIME block | — | — | [08_Property_Values](../../08_Property_Values.md) |
| BR-PVAL-032 | LEADTIME class gets fixed `ARTICLECODE` (C/80) and `LEADTIME` (C/2, restrictable) properties. | `OCDExport` LEADTIME block | — | — | [08_Property_Values](../../08_Property_Values.md) |
| BR-PVAL-033 | One value per distinct lead-time; position `= floor(firstDigit/2)+1`; desc `<n> days/Tage/Dagen`. | `OCDExport` LEADTIME block | — | — | [08_Property_Values](../../08_Property_Values.md) |
| BR-PVAL-034 | The non-`_newformat` branch emits a single `<leadtime>_DAY` class with one value. | `OCDExport` LEADTIME block | — | — | [08_Property_Values](../../08_Property_Values.md) |
| BR-PVAL-035 | Property values inherit option ordering from `PDMOptionDataReport`; CSV order = insertion order. | `OCDExport` build loop | Q-PVAL-001 | — | [08_Property_Values](../../08_Property_Values.md) |

## BR-OPT — Options → [doc](../../09_Options.md)

| Rule ID | Short description | Related methods | Related SQL | Related tables | Source doc |
|---|---|---|---|---|---|
| BR-OPT-001 | An Option is the `[Option]` row; its values are `OptionValue` (joined via `PDMOptionDataReport`). | — | Q-OPT-001, Q-OPT-015 | [Option], OptionValue | [09_Options](../../09_Options.md) |
| BR-OPT-002 | `IsFabric`: `1` = fabric type, `2` = fabric colour (sub-option of type), else normal. | `CreateOpt` | Q-OPT-001 | [Option] | [09_Options](../../09_Options.md) |
| BR-OPT-003 | Fabric-colour rows start a new option group when the order code leaves the current fabric prefix. | `CreateOpt` | Q-OPT-001 | [Option], OptionValue | [09_Options](../../09_Options.md) |
| BR-OPT-004 | Fabric-type rows build a synthetic sub-option ref `<code w/o '#'>_0` padded to 10 with `0`. | `CreateOpt` | — | OptionValue | [09_Options](../../09_Options.md) |
| BR-OPT-005 | With a `ParentOptValId`, the exporter substitutes the parent's sub-option ref and may rename to `<prefix>_Colors`. | `CreateOpt` | Q-OPT-001 | OptionValue, DependentOptionValues | [09_Options](../../09_Options.md) |
| BR-OPT-006 | Option name `"Fabric type"` is renamed to `"Fabric"` on `.opt` output. | `OutputOpt` | — | — | [09_Options](../../09_Options.md) |
| BR-OPT-007 | `.opt` order codes have all `#` characters stripped. | `OutputOpt` | — | — | [09_Options](../../09_Options.md) |
| BR-OPT-008 | An option emits for an item only if ≥1 value is in the catalogue and `Status = 1`. | `CreateOpt` | Q-OPT-001 | CatalogueOptionValues, OptionValue | [09_Options](../../09_Options.md) |
| BR-OPT-009 | On SIF import, a new fabric-type option whose name contains "kvadrat" gets `SupplierId = 2`. | `createOption` | Q-OPT-011 | [Option] | [09_Options](../../09_Options.md) |
| BR-OPT-010 | In OFDA, colour (28) without type (8) back-fills the parent option/value from `[Option]`+`OptionValue`. | OFDA back-fill | Q-OPT-015 | [Option], OptionValue | [09_Options](../../09_Options.md) |
| BR-OPT-011 | OFDA injects a master-template default value (`OrderCodeValue = '<MT>'`) for the category. | OFDA back-fill | Q-OPT-015 | [Option], OptionValue | [09_Options](../../09_Options.md) |
| BR-OPT-012 | New `OrderCodeFormatKey`: non-empty, ≤6 chars, `{…}`, uppercased, unique in category. | Set Order Code Format Key handler | Q-OPT-006 | [Option], Attribute | [09_Options](../../09_Options.md) |
| BR-OPT-013 | Changing an option's key cascades a `Replace` across every embedding `ProductRange.OrderCodeFormatString`, audited. | Set Order Code Format Key handler | Q-OPT-007, Q-OPT-010 | [Option], ProductRange, PDMAudit.dbo.Transactions | [09_Options](../../09_Options.md) |
| BR-OPT-014 | `EOSLiteDisplayOrder`/`SLFeatureLength` must be positive integers (char-by-char check). | context-menu handlers | Q-OPT-004, Q-OPT-005 | [Option] | [09_Options](../../09_Options.md) |
| BR-OPT-015 | `HideByDefault` update applies only when the existing value is `≤ 9`. | CAD Hide By Default handler | Q-OPT-008 | [Option] | [09_Options](../../09_Options.md) |
| BR-OPT-016 | CAD path stores `EOSLiteDisplayOrder` negated; ProductDescriptions stores it raw (inconsistency). | CAD / ProductDescriptions handlers | Q-OPT-009, Q-OPT-004 | [Option] | [09_Options](../../09_Options.md) |
| BR-OPT-017 | Temp table exposes `TertiayOption` (misspelled) while OFDA reads `TertiaryOption` (proc column UNKNOWN). | SyteLine grouping | Q-OPT-014 | #temptable (PDMOptionDataReport) | [09_Options](../../09_Options.md) |
| BR-OPT-018 | SIF import appends the key token to `OrderCodeFormatString` only if not already present. | SIF import post-insert block | Q-OPT-012 | ProductRange | [09_Options](../../09_Options.md) |
| BR-OPT-019 | Post-insert identity is recovered by re-selecting the full column set (no `SCOPE_IDENTITY`). | `createOption` | Q-OPT-011 | [Option] | [09_Options](../../09_Options.md) |
| BR-OPT-020 | Options are grouped/sorted by `OptionId` runs via `SortClasses` (contiguous per OptId). | `SortClasses` | — | — | [09_Options](../../09_Options.md) |
| BR-OPT-021 | `CheckDependents` chains dependency PO links between adjacent option classes. | `CheckDependents` | — | — | [09_Options](../../09_Options.md) |
| BR-OPT-022 | `CheckDuplicate` treats classes as duplicates by same OptId, DependPOs count, and value-id superset. | `CheckDuplicate` | — | — | [09_Options](../../09_Options.md) |
| BR-OPT-023 | Global de-dup also requires matching `IncPrices` per value and matching has-dependency state. | `ProcessGlobal`/`CheckGlobalDuplicate` | — | — | [09_Options](../../09_Options.md) |
| BR-OPT-024 | `CreateDependent` uses a globally incremented PO and recurses only when rows exist. | `CreateDependent` | Q-OPT-013 | DependentOptionValues, OptionValue, CatalogueOptionValues | [09_Options](../../09_Options.md) |
| BR-OPT-025 | `IncPrice = -1` = "no increment" → `O1=0.00`; else 2dp with `.00` suffix appended. | `OutputOpt` | Q-OPT-002 | — | [09_Options](../../09_Options.md) |
| BR-OPT-026 | With `_catalogueLeadTime == 99`, an `@` prefix is prepended to option/product descriptions. | `OutputOpt`/`RunKeyOpt` | — | — | [09_Options](../../09_Options.md) |
| BR-OPT-027 | Lead-time lines `O4`/`O5` (and `P4`/`P5`) are always `<_catalogueLeadTime>.00`. | `OutputOpt` | — | — | [09_Options](../../09_Options.md) |
| BR-OPT-028 | Every catalogue-affecting option UPDATE writes a `PDMAudit.dbo.Transactions` row. | maintenance handlers | Q-OPT-010 | PDMAudit.dbo.Transactions | [09_Options](../../09_Options.md) |
| BR-OPT-029 | Fabric type/colour option ids accumulate into `fabricTypeOptionIds`/`fabricColourOptionIds`, de-duped. | OFDA report read | Q-OPT-001 | [Option] | [09_Options](../../09_Options.md) |
| BR-OPT-030 | `Option2` display name and parent-option context (`ParentOptId/Name/DescId`) are captured; empty parent → `-1`. | `CreateOpt`/`OptionData` fill | Q-OPT-001 | [Option] | [09_Options](../../09_Options.md) |

## BR-OVAL — Option Values → [doc](../../10_Option_Values.md)

| Rule ID | Short description | Related methods | Related SQL | Related tables | Source doc |
|---|---|---|---|---|---|
| BR-OVAL-001 | An OptionValue belongs to one Option via `OptionId`; read through `PDMOptionDataReport`. | OFDA report read | Q-OVAL-001 | OptionValue, [Option] | [10_Option_Values](../../10_Option_Values.md) |
| BR-OVAL-002 | `Status` is 4-state: `0=URL, 1=ACT, 2=OBS, 3=HLD`, set from context-menu labels. | status context-menu handler | Q-OVAL-003 | OptionValue | [10_Option_Values](../../10_Option_Values.md) |
| BR-OVAL-003 | Only `Status = 1` values present in `_catalogueOptionValues` are exported to `.opt`. | `CreateOpt` | Q-OVAL-001 | OptionValue, CatalogueOptionValues | [10_Option_Values](../../10_Option_Values.md) |
| BR-OVAL-004 | New option values default to `Status = 1` on creation. | create-value handlers | Q-OVAL-010, Q-OVAL-012 | OptionValue | [10_Option_Values](../../10_Option_Values.md) |
| BR-OVAL-005 | Value creation is idempotent on `(OrderCodeValue, OptionId)`; existing rows reused. | create-value handlers | Q-OVAL-010, Q-OVAL-012 | OptionValue | [10_Option_Values](../../10_Option_Values.md) |
| BR-OVAL-006 | On creation, an `OtherDescription` row (`RelatedTable='OptionValue'`, lang 1, max+1 id) is inserted first. | `createOtherDescription` | Q-OVAL-010 | OtherDescription | [10_Option_Values](../../10_Option_Values.md) |
| BR-OVAL-007 | Fabric image path = `Images\Options\Fabrics\<code>.jpg`, except Knoll ids 8513/8525/8625 (`…\Knoll\`). | Add New Data build | Q-OVAL-010 | OptionValue | [10_Option_Values](../../10_Option_Values.md) |
| BR-OVAL-008 | Fabric `CADMaterial` is synthesised as `S_T150_<code>.gm`. | Add New Data build | Q-OVAL-010 | OptionValue | [10_Option_Values](../../10_Option_Values.md) |
| BR-OVAL-009 | `OrderCodeValue` may carry a trailing `#`; stripped on export; fabric-type stored with `#`. | `OutputOpt` / code build | Q-OVAL-010 | OptionValue | [10_Option_Values](../../10_Option_Values.md) |
| BR-OVAL-010 | An embedded `{…}` format token is stripped before storing the code. | SIF import code parse | Q-OVAL-012 | OptionValue | [10_Option_Values](../../10_Option_Values.md) |
| BR-OVAL-011 | `ExcludeFromFabricIndex` is a toggle (`CASE WHEN =1 THEN 0 ELSE 1`). | Exclude-from-fabric-index handler | Q-OVAL-004 | OptionValue | [10_Option_Values](../../10_Option_Values.md) |
| BR-OVAL-012 | Clearing composition writes `NULL`; a non-blank edit writes the three fabric fields together. | Composition/Application/Standards handler | Q-OVAL-005 | OptionValue | [10_Option_Values](../../10_Option_Values.md) |
| BR-OVAL-013 | `ExcludeFromValidation` is set by `OptionId` (affects all values), unlike per-value flags. | Price Maintenance handler | Q-OVAL-009 | OptionValue | [10_Option_Values](../../10_Option_Values.md) |
| BR-OVAL-014 | Incremental prices upsert per `(ItemId, OptionValueId)` in `ItemOptionValues` (SELECT→UPDATE/INSERT). | inc-price upsert | Q-OVAL-014 | ItemOptionValues | [10_Option_Values](../../10_Option_Values.md) |
| BR-OVAL-015 | `IncPrice = -1`/DBNull = "no increment"; `GetIncPrice` returns `-1` when not found. | `GetIncPrice` | Q-OVAL-002 | ItemOptionValues | [10_Option_Values](../../10_Option_Values.md) |
| BR-OVAL-016 | SIF INSERT columns are conditional (`ImageFile`/`OrderCodeValue`/`SupplierCode` only if supplied/parsable). | SIF import create-value | Q-OVAL-012 | OptionValue | [10_Option_Values](../../10_Option_Values.md) |
| BR-OVAL-017 | Fabric-colour values use hardcoded option id `28`; fabric-type id `8`. | Validate SIF create-value | Q-OVAL-015 | OptionValue | [10_Option_Values](../../10_Option_Values.md) |
| BR-OVAL-018 | A colour value (28) missing its parent type value has the parent inserted at front (`Insert(0,…)`). | OFDA back-fill | Q-OVAL-018 | OptionValue, [Option] | [10_Option_Values](../../10_Option_Values.md) |
| BR-OVAL-019 | OFDA appends a synthetic master-template value (`OrderCodeValue='<MT>'`) for the category. | OFDA back-fill | Q-OVAL-018 | OptionValue, [Option] | [10_Option_Values](../../10_Option_Values.md) |
| BR-OVAL-020 | Removing a value from a catalogue DELETEs `CatalogueOptionValues` only; the value row is kept and audited. | remove-from-catalogue handler | Q-OVAL-016 | CatalogueOptionValues, PDMAudit.dbo.Transactions | [10_Option_Values](../../10_Option_Values.md) |
| BR-OVAL-021 | Bulk `ImageFile` REPLACE uses `LIKE '%<old>%'` — affects every matching value. | bulk image rewrite | Q-OVAL-007 | OptionValue | [10_Option_Values](../../10_Option_Values.md) |
| BR-OVAL-022 | `CADSuffix` is set to `NULL` when empty, else the quoted value. | CAD attributes handler | Q-OVAL-008 | OptionValue | [10_Option_Values](../../10_Option_Values.md) |
| BR-OVAL-023 | Fabric-colour value names are augmented with a supplier code during SIF export (contained-name + IsFabric 2). | `CreateOpt` | Q-OVAL-001 | OptionValue | [10_Option_Values](../../10_Option_Values.md) |
| BR-OVAL-024 | New `DisplayOrdinal`/`DisplayOrder` come from `getNextDisplayOrder(...)`. | `getNextDisplayOrder` | Q-OVAL-012 | OptionValue, [Option] | [10_Option_Values](../../10_Option_Values.md) |
| BR-OVAL-025 | `IsFabric` on the value drives sub-option handling (1 registers ref, 2 strips prefix). | `CreateOpt` | Q-OVAL-001 | OptionValue | [10_Option_Values](../../10_Option_Values.md) |
| BR-OVAL-026 | Back-fill (BR-OVAL-018) triggers when `optIdList` has 28 but not 8 and the parent value is absent. | OFDA back-fill | Q-OVAL-018 | OptionValue, [Option] | [10_Option_Values](../../10_Option_Values.md) |
| BR-OVAL-027 | Every catalogue-affecting value UPDATE is audited; status changes log previous/next label. | maintenance handlers | Q-OVAL-003 | PDMAudit.dbo.Transactions | [10_Option_Values](../../10_Option_Values.md) |
| BR-OVAL-028 | Import re-activation: an existing value's `Status` is forced to `1`. | SIF import reactivate | Q-OVAL-013 | OptionValue | [10_Option_Values](../../10_Option_Values.md) |
| BR-OVAL-029 | A new colour value is linked to both parent (`DependentOptionValues`) and catalogue immediately. | Add New Data link | Q-OVAL-011 | DependentOptionValues, CatalogueOptionValues | [10_Option_Values](../../10_Option_Values.md) |
| BR-OVAL-030 | Value names are normalised on insert (camelCase, US→UK English, apostrophes/CRs removed). | `camelCase`/`convertUSEnglishToEnglish` | Q-OVAL-012 | OptionValue | [10_Option_Values](../../10_Option_Values.md) |

## BR-TRAN — Translations → [doc](../../12_Translations.md)

| Rule ID | Short description | Related methods | Related SQL | Related tables | Source doc |
|---|---|---|---|---|---|
| BR-TRAN-001 | Two independent language selections exist: a primary editing language and a secondary comparison/target language. | form load population | Q-TRAN-001 | Language | [12_Translations](../../12_Translations.md) |
| BR-TRAN-002 | Language display names are data-driven from `Language.Language`; dropdown order = natural row order (no `ORDER BY`). | form load population | Q-TRAN-001 | Language | [12_Translations](../../12_Translations.md) |
| BR-TRAN-003 | Default primary language is `AuthenticateUser.DefaultLanguageId` when present, else index 0. | form load population | Q-TRAN-001 | Language | [12_Translations](../../12_Translations.md) |
| BR-TRAN-004 | `AuthenticateUser.DefaultLanguageId` defaults to `1`, overwritten from `PDMUserPrivileges.DefaultLanguageId` at login. | `AuthenticateUser` | — | PDMUserPrivileges | [12_Translations](../../12_Translations.md) |
| BR-TRAN-005 | The secondary language defaults to index 0 on load. | form load population | Q-TRAN-001 | Language | [12_Translations](../../12_Translations.md) |
| BR-TRAN-006 | Language cannot be typed into either combo; `KeyPress` is swallowed forcing selection only. | `languageselector_KeyPress` | — | — | [12_Translations](../../12_Translations.md) |
| BR-TRAN-007 | Product text lives in `ProductDescription`; all other entity text lives in `OtherDescription` (keyed DescriptionId+LanguageId). | `getTableName` | Q-TRAN-002, Q-TRAN-003 | ProductDescription, OtherDescription | [12_Translations](../../12_Translations.md) |
| BR-TRAN-008 | `LanguageId = 1` is the base/English language: fallback source, copy source, always-translated language. | fallback/copy paths | Q-TRAN-010, Q-TRAN-012, Q-TRAN-013 | OtherDescription, ProductDescription | [12_Translations](../../12_Translations.md) |
| BR-TRAN-009 | Marketing/"Lifestyle" text is always read from `LanguageId = 1`, never the selected language. | marketing text read | — | ProductDescription | [12_Translations](../../12_Translations.md) |
| BR-TRAN-010 | Changing the primary language with unsaved edits is blocked and reverted, unless the catalogue is read-only. | `language_selector_SelectedIndexChanged` | — | — | [12_Translations](../../12_Translations.md) |
| BR-TRAN-011 | In `DescriptionsFindReplace`, target/source `LanguageId` is computed positionally as `SelectedIndex + 1`, not from `langArray`. | `FindNext`/`InsertButton_Click` | Q-TRAN-015, Q-TRAN-016 | ProductDescription | [12_Translations](../../12_Translations.md) |
| BR-TRAN-012 | A catalogue's translated state per language is represented purely by row presence in `CatalogueTranslations`. | `showTranslatedStatus` | Q-TRAN-004, Q-TRAN-005, Q-TRAN-006 | CatalogueTranslations | [12_Translations](../../12_Translations.md) |
| BR-TRAN-013 | When the secondary language is English (`1`), "Catalogue Translated" is forced checked and disabled. | `showTranslatedStatus` | Q-TRAN-004 | CatalogueTranslations | [12_Translations](../../12_Translations.md) |
| BR-TRAN-014 | The translated-flag toggle only writes when `LanguageId > 1` and the UI is not mid-refresh. | `TranslatedCheck_CheckedChanged` | Q-TRAN-005, Q-TRAN-006 | CatalogueTranslations | [12_Translations](../../12_Translations.md) |
| BR-TRAN-015 | The "Catalogue Translated" checkbox is only editable when the catalogue is not read-only. | `showTranslatedStatus` | — | CatalogueTranslations | [12_Translations](../../12_Translations.md) |
| BR-TRAN-016 | Fallback (programmatic descriptions): attribute-value text uses selected language if present, else English. | `generateProgrammaticDescription` | Q-TRAN-012 | ProductAttributeValues, AttributeValue, OtherDescription | [12_Translations](../../12_Translations.md) |
| BR-TRAN-017 | Fallback (pCon push): product short/long text uses target language if non-null/non-empty, else English. | `UpdatePConButton` | Q-TRAN-013 | Product, ProductDescription | [12_Translations](../../12_Translations.md) |
| BR-TRAN-018 | When editing spawns a new `DescriptionId`, all existing non-English translations are re-inserted so no language is lost. | `modifyOtherDescription` | Q-TRAN-007, Q-TRAN-010 | OtherDescription | [12_Translations](../../12_Translations.md) |
| BR-TRAN-019 | Writes to per-language rows are manual UPSERTs: try `UPDATE`, and if `rowcount == 0` `INSERT`. | `modifyOtherDescription`/`InsertButton_Click` | Q-TRAN-008, Q-TRAN-009, Q-TRAN-015 | OtherDescription, ProductDescription | [12_Translations](../../12_Translations.md) |
| BR-TRAN-020 | The Find & Replace tool is Product-only; the `type == "Other"` branch is an empty stub. | `FindNext` | Q-TRAN-016 | Product, ProductDescription | [12_Translations](../../12_Translations.md) |
| BR-TRAN-021 | pCon receives only four languages: `1→_en`, `2→fr`, `5→de`, `9→nl`. | `UpdatePConButton` | Q-TRAN-014 | tCOMd_Text | [12_Translations](../../12_Translations.md) |
| BR-TRAN-022 | When the Products tab is on tab index 9, the pCon "all languages?" prompt is skipped and only English pushed. | `UpdatePConButton` | Q-TRAN-014 | tCOMd_Text | [12_Translations](../../12_Translations.md) |
| BR-TRAN-023 | pCon short descriptions longer than 50 characters are rejected per product with a warning and skipped. | `UpdatePConButton` | Q-TRAN-014 | tCOMd_Text | [12_Translations](../../12_Translations.md) |
| BR-TRAN-024 | For product codes starting `"AER"`, code trims last 2 chars and truncates text at `" / "`/`" >"` before pCon push. | `UpdatePConButton` | Q-TRAN-013, Q-TRAN-014 | tCOMd_Text | [12_Translations](../../12_Translations.md) |
| BR-TRAN-025 | pCon long descriptions have `>` replaced with a CR/LF before writing. | `UpdatePConButton` | Q-TRAN-014 | tCOMd_Text | [12_Translations](../../12_Translations.md) |
| BR-TRAN-026 | On new-id copy, non-English rows equal to the just-edited language are replaced with new text, others carried verbatim. | `modifyOtherDescription` | Q-TRAN-010 | OtherDescription | [12_Translations](../../12_Translations.md) |
| BR-TRAN-027 | `CatalogueApplicationText` is language-keyed and supports a negative-catalogue-id "Pricebook" variant (`-1 * CatalogueId`). | application-text handler | — | CatalogueApplicationText | [12_Translations](../../12_Translations.md) |
| BR-TRAN-028 | Permission `DescriptionMaintenance` gates whether the Product Descriptions screen appears on the Main Menu. | `MainMenu` gate | — | PDMUserPrivileges | [12_Translations](../../12_Translations.md) |
| BR-TRAN-029 | Permission `DescriptionEdit` overrides catalogue read-only status unless `ignoreDescriptionEditPermission`. | `catalogueIsReadOnly()` | — | PDMUserPrivileges | [12_Translations](../../12_Translations.md) |
| BR-TRAN-030 | `metaDescriptions` is an inert 3-field data holder; no language selection, persistence, or fallback. | `metaDescriptions` ctor | — | — (DTO) | [12_Translations](../../12_Translations.md) |
