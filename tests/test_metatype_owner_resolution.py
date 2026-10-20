"""Owner-Metatype resolution from go_articles (verified rule D1). Synthetic fixtures only."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from core.application_context import ApplicationContext
from core.config import AppConfig
from services.metatype.owner_resolution import resolve_owner_metatype
from tests.test_metatype_write_contract import HEADER, make_series


@pytest.fixture
def root(tmp_path):
    path = tmp_path / "hmx"
    path.mkdir()
    return path


def reconcile(root, articles):
    make_series(root, articles=HEADER + articles)
    return ApplicationContext(AppConfig(metatype_repository_root=str(root))).metatype_article_service.reconcile(
        "demo", root=root)


ROWS = "MT_A;hmx;test;ART1;C1;\nMT_A;hmx;test;ART2;C2;\nMT_B;hmx;test;ART3;C3;\n"


def test_articles_of_one_metatype_resolve_to_it(root):
    result = resolve_owner_metatype(reconcile(root, ROWS), ["ART1", " ART2 "])
    assert result.resolved and result.metatype_id == "MT_A" and result.candidates == ("MT_A",)


def test_articles_spanning_metatypes_are_not_guessed(root):
    result = resolve_owner_metatype(reconcile(root, ROWS), ["ART1", "ART3"])
    assert not result.resolved and result.candidates == ("MT_A", "MT_B") and "2 different Metatypes" in result.reason


def test_unknown_articles_are_reported_not_invented(root):
    result = resolve_owner_metatype(reconcile(root, ROWS), ["ART1", "NEWART"])
    assert not result.resolved and result.missing == ("NEWART",) and "not in go_articles" in result.reason


def test_no_articles_or_no_role_resolve_nothing(root):
    rec = reconcile(root, ROWS)
    assert not resolve_owner_metatype(rec, []).resolved
    assert not resolve_owner_metatype(None, ["ART1"]).resolved
