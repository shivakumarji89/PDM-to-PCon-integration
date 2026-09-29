# Engineering Domain

The engineering-object models underneath a configurable product: properties, options, relations, dependencies/exclusions, and Metatype.

| Document | Covers |
|---|---|
| [Property_Model.md](./Property_Model.md) | Property/Option cardinality (0/1/many) |
| [Relation_Model.md](./Relation_Model.md) | `tCOMd_RelObj`/`Relation`/`RelObjRel` model — spec + MDB schema |
| [Dependency_Model.md](./Dependency_Model.md) | `DependentAttributeValues`/`DependentOptionValues`/exclusion tables → pCon/OCD mapping |
| [Metatype.md](./Metatype.md) | Metatype (`go_*` table family) — real HMX repository findings, data relationships, and the (proposed, unimplemented) polymorphic-Metatype workflow |

Metatype is deliberately kept in this Engineering domain rather than under Repository/Article_Encoding: it is a distinct data family (`go_*`, not `ocd_*`/`tCOMd_*`) with its own investigation trail — see `Metatype.md`'s scope note.
