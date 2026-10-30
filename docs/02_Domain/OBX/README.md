# OBX Domain

OBX/packaging generation — belongs to QA (the OBX generator produces the article data QA validates).

| Document | Covers |
|---|---|
| [OBX_Generation.md](./OBX_Generation.md) | Stage-by-stage packaging workflow (inputs/outputs/dependencies) |
| [Contains_Relationship_Graph.md](./Contains_Relationship_Graph.md) | The generated `contains` relationship graph |
| [Generator_Roadmap.md](./Generator_Roadmap.md) | Executive summary of the packaging subsystem + the future-generator implementation roadmap |

| [OCD_Engine.md](./OCD_Engine.md) | The standalone OCD engine behind the Article OBX generator: relations, CodeScheme, VARCOND, pricing; verified datasets, limits, decisions needed, performance |

**Status:** the former CodeScheme/relation gap (`Article_Encoding.md` §16) is closed by `services/ocd_engine`; what is and is not verified against pCon is stated in [OCD_Engine.md](./OCD_Engine.md).

For QA/validation of generated OBX output, see [`../../03_Workflows/QA_Validation.md`](../../03_Workflows/QA_Validation.md).
