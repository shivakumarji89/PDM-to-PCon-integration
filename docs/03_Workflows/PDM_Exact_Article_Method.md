# Additive PDM-exact article-code method

The PDM-exact helper is an additional source-identity method. It does not
replace or change the existing splitting/reducing engines.

For a PDM article code such as `ABC.123.456`, the method exposes:

- Original PDM source code: `ABC.123.456` (unchanged)
- Matching key: `ABC` (characters before the first dot)
- Suffix: `123.456` (everything after the first dot)
- Article ID, Product ID, and original source order

The index preserves all source rows. If several rows share the same pre-dot
key, it reports that key as duplicated instead of silently choosing one. This
lets downstream logic retain PDM OrderCodeValue/value-ID relationships and
handle collisions explicitly.

The method is intentionally additive and pure: it does not mutate a snapshot
or change current Article / Class Creation reduction behavior. Existing
splitting/reducing engines remain available and unchanged.
