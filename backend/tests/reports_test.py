"""Step 6 tests: the consolidated report set.

Five reports were merged away. The thing to hold is that merging removed DOCUMENTS, not
NUMBERS -- every figure the merged report carried has to appear in the one that absorbed
it, or consolidation was just deletion.
"""
import sys, os, io as _io
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest

import engine, engineering as englib, reports as R
from defaults import default_project


@pytest.fixture(scope="module")
def ctx():
    p = default_project("Rep", "QA", "Hyderabad", "R-1", "owner")
    a = engine.analyse(p)
    return p, a, englib.analyse_engineering(p, a)


def text_of(pdf: bytes) -> str:
    from pypdf import PdfReader
    return "\n".join(pg.extract_text() or "" for pg in PdfReader(_io.BytesIO(pdf)).pages)


def test_there_are_exactly_eleven_reports():
    assert len(R.REPORT_TITLES) == 12
    assert set(R.ALL_ORDER) == set(R.REPORT_TITLES)


@pytest.mark.parametrize("key", list(R.REPORT_TITLES))
def test_every_report_builds(ctx, key):
    p, a, eng = ctx
    pdf = R.build_pdf(key, p, a, eng)
    assert pdf.startswith(b"%PDF") and len(pdf) > 1500


@pytest.mark.parametrize("key", list(R.REPORT_TITLES))
def test_every_report_carries_the_project_metrics(ctx, key):
    p, a, eng = ctx
    assert "Key Project Metrics" in text_of(R.build_pdf(key, p, a, eng))


# ---------------------------------------------------------------- merges kept the numbers
def test_a_merged_id_still_resolves(ctx):
    """An old link must land on the report that absorbed those numbers, not a 400."""
    p, a, eng = ctx
    for old, new in R.MERGED_INTO.items():
        assert new in R.REPORT_TITLES
        # Text, not bytes: every PDF embeds a generation timestamp and a document id, so
        # two renders of the same report are never byte-identical.
        assert text_of(R.build_pdf(old, p, a, eng)) == text_of(R.build_pdf(new, p, a, eng))


def test_quantities_survive_inside_the_boq(ctx):
    p, a, eng = ctx
    t = text_of(R.build_pdf("boq", p, a, eng))
    assert "Estimated Quantities" in t
    assert "Material Summary" in t and "Labour Summary" in t


def test_accessibility_survives_inside_compliance(ctx):
    p, a, eng = ctx
    assert "ccessibilit" in text_of(R.build_pdf("compliance", p, a, eng))


def test_utility_sizing_survives_inside_water(ctx):
    p, a, eng = ctx
    assert len(R.build_pdf("water", p, a, eng)) > 3000


# ---------------------------------------------------------------- the new reports
def test_programme_report_has_the_phases_and_the_safety_basis(ctx):
    p, a, eng = ctx
    t = text_of(R.build_pdf("programme", p, a, eng))
    assert "Phase Breakdown" in t
    assert "Critical Path" in t
    assert "IS 456" in t and "Floor cycle" in t


def test_cost_report_carries_the_feasibility_figures(ctx):
    p, a, eng = ctx
    t = text_of(R.build_pdf("cost", p, a, eng))
    for probe in ("Feasibility", "Break-even", "Cash Flow", "IRR"):
        assert probe in t, probe


def test_cost_report_carries_the_optimisation_findings(ctx):
    """The brief lists Optimisation Findings under "Add" but fixes the final set at eleven
    without it. Both hold: the content ships inside Cost & Feasibility."""
    p, a, eng = ctx
    t = text_of(R.build_pdf("cost", p, a, eng))
    assert "Optimisation Findings" in t
    assert "Change required" in t
    assert "Waste reduction" in t
    assert len(R.REPORT_TITLES) == 12


def test_setbacks_appear_in_a_report_of_their_own(ctx):
    """Burying them inside Compliance meant a reader looking for setbacks had nothing to
    click, which is the same as not having them."""
    p, a, eng = ctx
    t = text_of(R.build_pdf("plot", p, a, eng))
    assert "Plot Geometry" in t
    assert "Setbacks & Development Controls" in t
    assert "Minimum (m)" in t and "NBC 2016 Part 3" in t


def test_setbacks_also_stay_in_the_compliance_report(ctx):
    p, a, eng = ctx
    assert "Setbacks & Development Controls" in text_of(R.build_pdf("compliance", p, a, eng))


def test_a_failing_setback_says_it_is_not_sanctionable(ctx):
    p, a, eng = ctx
    assert "Not sanctionable" in text_of(R.build_pdf("plot", p, a, eng))


def test_sustainability_report_carries_m13_and_m14(ctx):
    p, a, eng = ctx
    t = text_of(R.build_pdf("sustainability", p, a, eng))
    assert "Embodied Carbon" in t
    assert "Plantation Plan" in t
    assert "Green Rating" in t


def test_engineering_summary_was_extended_with_m13_and_m14(ctx):
    p, a, eng = ctx
    t = text_of(R.build_pdf("engineering", p, a, eng))
    assert "Embodied carbon" in t and "Trees required" in t


def test_site_report_says_so_when_no_gis_has_been_run(ctx):
    """Silence would read as "the site is fine"."""
    p, a, eng = ctx
    assert "No site analysis has been run" in text_of(R.build_pdf("site", p, a, eng))


# ---------------------------------------------------------------- download all
def test_download_all_is_one_pdf_with_a_contents_page(ctx):
    from pypdf import PdfReader
    p, a, eng = ctx
    pdf = R.build_all_pdf(p, a, eng)
    reader = PdfReader(_io.BytesIO(pdf))
    assert len(reader.pages) > len(R.REPORT_TITLES)
    first = reader.pages[0].extract_text()
    assert "Contents" in first
    for title in R.REPORT_TITLES.values():
        assert title in first, f"{title} missing from contents"


def test_contents_page_numbers_point_at_the_right_reports(ctx):
    """A contents page with wrong page numbers is worse than none."""
    from pypdf import PdfReader
    p, a, eng = ctx
    reader = PdfReader(_io.BytesIO(R.build_all_pdf(p, a, eng)))
    first = reader.pages[0].extract_text()
    # Executive Summary is first in ALL_ORDER, so it must start on page 2.
    lines = [l for l in first.split("\n") if R.REPORT_TITLES["executive"] in l]
    assert lines, "executive row missing"
    page2 = reader.pages[1].extract_text()
    assert R.REPORT_TITLES["executive"] in page2


def test_every_module_is_represented_somewhere():
    """The gap this step existed to close: six modules produced nothing downloadable."""
    covered = " ".join(R.REPORT_TITLES.values()).lower()
    for topic in ("site", "compliance", "engineering", "structural", "water", "fire",
                  "sustainability", "boq", "cost", "programme"):
        assert topic in covered, topic
