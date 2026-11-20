# Articles incremental vs Development export parity

Reference: `XocdExportService._base_codes()`, `OcdExportService._articles()`,
`OcdExportService._code_schemes()`, and `ArticleMdbExportService`.

## Mapping rules aligned

- Base article identity follows Development order and rule: price-base mapping first,
  then `member.reduced_article`; no additional source-code dot-splitting fallback.
- Selected source article IDs filter engineering members before base-code de-duplication.
- One MDB Article row is produced per distinct base code, retaining first-seen member order.
- The CodeScheme name is the base article code, matching Development's
  `scheme_by_code[code] = code`.
- The session exporter retains its own stable primary keys rather than using
  Development's per-full-export sequential IDs.

## Intentional incremental differences

- `tCOMd_CodeScheme` is initially written with only the mandatory `@` code
  positions. Development appends Class/Property tokens in the full export;
  the incremental Class Creation workflow must extend the existing scheme body.
- Relation-object and article-text IDs are reused only when matching rows already
  exist in the session MDB. Otherwise they remain unlinked for the Relation and
  Text workflows to resolve. Development creates these records in the same full
  export and links them immediately.
- Article updates are non-destructive upserts. Existing IDs and unrelated tables
  are retained; Development's full export starts from a clean template and
  assigns sequential IDs.

## Validation status

Focused regression tests cover missing reduced bases, source-article lookup,
price-base precedence, CodeScheme naming, selection and first-seen de-duplication.
They are included in the Incremental MDB Workflow CI job and passed: **5 passed**.
The Windows ACE/MDB integration tests and full-export row comparison still require
execution in the local application environment.
