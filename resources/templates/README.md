# Bundled MDB template setup

Keep the original template package and its entire folder tree under this directory. Do not flatten, rename, or remove sibling files/folders; the current direct MDB exporter reads only the MDB file (`ocd.mdb` or `ocd.mdb`).

Supported template families:

- HM seating: a folder named `Seating_Template`
- HM tables: a folder named `Tables_Template`
- KNOLL: the original folder named `_TEMPLATE_KNOLL`

The resolver supports these folders directly under `resources/templates/`, under `resources/templates/1_WS_Templates/`, or under an extra wrapper directory. The MDB must be inside the matching template folder. The resolver accepts either `ocd.mdb` or `ocd.mdb`.

Expected examples:

```text
resources/templates/
  1_WS_Templates/
    Seating_Template/
      ocd.mdb
      ...all original sibling files and folders...
    Tables_Template/
      ocd.mdb
      ...all original sibling files and folders...
    _TEMPLATE_KNOLL/
      ocd.mdb
      ...all original sibling files and folders...
```

Only add the template files that actually exist in the source package. This README is not a substitute for the original MDB files.
