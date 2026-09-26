# 10 — Canonical MK Workbench Engineering Model

**Status:** Forensic synthesis, evidence-only. No code changed. Builds strictly on the
findings of files 01–09 (and their internal citations into `services/`, `models/`,
`repositories/`); introduces no abstraction that is not directly justified by a gap or
reuse-opportunity those files already identified. Labels: **FACT** / **INFERENCE** /
**UNKNOWN**, as established in file 01 §0.

Per settled conclusion (files 01, 09): **"MDF" is not used anywhere below.** The real
target/source formats are **OCD** (CSV), **XOCD**, **XCF**, **MDB** (Access,
`pcr_data_com_ocd.mdb`), and **EBASE** (release distribution). "MDB/OCD" is used
throughout to mean "the commercial-data package, in whichever of its two current
serializations (`ocd_export_service.py` → MDB, `xocd_export_service.py` → CSV/XOCD) is
relevant."

---

## 1. What "canonical" has to mean here

The brief asks for a model that sits between PDM / pCon Creator / MDB / OCD-XOCD. Files
02 and 07 already establish that MK Workbench **has** such a model — it is
`Snapshot` (`models/snapshot.py`) plus its satellite domain objects
(`models/relation_object.py`, `models/property.py`, etc.) — populated from PDM by
`repositories/pdm_repository.py` and consumed by a family of `services/engineering/*`
generators, then serialized by `ocd_export_service.py` / `xocd_export_service.py`, and
partially deserialized back by `mdb_reverse_engineering_service.py`. This file does not
invent a new container; it states which parts of the existing `Snapshot`-centered
architecture already qualify as "canonical" in the sense the brief wants (a
format-neutral representation any of the four surrounding systems can be translated
to/from), which parts need extension to actually deserve that description, and which
parts are simply missing.

**FACT, restated from file 02 §0:** the `docs/pcon_reference/database_relationships/`
tree and `docs/PDM_MDB_Engineering/06_OCD_Integration.md` describe a *different*,
stale/non-existent pipeline (`mdb_helper.py`, `workspace_snapshot_builder.py`, etc. — none
of these files exist in the repo today). None of the proposals below reintroduce that
stale architecture; they extend the live one (`Snapshot` + `services/engineering/*` +
`ocd_export_service.py`/`xocd_export_service.py`/`mdb_reverse_engineering_service.py`).

---

## 2. Flow 1 — PDM → Canonical Engineering Model → {pCon/OCD exporter, MDB exporter}

```
┌────────────┐     ┌──────────────────────────────┐     ┌───────────────────────┐
│    PDM     │────▶│  Canonical Engineering Model  │────▶│  OCD/XOCD exporter    │──▶ pCon.creator
│ (live DB)  │     │        (Snapshot)             │     │ xocd_export_service.py│    (Import of
│            │     │                                │     └───────────────────────┘    commercial data)
│ Product/   │     │  - snapshot.articles /         │
│ Item/      │     │    article_sets                │     ┌───────────────────────┐
│ Attribute/ │     │  - snapshot.classes            │────▶│   MDB exporter        │──▶ pcr_data_com_
│ Option/    │     │  - snapshot.properties /       │     │ ocd_export_service.py │    ocd.mdb
│ Dependency │     │    property_values              │     └───────────────────────┘
│ tables     │     │  - snapshot.relation_objects   │
│ (26_Data_  │     │  - snapshot.value_tables        │
│  Model.md) │     │  - snapshot.config_value_codes │
│            │     │  - snapshot.option_option_     │
│            │     │    dependencies /               │
│            │     │    attribute_option_            │
│            │     │    dependencies /                │
│            │     │    attribute_value_exclusions   │
└────────────┘     └──────────────────────────────┘     └───────────────────────┘
      │                          ▲
      │                          │
      └── repositories/pdm_repository.py (fetch_*) ─────┘
```

Populating services already in the codebase, per files 03/06/07:
- `EngineeringClassService` — property-class/config-code decode (file 04 Q5, file 08 §7).
- `EngineeringArtbaseService` — base/generic/combination value classification, feeds
  `tCOMd_ArtBase` (file 07 §2.2 item 3, `engineering_artbase_service.py:50-51,59`).
