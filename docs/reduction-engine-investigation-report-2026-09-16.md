# Generic PDM Product Reduction Engine — Investigation Report

Date: 2026-09-16
Branch: `feature/reduction-engine-2026-09-16`
Scope: read-only investigation and validation. No production/application code was modified. New diagnostic output lives under the session scratchpad (`get_sp_def.py`, `ProductsList_def.sql`) and the pre-existing `.audit_tmp_*` files in the repo root, which were reused/read, not treated as ground truth without spot-checking.

Legend used throughout:
- **[OBSERVED]** — pattern noticed in data/scripts, not a proven rule
- **[PROVEN]** — verified against live DB objects or source, with citation
- **[HYPOTHESIS]** — stated assumption not yet fully proven or disproven
- **[PROPOSED]** — new-engine behavior recommendation, not existing/legacy behavior

---

## 1. Confirmed facts

- **[PROVEN]** The 591-product validation dataset splits exactly as expected: ProductRangeId 5416 → 297 products, ProductRangeId 5430 → 294 products (verified against the live `Product` table, not just the cached TSV).
- **[PROVEN]** `dbo.ProductsList` exists in the live database. **No `.sql` file, migration, or dump anywhere in the repository contains its definition.** Every prior reference to its "semantics" in this repo (including `docs/legacy-pdm-reduction-engine.md`) was prose written without checking the live object text. This investigation extracted the real definition via a read-only `OBJECT_DEFINITION()` query and saved it to the scratchpad (`ProductsList_def.sql`) for the record.
- **[PROVEN]** `docs/DPS_Original_Extraction_SQL.md` is explicitly an auto-extracted, heuristic flattening of SQL string literals pulled out of the legacy DPS Windows client's C# source (per its own header) — it is not the C# source itself and not a stored-procedure dump. It is the only in-repo trace of `PermutateThread.cs` logic.
- **[OBSERVED]** Prefix families in the 591 dataset are not flat/disjoint — they nest (see §3, §5).
- **[OBSERVED]** Two independently-written analysis paths in this repo (`services/engineering/legacy_pdm_reduction_engine.py` + `scripts/run_591_reduction_analysis.py` vs. `scripts/explore_591_candidate_filters.py` / `scripts/validate_range_scoped_reduction.py`) produce materially different results on the same input — one finds 0/591 groups, the others find close to full coverage. This divergence is itself an important finding: the "production-adjacent" engine currently in the codebase does not work on real data.

## 2. Proven legacy behavior

Extracted directly from `OBJECT_DEFINITION(OBJECT_ID('dbo.ProductsList'))` (saved verbatim to scratchpad `ProductsList_def.sql`). When `@SelAttribValuesXml` is non-empty, the qualifying-product subquery is:

```sql
INNER JOIN (
  SELECT p.ProductId
  FROM Product p
  INNER JOIN ProductAttributeValues pav ON pav.ProductId = p.ProductId
  INNER JOIN OPENXML(@hDoc, '/attributes/attribute', 1)
       WITH (attributeid INT, attributevalueid INT) x
       ON x.AttributeValueId = pav.AttributeValueId
  WHERE p.ProductRangeId = @ProductRangeId
  GROUP BY p.ProductId
  HAVING COUNT(*) = @AttribCount
) s ON s.ProductId = po.ProductId
WHERE po.ProductRangeId = @ProductRangeId
  AND (po.ProductId IN (SELECT DISTINCT Product.ProductId FROM Product
                         INNER JOIN Item ON Product.ProductId = Item.ProductId
                         WHERE Item.Status = 1)
       OR po.NewProduct = 1)
```

