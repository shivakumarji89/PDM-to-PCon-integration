import ast
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from services.obx_validation_service import ObxLine, ObxValidationService
from services.sif_validation_service import SifResult


def _line(seq, article, currency="EUR", price=100.0, plc="", date=""):
    return ObxLine(
        seq=seq, base_article=article.split()[0], final_article=article,
        currency=currency, obx_price=price, plc=plc, source_date=date,
    )


def _ten_lines():
    # 4 unique (currency, article) keys, 6 duplicates.
    return [
        _line(1, "A X", price=100, plc="P1", date="2026-01-01"),
        _line(2, "A X", price=105, plc="P2", date="2026-01-02"),
        _line(3, "B X", price=50),
        _line(4, "A X", price=100, plc="P3", date="2026-01-03"),
        _line(5, "B X", price=55),
        _line(6, "C X", price=70),
        _line(7, "C X", price=70),
        _line(8, "C X", price=71),
        _line(9, "B X", price=50),
        _line(10, "A X", currency="GBP", price=90),
    ]


def _service():
    return ObxValidationService.__new__(ObxValidationService)


def _pdm_result(line, pdm_price):
    return SifResult(
        seq=line.seq, sku=line.final_article, currency=line.currency,
        qty=line.qty, sif_price=line.sif_price, pdm_price=pdm_price,
    )


class GlobalDeduplicationTests(unittest.TestCase):
    def test_dispatch_plan_reduces_ten_sources_to_four_unique(self):
        lines = _ten_lines()
        unique, groups = _service().dispatch_plan(lines)
        self.assertEqual([line.seq for line in unique], [1, 3, 6, 10])
        self.assertEqual(ObxValidationService.duplicate_count(lines), 6)
        self.assertEqual({seq: [l.seq for l in g] for seq, g in groups.items()},
                         {1: [1, 2, 4], 3: [3, 5, 9], 6: [6, 7, 8], 10: [10]})

    def test_currency_aware_keys_stay_separate(self):
        lines = [_line(1, "A X", "EUR"), _line(2, "A X", "GBP"), _line(3, "A X", "EUR")]
        unique, groups = _service().dispatch_plan(lines)
        self.assertEqual([line.seq for line in unique], [1, 2])
        self.assertEqual([l.seq for l in groups[1]], [1, 3])
        self.assertEqual([l.seq for l in groups[2]], [2])

    def test_no_duplicates_is_unchanged(self):
        lines = [_line(1, "A X"), _line(2, "B X"), _line(3, "C X")]
        unique, groups = _service().dispatch_plan(lines)
        self.assertEqual([l.seq for l in unique], [1, 2, 3])
        svc = _service()
        for line in lines:
            out = svc.expand_unique_result(_pdm_result(line, line.obx_price), groups)
            self.assertEqual([r.seq for r in out], [line.seq])

    def test_expansion_returns_all_ten_source_rows_with_own_fields(self):
        lines = _ten_lines()
        svc = _service()
        unique, groups = svc.dispatch_plan(lines)
        pdm = {1: 100.0, 3: 50.0, 6: 70.0, 10: 90.0}
        expanded = []
        for u in unique:
            expanded.extend(svc.expand_unique_result(_pdm_result(u, pdm[u.seq]), groups))
        self.assertEqual(sorted(r.seq for r in expanded), list(range(1, 11)))
        by_seq = {r.seq: r for r in expanded}
        # Own seq, price, PLC, date, currency are kept; status vs the PDM price.
        self.assertEqual(by_seq[2].sif_price, 105.0)
        self.assertEqual(by_seq[2].plc, "P2")
        self.assertEqual(by_seq[2].source_date, "2026-01-02")
        self.assertEqual(by_seq[2].status, "price_mismatch")
        self.assertIn("105.00", by_seq[2].message)
        self.assertEqual(by_seq[4].status, "ok")
        self.assertEqual(by_seq[4].plc, "P3")
        self.assertEqual(by_seq[5].status, "price_mismatch")
        self.assertEqual(by_seq[8].status, "price_mismatch")
        self.assertEqual(by_seq[7].status, "ok")
        self.assertEqual(by_seq[10].currency, "GBP")

    def test_unresolved_unique_result_fans_out_unresolved(self):
        lines = [_line(1, "A X"), _line(2, "A X", price=9)]
        svc = _service()
        _, groups = svc.dispatch_plan(lines)
        unresolved = SifResult(seq=1, sku="A X", status="unresolved", message="no SKU")
        out = svc.expand_unique_result(unresolved, groups)
        self.assertEqual([(r.seq, r.status, r.message) for r in out],
                         [(1, "unresolved", "no SKU"), (2, "unresolved", "no SKU")])

    def test_only_unique_lines_reach_the_expensive_path(self):
        lines = _ten_lines()
        svc = _service()
        svc._obx_validation_cache = {}
        svc._obx_lookup_cache = {}
        seen = []

        class FakePricing:
            def validate(self, currency, batch, **kwargs):
                seen.extend(line.seq for line in batch)
                for line in batch:
                    kwargs["on_result"](_pdm_result(line, 100.0))
                return {currency: 1}, []

        svc._pricing_service = lambda operation_control=None: FakePricing()
        unique, _groups = svc.dispatch_plan(lines)
        _sites, results = svc.validate("EUR", unique, site=1)
        self.assertEqual(seen, [1, 3, 6, 10])
        self.assertEqual([r.seq for r in results], [1, 3, 6, 10])

    def test_expand_pending_restores_duplicate_source_rows(self):
        lines = _ten_lines()
        svc = _service()
        unique, _ = svc.dispatch_plan(lines)
        remaining = [unique[1], unique[2]]  # B and C representatives still pending
        pending = svc.expand_pending(remaining, lines, completed_seqs={1, 2, 4, 10})
        self.assertEqual([l.seq for l in pending], [3, 5, 6, 7, 8, 9])
        # A group already completed is never re-queued.
        again = svc.expand_pending(remaining, lines, completed_seqs={3, 5, 9})
        self.assertEqual([l.seq for l in again], [6, 7, 8])


