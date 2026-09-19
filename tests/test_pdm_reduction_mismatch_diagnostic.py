import unittest
from types import SimpleNamespace

from services.engineering.pdm_family_reduction_service import (
    FamilyCandidate,
    FamilyValidation,
    PDMFamilyReductionService,
)
from services.engineering.pdm_reduction_mismatch_diagnostic import (
    PDMReductionMismatchDiagnostic,
)


class FakeRepository:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def fetch_products_filter_attributes(self, product_ids, connection=None):
        self.calls.append(tuple(str(pid) for pid in product_ids))
        wanted = {str(pid) for pid in product_ids}
        return [row for row in self.rows if str(row.ProductId) in wanted]


def row(product_id, attribute_id, value_id, *, functional=True):
    return SimpleNamespace(
        ProductId=product_id,
        AttributeId=attribute_id,
        AttributeValueId=value_id,
        AttributeType=0 if functional else 1,
        OrderCodeFormatKey="" if functional else "OC",
        OrderCodeValue="",
        ModelSuffix=None,
        AttributeName="Power cutout" if value_id == "109863" else "",
    )


class MismatchDiagnosticTests(unittest.TestCase):
    def make_service(self, rows):
        validator = PDMFamilyReductionService.__new__(PDMFamilyReductionService)
        validator.context = None
        validator.repository = FakeRepository(rows)
        return validator

    def test_reports_dominant_functional_value_missing_from_extra(self):
        rows = []
        for pid in ("1", "2", "3", "4", "5", "6", "7", "8", "9", "10"):
            rows.append(row(pid, "50", "109863"))
        rows.append(row("11", "60", "999999"))
        validator = self.make_service(rows)
        diagnostic = PDMReductionMismatchDiagnostic(validator)

        candidate = FamilyCandidate("DWE36A", tuple(str(i) for i in range(1, 11)))
        validation = FamilyValidation(
            base="DWE36A",
            intended_product_ids=tuple(str(i) for i in range(1, 11)),
            filtered_product_ids=tuple(str(i) for i in range(1, 12)),
            status="rejected",
        )

        gaps = diagnostic.diagnose(candidate, validation)

        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0].product_id, "11")
        self.assertEqual(gaps[0].attribute_value_id, "109863")
        self.assertEqual(gaps[0].supporting_product_count, 10)
        self.assertEqual(gaps[0].candidate_product_count, 10)
        self.assertEqual(gaps[0].support_ratio, 1.0)
        self.assertEqual(gaps[0].attribute_name, "Power cutout")

    def test_diagnostic_never_changes_validation(self):
        validator = self.make_service([
            row("1", "50", "100"),
            row("2", "50", "100"),
            row("3", "60", "200"),
        ])
        diagnostic = PDMReductionMismatchDiagnostic(validator)
        candidate = FamilyCandidate("B", ("1", "2"))
        validation = FamilyValidation(
            base="B",
            intended_product_ids=("1", "2"),
            filtered_product_ids=("1", "2", "3"),
            status="rejected",
        )

        result = diagnostic.diagnose(candidate, validation)

        self.assertEqual(validation.status, "rejected")
        self.assertEqual(validation.filtered_product_ids, ("1", "2", "3"))
        self.assertTrue(result)

    def test_ignores_validated_and_unresolved_candidates(self):
        validator = self.make_service([])
        diagnostic = PDMReductionMismatchDiagnostic(validator)
        candidate = FamilyCandidate("B", ("1", "2"))

        for status in ("validated", "unresolved", "error"):
            validation = FamilyValidation(
                base="B",
                intended_product_ids=("1", "2"),
                filtered_product_ids=("1", "2", "3"),
                status=status,
            )
            self.assertEqual(diagnostic.diagnose(candidate, validation), ())
        self.assertEqual(validator.repository.calls, [])

    def test_support_threshold_is_respected(self):
        rows = [
            row("1", "50", "100"),
            row("2", "50", "100"),
            row("3", "50", "100"),
            row("4", "50", "100"),
            row("5", "50", "100"),
            row("6", "50", "100"),
            row("7", "50", "100"),
            row("8", "50", "100"),
            row("9", "50", "100"),
            row("10", "50", "100"),
            row("11", "50", "200"),
        ]
        validator = self.make_service(rows)
        diagnostic = PDMReductionMismatchDiagnostic(validator)
        candidate = FamilyCandidate("B", tuple(str(i) for i in range(1, 11)))
        validation = FamilyValidation(
            base="B",
            intended_product_ids=tuple(str(i) for i in range(1, 11)),
            filtered_product_ids=tuple(str(i) for i in range(1, 12)),
            status="rejected",
        )

        gaps = diagnostic.diagnose(
            candidate, validation, min_support_ratio=1.0
        )
        self.assertEqual(gaps[0].attribute_value_id, "100")


if __name__ == "__main__":
    unittest.main()
