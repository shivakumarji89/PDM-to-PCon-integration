# Article Encoding Domain

**Confirmed finding (high priority — do not lose this during any future edit):** Article Encoding cannot be modeled as `base article + concatenated property codes`. Real CodeScheme grammars contain literal characters (including literal spaces), separators, grouping, ordering rules, and — for ranges like Aeron — computed/relation-driven script-style encoding. Spacing, separators, grouping, order, and conditional segments must all be derived from the actual CodeScheme, not assumed.

| Document | Covers |
|---|---|
| [Article_Encoding.md](./Article_Encoding.md) | **Canonical.** Article Encoding and CodeScheme, backed by real HMX repository CSV evidence (Aeron, Cosm, Atlas, Civic_tables, Lino, Hush, Fold) |
| [Variant_Code_and_Final_Article_Number.md](./Variant_Code_and_Final_Article_Number.md) | Variant Code / Final Article Number, via a real Nevi (`DWE4`) end-to-end trace |

Real evidence source: `C:\HermanMillerOFMLSVN\Staging\HermanMiller\_repository\hmx\` (`ocd_article.csv`, `ocd_artbase.csv`, `ocd_codescheme.csv`, `ocd_property.csv`, `ocd_propertyvalue.csv`, `ocd_relation.csv`, `ocd_relationobj.csv`, `ocd_price.csv`).

See also: [`../Permutation/`](../Permutation/) (how encoding fits into permutation generation) and [`../OBX/OBX_Generation.md`](../OBX/OBX_Generation.md) (where a current OBX-generation gap tied to encoding is diffed against real behavior).
