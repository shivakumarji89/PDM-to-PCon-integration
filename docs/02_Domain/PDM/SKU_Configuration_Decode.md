# SKU Configuration-Code Decode — Findings & Decisions

Session: 2026-08-03 / 2026-08-04. Read-only investigation → implemented fix.
Scope: how a MillerKnoll SKU encodes its configuration, why decoding failed for
some families, and what we changed. Databases: PDM Test (DBCHIP11V/PDMTEST),
PDM Live (DBCHIP12V/PDMLive).

---

## 1. The SKU model

- A SKU is `head.tail`. `head = code.split(".")[0]`.
- **HEAD** = the product base + positional **configuration codes** (Type, Leg
  style, Control switch, Access, Power…). These attributes have
  `AttributeValue.OrderCodeValue = NULL` — their code exists **only positionally**
  in the head string, nowhere stored.
- **TAIL** = **parametric** attributes (Width, Depth, Material, Castors…). These
  carry a stored `OrderCodeValue` and a token (`Attribute.OrderCodeFormatKey`,
  e.g. `{WD}`).
- Head/tail split is the `.`; head vs tail attributes split by **token presence**
  (no token = head/positional; token = tail/parametric).

## 2. Tail ordering (confirmed)

- `ProductRange.OrderCodeFormatString` = ordered `{TOKEN}` template
  (e.g. `{DEP}{WD}{MT}{GC}{WF}{EF}{UF}{AFF}`). Token order = tail slice order
  (NOT `DisplayOrder`). Proven across 12+ ranges.
- `HandbookAttributes` token order is a consistent prefix-subset of the same list.
- **Deferred:** our tail slicer still sequences by `DisplayOrder` — a known gap
  ("tail update later"), independent of the head fix below.

## 3. Handbook tables

- `HandbookProducts.ProductListEntry` = a head template with `_` placeholders
  (e.g. `NOALE2__`, `AER______`). Display/publishing aid — **not** used by PDM to
  slice, and only ~54% of handbook products carry placeholders.
- `HandbookAttributes(HandbookId, ProductGroupId, AttrNum, AttributeId, ColIndex,
  GroupCodeOffset)`:
  - **`AttrNum`** = authoritative attribute **order** (head + tail).
  - **`ColIndex`** = price-list column — **NOT** the head/tail split (DWE4 proves
    `ColIndex=2` mixes head + tail). Use token presence for the split.
  - `GroupCodeOffset` = price-list positioning, not character width.
- **Coverage (active products):**
  - By product (own handbook row): **~47%** (Live 46.7% / Test 45.9%).
  - **By category** (category laid out via any sibling group — the "Nevi Dach"
    effect): **~76%** (Live 76.1% / Test 75.6%). ~24% truly uncovered.

## 4. DWE4 (Nevi) case study

- 69 active `DWE4` products (Live), **0** `HandbookProducts` rows — the series was
  never templated. PDM did **not** reuse the `DWE3` template for it (verified 4
  ways). Confirmed in both DBs.
- BUT `DWE4`'s category (1239, "Nevi Dach") **is** laid out in `HandbookAttributes`
  via the `DWE3` B2B group — so `DWE4` inherits the order through its category.
- `DWE3` and `DWE4` are structurally identical in `Product/ProductRange/Attribute`
  columns; the only difference is the handbook row, which never decoded `DWE3`'s
  head anyway.

## 5. Root cause of decode failure

The old decoder mapped **value → code** and dropped any code claimed by two
concepts (`_reliable_by_concept`). Config codes are **reused across attributes**
(`A` = both `Control box` and `Access`), so entangled families collided and were
discarded. Ratio `RY3XSDABAD` resolved only **1/5**.

Widths are also **not** reliably `HasDependentOptions` (Access is `HDO=2` but 1
char) — HDO is a hint, not a width.

## 6. The fix — POSITION-based decode (implemented)