- `EngineeringRelationService` — value-level Precondition + code Action (file 07 §2.2
  items 1-2).
- `EngineeringValueTableService` — `DependentOptionValues` → value-combination table +
  Constraint relation object (file 06 §1, "Implemented").
- `PricingRelationService` / `services/varcond_service.py` — price variant-condition
  Action relations, ported from PDM's own `VarCondThread`/`SuperProductVarCondRelation`
  (file 07 §2.2 item 6, file 03 Price row).

**FACT:** this flow already exists and already deserves the label "canonical model in the
middle" — `Snapshot` is not exporter-specific; both `ocd_export_service.py` and
`xocd_export_service.py` read the same `snapshot.relation_objects`/`snapshot.classes`/etc.
generically (file 07 §2.3). The gap is not "there is no canonical model," it is "the
canonical model does not yet capture everything PDM has and OCD/MDB expect" — see §4.

---

## 3. Flow 2 — MDB/OCD → Canonical Engineering Model → Snapshot/Engineering workflows

```
┌───────────────────────┐     ┌──────────────────────────────┐     ┌───────────────────┐
│ pcr_data_com_ocd.mdb  │────▶│  Canonical Engineering Model  │────▶│ Engineering /     │
│ (tCOMd_* rows)        │     │        (Snapshot)             │     │ review workflows  │
│                       │     │                                │     │ (curation UI,     │
│ read by:              │     │  same object as Flow 1 —       │     │  add_relation /   │
│ mdb_reverse_          │     │  reimported relation objects   │     │  remove_relation,  │
│ engineering_service.py│     │  carry rel_obj_id/relation_id/ │     │  engineering_      │
│ .read() / .import_    │     │  relation_name so a round-trip │     │  relation_service   │
│ snapshot()             │     │  can preserve original keys    │     │  .py:392-454)       │
│                       │     │  (models/relation_object.py:   │     │                   │
│ STRUCTURAL_TABLES /   │     │  31-51, file 07 §2.1)           │     └───────────────────┘
│ PRICE_TABLES /        │     │                                │
│ PACKAGE_TABLES        │     │  "preserve if already           │     ┌───────────────────┐
│ allow-list             │     │  imported/edited" guard —       │────▶│ Re-export         │
│ (file 02 §0)          │     │  ocd_export_service.py:663-665  │     │ (same two          │
└───────────────────────┘     └──────────────────────────────┘     │ exporters as       │
                                                                      │ Flow 1)            │
                                                                      └───────────────────┘
```

**FACT (file 07 §7):** this direction is real but asymmetric and only partially safe
today. The reverse-engineering reader (`mdb_reverse_engineering_service.py:299-390`) is
**more general than the writer**: it correctly parses property-level `RelObjID` bindings
that the generator-side of Flow 1 never produces, and it round-trips whatever
`com_RelObjTypeCode`/`com_RelObjDomainCode`/`com_RelationBody` it finds without filtering
by type — so an imported MDB using Selection condition/Constraint/Reaction/Post-Reaction
or BOI/Packaging/Tax domains lands in `Snapshot.relation_objects` faithfully. But the
"preserve" guard in `ocd_export_service.py` (`if not snapshot.relation_objects`) is an
**all-or-nothing** fork, not a per-relation merge: once *any* relation object exists
(imported or hand-edited), canonical derivation is skipped entirely for the whole
snapshot, so newly-added values/properties never get their canonical Precondition/Action
relations generated on top of a previously-imported exotic set. This is the single
clearest place the "canonical model" is not yet actually canonical for round-tripping —
it behaves more like "whichever set showed up first, keep it."

---

## 4. Reuse / extend / missing — per component