**[PROVEN]** facts derived from this text:
1. AND-semantics confirmed: a product qualifies only if it holds a `ProductAttributeValues` row for *every* selected `AttributeValueId`, via `GROUP BY ProductId HAVING COUNT(*) = @AttribCount`.
2. Range scoping is applied twice — once inside the qualifying subquery, once on the outer product-range filter — both against the same `@ProductRangeId` parameter. Range scope is structurally load-bearing, not incidental.
3. Eligibility is `(exists an Item with Status=1 for the product) OR (Product.NewProduct = 1)` — confirmed exactly as hypothesized.
4. **[PROVEN, previously unstated]** The stored procedure itself does **not** know about or enforce the order-code/functional attribute split. It will accept any `AttributeValueId`s the caller puts in the XML, order-code-bearing or not. The functional-vs-order-code separation is entirely a caller responsibility — it lives in client logic (see below), not in this SP.
5. **[PROVEN, latent risk]** `@AttribCount` is `COUNT(*)` over XML rows, not `COUNT(DISTINCT ...)`. A caller passing duplicate `(attributeid, attributevalueid)` pairs inflates the required count and silently breaks matching. No script in the repo asserts dedup before calling the SP; all current scripts happen to avoid duplicates but none guard against it explicitly.
6. `USProductsList` (mentioned in `docs/legacy-pdm-reduction-engine.md` as a presumed parallel implementation) was **not** independently pulled/verified in this pass — its parity with `ProductsList` remains **[HYPOTHESIS]**, not proven.

**[PROVEN]** functional/order-code separation, from `docs/DPS_Original_Extraction_SQL.md` (extracted `PermutateThread.cs` literals, lines ~3385–3405):
- `PermutateThread.cs#2` (source line 88): pulls all `ProductAttributeValues` for a product/root code with no `OrderCodeValue` filter.
- `PermutateThread.cs#4` (source line 161): a **separate** query scoped by `CatalogueAttributeValues` with an explicit `WHERE atval.OrderCodeValue IS NOT NULL` clause.

This is a genuine two-query split in the legacy client: one query for "all attribute values", a distinct query specifically for "order-code-bearing attribute values." It directly corroborates: **non-empty `OrderCodeValue` marks an attribute value as post-dot/order-code-side**, and the legacy engine already treats it as a separate axis from functional/pre-dot values. Caveat: this is recovered from an auto-extracted literal dump, not the actual C# control flow, so the exact usage context of these two queries (e.g., whether results are ever merged back together) is **[HYPOTHESIS]**, not fully proven.

## 3. Evidence supporting ProductRange as scope

- The SP filters on `ProductRangeId` in two places (§2.2) — it is structurally central to the legacy matching logic, not optional.
- Every exact-match family found across both ranges in the 591 dataset stayed within a single `ProductRangeId`; no filter or prefix family was observed spanning two ranges.
- `scripts/investigate_ambiguous_reduction_families.py` explicitly compared cross-range "sibling" families (e.g. `RY3XS` in 5430 vs `RYCX1` in 5416) and found `Same ProductRangeId: False` with disjoint functional-value sets in every pair — i.e., apparent cross-range similarity in prefix naming does not correspond to a shared functional filter or shared product set. This supports range as a meaningful, sufficient partition boundary for at least this dataset.

## 4. Evidence against ProductRange as scope (if any)

- No direct counter-evidence was found in the 591 dataset. However, the test that would actually stress this (two ranges sharing overlapping `AttributeValueId`s but intending genuinely different families, or a real base-article family whose concrete products span more than one `ProductRangeId`) was **not constructed or run** — absence of counter-evidence here is weak, not a proof of sufficiency. **[UNPROVEN]** whether ProductRange is *always* sufficient scope, or only sufficient for the two ranges sampled.
- The dataset itself was pre-selected as "591 products across ranges 5430/5416" — i.e., scope was chosen by the investigators before the analysis, so the dataset cannot itself validate that range is the correct natural boundary; it can only fail to falsify it.

## 5. Prefix → Product set mapping (summary)

From `scripts/validate_range_scoped_reduction.py` (in-memory SP reimplementation, `--min-group 24 --max-filter-values 4`, both hardcoded — see §8):

| Range | Prefix families found | Exact-filter groups | Uncovered | Pairwise overlaps between prefix groups |
|---|---|---|---|---|
| 5416 | 22 | 21 | 0 (within 591 subset) | 51 |
| 5430 | 22 | 21 | 0 (within 591 subset) | 51 |

