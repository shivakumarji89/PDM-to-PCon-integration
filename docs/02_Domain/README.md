# Domain Documentation

This is the **current, authoritative knowledge base** for what MK Workbench models and how it works — organized by subject, not by investigation history. Each subfolder below has exactly one (or a small, non-competing set of) canonical document(s) per concept.

| Domain | Canonical concept(s) |
|---|---|
| [PDM/](./PDM/) | Legacy PDM business logic, the PDM↔MDB/OCD bridge, base-article reduction/family rules, SKU decode |
| [Repository/](./Repository/) | The repository (MDB/OCD) model, **Snapshot** (the canonical repository representation), table catalogue |
| [Engineering/](./Engineering/) | Property/Option, Relation, Dependency/Exclusion models, Metatype |
| [Product/](./Product/) | Article/Product/Configuration model |
| [Permutation/](./Permutation/) | Permutation model (Base Article + Property Values + Relation/Dependency Conditions + Encoding) and the current implementation gap analysis |
| [Article_Encoding/](./Article_Encoding/) | Article Encoding / CodeScheme, Variant Code, Final Article Number |
| [Pricing/](./Pricing/) | Pricing model, price resolution, Variant Condition |
| [OBX/](./OBX/) | OBX/packaging generation, the `contains` relationship graph, the generator roadmap |

For **external** OFML/OCD/OAP/Metatype specifications, MK's own pCon investigation notes, and legacy-DPS SQL extraction, see [`../04_Reference/`](../04_Reference/) instead — reference material is kept separate from domain conclusions.

For historical/superseded material, see [`../99_Archive/`](../99_Archive/).
