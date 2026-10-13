from types import SimpleNamespace

from ui.pages.obx_validation_page import ObxValidationPage


def _line(seq, article, currency="EUR"):
    return SimpleNamespace(seq=seq, final_article=article, currency=currency)


def _result(seq, status):
    return SimpleNamespace(seq=seq, status=status)


def test_duplicate_filter_includes_all_occurrences_and_normalizes_article_key():
    lines = [
        _line(1, "ABC  X"),
        _line(2, "UNIQUE X"),
        _line(3, " abc x "),
        _line(4, "ABC X", currency="GBP"),
    ]

    assert ObxValidationPage._duplicate_source_seqs(lines) == {1, 3}


def test_result_matches_each_clickable_metric_filter():
    page = SimpleNamespace(
        _table_filter="matched",
        _duplicate_seq_set={2, 3},
        _seq_key=ObxValidationPage._seq_key,
    )

    assert ObxValidationPage._result_matches_filter(page, _result(1, "ok"))
    assert not ObxValidationPage._result_matches_filter(page, _result(2, "price_mismatch"))

    page._table_filter = "price_mismatch"
    assert ObxValidationPage._result_matches_filter(page, _result(2, "price_mismatch"))
    assert not ObxValidationPage._result_matches_filter(page, _result(1, "ok"))

    page._table_filter = "unresolved"
    assert ObxValidationPage._result_matches_filter(page, _result(4, "unresolved"))

    page._table_filter = "skipped"
    assert ObxValidationPage._result_matches_filter(page, _result(5, "skipped"))
    assert not ObxValidationPage._result_matches_filter(page, _result(4, "unresolved"))

    page._table_filter = "duplicate"
    assert ObxValidationPage._result_matches_filter(page, _result(2, "price_mismatch"))
    assert ObxValidationPage._result_matches_filter(page, _result(3, "ok"))
    assert not ObxValidationPage._result_matches_filter(page, _result(1, "ok"))

    page._table_filter = "unique"
    assert ObxValidationPage._result_matches_filter(page, _result(1, "ok"))
    assert not ObxValidationPage._result_matches_filter(page, _result(2, "price_mismatch"))

    page._table_filter = "all"
    assert ObxValidationPage._result_matches_filter(page, _result(1, "ok"))
    assert ObxValidationPage._result_matches_filter(page, _result(2, "price_mismatch"))