The 51 overlaps per range are not noise — they are **nested** relationships: shorter prefixes are supersets of longer, more specific prefixes (e.g. `RYCX1` (99) ⊃ `RYCX1E` (48) ⊃ `RYCX1EA` (24) in range 5416; `RY3XS` (98) ⊃ `RY3XSD` (48) ⊃ a 24-product child in range 5430). Overlap sizes consistently equal another group's exact size, which is the fingerprint of strict nesting rather than partial/accidental overlap.

Independently, `scripts/explore_591_candidate_filters.py` (live `EXEC dbo.ProductsList` round-trip against the true full range population, combo size ≤3, top 30 support patterns/range) found 60 unique exact-match groups across both ranges with a group-size distribution of `{48:2, 72:25, 75:2, 96:9, 98:3, 99:6, 144:12, 196:1}` — broadly consistent with the nested-family picture above, though it uses a different search strategy so exact family boundaries differ slightly from the in-memory script's output. A greedy non-overlapping partition over these 60 groups covers 582/591 (9 uncovered) — but greedy-largest-first is a deliberately labeled new-policy choice, not a legacy behavior (see §9, §10).

## 6. Product set → functional filter mapping (summary)

- Every prefix family in both ranges that was checked had **at least one** functional `AttributeValueId` combination (all with `OrderCodeValue` empty) that reproduced its ProductId set — either exactly within the 591 subset (`validate_range_scoped_reduction.py`) or exactly against the true live range population (`explore_591_candidate_filters.py`, the stronger of the two checks).
- Minimal filters are typically 1–3 `AttributeValueId`s for the coarsest families (e.g. `RYCX1` = single `Type=Single Desk` value) and up to 2–4 for more specific nested children (e.g. `RYCX1E` needs `Desk type(A)=Electric 700-1200` + `Type=Single Desk`).
- **[OBSERVED]** At least one family (`RY3XBDA`, 24 products, range 5430) has **three distinct 2-value filter combinations**, each exactly reproducing the identical 24-ProductId set — because two attribute pairs co-vary identically across that family. This proves minimal functional filters are **not always unique** (see §7, §8-E).

## 7. Exact set-equality validation results

Two levels of "exact" were used across the existing scripts, and they are **not equivalent in strength**:

1. **Weak exactness** (`validate_range_scoped_reduction.py`): filter-set vs. prefix-set equality checked only within the 591-row input subset, using an in-memory reimplementation of the SP logic that **omits the eligibility clause** (`Item.Status=1 OR NewProduct=1`) entirely and never queries the true full `ProductRange` population. Result: 22 prefix families found across both ranges combined (44 total), 42 validated as exact matches within-subset, 0 uncovered within-subset.
2. **Strong exactness** (`explore_591_candidate_filters.py`): filter-set vs. product-set equality checked via a live `EXEC dbo.ProductsList` call against the true full range population in the database (not limited to the 591 rows). Result: 60 unique exact-match groups found (bounded by a combo-size ≤3 / top-30-support-pattern search cap — see §8), non-overlapping greedy partition covers 582/591 (9 uncovered), 9/591 have no assigned family under that specific partition policy.
3. The "production" candidate implementation (`services/engineering/legacy_pdm_reduction_engine.py` via `scripts/run_591_reduction_analysis.py`) validates **0/591** products into any group, due to a concrete bug (§8) rather than a genuine absence of structure — this is not evidence against the reduction hypothesis, it is evidence the current implementation is broken.

**Bottom line: no single existing script has actually performed a fully strong exact-set-equality validation (true full-range population, eligibility clause included, uncapped search space) end-to-end.** The strongest partial evidence (`explore_591_candidate_filters.py`) supports the hypothesis but with known search-space caps that could hide undiscovered ambiguity or families needing more discriminating attribute values.

## 8. Ambiguities found

