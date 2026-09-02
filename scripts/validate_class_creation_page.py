"""Headless validation for the Class Creation workspace (additive workflow).

Verifies, without a live PDM:
  * the page builds three sections - Attributes, Options, Visual / Misc;
  * value rows carry an editable Code (order-code letter) and a selection
    checkbox, and edits route to the correct value service;
  * the Visual/Misc "type to add" row creates an engineering PropertyDefinition;
  * inline rename and Delete-key removal work on created definitions;
  * PDM source properties/options are never mutated in structure.

Run:  $env:QT_QPA_PLATFORM="offscreen"; $env:PYTHONPATH="."; \
      python scripts/validate_class_creation_page.py
"""
from __future__ import annotations

import sys

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from core.application_context import ApplicationContext
from models.article import Article
from models.option import Option
from models.option_value import OptionValue
from models.product import Product
from models.property import Property
from models.property_value import PropertyValue
from ui.pages.class_creation_page import (
    _COL_CODE,
    _COL_NAME,
    _COL_RELATION,
    _COL_SELECTED,
    ClassCreationPage,
)


def _snapshot(ctx: ApplicationContext):
    product = Product(id="p1", code="P1", name="Prod", range_name="Bolster")
    snap = ctx.snapshot_manager.create_empty_snapshot(product)
    snap.id = "p1"

    prop = Property(id="pr1", code="PR1", name="Colour")
    v1 = PropertyValue(id="pv1", property_id="pr1", value="Red", code="")
    v2 = PropertyValue(id="pv2", property_id="pr1", value="Blue", code="")
    prop.values.extend([v1, v2])
    snap.properties.append(prop)
    snap.property_values.extend([v1, v2])

    option = Option(id="op1", code="OP1", name="Base")
    ov1 = OptionValue(id="ov1", option_id="op1", value="Sled", code="")
    option.values.append(ov1)
    snap.options.append(option)
    snap.option_values.append(ov1)

    # Two articles that split into base 'P1' + remaining 'AB' / 'BA', so the
    # Colour slice (width 1, pos 0) discovers distinct codes {A, B}.
    snap.articles.append(Article(id="a1", code="P1AB", product_id="p1"))
    snap.articles.append(Article(id="a2", code="P1BA", product_id="p1"))
    # Product-level property links drive article-set classification.
    snap.product_property_value_ids = {"p1": ["pv1", "pv2"]}

    ctx.engineering_initialization_service.initialize(snap)
    for member in snap.engineering.families[0].members:
        ctx.engineering_member_service.set_reduced_article(member, "P1")
    return snap, v1, option


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)  # noqa: F841
    ctx = ApplicationContext()
    snap, v1, option = _snapshot(ctx)

    page = ClassCreationPage(ctx)

    def attr_prop():
        """The single property row (top-level in the flat unique-property list)."""
        return page._attr_tree.topLevelItem(0)

    # 1) Three module cards, renamed <Category>_* (category = Bolster).
    assert page._attr_tree.topLevelItemCount() == 1  # one property (Colour)
    assert page._attr_tree.topLevelItem(0).childCount() == 2  # Red + Blue values
    assert page._opt_tree.topLevelItemCount() == 1   # one option
    assert page._misc_tree.topLevelItemCount() == 1  # just the add-row initially
    assert page._attr_box.title() == "Bolster_Attribute", page._attr_box.title()
    assert page._opt_box.title() == "Bolster_Options"
    assert page._misc_box.title() == "Bolster_Visual"
    print("OK: three cards renamed <Category>_* (Bolster_Attribute/_Options/_Visual)")

    # 1b) Cards are collapsible ("hide and see"): collapsing hands its stretch
    #     to the expanded cards.
    assert page._attr_box.is_expanded()
    page._attr_box.set_expanded(False)
    assert not page._attr_box.is_expanded()
    assert page._body_layout.stretch(page._body_layout.indexOf(page._attr_box)) == 0
    page._attr_box.set_expanded(True)
    assert page._body_layout.stretch(page._body_layout.indexOf(page._attr_box)) == 1
    print("OK: cards collapse/expand and redistribute vertical stretch")

    # 2) Attribute value: edit Code (col 1). The property row shows its
    #    relation object (B_<property name>) in the last column.
    prop_node = attr_prop()
    red = prop_node.child(0)
    red.setText(_COL_CODE, "R")
    assert v1.code == "R", v1.code
    prop_node = attr_prop()   # re-fetch (repopulated)
    # Single base master -> every value is generic -> Relation cell is blank.
    assert prop_node.text(_COL_RELATION) == "", prop_node.text(_COL_RELATION)
    assert prop_node.child(0).text(_COL_RELATION) == "", prop_node.child(0).text(_COL_RELATION)
    # The raw name helper still builds the PascalCase relation object name.
    assert page._relation_object("Number of Fabrics") == "B_NumberOfFabrics"
    print("OK: attribute value Code edit + property relation object shown")

    # 2b) Editing is enabled: Code cell (col 1) + Width cell (col 2) carry the
    #     editable marker, and double-click edits (not expands).
    prop_node = attr_prop()
    assert prop_node.data(2, Qt.ItemDataRole.UserRole + 1) == {2}
    assert prop_node.child(0).data(1, Qt.ItemDataRole.UserRole + 1) == {1}
    assert not page._attr_tree.expandsOnDoubleClick()
    print("OK: Code/Width cells are editable (double-click edits, click expands)")

    # 3) Option row: option-level selection + expandable to its values.
    opt_row = page._opt_tree.topLevelItem(0)
    assert opt_row.childCount() == 1, "option expands to its values"
    assert opt_row.child(0).text(0) == "Sled"
    assert opt_row.data(_COL_NAME, Qt.ItemDataRole.UserRole)[0] == "option"
    assert not page._opt_tree.expandsOnDoubleClick()
    opt_row.setCheckState(_COL_NAME, Qt.CheckState.Checked)
    assert option.selected is True
    assert option in ctx.option_service.selected_options()
    print("OK: option row selection routes + expands to its values")

    # 4) Visual/Misc: type a name in the add-row -> creates a definition.
    misc = page._misc_tree
    add_row = misc.topLevelItem(misc.topLevelItemCount() - 1)
    assert add_row.data(_COL_NAME, Qt.ItemDataRole.UserRole)[0] == "add"
    add_row.setText(_COL_NAME, "Width")
    names = [d.name for d in snap.engineering.properties]
    assert names == ["Width"], names
    print("OK: typing in the add-row creates an engineering property")

    # 5) Inline rename of the created definition.
    definition = page._misc_tree.topLevelItem(0)
    assert definition.data(_COL_NAME, Qt.ItemDataRole.UserRole)[0] == "definition"
    definition.setText(_COL_NAME, "Depth")
    names = [d.name for d in snap.engineering.properties]
    assert names == ["Depth"], names
    print("OK: inline rename updates the engineering property")

    # 6) Delete key removes the selected definition.
    definition = page._misc_tree.topLevelItem(0)
    page._misc_tree.setCurrentItem(definition)
    page._misc_tree.keyPressEvent(
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Delete, Qt.KeyboardModifier.NoModifier)
    )
    assert snap.engineering.properties == [], snap.engineering.properties
    print("OK: Delete key removes the engineering property")

    # 7) PDM source untouched in structure (still 1 property, 1 option).
    assert len(snap.properties) == 1 and len(snap.options) == 1
    print("OK: PDM source properties/options structurally untouched")

    # 8) Standard <Category>_* classes auto-created + properties auto-grouped.
    classes = ctx.engineering_class_service.get_classes(snap)
    assert sorted(c.name for c in classes) == [
        "Bolster_Attribute", "Bolster_Options", "Bolster_Visual",
    ], [c.name for c in classes]
    attr_cls = next(c for c in classes if c.name == "Bolster_Attribute")
    opt_cls = next(c for c in classes if c.name == "Bolster_Options")
    assert any(a.property_id == "pr1" for a in attr_cls.properties)   # Colour
    assert any(a.property_id == "op1" for a in opt_cls.properties)    # Base option
    print("OK: standard <Category>_* classes auto-created + auto-grouped")

    # 9) Set Colour Width 1 -> discovers the distinct codes across all articles
    #    ({A, B}) and flags them unassigned in the Sliced column.
    # Clear the section-2 manual code so Colour is uncoded again: its Width then
    # defaults to 0 (a coded value would take its width from the code), letting
    # this step exercise setting the Width.
    v1.code = ""
    page.refresh()
    prop_node = attr_prop()
    prop_node.setText(2, "1")                                         # Width column
    assert next(a for a in attr_cls.properties if a.property_id == "pr1").width == 1
    prop_node = attr_prop()
    sliced = prop_node.text(3)
    assert "A" in sliced and "B" in sliced, sliced
    assert "\u26A0" in sliced, sliced
    print("OK: setting Width discovers distinct codes across articles")

    # 9b) Value Code cell has an embedded pull-down of the discovered codes.
    prop_node = attr_prop()
    combo = page._attr_tree.itemWidget(prop_node.child(0), 1)
    assert combo is not None, "no embedded code pull-down"
    assert [combo.itemText(i) for i in range(combo.count())] == ["", "A", "B"]
    print("OK: value Code cell is an embedded pull-down of discovered codes")

    # 10) Pick a code from the pull-down -> writes the value code (single source).
    combo.setCurrentText("A")   # Red -> A
    assert v1.code == "A", v1.code
    print("OK: picking a code from the pull-down writes the value code")

    # 11) Coding the remaining value clears the discovered-codes warning.
    blue = next(v for v in snap.property_values if v.value == "Blue")
    blue.code = "B"
    page.refresh()
    assert v1.code == "A" and blue.code == "B", (v1.code, blue.code)
    assert "\u26A0" not in attr_prop().text(3)
    print("OK: coding the remaining value clears the discovered-codes warning")

    # 12) A rebuild (e.g. Width change) keeps the property row expanded.
    prop_node = attr_prop()
    prop_node.setExpanded(True)
    prop_node.setText(2, "2")   # width change triggers a rebuild
    assert attr_prop().isExpanded(), "row collapsed after rebuild"
    print("OK: property row stays expanded after a rebuild")

    # 13) Property row has a Type dropdown (column 4) with C/L/N/T options.
    prop_node = attr_prop()
    type_combo = page._attr_tree.itemWidget(prop_node, 4)
    assert type_combo is not None, "no Type dropdown on property row"
    items = [type_combo.itemText(i) for i in range(type_combo.count())]
    expected = ["", "C - Character", "L - Length", "N - Number", "T - Text"]
    assert items == expected, f"Type options mismatch: {items}"
    
    # 13b) Verify dropdown itemData (userData) stores codes, not display text
    codes = [type_combo.itemData(i) for i in range(type_combo.count())]
    assert codes == ["", "C", "L", "N", "T"], f"Type codes mismatch: {codes}"
    
    # 13c) Changing Type dropdown updates the class property assignment (stores code, not display).
    # Find index by itemData (code)
    c_idx = next(i for i in range(type_combo.count()) if type_combo.itemData(i) == "C")
    type_combo.setCurrentIndex(c_idx)
    cls_prop = next(a for a in attr_cls.properties if a.property_id == "pr1")
    assert cls_prop.type == "C", f"Type not updated: {cls_prop.type}"
    
    l_idx = next(i for i in range(type_combo.count()) if type_combo.itemData(i) == "L")
    type_combo.setCurrentIndex(l_idx)
    assert cls_prop.type == "L", f"Type not updated: {cls_prop.type}"
    
    # Verify selected text shows description, but stored code is just the letter
    assert "L" in type_combo.currentText() and "Length" in type_combo.currentText(), \
        f"Current text should show L - Length, got: {type_combo.currentText()}"
    print("OK: property row Type dropdown shows descriptions but stores codes")

    # 14) Usage dropdown (column 5): Configuration / Graphic, writes to the class.
    prop_node = attr_prop()
    usage_combo = page._attr_tree.itemWidget(prop_node, 5)
    assert usage_combo is not None, "no Usage dropdown on property row"
    usage_items = [usage_combo.itemText(i) for i in range(usage_combo.count())]
    assert usage_items == ["", "Configuration", "Graphic"], usage_items
    usage_combo.setCurrentText("Graphic")
    cls_prop = next(a for a in attr_cls.properties if a.property_id == "pr1")
    assert cls_prop.usage == "Graphic", f"Usage not updated: {cls_prop.usage}"
    print("OK: property row Usage dropdown writes Configuration/Graphic")

    # 15) Text-block (column 6) auto-derived from the property name; edit persists.
    assert ClassCreationPage._text_block("Desk type (A)") == "Desk_Type"
    assert ClassCreationPage._text_block("Number of Fabrics") == "Number_Of_Fabrics"
    prop_node = attr_prop()
    assert prop_node.text(6) == "Colour", prop_node.text(6)
    prop_node.setText(6, "Colour_Block")
    cls_prop = next(a for a in attr_cls.properties if a.property_id == "pr1")
    assert cls_prop.text_block == "Colour_Block", cls_prop.text_block
    print("OK: property row Text-block auto-derived + editable")

    # 16) The bulk-code button is now "Resolve remaining"; disabled when the
    # loaded config codes are all resolved.
    assert page._auto_btn.text() == "Resolve remaining", page._auto_btn.text()
    assert not page._auto_btn.isEnabled(), "Resolve remaining should be disabled"
    page._on_resolve_remaining()  # no-op when nothing is unresolved
    print("OK: Resolve-remaining button repurposed + disabled when resolved")

    print("ALL CLASS CREATION CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
