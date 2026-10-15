"""Reference and key rules the Metatype relationship resolver checks.

Every rule cites its evidence. "documented" = stated in MT_1.18.0 (line numbers
refer to ``docs/04_Reference/pCon/Specifications/MT_1.18.0_en.md``); "observed" =
visible in the HMX data and the project notes (``Metatype.md`` section 4) but
not stated explicitly by the manual.

Deliberately NOT checked (evidence says the reference is not resolvable inside
one family, or is not a requirement):

* ``go_actions.param_1`` of ``CH_PROP``/``CON_CH_PROP`` - names a property of the
  *child* metatype (670 of 744 such rows in the 49 real families are not own
  properties).
* ``go_types.filter`` of ``na`` properties - may name child properties (manual
  change note for MT 1.7.x, line 3867).
* ``go_freenumeric.name`` - "free properties are not bound to the metatypes in
  table go_types" (line 2576).
* ``go_texts.key`` coverage - texts may live in resource files (manual section 5);
  1,549 of 1,889 real property names have no go_texts row.
* ``go_children.child_key`` uniqueness - one key legitimately repeats for
  conditional alternatives (Verus example; 1,011 repeated rows in real data).
* Tables that are empty in every real family (go_inhproperties, go_nativeproperties,
  go_attptsorder, go_childmoving, go_interactors, go_itemplates, go_feedback,
  go_metainfo, go_attptgeo): their references are documented but unverifiable.
"""
from __future__ import annotations

from models.metatype_relationships import DuplicateSpec, RelationshipSpec

R = RelationshipSpec