- **[OBSERVED]** Non-unique minimal functional filters: `RY3XBDA` (24 products, range 5430) has 3 different 2-attribute-value combinations that all exactly reproduce the same product set (co-varying attribute pairs). No canonical tie-break rule exists in any current script — they just report all ties.
- **[OBSERVED]** Nested/nesting ambiguity: because prefix families nest (e.g. `RYCX1` ⊃ `RYCX1E` ⊃ `RYCX1EA`), a naive "assign each product to a family" step must pick a level of granularity; none of the scripts state a policy for which nesting level is "the" base article, they merely enumerate all levels found.
- No case of the same `(ProductRangeId, filter)` pair mapping to two genuinely different, non-nested product sets was found — but this specific stress test (deliberately constructing/searching for such a collision) was not performed; its absence is not proof it cannot occur outside the sampled 60/22-family search space.

## 9. Failure cases found

- **Concrete bug, not just a search gap**: `services/engineering/legacy_pdm_reduction_engine.py:117` builds each candidate group's seed from a product's **entire** `ProductAttributeValues` set (via `run_591_reduction_analysis.py`'s `fetch_pav_rows`, lines ~106–134) without excluding `OrderCodeValue`-bearing values first. Since every product's full attribute-value set includes its own order-code-specific values, no two products ever share an identical full set, so intersection-based grouping degenerates to 0 groups over the entire 591-product dataset. This is the clearest and most important failure case identified in this investigation: **the reduction engine code currently on this branch does not implement the order-code exclusion rule, and consequently cannot reduce any real data.**
- No genuine "same range+filter → multiple unrelated prefixes" or "same prefix → multiple disjoint product sets" case was found in the 591 dataset with the scripts as they stand, but see the caveats in §7/§8 about search-space caps and the eligibility-clause gap — a stronger validation pass (full range population, uncapped search, eligibility included) has not yet been run and could surface cases the current scripts cannot see.

## 10. Recommended generic algorithm

The task references an "original strawman 6-step algorithm" — the description above (the SP-derived semantics, order-code exclusion, prefix-family discovery) implies the following revision, informed by the evidence in §5–§9. Differences from a naive/greedy approach are called out explicitly.

```
PROPOSED NEW-ENGINE ALGORITHM (pseudocode)

for each ProductRangeId in scope:
    products := all Product rows in this ProductRangeId
                 (NOT limited to any validation subset)

    # Step 1: build functional-only attribute-value sets
    for each product in products:
        pav := ProductAttributeValues for product
        functional_pav := { v in pav : v.OrderCodeValue is NULL or empty }
        # PROVEN separation rule (PermutateThread.cs), applied BEFORE
        # any grouping/filter-construction step -- not after, and not
        # relied upon implicitly via a round-trip check.

    # Step 2: discover candidate prefix families (pre-dot article code)
    candidate_prefixes := group products by common leading substring
                          of their pre-dot code, at EVERY nesting level
                          observed (not just the longest or shortest) --
                          because families are proven to nest (Sec. 5).

    # Step 3: for each candidate prefix-family's product-id-set S,
    #         search for a functional AttributeValueId combination F
    #         (drawn only from functional_pav, never order-code values)
    #         such that:
    #             EXEC dbo.ProductsList(@ProductRangeId, @LanguageId, F)
    #         returns exactly S (verified by set equality against the
    #         TRUE FULL RANGE population, live SP call -- not an
    #         in-memory reimplementation, and not restricted to any
    #         validation subset). Eligibility clause (Item.Status=1 OR
    #         NewProduct=1) must be exercised as part of this call,
    #         not skipped.
    #
    #         Do NOT cap combination size or the number of support
    #         patterns tried a priori based on what happened to work on
    #         one sample dataset (Sec. 8 bug: --max-values=3,
    #         --limit-per-range=30 hardcoded caps found in
    #         explore_591_candidate_filters.py must not carry over as
    #         production defaults). Bound search space by measured
    #         complexity of the real attribute schema, or make it
    #         configurable and prove convergence empirically per range.

    # Step 4: collect ALL exact minimal filters per family (there may be
    #         more than one, per Sec. 6/8's RY3XBDA finding). Record
    #         all of them; do not silently pick one without a stated,
    #         explicit tie-break rule (e.g., lowest AttributeValueId
    #         tuple) that is documented as a NEW ENGINE POLICY DECISION,
    #         not a rediscovered legacy rule (none exists at the SP level).

    # Step 5: represent the discovered family structure as a hierarchy/
    #         DAG (nested supersets), not a flat partition. Do not
    #         force a single non-overlapping partition via greedy
    #         largest-first selection unless the product/business
    #         requirement genuinely calls for a flat "one base article
    #         per concrete product" outcome. If a flat assignment is
    #         required, the greedy policy must be an explicit, reviewed,
    #         documented NEW ENGINE POLICY -- not treated as a
    #         rediscovery of legacy behavior (legacy has no such
    #         partitioning concept; it only answers ad hoc filter
    #         queries).

    # Step 6: report, per range: covered / uncovered products, families
    #         with non-unique minimal filters, families that nest inside
    #         other families, and any product with zero exact-matching
    #         functional filter at any nesting level (a true
    #         "unreducible" concrete product) for manual review.
```

Key revisions vs. a naive strawman:
- Order-code exclusion happens **before** filter/grouping construction, always, not as an incidental side effect of a live-SP round trip.
- Exactness is validated against the **true full range population** via a **live** SP call including the eligibility clause — not an in-memory reimplementation and not restricted to a hand-picked validation subset.
- Family structure is treated as a **nested hierarchy**, not a flat partition; flattening (if needed) is a separate, explicit, documented policy step.
- Non-unique minimal filters are expected and recorded, not silently resolved.
- Search-space caps (combo size, support-pattern limits) must not be hardcoded from what worked on the 591-product sample; they need either a principled bound or must be proven to not truncate real families before being shipped.

## 11. What remains unproven

- Whether `ProductRange` is a **universally** sufficient scope, versus needing a broader catalogue/category/series boundary in some part of the wider (non-591) product population — only two ranges were examined, and no adversarial case (overlapping AttributeValueIds across ranges intended to mean different things) was constructed.
- Whether `USProductsList` (or any other regional/variant stored procedure) shares identical semantics with `dbo.ProductsList` — not independently verified in this pass.
- Whether a genuine "same range+filter → multiple unrelated prefixes" or "same prefix → disjoint product sets" failure case exists outside the search-space caps used by `explore_591_candidate_filters.py` (combo size ≤3, top 30 support patterns/range) — the negative result in §9 is only as strong as that search space.
- Whether the true full-range-population, eligibility-included, live-SP exactness check (the strongest version described in §10) actually holds for every candidate family — it has not yet been run end-to-end for all families in both ranges; only a search-capped subset was validated this way.
- The exact semantics/control-flow of `PermutateThread.cs` beyond the two extracted query literals — the extraction is heuristic and does not show how/whether the two queries' results are combined downstream, so the "separate axes" conclusion, while well-supported, is not a full proof of the legacy client's end-to-end behavior.
- Whether a canonical/minimal-filter tie-break rule is needed by any actual downstream consumer, or whether reporting all tied minimal filters is acceptable long-term.
- Behavior of the reduction concept on products/ranges with **no** clean prefix structure at all (the 591 dataset was likely selected because it has clean structure) — coverage on a random or adversarial sample of the wider product catalog is untested.

## 12. Concrete acceptance tests required before production implementation

1. **Full-population live-SP exactness test**: for every discovered family (all nesting levels, both sampled ranges and at least 2–3 additional ranges not in the 591 set), call the real `dbo.ProductsList` (not an in-memory reimplementation) against the **entire** range population (not a validation subset) and assert `ProductId` set equality, including eligibility clause behavior, with a fixed `@LanguageId`.
2. **Order-code exclusion regression test**: assert that every functional filter used in family discovery contains zero `AttributeValueId`s whose `OrderCodeValue` is non-empty; add a unit test against `services/engineering/legacy_pdm_reduction_engine.py`'s grouping seed to prevent the regression found in §9 from recurring silently.
3. **Duplicate-AttributeValueId defense test**: verify the caller-side XML builder never emits duplicate `(attributeid, attributevalueid)` pairs, and add a test that intentionally passes a duplicate to `dbo.ProductsList` to document/confirm the `COUNT(*)` inflation behavior (§2.5) so future callers don't get silently broken results.
4. **Cross-range collision test**: construct or find real `AttributeValueId`s that occur in more than one `ProductRangeId` and confirm that scoping by range still produces disjoint, correct families (directly tests §4/§11's open question on scope sufficiency).
5. **Non-unique minimal filter handling test**: reproduce the `RY3XBDA` tie (§6/§8) and confirm the production algorithm records/handles all tied minimal filters per the documented policy, rather than picking one arbitrarily and silently dropping the others.
6. **Nesting-hierarchy integrity test**: for every pair of families where one product-set is a strict superset of another (as in `RYCX1`/`RYCX1E`/`RYCX1EA`), confirm the discovered filters are themselves in a strict subset/superset relationship of `AttributeValueId`s (the superset family's filter should be a subset of the subset family's filter) — this checks internal consistency of the hierarchy, not just set equality per family.
7. **Uncovered-product review gate**: any product with zero exact-matching functional filter at any nesting level must be surfaced to a human reviewer before go-live, not silently dropped or force-assigned to a nearest/approximate family (explicitly disallowed per task constraints — no description-similarity fallback).
8. **Search-space-completeness test**: re-run family discovery with no artificial combo-size/support-pattern cap on a bounded sample and confirm results match the capped run; if they diverge, the production search bound must be re-derived from measured attribute-schema complexity, not copied from the 591-dataset scripts' hardcoded defaults (`--max-values 3`, `--limit-per-range 30`, `--min-group 24`, `--max-filter-values 4`).
9. **`USProductsList` parity test** (if that procedure is still in use anywhere in scope): pull its live definition the same way `ProductsList`'s was pulled here, and diff semantics explicitly rather than assuming parity.
10. **Greedy-partition policy review**: if a flat (non-nested) assignment is required by the business, require explicit sign-off on the tie-break/partition policy (e.g., greedy-largest-first) as a **new** engine decision, with a test asserting the 9 currently-uncovered 591-dataset products (or whatever the current uncovered set is under the finalized algorithm) are consciously accounted for, not silently dropped.

---

### Appendix: source references

- Live SP definition extracted via read-only `OBJECT_DEFINITION(OBJECT_ID('dbo.ProductsList'))`, saved to scratchpad `ProductsList_def.sql`.
- `docs/DPS_Original_Extraction_SQL.md` (lines ~3385–3410) — `PermutateThread.cs#2`/`#4` extracted literals.
- `docs/legacy-pdm-reduction-engine.md` — prior prose description of legacy semantics (now confirmed against live DB; discrepancies noted in §2).
- `services/engineering/legacy_pdm_reduction_engine.py` (grouping bug at line ~117).
- `scripts/run_591_reduction_analysis.py` (PAV fetch not excluding OrderCodeValue, lines ~106–134, ~214–224).
- `scripts/explore_591_candidate_filters.py` (live SP round-trip validation, hardcoded search caps at lines ~195–227, ~236–241).
- `scripts/validate_range_scoped_reduction.py` (in-memory SP reimplementation missing eligibility clause, lines ~115–142, functional exclusion correctly applied at line ~152).
- `scripts/investigate_ambiguous_reduction_families.py` (hardcoded Ratio-Desk prefix list default at line ~98; own results show no true ambiguity in the pairs it checked).
- `.audit_tmp_591_reduction_report.json`, `.audit_tmp_range_scoped_reduction.txt`, `.audit_tmp_ambiguous_reduction_families.txt` — cached outputs reused as evidence, spot-checked rather than trusted blindly.