Decode by **position**, not value:
- Group products by **same head length** (= same structure).
- For products differing in exactly **one** head attribute (compared by
  normalized concept, so per-line duplicate value-ids don't count as a diff), the
  head positions that flip are that attribute's span.
- A position is **owned** by the attribute whose single-diff pairs flip it in
  ≥90% of that attribute's own pairs (uniquely).
- Each value's code = the head at its owned **contiguous** positions.
- Attributes that never vary within the structure = **identity, baked into the
  base** (DPS `$BAN` model), no code.

Position is unambiguous, so reused codes no longer collide. Data-driven — works
beyond the 76% handbook set (needs same-length siblings loaded; sparse → override).

**Results:** RY3XSDABAD **5/5** (was 1/5), AER1A11AW 2/2, DWE42AN4YSNBADNN 3/3,
NOALE212 2/2, DWE36DT4YSNMNDL 5/5 (no regression).

**Files:** `services/engineering/engineering_class_service.py`
(`decode_config_codes_by_position` / `_decode_config_codes_by_position`, additive —
the old `decode_config_codes` and `slice_config_codes` are untouched fallbacks);
`resolve_config_codes` priority = **override > position > correlation/slice**.
New validator `scripts/validate_position_decode.py`.

## 7. Stored filter relation — `config_value_codes` (implemented)

To capture the head-property filter the way PDM does — as a stored
`property-value → code` relation that drives the slice and the article relations
(not re-derived each render):
- `snapshot.config_value_codes: {property_id: {value_id: code}}` (new, persisted).
- `EngineeringClassService.commit_config_codes(snapshot)` writes the resolved
  codes into it (idempotent; overrides untouched).
- `resolve_config_codes` priority now **override > stored > position >
  correlation/slice**.
- Committed automatically in `pdm_service.load_family_details` (after
  `materialize_article_sets`), so it's stored at load and saved with the project.

With the existing `article_property_value_ids` (article → its head values), this
gives the full **article → property-value → code** relation.

**Files:** `models/snapshot.py`, `services/snapshot_serialization.py`,
`services/engineering/engineering_class_service.py`, `services/pdm_service.py`.

## 8. Open items

- **Tail slicer**: sequence by `OrderCodeFormatString` token order (not
  `DisplayOrder`). Deferred earlier.
- **Class Creation Width column** — DONE (2026-08-04): now shows the decoder's
  **evidence-based true width** (owned-position count, via
  `EngineeringClassService.config_code_layout`), e.g. `Power cutout` = 2 (`NN`).
  `HasDependentOptions` is only a last-resort fallback.
- **Property order** — still `DisplayOrder`. Correct order needs
  `HandbookAttributes.AttrNum` (authoritative, includes 0-width identity attrs the
  position decoder can't place). Requires a loader fetch; covers ~76%, DisplayOrder
  fallback. NOT done.
- **11 families load-failed** entirely during the coverage sweep — a separate
  loading issue worth investigating.

## 9. How PDM filters a product by head properties (evidence, 2026-08-04)

The PDM/DPS front-end filters products by **`ProductAttributeValues`** (product ↔
attribute-value link) — **not** the handbook.

- **Head properties = functional attributes**: `AttributeType = 0`,
  `AttributeValue.ModelSuffix IS NULL`, empty `OrderCodeValue`
  (`15_Filtering.md` Q-FILT-007/008; `DPS/PermutateThread.cs` splits functional =
  empty `OrderCodeValue` vs physical = has it).
- **Each product = a unique combination** of its functional attribute values.
  Live proof (PDMTEST): every `AER1A11*` product carries `Type=Work Chair`,
  `Assembly=Fully assembled`, `Size=A`, `Height=Low`, `Tilt=Std`, plus `Arms` /
  `Armpads`; `AER1A12AW` differs only in `Tilt`, `AER1B11AW` only in `Size`.
- **The selection→product matcher** (`DPS/BOM_ExtractItemList.cs:797`) builds one
  `INNER JOIN ProductAttributeValues` **per selected value**, so the product with
  ALL selected `AttributeValueId`s is the SKU:
  ```sql
  SELECT Item.Item FROM Item INNER JOIN Product ON Item.ProductId = Product.ProductId
    INNER JOIN ProductAttributeValues pav0 ON Product.ProductId=pav0.ProductId AND pav0.AttributeValueId=<v0>
    INNER JOIN ProductAttributeValues pav1 ON ... AND pav1.AttributeValueId=<v1>
    ... (one join per selected functional value) ...
  ```
- `CatalogueUIGroups` (`UIGroups` / `DefaultedGroups`) stores which functional-value
  tokens define each UI filter group.

**Correction:** `HasDependentOptions = 0` (Size/Height/Tilt/Assembly/Type) does NOT
mean "ignore / metatype" — those are **functional filter attributes**. HDO only
indicates whether a value unlocks dependent options, not whether it filters.

**Universal (verified across families, PDMTEST 2026-08-04)** — same split everywhere,
functional count varies:
Ratio `RY3XSDABAD` 6 functional / 11 physical; Nevi `DWE42AN4YS…` 10 / 8;
Bolster `AL1C1002LS` 3 / 0; Always `NOALE212` 3 / 0; Lino `MI1E335P` 2 / 1;
Layout Studio `GEPMFA` 2 / 32. Product-coded families (Bolster, Always) have zero
physical/tail — every variant is its own product selected purely by functional
combination. The filter uses **all** functional attributes regardless of HDO.

## Validation status

All `scripts/validate_*.py` PASS (exit codes), pyflakes clean, headless boot OK.
Live-load of NOALE auto-stored `config_value_codes` (Type 1/2/3/5, Fabrics 1/2)
and round-trips through save/load.
