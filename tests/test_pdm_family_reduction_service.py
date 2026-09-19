import unittest
from types import SimpleNamespace

from services.engineering.pdm_family_reduction_service import (
    FamilyCandidate,
    PDMFamilyReductionService,
)


class FakeRepository:
    """Records calls and returns scripted PDM rows; no database involved."""

    def __init__(self, range_rows, attribute_rows, filtered_ids, us_range=False,
                 category_id="90"):
        self._range_rows = range_rows
        self._attribute_rows = attribute_rows
        self._filtered_ids = filtered_ids
        self._us_range = us_range
        self._category_id = category_id
        self.filter_calls = []
        self.us_filter_calls = []

    def fetch_products_range_info(self, product_ids, connection=None):
        wanted = {str(p) for p in product_ids}
        return [r for r in self._range_rows if str(r.ProductId) in wanted]

    def range_scope(self, product_range_id, connection=None):
        return self._category_id, self._us_range

    def fetch_range_product_ids(self, product_range_id, connection=None):
        return [SimpleNamespace(ProductId=r.ProductId) for r in self._range_rows]

    def fetch_products_filter_attributes(self, product_ids, connection=None):
        wanted = {str(p) for p in product_ids}
        return [r for r in self._attribute_rows if str(r.ProductId) in wanted]

    def fetch_legacy_filtered_products(
        self, product_range_id, language_id, xml, connection=None
    ):
        self.filter_calls.append((product_range_id, language_id, xml))
        return [SimpleNamespace(ProductId=pid) for pid in self._filtered_ids]

    def fetch_legacy_filtered_us_items(
        self, product_category_id, language_id, xml, connection=None
    ):
        self.us_filter_calls.append((product_category_id, language_id, xml))
        return []


def range_row(product_id, product_range_id):
    return SimpleNamespace(
        ProductId=product_id, Product=f"P{product_id}",
        ProductRangeId=product_range_id, Status=1, NewProduct=0,
    )


def attr_row(product_id, attribute_id, attribute_value_id, order_code_key="",
             attribute_type=0, order_code_value="", model_suffix=""):
    """One ProductAttributeValues row as the legacy filter read returns it."""
    return SimpleNamespace(
        ProductId=product_id, AttributeId=attribute_id,
        AttributeValueId=attribute_value_id,
        AttributeType=attribute_type,
        OrderCodeFormatKey=order_code_key,
        OrderCodeValue=order_code_value,
        ModelSuffix=model_suffix,
    )


def make_service(repository):
    service = PDMFamilyReductionService.__new__(PDMFamilyReductionService)
    service.context = None
    service.repository = repository
    return service


