# PDM family boundary — what legacy PDM actually defines, and what our engine must match

Read-only investigation against `PDMLive` (DBCHIP12V), 2026-09-19. Every claim
below is either a recovered procedure body, a live query result, or a source
reference in `docs/Legacy_PDM_Business_Logic`.

---

## 1. Legacy PDM has no family algorithm

There is no table, column or routine in PDM that says "these Products are one
base/series family". There are three separate mechanisms that look like one,
and none of them is a reduction-family engine.

### 1.1 `dbo.ProductsList` — a selector filter

Recovered live via `OBJECT_DEFINITION`. The filtering branch is:

```sql
INNER JOIN (SELECT p.ProductId
    FROM Product p
    INNER JOIN ProductAttributeValues pav ON pav.ProductId = p.ProductId
    INNER JOIN OPENXML (@hDoc, '/attributes/attribute', 1)
         WITH (attributeid INT, attributevalueid INT) x
         ON x.AttributeValueId = pav.AttributeValueId
    WHERE p.ProductRangeId = @ProductRangeId
    GROUP BY p.ProductId
    HAVING COUNT(*) = @AttribCount) s ON s.ProductId = po.ProductId
WHERE po.ProductRangeId = @ProductRangeId
  AND (po.ProductId IN (SELECT DISTINCT Product.ProductId FROM Product
                        INNER JOIN Item ON Product.ProductId = Item.ProductId
                        WHERE Item.Status = 1)
       OR po.NewProduct = 1)
```

| Property | Value |
|---|---|
| Scope | exactly ONE `ProductRangeId` |
| Eligibility | ≥1 released Item (`Item.Status = 1`) **or** `NewProduct = 1` |
| Match | **containment** — `ProductAttributeValues(p) ⊇ selection` |
| Not applied | no catalogue predicate, no ProductCategory predicate, no `AttributeValue.Status` predicate |
| Empty XML | returns the whole eligible range (`LEN(@SelAttribValuesXml) = 0` branch) |

`USProductsList` is the US path: `USItem` joined to `USItemAttributeValues` on
`USAttributeValueId`, scoped by `USItem.ProductCategoryId`, returning
`USItem.USItemId` aliased as `ProductId` with `ProductRangeId` hardcoded `-1`,
and with its eligibility clause commented out. `USItemId` and
`Product.ProductId` are disjoint key spaces, so a Product-based candidate
cannot be compared against its result at all.

**This is a filter, not a family definition.** It is monotone: a larger
selection returns a smaller set, and it can never return fewer Products than
those carrying the selection.

### 1.2 `CatalogueUIGroups` — ruled out by data

The matcher `UIGroupMaintenance.getUIGroupIdForProduct` is a real grouping rule
(per Catalogue + ProductCategory, first group by `Sequence` whose `UIGroups`
selectors **cover every** functional token the product carries, with `{` prefix
wildcards and `DefaultedGroups` as coverage — see
[15_Filtering.md](Legacy_PDM_Business_Logic/15_Filtering.md), BR-FILT-012/013/014).

Live, the table holds **290 rows in total, all for CatalogueId 272 /
ProductCategoryId 686**. There are **zero rows for Nevi** (ProductCategoryId
1202, ProductRangeId 6511). It cannot be the family mechanism for the failing
example, and with 290 rows company-wide it is not a general one.

### 1.3 `HandbookProducts` — curated, and the closest thing to a base

`Handbook 956 = "Nevi and Nevi Link"`, `CatalogueId 764`. It covers all 2,112
Products of range 6511 across 27 `ProductGroupId`s, and carries
`ProductListEntry` — a **masked base article**, e.g. `DWE36A_________.` for a
16-character product code.

It is authored by hand in `HandbookDesigner`, and the data shows it:

- Range 6511 alone holds **581 distinct masks** — `DWE36A_________.` (1,348
  products), `DWE36AC4Y______.` (108), `DWE36AT4Y______.` (72), and 577
  single-product masks. Three different base lengths for one physical family.
- One entry is `' DWE36A_________.'` (leading space) and one is the mask
  repeated twice.
- Across the whole database, for the 6,841 multi-product masked entries, the
  mask's first `_` equals the members' common product-code prefix in **72.2%**
  of cases and is *more conservative* (never tighter) in all but 18.

`docs/SKU_Config_Decode_Findings.md` §3 already recorded this: the mask is a
display aid, not a slicing rule, and covers ~47% of active products.

