"""OCD catalogue discovery: manufacturer / program / series / articles from an OCD repository."""
from __future__ import annotations

from pathlib import Path

import pytest

from services.ocd_engine.catalogue import CatalogueError, OcdCatalogueService, find_db_dir
from tests.ocd_engine.ocd_helpers import REAL_OCD_ROOT

_DESCRIPTOR = (
    "table\tocd_artshorttext\tocd_artshorttext.csv\tmscsv\n"
    "fields\t5\n"
    "field\t1\ttextnr\tvstring\t\tdelim ;\n"
    "field\t2\tlanguage\tvstring\t\tdelim ;\n"
    "field\t3\tline_nr\tuint8\t\tdelim ;\n"
    "field\t4\tline_fmt\tvstring\t\tdelim ;\n"
    "field\t5\ttext\tvstring\t\tdelim ;\n"
)


def _db(root: Path, program: str, region="ANY", version="1") -> Path:
    db = root / program / region / version / "db"
    db.mkdir(parents=True)
    return db


def _article(number, manufacturer, series, text_nr):
    return f"{number};C;{manufacturer};{series};{text_nr};;0;0;1;C62;\n"


def test_scan_groups_by_manufacturer_program_and_series(tmp_path):
    db = _db(tmp_path, "alpha")
    (db / "ocd_article.csv").write_text(
        _article("A1", "HM", "S1", "t1") + _article("A2", "HM", "S2", "t2")
        + _article("A3", "OTH", "", "t3"), encoding="latin-1")
    scan = OcdCatalogueService(tmp_path).scan()
    assert scan.manufacturers() == ["HM", "OTH"]
    hm = scan.programs_for("HM")[0]
    assert (hm.program, hm.series_ids, hm.article_count) == ("alpha", ("S1", "S2"), 2)
    assert scan.programs_for("OTH")[0].series_ids == ()


def test_scan_skips_folders_without_ocd_data_and_reports_them(tmp_path):
    (tmp_path / "plain").mkdir()
    (tmp_path / ".svn").mkdir()
    (tmp_path / "loose.txt").write_text("x")
    db = _db(tmp_path, "blank")
    (db / "ocd_article.csv").write_text("", encoding="latin-1")
    scan = OcdCatalogueService(tmp_path).scan()
    assert scan.programs == []
    assert {name for name, _ in scan.skipped} == {"plain", "blank"}


def test_db_folder_prefers_region_any_and_the_highest_version(tmp_path):
    for region, version in (("EURO", "9"), ("ANY", "1"), ("ANY", "2")):
        db = _db(tmp_path, "p", region, version) if not (tmp_path / "p" / region / version).exists() \
            else tmp_path / "p" / region / version / "db"
        (db / "ocd_article.csv").write_text(_article(f"{region}{version}", "HM", "S", "t"), encoding="latin-1")
    assert find_db_dir(tmp_path / "p") == tmp_path / "p" / "ANY" / "2" / "db"


def test_articles_are_filtered_by_series_and_manufacturer_with_english_labels(tmp_path):
    db = _db(tmp_path, "alpha")
    (db / "ocd_article.csv").write_text(
        _article("A1", "HM", "S1", "t1") + _article("A2", "HM", "S2", "t2")
        + _article("A1", "HM", "S1", "t1") + _article("X1", "OTH", "S1", "t4"), encoding="latin-1")
    (db / "ocd_artshorttext.csv").write_text(
        't1;de; 1;\\;"Stuhl"\nt1;en; 1;\\;"Chair"\nt1;en; 2;\\;"large"\nt2;de; 1;\\;"Nur Deutsch"\n',
        encoding="latin-1")
    (db / "pdata.ocd_artshorttext.inp_descr").write_text(_DESCRIPTOR, encoding="latin-1")
    service = OcdCatalogueService(tmp_path)
    program = service.scan().programs_for("HM")[0]
    everything = service.list_articles(program)
    assert [(a.article_number, a.label) for a in everything] == [("A1", "Chair large"), ("A2", "Nur Deutsch")]
    assert [a.article_number for a in service.list_articles(program, "S2")] == ["A2"]
    assert service.list_articles(program, "NOPE") == []


def test_missing_or_unconfigured_root_raises_a_readable_error(tmp_path):
    with pytest.raises(CatalogueError, match="not found"):
        OcdCatalogueService(tmp_path / "missing").scan()
    with pytest.raises(CatalogueError, match="No OCD repository folder"):
        OcdCatalogueService("").scan()


@pytest.mark.skipif(not Path(REAL_OCD_ROOT, "dalby").is_dir(), reason="real OCD repository not available")
def test_real_repository_dalby_is_discoverable():
    service = OcdCatalogueService(REAL_OCD_ROOT)
    program = next(p for p in service.scan().programs if p.program == "dalby")
    assert program.manufacturer_id == "HM" and "DALBY" in program.series_ids
    articles = service.list_articles(program, "DALBY")
    assert articles and all(a.series_id == "DALBY" for a in articles)
    assert any(a.label for a in articles)
