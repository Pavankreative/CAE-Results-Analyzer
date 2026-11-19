import pytest

from app.analysis.comparison import ComparisonValidationError, compare
from app.services import assistant, reports


# ----------------------------------------------------------------- compare
def test_compare_same_simulation_has_zero_delta(bracket):
    res = compare(bracket, bracket)
    assert res["same_mesh"] is True
    assert all(abs(s["delta"]) < 1e-9 for s in res["scalars"])
    assert all(abs(d["abs_max"]) < 1e-9 for d in res["field_differences"])


def test_compare_reports_percentage_change(bracket, store, tmp_path):
    variant = store.get_simulation("brk-114")
    import copy
    b = copy.deepcopy(variant)
    b.id = "brk-114-variant"
    b.fields["von_mises"].values *= 0.86
    res = compare(bracket, b, fields=["von_mises"])
    maxrow = next(s for s in res["scalars"] if s["metric"] == "maximum")
    assert maxrow["percent"] == pytest.approx(-14.0, abs=0.5)


def test_compare_across_unrelated_models_rejects_comparison(bracket, plate):
    with pytest.raises(ComparisonValidationError):
        compare(bracket, plate)


def test_compare_overlays_convergence_monitors(aero):
    import copy
    b = copy.deepcopy(aero)
    res = compare(aero, b)
    assert any(o["field"].startswith("monitor:") for o in res["overlays"])


# --------------------------------------------------------------- assistant
def test_answer_blocks_are_labelled_by_source(bracket):
    a = assistant.ask(bracket, "Where is maximum stress?")
    kinds = [b["kind"] for b in a["blocks"]]
    assert assistant.DATA in kinds
    assert assistant.INTERP in kinds
    assert a["evidence"]
    assert "not a verified engineering conclusion" in a["disclaimer"]


def test_maximum_answer_quotes_the_real_peak(bracket):
    from app.analysis.statistics import field_statistics
    peak = field_statistics(bracket, "von_mises").maximum.value
    a = assistant.ask(bracket, "where is maximum stress")
    assert f"{peak:.4g}" in a["blocks"][0]["text"]


def test_safety_answer_uses_the_calculation(bracket):
    a = assistant.ask(bracket, "what is the factor of safety?")
    assert a["intent"] == "safety"
    assert any(b["kind"] == assistant.CALC for b in a["blocks"])


def test_convergence_answer_without_history_says_so(bracket):
    a = assistant.ask(bracket, "why might convergence be poor?")
    assert "no convergence history" in a["blocks"][0]["text"].lower()


def test_convergence_answer_with_history_uses_monitors(aero):
    a = assistant.ask(aero, "why might convergence be poor?")
    assert a["intent"] == "convergence"
    assert any("continuity" in b["text"] for b in a["blocks"])


def test_threshold_question_computes_a_selection(bracket):
    a = assistant.ask(bracket, "show regions above 80% of the peak")
    assert a["intent"] == "filter"
    assert any(e["label"] == "entities selected" for e in a["evidence"])


def test_unmatched_question_is_honest(bracket):
    a = assistant.ask(bracket, "what colour should the bracket be painted")
    assert a["intent"] == "unmatched"
    assert "No stored answer" in a["blocks"][0]["text"]


def test_assistant_never_returns_empty_evidence(bracket, aero, plate, suspension):
    for sim in (bracket, aero, plate, suspension):
        for q in assistant.SUGGESTIONS:
            a = assistant.ask(sim, q)
            assert a["blocks"]
            assert a["evidence"]


# ----------------------------------------------------------------- reports
def test_report_contains_every_requested_section(bracket, store):
    project = store.project_of("brk-114")
    r = reports.build_report(bracket, project)
    assert r["sections"] == reports.SECTIONS
    assert set(r["body"]) == set(reports.SECTIONS)


def test_report_marks_sample_data(bracket):
    md = reports.to_markdown(reports.build_report(bracket))
    assert "Sample data" in md


def test_markdown_and_html_render(bracket, store):
    r = reports.build_report(bracket, store.project_of("brk-114"))
    md = reports.to_markdown(r)
    html = reports.to_html(r)
    assert md.startswith("# ")
    assert "Factor of safety" in md
    assert html.startswith("<!DOCTYPE html>")
    assert "<table>" in html


def test_section_selection_is_respected(bracket):
    r = reports.build_report(bracket, sections=["results", "diagnostics"])
    assert r["sections"] == ["results", "diagnostics"]
    assert "materials" not in r["body"]


def test_report_comparison_section(bracket):
    import copy
    b = copy.deepcopy(bracket)
    r = reports.build_report(bracket, sections=["comparison"], compare_with=b)
    assert r["body"]["comparison"]["same_mesh"] is True