| Component | Cited service/file | Status | Justification |
|---|---|---|---|
| Snapshot container itself | `models/snapshot.py` | **Reuse as-is** | Already format-neutral; both exporters and the reverse-engineering reader already target it generically (file 02 §0, file 07 §2.3). |
| Article/base-article identity | `EngineeringClassService`, `_base_by_article` (file 03 Base Article row) | **Reuse as-is** | Matches pCon's single-Article/base-article-number model exactly (file 04 Q1-Q4); no PDM "final article" row needs to be modeled since pCon has none either (file 04 bottom line). |
| Value classification (generic/base/combination) | `EngineeringArtbaseService` (`engineering_artbase_service.py:50-51,59`) | **Reuse as-is** | Deliberate, already-working division of labour between `ArtBase` and relation-based Precondition (file 07 §2.2 item 3); this is the cleanest, most-verified mapping in the whole investigation (file 03 Article restriction row). |
| Value-level Precondition / code Action generation | `EngineeringRelationService.build_relation_objects` | **Reuse as-is** | Fully mechanical/deterministic from article-set co-occurrence and value-code data (file 07 §5 items 1-2); "as close to already proven safe as anything in this codebase." |
| Pricing variant-condition Action relations | `PricingRelationService`, `services/varcond_service.py` | **Reuse as-is** | A faithful, like-for-like port of PDM's own `VarCondThread`/`SuperProductVarCondRelation` (file 07 §5 item 3, file 03 Price row) — not a reinvention. |
| `DependentOptionValues` → Constraint + value-combination table | `EngineeringValueTableService.build_dependency_tables` | **Reuse as-is; template for extension** | Confirmed implemented end-to-end (file 06 §1). Its shape (one table + one `C_<TABLE>` Constraint per parent-with-dependents, chain-aware per file 05 Q7) is the right *pattern* to extend to the two mechanisms below — no new abstraction needed, just new inputs. |
| `DependentAttributeValues` (cross-kind availability) | `snapshot.attribute_option_dependencies` (`models/snapshot.py:117-118`) modeled; consumption **UNKNOWN** | **Needs extension** | Field exists and is fetched (`repositories/pdm_repository.py:699-710`), but `build_dependency_tables` as read in this investigation only references `option_option_dependencies` (file 05 Q6, file 06 §2). Extension = feed this edge kind into the same value-combination-table builder used for `DependentOptionValues`, once a grep confirms it is not already wired elsewhere. |
| `AttributeValueExclusions` (negative joint-validity rule) | `snapshot.attribute_value_exclusions` modeled; no consumer found | **Missing generator** | Modeled in-memory (`models/snapshot.py:112-114`) and fetched (`repositories/pdm_repository.py:681-696`), but no code converts it into a Constraint `Restrictions:` clause or into omitted rows in a value-combination table (file 06 §3, "likely GAP"). This is semantically the *opposite polarity* of `DependentOptionValues` (omission vs. enablement) and needs a genuinely new code path, not just a new input to the existing builder, because the existing builder only ever emits positive rows. |
| `CatalogueProductOptionExclusions` (base-article-scoped mandatory exclusion) | none found | **Missing: fetch + generator** | No repository method or service reads this table at all (file 06 §5). Natural target is `ArtBase` (same base-article granularity as `EngineeringArtbaseService` already handles) — this is an extension of an existing table's *inputs*, not a new export mechanism. |
| `CatalogueItemOptionExclusions` (Item/SKU-scoped mandatory exclusion) | none found | **Missing, and structurally hard** | No clean pCon target exists at all (file 04 Q7-Q8: no `tCOMd_FinalArticle`); would require a Precondition/Constraint keyed on the decoded variant code (file 06 §5) — this is the one place a genuinely new mechanism, not just new inputs to an old one, is needed. |
| Property-level / Article-level / PropertyClass-level relation binding | schema columns exist (`com_RelObjID` on `tCOMd_Property`/`tCOMd_Article`/`tCOMd_ArticleClass`), always written `None` (file 02 §2 rows 6/10/13; file 07 §3 item 1) | **Missing write path (reader already supports it)** | The reverse-engineering reader already parses `prop_relobj` (file 07 §7) — the gap is purely on the generation side. This is a real "genuinely missing" item per the brief's own example, not a reuse candidate, because nothing in `EngineeringRelationService` currently produces a relation scoped above PropertyValue. |
| Selection condition / Constraint(article-level) / Reaction / Post-Reaction generation | none found (file 07 §3 items 1-2, §6 item 1) | **Missing, and not mechanically derivable** | File 07 §6 is explicit: these "encode editorial/business judgment... None of that intent is captured anywhere in the current source data." This is not an extension of existing services — it would require either new PDM-side input that does not currently exist, or permanent Review-Required human authoring (see file 11). |
| BOI / Packaging / Tax domain relations | none found (file 02 §3.1, file 07 §3 item 3) | **Missing; source-of-truth UNKNOWN** | File 07 §6 item 3: "their source-of-truth is UNKNOWN." Not safely automatable until a PDM-side source is identified. |
| Real Option-collapse layer | Implicit today inside `_properties`/`_property_values` builders in both exporters (comment: "OCD unifies options into properties," file 02 §1) | **Genuinely missing as an explicit layer** | This is the item the brief names directly. Today the PDM Option → pCon Property (`Usage=Configuration`) collapse is an implicit side-effect of shared builder code, distinguished only by an internal `com_PropTypeCode` marking (file 03 Option row). There is no single named service that states the collapse rule, validates it against pCon's own constraints (numeric properties always mandatory regardless of `Obligatory`, `Multivalued`/`Multioption` unsupported at runtime for Configuration scope — file 01 §5, file 05 Q2), or preserves enough provenance to distinguish "this was originally a PDM Attribute" from "this was originally a PDM Option" for audit/round-trip purposes. Making this an explicit, named layer (not a new data model — the data already lives in `snapshot.properties`/`property_values` with `com_PropTypeCode`) is the one clear net-new architectural component this investigation justifies. |
| Property Class sourcing | `class_name` inferred from property text, not sourced from PDM (file 03 Class row, `02_PDM_Data_Model.md`/`03_Engineering_Object_Mapping.md` gap) | **Missing real source; current synthesis is a stand-in, not a bug** | pCon requires Property Class as mandatory (file 01 §8); PDM has never populated a real source for it. This is flagged, not silently accepted — any canonical model must either (a) formalize "class name inferred from property text" as an explicit, documented, reviewable derivation rule, or (b) get a real PDM-side class-grouping source identified. Neither is resolved here; see file 13. |

