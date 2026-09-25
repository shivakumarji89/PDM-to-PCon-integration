import unittest

from services.obx_validation_service import ObxLine, ObxValidationService


class OBXCurrencyDuplicateTests(unittest.TestCase):
    def test_same_sku_in_different_currencies_is_not_duplicate(self):
        lines = [
            ObxLine(seq=1, base_article="PEP200", final_article="PEP200 A", currency="EUR", obx_price=100),
            ObxLine(seq=2, base_article="PEP200", final_article="PEP200 A", currency="GBP", obx_price=90),
        ]
        self.assertEqual(ObxValidationService.duplicate_count(lines), 0)

    def test_same_sku_and_currency_is_duplicate(self):
        lines = [
            ObxLine(seq=1, base_article="PEP200", final_article="PEP200 A", currency="EUR", obx_price=100),
            ObxLine(seq=2, base_article="PEP200", final_article="PEP200 A", currency="EUR", obx_price=100),
            ObxLine(seq=3, base_article="PEP200", final_article="PEP200 B", currency="EUR", obx_price=110),
        ]
        self.assertEqual(ObxValidationService.duplicate_count(lines), 1)

    def test_deduplication_keeps_one_pdm_calculation_per_currency_and_sku(self):
        lines = [
            ObxLine(seq=1, base_article="PEP200", final_article="PEP200 A", currency="EUR", obx_price=100),
            ObxLine(seq=2, base_article="PEP200", final_article="PEP200 A", currency="EUR", obx_price=100),
            ObxLine(seq=3, base_article="PEP200", final_article="PEP200 A", currency="GBP", obx_price=90),
        ]
        svc = ObxValidationService.__new__(ObxValidationService)
        unique, groups = svc._deduplicate(lines)
        self.assertEqual([line.seq for line in unique], [1, 3])
        self.assertEqual(len(groups[("EUR", "PEP200 A")]), 2)
        self.assertEqual(len(groups[("GBP", "PEP200 A")]), 1)


if __name__ == "__main__":
    unittest.main()
