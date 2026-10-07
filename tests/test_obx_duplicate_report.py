import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from services.obx_validation_service import ObxLine, ObxValidationService


def _line(seq, article, currency="EUR", price=100.0, plc="", date=""):
    return ObxLine(
        seq=seq, base_article=article.split()[0], final_article=article,
        currency=currency, obx_price=price, plc=plc, source_date=date,
    )


def _service():
    return ObxValidationService.__new__(ObxValidationService)


PATHS = ["C:/a/File_A.obx", "C:/b/File_B.obx", "C:/c/File_C.obx"]


def _abc_lines(prices=(1890, 1890, 1920)):
    lines = [
        _line(14, "ABC X", price=prices[0]),
        _line(15, "UNIQ X"),
        _line(327, "abc  x", price=prices[1]),
        _line(891, "ABC X", price=prices[2]),
    ]
    mapping = {14: PATHS[0], 15: PATHS[0], 327: PATHS[1], 891: PATHS[2]}
    return lines, mapping


class DuplicateReportTests(unittest.TestCase):
    def test_same_article_in_three_files(self):
        lines, mapping = _abc_lines()
        report = _service().build_duplicate_report(lines, mapping, PATHS)
        self.assertEqual(len(report.duplicate_groups), 1)
        group = report.duplicate_groups[0]
        self.assertEqual((group.currency, group.final_article), ("EUR", "ABC X"))
        self.assertEqual(group.occurrence_count, 3)
        self.assertEqual(group.source_files, ["File_A.obx", "File_B.obx", "File_C.obx"])
        self.assertEqual(
            [(o.seq, o.source_file) for o in group.occurrences],
            [(14, "File_A.obx"), (327, "File_B.obx"), (891, "File_C.obx")],
        )
        self.assertEqual([o.obx_price for o in group.occurrences], [1890, 1890, 1920])

    def test_repeated_within_one_file(self):
        lines = [_line(1, "A X"), _line(2, "A X"), _line(3, "A X"), _line(4, "A X")]
        report = _service().build_duplicate_report(lines, {s: "x/F.obx" for s in range(1, 5)}, ["x/F.obx"])
        self.assertEqual(report.duplicate_rows, 3)
        self.assertEqual(report.unique_rows, 1)
        self.assertEqual(report.duplicate_groups[0].occurrence_count, 4)
        self.assertEqual(report.duplicate_groups[0].source_files, ["F.obx"])

    def test_currencies_stay_separate(self):
        lines = [
            _line(1, "A X", "EUR"), _line(2, "A X", "GBP"),
            _line(3, "A X", "EUR"), _line(4, "A X", "GBP"), _line(5, "A X", "GBP"),
        ]
        mapping = {1: PATHS[0], 2: PATHS[0], 3: PATHS[1], 4: PATHS[1], 5: PATHS[2]}
        report = _service().build_duplicate_report(lines, mapping, PATHS)
        by_cur = {g.currency: g for g in report.duplicate_groups}
        self.assertEqual(by_cur["EUR"].occurrence_count, 2)
        self.assertEqual(by_cur["GBP"].occurrence_count, 3)
        self.assertEqual(by_cur["GBP"].source_files, ["File_A.obx", "File_B.obx", "File_C.obx"])

    def test_price_consistency(self):
        lines, mapping = _abc_lines()
        self.assertEqual(
            _service().build_duplicate_report(lines, mapping, PATHS).duplicate_groups[0].price_consistency,
            "DIFFERENT",
        )
        lines, mapping = _abc_lines(prices=(1890, 1890, 1890))
        self.assertEqual(
            _service().build_duplicate_report(lines, mapping, PATHS).duplicate_groups[0].price_consistency,
            "SAME",
        )

    def test_counts_match_duplicate_count(self):
        lines, mapping = _abc_lines()
        report = _service().build_duplicate_report(lines, mapping, PATHS)
        self.assertEqual(report.total_rows, 4)
        self.assertEqual(report.unique_rows, 2)
        self.assertEqual(report.duplicate_rows, 2)
        self.assertEqual(report.duplicate_rows, ObxValidationService.duplicate_count(lines))

    def test_same_filename_different_paths_not_merged(self):
        lines = [_line(1, "A X"), _line(2, "A X")]
        mapping = {1: "C:/one/F.obx", 2: "C:/two/F.obx"}
        group = _service().build_duplicate_report(lines, mapping, list(mapping.values())).duplicate_groups[0]
        self.assertEqual(group.source_paths, ["C:/one/F.obx", "C:/two/F.obx"])

    def test_no_duplicates(self):
        lines = [_line(1, "A X"), _line(2, "B X"), _line(3, "A X", "GBP")]
        report = _service().build_duplicate_report(lines, {}, [])
        self.assertEqual(report.duplicate_groups, [])
        self.assertEqual((report.total_rows, report.unique_rows, report.duplicate_rows), (3, 3, 0))

    def test_csv_one_row_per_occurrence(self):
        svc = _service()
        lines, mapping = _abc_lines()
        report = svc.build_duplicate_report(lines, mapping, PATHS)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "dups.csv"
            self.assertEqual(svc.export_duplicate_report_csv(report, out), 3)
            with open(out, newline="", encoding="utf-8-sig") as handle:
                rows = list(csv.reader(handle))
        self.assertEqual(rows[0], ObxValidationService.DUPLICATE_CSV_HEADER)
        self.assertEqual(len(rows), 4)
        self.assertEqual([r[7] for r in rows[1:]], ["14", "327", "891"])
        self.assertEqual([r[5] for r in rows[1:]], ["File_A.obx", "File_B.obx", "File_C.obx"])
        self.assertTrue(all(r[11] == "3" and r[12] == "DIFFERENT" for r in rows[1:]))

    def test_no_pdm_or_validation_calls(self):
        svc = _service()
        svc.context = MagicMock()
        svc.validate = MagicMock()
        svc._pricing_service = MagicMock()
        lines, mapping = _abc_lines()
        report = svc.build_duplicate_report(lines, mapping, PATHS)
        svc.duplicate_report_csv_rows(report)
        svc.validate.assert_not_called()
        svc._pricing_service.assert_not_called()
        self.assertEqual(svc.context.mock_calls, [])

    def test_not_called_from_validation_paths(self):
        import ast
        allowed = {"build_duplicate_report", "duplicate_report_csv_rows", "export_duplicate_report_csv"}
        for path in ("services/obx_validation_service.py", "ui/pages/obx_validation_page.py"):
            tree = ast.parse(Path(path).read_text(encoding="utf-8"))
            for fn in ast.walk(tree):
                if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) or fn.name in allowed:
                    continue
                for node in ast.walk(fn):
                    name = getattr(node, "attr", None) or getattr(node, "id", None)
                    self.assertNotIn(name, allowed, f"{fn.name} in {path} uses {name}")


if __name__ == "__main__":
    unittest.main()
