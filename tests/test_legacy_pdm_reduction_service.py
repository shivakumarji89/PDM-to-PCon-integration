import unittest
from types import SimpleNamespace

from services.engineering.legacy_pdm_reduction_service import (
    LegacyPDMReductionService,
    PDMSelection,
)


class LegacyPDMReductionServiceTests(unittest.TestCase):
    def test_attribute_xml_matches_legacy_selector_shape(self):
        xml = LegacyPDMReductionService.build_attribute_xml(
            [PDMSelection("10", "101"), PDMSelection("20", "202")]
        )
        self.assertEqual(
            xml,
            '<attributes><attribute attributeid="10" attributevalueid="101"/>'
            '<attribute attributeid="20" attributevalueid="202"/></attributes>',
        )

    def test_ocfs_controls_sequence_not_display_order(self):
        attrs = (
            PDMSelection("1", "11", order_code_value="A", order_code_format_key="FIRST"),
            PDMSelection("2", "22", order_code_value="B", order_code_format_key="SECOND"),
        )
        result, unresolved, duplicates = LegacyPDMReductionService._expand_ocfs(
            "BASE", "{SECOND}{FIRST}", attrs, ()
        )
        self.assertEqual(result, "BASEBA")
        self.assertEqual(unresolved, ())
        self.assertEqual(duplicates, ())

    def test_effective_ocfs_uses_product_override(self):
        row = SimpleNamespace(
            ProductOrderCodeFormatString="{A}{B}",
            RangeOrderCodeFormatString="{B}{A}",
        )
        from repositories.legacy_pdm_compat_repository import LegacyPDMCompatRepository
        self.assertEqual(LegacyPDMCompatRepository.effective_ocfs(row), "{A}{B}")

    def test_effective_ocfs_falls_back_to_range(self):
        row = SimpleNamespace(
            ProductOrderCodeFormatString=None,
            RangeOrderCodeFormatString="{B}{A}",
        )
        from repositories.legacy_pdm_compat_repository import LegacyPDMCompatRepository
        self.assertEqual(LegacyPDMCompatRepository.effective_ocfs(row), "{B}{A}")


if __name__ == "__main__":
    unittest.main()