**What it is good for:** it is the best available independent reference for
what PDM's own maintainers consider the base of a family, and for attribute
order (§3 below).

### 1.4 The only provable boundary

```
F is PDM-representable  ⟺  Sel(R, ⋂ functional PAV(F)) = F   over Eligible(R)
```

That closure test is exactly what `PDMFamilyReductionService.validate_family`
performs. The test was never the problem.

---

## 2. Why our candidates did not match

### 2.1 The `--snapshot` harness measured a grouping the app never produces

`cache/pdm_snapshots/*.json` is written by `PDMService.save_family_snapshot`.
It is a **lossy source-data archive**: properties go through `_scalars`, which
drops each property's nested `values`, and `product_property_value_ids` is not
stored at all. `scripts/validate_pdm_family_reduction.py --snapshot` read it
back with `snapshot_serialization.snapshot_from_dict` — the *project* format.

Result: `classify_by_properties` saw no product-to-value link, returned **one
class with an empty property signature holding all 8,919 articles**, and
`candidate_families` sliced it by range name into a 1,824-product "Nevi Desks"
candidate. Every `--snapshot` validation run to date measured that.

Fixed: the mode now reads the cache only to recover WHICH Products the family
covered, then loads them through the real `PDMService.load_family`.

### 2.2 Classification was not ProductRange-scoped

On a faithful production load of the same 1,847 Products, **2 of 7 ArticleSets
spanned three ProductRanges each**, mixing article code lengths 15/16/18 and
7/8 under one `base_length`.

Worse, `base_length` came from a **snapshot-wide** `config_code_layout`, so
*every* set in the Nevi snapshot got `base_length = 3` and `base_code = 'DWE'` —
the minimum head position across the whole snapshot, contributed by the short
Wire Management codes.

### 2.3 The base ended at the first head property CARRIED, not CONFIGURED

`materialize_article_sets` took `min(head position)` over every head property
the set carried, including properties whose value is identical for every
product in the set. Those are set identity and belong in the base — the `$BAN`
rule in `docs/SKU_Config_Decode_Findings.md` §6.

For the main Nevi desk family, `Type` is constant (`Single-sided rectangular`)
and sits at head position 3, so the base was cut to `DWE`. PDM's own handbook
records `DWE36A`.

This also makes the base robust against a known decoder artifact: the
positional decoder can only see attributes that VARY in the loaded set, so a
constant attribute gets no position, or a wrong one. In the Nevi snapshot
`Application` (constant) was assigned position 6, colliding with `Leg type`.
Excluding constant properties removes that class of error from the base.

### 2.4 The comparison population was not the one `ProductsList` answers over

`missing_from_filter` is empty **by construction**: every candidate member
carries the intersection, so `ProductsList` must return it (bar an ineligible
Product). The check is therefore a pure *over-match* test — and the candidate
was drawn from `Loaded ∩ Range` while `Sel` ranges over all of
`Eligible(Range)`.

**A partially loaded ProductRange could never validate, however correct the
grouping.** For Nevi: range 6511 holds 2,112 Products, all eligible, all in
catalogue 764; the session held 1,824. The missing 288 (the
`Power entry = Swiss ∩ Leg type = Circular` block) are not excluded by range,
category, catalogue, status, `NewProduct`, order-code attribute or UI group —
they were simply never selected into the working set.

Fixed two ways: the population gap is now reported and closable
(`PDMService.product_range_gaps` / `complete_product_ranges`), and a candidate
from a partly loaded range is `unresolved` — never a pass, and never a
`rejected` that blames the grouping. Exact equality is unchanged.

---

## 3. Head layout is corroborated by `HandbookAttributes`

`HandbookAttributes.AttrNum` is the authoritative attribute order. For Nevi
group 81:

```
 1 Type            (no OrderCodeFormatKey)     head
 2 Leg type                                    head
 3 Leg style                                   head
 4 Application                                 head
 5 Worktop type                                head
 6 Corner detail                               head
 7 Control switch                              head
 8 Access detail                               head
 9 Power entry                                 head
10 Power cutout                                head
11 Depth           {DEP}                       tail
12 Width           {WD}                        tail
13 Material type   {MT}                        tail
14 Castors / glides {GC}                       tail
```

Against the product code `DWE36AT4YSABFSN.`:

```
D W E | 3 6 A | T | 4 | Y | S | A | B | F | S | N | .
 base  Type    Leg Leg Appl Work Corn Ctrl Acc Pwr Pwr
       (3ch)   type style     top  det  sw   det ent cut
```

A perfect 1:1 with `AttrNum` 1..10, and the tail order matches
`ProductRange.OrderCodeFormatString`
(`{DEP}{HEI}{WD}{RW}{MT}{GC}{WF}{EF}{UF}{AFF}{FBT}{FBC}`) as a prefix subset —
as `SKU_Config_Decode_Findings.md` §2 states.

Checked across the whole database: for the 6,057 handbook groups with >1
product, a `.` in the code, uniform code length and a `HandbookAttributes` row,
`head_length - head_attribute_count >= 0` in **6,036 (99.65%)**, consistent with
"series prefix + at least one character per head attribute, in `AttrNum`
order". This corroborates the head model but does not pin per-attribute widths,
so it is evidence, not a replacement for the positional decoder.

---

## 4. What Product/Article descriptions contribute — nothing structural

- `Product.Name` for range 6511 has **16 distinct values over 2,112 Products**,
  shaped `<Type>/<Control switch>/<Power entry>`, and contains typos
  (`Dig disply & memory` vs `Dig display & memory`). The main 1,435-Product
  candidate spans 15 of the 16. It is a hand-typed label, not a grouping key.
- `ProductDescription.LongDescription` is a `>>`-delimited rendering of the
  attribute values (`Nevi - Single-sided rectangular>>Leg type: T-foot ...`) —
  derived from the same `ProductAttributeValues`, so it adds no information.

---

## 5. Result on the real Nevi family

With every ProductRange in the session complete (2,112/2,112 for Nevi Desks):

| candidate | base | products | `ProductsList` | missing | extra | status |
|---|---|---:|---:|---:|---:|---|
| Nevi Desks, single-sided rectangular | `DWE36A` | 1,723 | 1,728 | 0 | **5** | rejected |
| Nevi Desks, rectangular return | `DWE36R` | 384 | 384 | 0 | 0 | **validated** |
| Nevi Screen Components | `DWE3VN` | 3 | 3 | 0 | 0 | validated |
| Nevi Screen Components | `DWE3SMSH` | 3 | 3 | 0 | 0 | validated |
| Screen with Brackets | `DWE3SC` | 3 | 3 | 0 | 0 | validated |
| Screen with Brackets | `DWE3SCRM` | 3 | 3 | 0 | 0 | validated |
| Spacing Plate Kits | `DWE` | 2 | 2 | 0 | 0 | validated |

`DWE36A` is exactly the mask PDM's own handbook records for 1,348 Products of
this family, derived independently from the data.

### The residual 5 — a PDM data defect, not a grouping defect

ProductIds **115561, 115562, 115563, 115564, 115565**
(`DWE36AT4YS/DB*BFSN.`, "Nevi SS Desk/Basic switch/Swiss") carry **no
`Power cutout` row in `ProductAttributeValues`**. Their direct neighbour
`115525` (`DWE36AT4YSABNSN.`) carries `Power cutout = None`. Every
`AttributeValue` used by range 6511 has `Status = 1`, so this is not our
`av.Status = 1` filter dropping a row.

Our engine correctly classes them apart (they cannot take the family's
`Power cutout` property). `ProductsList` containment cannot express "lacks
attribute X", so it pulls them into the closure. PDM's own handbook is
inconsistent about them too: 2 of the 5 sit under the masked
`DWE36A_________.` entry (groups 58 and 66), the other 3 under un-masked
per-product entries in group 81.

**Remediation is in PDM, not in code:** add `Power cutout = None`
(`AttributeValueId 109863`) to those five Products.

Proven by simulation (in-memory only, nothing written to PDM): adding that one
value to the five Products in the loaded snapshot and re-running the whole
chain gives

```
base='DWE36A'  range=Nevi Desks  products=1728  validated  filtered=1728  missing=0  extra=0
```

`1,723 + 5 = 1,728`. The family closes exactly, and the residual is accounted
for in full.

### The two Wire Management outcomes are also correct

- **4 Products, rejected with 4 extra.** The only functional value the four
  share is `Type = Lower`, so the selector `{Type=Lower}` selects all eight
  "Lower" Products of the range. The other four (`Single-sided - Transom pair`,
  `Hardware pack`, `sleeves`, `transom kit`) are a different property
  structure: they carry no `Width`, so they cannot share one parametric master.
  Same shape as the Nevi five — `ProductsList` containment cannot express
  "lacks attribute X" — but here the split is genuine, not a data defect.
