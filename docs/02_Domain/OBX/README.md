# OBX Domain

OBX/packaging generation — belongs to QA (the OBX generator produces the article data QA validates).

| Document | Covers |
|---|---|
| [OBX_Generation.md](./OBX_Generation.md) | Stage-by-stage packaging workflow (inputs/outputs/dependencies) |
| [Contains_Relationship_Graph.md](./Contains_Relationship_Graph.md) | The generated `contains` relationship graph |
| [Generator_Roadmap.md](./Generator_Roadmap.md) | Executive summary of the packaging subsystem + the future-generator implementation roadmap |

**Known current gap (see [`../Article_Encoding/Article_Encoding.md`](../Article_Encoding/Article_Encoding.md) §16):** the current OBX generator (`services/article_obx/article_permutation_service.py`) only orders CodeScheme properties — it does not tokenize `@`/literal characters, insert separators, or evaluate computed/script (`R`-type) properties, and may write an incorrect `<artNr type="final">` value.

For QA/validation of generated OBX output, see [`../../03_Workflows/QA_Validation.md`](../../03_Workflows/QA_Validation.md).