class PDMFamilyReductionServiceTests(unittest.TestCase):
    def test_exact_common_functional_filter_validates(self):
        range_rows = [range_row("1", "500"), range_row("2", "500")]
        attribute_rows = [
            attr_row("1", "10", "100"),  # shared functional value
            attr_row("2", "10", "100"),
            attr_row("1", "20", "201", order_code_key="SIZE"),  # configurable, differs
            attr_row("2", "20", "202", order_code_key="SIZE"),
        ]
        repo = FakeRepository(range_rows, attribute_rows, filtered_ids=["1", "2"])
        service = make_service(repo)

        result = service.validate_family(FamilyCandidate(base="BASE1", product_ids=("1", "2")))

        self.assertEqual(result.status, "validated")
        self.assertEqual(result.functional_attribute_value_ids, ("100",))
        self.assertEqual(result.configurable_attribute_ids, ("20",))
        self.assertEqual(result.filtered_product_ids, ("1", "2"))
        self.assertEqual(repo.filter_calls[0][0], "500")
        self.assertIn('attributevalueid="100"', repo.filter_calls[0][2])

    def test_non_exact_filter_is_rejected(self):
        range_rows = [range_row("1", "500"), range_row("2", "500")]
        attribute_rows = [
            attr_row("1", "10", "100"),
            attr_row("2", "10", "100"),
        ]
        # ProductsList returns an extra Product (3) and misses Product 2.
        repo = FakeRepository(range_rows, attribute_rows, filtered_ids=["1", "3"])
        service = make_service(repo)

        result = service.validate_family(FamilyCandidate(base="BASE1", product_ids=("1", "2")))

        self.assertEqual(result.status, "rejected")
        self.assertEqual(result.missing_from_filter, ("2",))
        self.assertEqual(result.extra_in_filter, ("3",))

    def test_order_code_attributes_excluded_from_functional_set(self):
        range_rows = [range_row("1", "500"), range_row("2", "500")]
        attribute_rows = [
            # Identical order-code-bearing value on both members: still must
            # NOT be treated as shared functional identity.
            attr_row("1", "30", "300", order_code_key="FINISH"),
            attr_row("2", "30", "300", order_code_key="FINISH"),
            attr_row("1", "10", "100"),
            attr_row("2", "10", "100"),
        ]
        repo = FakeRepository(range_rows, attribute_rows, filtered_ids=["1", "2"])
        service = make_service(repo)

        result = service.validate_family(FamilyCandidate(base="BASE1", product_ids=("1", "2")))

        self.assertEqual(result.functional_attribute_value_ids, ("100",))
        self.assertNotIn("300", result.functional_attribute_value_ids)
        self.assertIn("30", result.configurable_attribute_ids)
        self.assertNotIn('attributevalueid="300"', repo.filter_calls[0][2])

    def test_family_spanning_multiple_ranges_is_unresolved(self):
        range_rows = [range_row("1", "500"), range_row("2", "501")]
        repo = FakeRepository(range_rows, attribute_rows=[], filtered_ids=[])
        service = make_service(repo)

        result = service.validate_family(FamilyCandidate(base="BASE1", product_ids=("1", "2")))

        self.assertEqual(result.status, "unresolved")
        self.assertIn("multiple ProductRangeIds", result.reason)

    def test_us_range_is_unresolved_and_never_filtered(self):
        range_rows = [range_row("1", "500"), range_row("2", "500")]
        attribute_rows = [attr_row("1", "10", "100"), attr_row("2", "10", "100")]
        repo = FakeRepository(range_rows, attribute_rows, filtered_ids=["1", "2"],
                              us_range=True, category_id="318")
        service = make_service(repo)

        result = service.validate_family(FamilyCandidate(base="BASE1", product_ids=("1", "2")))

        self.assertEqual(result.status, "unresolved")
        self.assertEqual(result.product_category_id, "318")
        # Neither procedure may be used: ProductsList would be an
        # approximation, USProductsList answers in a different key space.
        self.assertEqual(repo.filter_calls, [])
        self.assertEqual(repo.us_filter_calls, [])
        self.assertIn("USProductsList", result.reason)
        self.assertIn("USItemId", result.reason)
        self.assertIn("318", result.reason)


class LegacyFunctionalRuleTests(unittest.TestCase):
    """``is_functional`` requires EVERY legacy test to agree.

    Each legacy definition lives in a different demmy source file; admitting a
    value any of them calls physical could validate a base for the wrong
    reason, so all four must pass.
    """

    def test_plain_functional_value_is_functional(self):
        self.assertTrue(
            PDMFamilyReductionService.is_functional(attr_row("1", "10", "100"))
        )

    def test_non_zero_attribute_type_is_not_functional(self):
        # AttributeValidator.isFunctionalAttributeValue: AttributeType = 0.
        self.assertFalse(PDMFamilyReductionService.is_functional(
            attr_row("1", "10", "100", attribute_type=1)))
        self.assertFalse(PDMFamilyReductionService.is_functional(
            attr_row("1", "10", "100", attribute_type=2)))

    def test_order_code_format_key_is_not_functional(self):
        # ProductIntroduction.loadExistingProducts: OrderCodeFormatKey IS NULL.
        self.assertFalse(PDMFamilyReductionService.is_functional(
            attr_row("1", "10", "100", order_code_key="SIZE")))

    def test_order_code_value_is_not_functional(self):
        # PermutateThread: a value with an OrderCodeValue is Physical.
        self.assertFalse(PDMFamilyReductionService.is_functional(
            attr_row("1", "10", "100", order_code_value="A")))

    def test_model_suffix_value_is_not_functional(self):
        # UIGroupMaintenance.getUIGroupIdForProduct: ModelSuffix IS NULL.
        self.assertFalse(PDMFamilyReductionService.is_functional(
            attr_row("1", "10", "100", model_suffix="[X]")))

    def test_only_agreed_functional_values_reach_the_selector(self):
        range_rows = [range_row("1", "500"), range_row("2", "500")]
        attribute_rows = [
            attr_row("1", "10", "100"), attr_row("2", "10", "100"),          # kept
            attr_row("1", "11", "111", attribute_type=1),                    # dropped
            attr_row("2", "11", "111", attribute_type=1),
            attr_row("1", "12", "122", order_code_value="A"),                # dropped
            attr_row("2", "12", "122", order_code_value="A"),
            attr_row("1", "13", "133", model_suffix="[M]"),                  # dropped
            attr_row("2", "13", "133", model_suffix="[M]"),
        ]
        repo = FakeRepository(range_rows, attribute_rows, filtered_ids=["1", "2"])
        service = make_service(repo)

        result = service.validate_family(FamilyCandidate(base="B", product_ids=("1", "2")))

        self.assertEqual(result.functional_attribute_value_ids, ("100",))
        xml = repo.filter_calls[0][2]
        for dropped in ("111", "122", "133"):
            self.assertNotIn(f'attributevalueid="{dropped}"', xml)
        self.assertEqual(
            sorted(result.configurable_attribute_ids), ["11", "12", "13"]
        )