---

## 5. What the canonical model must NOT do (explicit non-goals, per the evidence)

1. **Must not introduce a `FinalArticle` entity.** File 04's bottom line is unambiguous:
   no source (manual, OCD spec, MDB schema, current exporter, PDM's own legacy exporter)
   models a stored parent-child row between base and final article. The one place a
   final-identity *row* genuinely exists is PDM's own `Item` table — that is a PDM-side
   fact to reconcile with generation-time computation, not a reason to add a pCon-side
   table that doesn't exist on any target system.
2. **Must not introduce a first-class `Option` object distinct from `Property`.** File 03's
   clearest non-mapping: neither the legacy PDM exporter nor the current MK Workbench
   exporter ever writes `tCOMd_Option`/`tCOMd_OptionValue`. Modeling PDM's real, DB-backed
   `Option` as an in-memory concept (which `Snapshot` already does, per file 02 §1) is
   fine and necessary for provenance; treating it as a genuine OCD/MDB *write target* is
   not.
3. **Must not assume MDB's `RelObjRel` join-table shape is the canonical relation shape.**
   File 02 §3.2 / file 07 §1.2: XOCD's native shape (name-linked, no join table) matches
   the OCD spec directly; MDB's 3-table join is an MDB-specific normalization. The
   canonical in-memory `RelationObject` model already abstracts over this correctly
   (`models/relation_object.py`) — any extension must preserve that neutrality rather than
   baking in MDB's join-table assumption.
4. **Must not assume `ArtBase`'s string-keyed shape generalizes.** File 02 §4 item 5: every
   other structural table is ID/surrogate-keyed; `ArtBase` alone is name-keyed. A canonical
   model that assumes uniform ID-based joins across all tables would be wrong for this one
   table specifically.