- **7 Products, unresolved.** Their functional values intersect to nothing
  (`Type` and `Application` both differ across the set), so PDM offers no basis
  to filter the grouping at all. Their shared code prefix is only `DWE`, so
  blocking the collapse is the correct outcome.

---

## 6. Standing limitation

`dbo.ProductsList` is a containment filter. It can express "carries value V"
and never "does not carry attribute A". Whenever our engine separates two
property structures that differ only by the **absence** of an attribute, the
closure will contain both and the candidate will be `rejected` even though the
grouping is right. Both residual Nevi/Wire Management mismatches are exactly
this case. There is no way to resolve it through `ProductsList`; it is resolved
either by fixing the PDM data (when the absence is a defect, as with the five
Nevi Products) or by accepting the block (when the absence is real, as with the
Wire Management hardware packs).


---

## 7. Functional vs configurable — the four legacy tests

`PDMFamilyReductionService.is_functional` requires ALL four legacy tests
(`Attribute.AttributeType = 0`, `Attribute.OrderCodeFormatKey IS NULL`,
`AttributeValue.OrderCodeValue` empty, `AttributeValue.ModelSuffix IS NULL`).

For range 6511 the four agree exactly — 21,115 of 38,779
`ProductAttributeValues` rows pass every test, and the count is identical for
each test taken alone. The conservative AND costs nothing here.

Database-wide they do not agree: 510,388 rows pass `AttributeType = 0` but only
480,748 pass all four. That ~6% gap is where the strict AND could leave a family
unproven on some other range. It is the deliberate trade-off recorded in
`is_functional` (being too strict only loses a proof; being too loose could
validate a base legacy would not support), but it is worth re-checking per range
before concluding a family is genuinely unprovable.


---

## 8. Fallback candidate strategies

The primary grouping (property structure within one ProductRange) is unchanged
and still outranks everything below. These are ADDITIONAL groupings offered to
the same boundary, implemented in
`services/engineering/candidate_strategy_service.py`. The flow is:

```
primary candidates -> fallback strategies -> merge/dedupe
    -> ProductRange completeness check -> exact ProductsList -> reduction
```

| Strategy | Rule | Evidence |
|---|---|---|
| `base-prefix` | Every eligible Product of the range whose product code starts with a base the primary grouping derived | §1.3 - the authored mask's first `_` equals the members' common code prefix in 72.2% of 6,841 multi-product entries, and is never tighter in all but 18 |
| `functional-signature` | Products of one range whose functional `ProductAttributeValues` set is identical | the rule already used by `validate_pdm_family_reduction.py --discover`, promoted into the service; functionality decided by the same four legacy tests the selector is built from (§7) |
| `handbook-group` | Products one handbook publishes under one `ProductListEntry` within one ProductGroup | §1.3 - the only place PDM records a human "one family, one base"; offered last because it is curated and measurably inconsistent |

**Why this is safe.** A proposal is only ever a question. It goes through the
unchanged `PDMFamilyReductionService`, must be returned *exactly* by
`ProductsList`, and stays `unresolved` if its range is partly loaded. A wrong
proposal costs a round trip and can never be applied. That is what makes it
acceptable to propose from curated data.

**Merge rule.** Proposals naming the same ProductIds collapse to one (earliest
strategy keeps it). A proposal that is a *subset* of a primary candidate is
dropped: it could only re-describe Products the primary grouping already
covers, and the primary grouping outranks it, so the round trip could not change
an outcome. Only a proposal reaching *further* than the primary candidate can
rescue one.

**Precedence** when several confirmed candidates cover one article - a declared
order, not a score:

1. a confirmed family before one that merely had nothing to prove (the
   single-Product candidate asserts no family at all);
2. strategy order, primary first - so between two confirmed answers the primary
   grouping always wins;
3. the widest confirmed family - one confirmed family often contains another,
   both are equally proven, and splitting one family across two bases would
   gain nothing;
4. longer base, then base text, for determinism.

**Deliberately not implemented: a "closure" strategy.** Asking `ProductsList`
what it would return and proposing that back would always validate - the
closure is idempotent - turning the boundary from a check into a rubber stamp.
Every strategy above derives its grouping from independent evidence and then
submits it to be judged.