class SelectorXmlGuardTests(unittest.TestCase):
    def test_selector_xml_over_the_varchar_limit_is_unresolved(self):
        # ProductsList declares @SelAttribValuesXml VARCHAR(4000); SQL Server
        # would truncate a longer payload into malformed XML.
        range_rows = [range_row("1", "500"), range_row("2", "500")]
        shared = [str(1000000 + i) for i in range(200)]
        attribute_rows = [
            attr_row(pid, "10", vid) for pid in ("1", "2") for vid in shared
        ]
        repo = FakeRepository(range_rows, attribute_rows, filtered_ids=["1", "2"])
        service = make_service(repo)

        result = service.validate_family(FamilyCandidate(base="B", product_ids=("1", "2")))

        self.assertEqual(result.status, "unresolved")
        self.assertIn("VARCHAR(4000)", result.reason)
        self.assertEqual(repo.filter_calls, [])  # never sent
        self.assertEqual(len(result.functional_attribute_value_ids), 200)

    def test_selector_xml_just_under_the_limit_is_sent(self):
        range_rows = [range_row("1", "500"), range_row("2", "500")]
        shared = [str(1000000 + i) for i in range(50)]
        attribute_rows = [
            attr_row(pid, "10", vid) for pid in ("1", "2") for vid in shared
        ]
        repo = FakeRepository(range_rows, attribute_rows, filtered_ids=["1", "2"])
        service = make_service(repo)

        result = service.validate_family(FamilyCandidate(base="B", product_ids=("1", "2")))

        self.assertEqual(result.status, "validated")
        self.assertLessEqual(
            len(repo.filter_calls[0][2]), PDMFamilyReductionService.MAX_SELECTOR_XML
        )

    def test_missing_product_id_is_unresolved(self):
        range_rows = [range_row("1", "500")]
        repo = FakeRepository(range_rows, attribute_rows=[], filtered_ids=[])
        service = make_service(repo)

        result = service.validate_family(FamilyCandidate(base="BASE1", product_ids=("1", "2")))

        self.assertEqual(result.status, "unresolved")
        self.assertIn("not found in PDM", result.reason)

    def test_single_product_family_is_unresolved(self):
        service = make_service(FakeRepository([], [], []))

        result = service.validate_family(FamilyCandidate(base="BASE1", product_ids=("1",)))

        self.assertEqual(result.status, "unresolved")

    def test_no_common_functional_value_is_unresolved(self):
        range_rows = [range_row("1", "500"), range_row("2", "500")]
        attribute_rows = [
            attr_row("1", "10", "100"),
            attr_row("2", "10", "999"),  # no overlap
        ]
        repo = FakeRepository(range_rows, attribute_rows, filtered_ids=[])
        service = make_service(repo)

        result = service.validate_family(FamilyCandidate(base="BASE1", product_ids=("1", "2")))

        self.assertEqual(result.status, "unresolved")
        self.assertIn("No shared non-order-code", result.reason)


if __name__ == "__main__":
    unittest.main()
