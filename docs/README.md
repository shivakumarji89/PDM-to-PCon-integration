# MK Product Workbench — Documentation

This is the documentation entry point. It is organized by **what the system is and does**, not by the history of how it was investigated.

## Where to go

| I want to... | Go to |
|---|---|
| Understand the overall system pipeline | [`01_Architecture/`](./01_Architecture/) |
| Understand a specific domain concept (PDM, Repository/Snapshot, Engineering, Product, Permutation, Article Encoding, Pricing, OBX) | [`02_Domain/`](./02_Domain/) |
| Understand a cross-cutting process (QA/validation) | [`03_Workflows/`](./03_Workflows/) |
| Read an external OFML/OCD/OAP spec, or MK's own pCon investigation narrative | [`04_Reference/`](./04_Reference/) |
| Find historical/superseded material | [`99_Archive/`](./99_Archive/) |

## Layout

```
docs/
├── README.md                    <- you are here
├── 01_Architecture/              System pipeline, module design, shared workflow architecture
├── 02_Domain/                    Current, authoritative domain knowledge (one canonical doc per concept)
│   ├── PDM/                      Legacy PDM business logic + current PDM↔MDB bridge + reduction/family rules
│   ├── Repository/               Repository/MDB/OCD model, Snapshot (canonical), table catalogue
│   ├── Engineering/               Property, Relation, Dependency/Exclusion, Metatype
│   ├── Product/                   Article/Product/Configuration model
│   ├── Permutation/               Permutation model + current implementation gap analysis
│   ├── Article_Encoding/          Article Encoding / CodeScheme, Variant Code, Final Article Number
│   ├── Pricing/                   Pricing model, Variant Condition
│   └── OBX/                       OBX/packaging generation
├── 03_Workflows/                 QA/validation and other cross-cutting processes
├── 04_Reference/                 External vendor specs + MK's own investigation narrative
│   ├── Engineering_Reference/     Curated OFML/OCD/ODB/OAP/Metatype industry knowledge base
│   ├── pCon/
│   │   ├── Specifications/       Verbatim EasternGraphics/pCon vendor specs
│   │   └── Investigation/        MK Workbench's own forensic pCon findings (narrative)
│   └── Legacy/                   Raw legacy-DPS SQL extraction
└── 99_Archive/                   Superseded / historical / temporary material (never current truth)
```

## Reading conventions

- Every major folder has its own `README.md` explaining what belongs there and pointing to the authoritative document(s) for that area.
- A document with `STATUS: ARCHIVED` at the top is never current — always follow its `SUPERSEDED BY` pointer.
- `docs/04_Reference/pCon/Specifications/` and `docs/04_Reference/Engineering_Reference/` are external/vendor or industry-standard reference material — cite them, don't duplicate their explanations elsewhere.
- Established architectural decisions that later documents must not silently contradict: **Snapshot** is the canonical repository representation ([`02_Domain/Repository/Snapshot.md`](./02_Domain/Repository/Snapshot.md)); a **permutation** is `Base Article + Property Values + Relation/Dependency Conditions + Encoding`, not an existing final-Article row ([`02_Domain/Permutation/`](./02_Domain/Permutation/)); pricing resolves via `Base Article + Variant Condition`, not a simple final-article lookup ([`02_Domain/Pricing/`](./02_Domain/Pricing/)); Article Encoding/CodeScheme cannot be modeled as `base + concatenated property codes` ([`02_Domain/Article_Encoding/`](./02_Domain/Article_Encoding/)).

See [`DOCUMENTATION_CLEANUP_REPORT.md`](./DOCUMENTATION_CLEANUP_REPORT.md) for the full record of this restructuring (before/after counts, what was merged/moved/archived/deleted).
