# Validation Rules

**Cross-refs:** [WriteOrder](./WriteOrder.md) · [ReadOrder](./ReadOrder.md) · [../PackagingPipeline.md](../PackagingPipeline.md)

Grounded in `services/ocd_payload_validation_service.py`, `helpers/mdb_helper.py` (get-or-create),
and `docs/uat_checklist.md` (UAT-02).

## Required Records (a valid OCD package must have)

- Exactly one resolvable `tCOMd_ComGroup` (by `com_ComGroupCode`).
- Exactly one `tCOMd_Package` under that ComGroup (by `com_PackageCode`), with a valid
  `com_DistributionRegionID` (region ensured, fixed id 5).
- At least one `tCOMd_Article` (non-empty `com_ArticleCode`) under the package.
- For each property used: one `tCOMd_Property` and its `tCOMd_PropValue` rows.
- `tCOMd_Text` rows for every referenced label (`com_TextID`/`com_ShortTextID`).
- `tCOMd_ArticleClass` / `tCOMd_ArtBase` for each article's class membership / base.

## Optional Records

- `tCOMd_Price` + `tCOMd_PriceList2` (item-level price stage; omitted for structural-only packages).
- Additional `tCOMd_Class` groupings beyond the minimum.

## Relationship Validation

- Every child FK must resolve to an existing parent PK **before** insert (enforced by the
  `get_or_create_*` ordering — see [WriteOrder](./WriteOrder.md)).
- `tCOMd_PropValue.com_PropertyID` must reference a created property.
- `tCOMd_ArticleClass` requires both `com_ArticleID` and `com_ClassID` to exist.
- `tCOMd_Price.com_ArticleID` / `com_PriceListID` must resolve.

## Duplicate Detection

- All structural inserts are **get-or-create** by natural key: `com_ComGroupCode`, `com_PackageCode`,
  article code, text name, normalized property/value codes. Re-running does not create duplicates.
- `normalize_prop_value_code` / `normalize_property_column_name` canonicalize codes so equivalent
  values collapse to one row.

## Missing References

- Article with empty `article_code` → **blocked** (UAT-02: "empty class/property or invalid
  article_numbers").
- PropValue without a resolvable Property → orphan → **blocked**.
- Unresolvable text type (`resolve_text_type_code`) → label cannot attach → **warn/block**.

## Integrity Checks

| Check | Where | Action |
|---|---|---|
| Payload row validity (class/property/article numbers) | `OCDPayloadValidationService` (pre-write) | block write |
| FK parent existence | `get_or_create_*` order (write-time) | create parent first / fail |
| Duplicate natural keys | `get_or_create_*` lookup | reuse existing row |
| Post-write conflicts | `WorkspaceSnapshotBuilder` read-back | report conflicts |
| Destructive replace | `ReplaceArticleSet` → `prune_package_article_set` | snapshot/backup before prune |

## Recommended Generator Additions

- Validate that every `com_VariantCondition` target resolves to an existing option value.
- Validate that every `tCOMd_Price.com_ArticleID` maps to a released Item before writing.
- Run the read-back conflict check as a mandatory post-generation gate.