class WorkerAndProgressTests(unittest.TestCase):
    def test_worker_still_passes_operation_control(self):
        source = Path("ui/pages/obx_validation_page.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        worker = next(
            n for n in ast.walk(tree)
            if isinstance(n, ast.ClassDef) and n.name == "_ObxWorker"
        )
        run = next(n for n in worker.body if isinstance(n, ast.FunctionDef) and n.name == "run")
        calls = [
            n for n in ast.walk(run)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr == "validate"
        ]
        self.assertEqual(len(calls), 1)
        keywords = {k.arg: ast.unparse(k.value) for k in calls[0].keywords}
        self.assertEqual(keywords.get("operation_control"), "self._control")
        self.assertEqual(
            next(
                n.value.value for n in worker.body
                if isinstance(n, ast.Assign) and n.targets[0].id == "_WORKER_SIZE"
            ),
            8,
        )

    def _page_stub(self, lines, duplicate_count):
        from ui.pages.obx_validation_page import ObxValidationPage

        svc = _service()
        stub = MagicMock()
        stub._context.obx_validation_service = svc
        stub._lines = lines
        stub._results = []
        stub._duplicate_count = duplicate_count
        stub._active_control = object()
        stub._unique_done = 0
        stub._unique_total = len(lines) - duplicate_count
        stub._dispatch_groups = svc.dispatch_plan(lines)[1]
        stub._completed_text = lambda: ObxValidationPage._completed_text(stub)
        stub._on_line_done = lambda r: stub._results.append(r)
        return ObxValidationPage, stub

    def test_progress_uses_unique_denominator_but_results_cover_all_rows(self):
        lines = _ten_lines()
        page, stub = self._page_stub(lines, duplicate_count=6)
        self.assertEqual(page._completed_text(stub), "0/4 unique")
        unique, _ = stub._context.obx_validation_service.dispatch_plan(lines)
        page._on_unique_result(stub, _pdm_result(unique[0], 100.0))
        self.assertEqual(stub._unique_done, 1)
        self.assertEqual(len(stub._results), 3)  # seq 1, 2, 4
        self.assertEqual(page._completed_text(stub), "1/4 unique")
        for u in unique[1:]:
            page._on_unique_result(stub, _pdm_result(u, 100.0))
        self.assertEqual(len(stub._results), 10)
        stub._active_control = None
        self.assertEqual(page._completed_text(stub), "10/10")

    def test_paused_payload_is_expanded_to_source_rows(self):
        lines = _ten_lines()
        page, stub = self._page_stub(lines, duplicate_count=6)
        unique, _ = stub._context.obx_validation_service.dispatch_plan(lines)
        stub._results = [SifResult(seq=1), SifResult(seq=2), SifResult(seq=4)]
        page._on_paused(stub, ({}, [unique[1]], "paused"))
        self.assertEqual([l.seq for l in stub._pending_lines], [3, 5, 9])


if __name__ == "__main__":
    unittest.main()