RELATIONSHIPS: tuple[RelationshipSpec, ...] = (
    R("articles.id->types.id", "Article is bound to a defined metatype",
      "go_articles", ("id",), "go_types", ("id",), "documented",
      ignore_values=("id", ("_native_",)),
      note="line 1125; id '_native_' is reserved (line 1146)."),
    R("articles.prm_key->properties.key", "Article's standard-property set exists",
      "go_articles", ("prm_key",), "go_properties", ("key",), "observed", severity="warning",
      note="Repository: 791 of 820 resolve, schema column is prm_key. UNRESOLVED in the manual: line 1136 "
           "says the set is located in go_noproperties, while line 1195 places it in go_properties."),
    R("articles.chprm_key->childprops.key", "Article's child-property sets exist",
      "go_articles", ("chprm_key",), "go_childprops", ("key",), "documented",
      list_columns=("chprm_key",), note="line 1141; several keys separated by commas."),
    R("childprops.child_key->children.child_key", "Child-property value creates a defined child",
      "go_childprops", ("child_key",), "go_children", ("child_key",), "documented",
      list_columns=("child_key",), note="line 1338; several keys separated by commas."),
    R("childprops.name->types.name", "Child-property names a property of the owning metatype",
      "go_childprops", ("key", "name"), "go_types", ("id", "name"), "documented", custom="owner_scoped",
      note="line 1334. The owning metatype(s) are those whose go_articles row lists the key in chprm_key; "
           "rows whose key no article uses cannot be scoped and are skipped."),
    R("properties.id->types.id", "Property row belongs to a defined metatype",
      "go_properties", ("id",), "go_types", ("id",), "documented", note="line 1193."),
    R("properties.name->types.name", "Property row sets a property the metatype defines",
      "go_properties", ("id", "name"), "go_types", ("id", "name"), "documented",
      note="line 1136: values are 'according to the properties defined in go_types for the metatype'."),
    R("noproperties.key->articles.prm_key", "Excluded-native-property set belongs to an article set",
      "go_noproperties", ("key",), "go_articles", ("prm_key",), "documented",
      note="line 1561. Empty in every real family, so unverified against data."),
    R("propvalues.id->types.id", "Value restriction belongs to a defined metatype",
      "go_propvalues", ("id",), "go_types", ("id",), "documented", note="line 1489."),
    R("propvalues.name->types.name", "Value restriction names a defined property",
      "go_propvalues", ("id", "name"), "go_types", ("id", "name"), "documented", note="line 1491."),
    R("propclasses.id->types.id", "Property class belongs to a defined metatype",
      "go_propclasses", ("id",), "go_types", ("id",), "documented",
      note="line 2912; a blank id means 'all metatypes' and is not a reference."),
    R("propclasses.prop_name->types.name", "Property class names a defined property",
      "go_propclasses", ("id", "prop_name"), "go_types", ("id", "name"), "documented", wildcard_blank="id",
      note="line 2916; with a blank id the name must exist for some metatype."),
    R("setup.id->types.id", "Setup flag belongs to a defined metatype",
      "go_setup", ("id",), "go_types", ("id",), "documented", note="line 2930."),
    R("classes.id->types.id", "Class mapping belongs to a defined metatype",
      "go_classes", ("id",), "go_types", ("id",), "documented", ignore_values=("id", ("*",)),
      note="line 2840; '*' sets the default class."),
    R("attpt.id->types.id", "Attachment point belongs to a defined metatype",
      "go_attpt", ("id",), "go_types", ("id",), "documented", note="line 2024."),
    R("actions.id->types.id", "Action belongs to a defined metatype",
      "go_actions", ("id",), "go_types", ("id",), "documented", note="line 1795."),
    R("actions.own_key->types.name", "CON action names the properties that trigger it",
      "go_actions", ("id", "own_key"), "go_types", ("id", "name"), "documented",
      list_columns=("own_key",), only_when=("direction", ("CON",)), note="line 1802."),
    R("actions.foreign_key->children.child_key", "CON action names the children it affects",
      "go_actions", ("foreign_key",), "go_children", ("child_key",), "documented",
      list_columns=("foreign_key",), only_when=("direction", ("CON",)), note="line 1812; may be empty."),
    R("actions.param_1->types.name", "Property action targets a property of its own metatype",
      "go_actions", ("id", "param_1"), "go_types", ("id", "name"), "documented",
      only_when=("action", ("SET_PROP", "CON_PROP")),
      note="line 1908-1911; CH_PROP/CON_CH_PROP address the child and are not checked."),
    R("actions.param_2->children.child_key", "ADD_CHILD names the child to create",
      "go_actions", ("param_2",), "go_children", ("child_key",), "documented",
      list_columns=("param_2",), only_when=("action", ("ADD_CHILD",)), note="line 1930."),
    R("types.filter->types.name", "Property filter names properties of the same metatype",
      "go_types", ("id", "filter"), "go_types", ("id", "name"), "documented",
      list_columns=("filter",), except_when=("format", ("na",)), severity="warning",
      note="line 973; 'na' properties are excluded because their filter may name child properties."),
)

D = DuplicateSpec

DUPLICATES: tuple[DuplicateSpec, ...] = (
    D("types(id,name)", "A property is defined once per metatype", "go_types", ("id", "name"), "documented",
      severity="error", note="line 634: each entry defines exactly one property of the metatype."),
    D("properties(id,key,name)", "A parameter set sets each property once", "go_properties",
      ("id", "key", "name"), "inferred", note="line 1154: one line per parameter."),
    D("articles(id,article_nr,prm_key,chprm_key)", "Identical article rows are redundant", "go_articles",
      ("id", "article_nr", "prm_key", "chprm_key"), "documented",
      note="line 1152: identical entries are only supported if they refer to different parameter sets."),
    D("childprops(key,name,value)", "A property value maps to one child entry per set", "go_childprops",
      ("key", "name", "value"), "inferred"),
    D("propvalues(id,name,value)", "A value restriction is listed once", "go_propvalues",
      ("id", "name", "value"), "inferred"),
    D("propclasses(id,prop_name)", "A property has one class per metatype", "go_propclasses",
      ("id", "prop_name"), "inferred"),
    D("setup(id,key)", "A setup flag is set once per metatype", "go_setup", ("id", "key"), "inferred"),
)
