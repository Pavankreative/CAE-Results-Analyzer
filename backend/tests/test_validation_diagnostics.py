import numpy as np
import pytest

from app.analysis.diagnostics import run_diagnostics
from app.analysis.validation import run_validation
from app.core.model import ValidationStatus


def _check(result, name):
    return next(c for c in result["checks"] if c["name"] == name)


def test_every_check_carries_a_status_and_message(bracket):
    res = run_validation(bracket)
    assert res["checks"]
    for c in res["checks"]:
        assert c["status"] in {s.value for s in ValidationStatus}
        assert c["message"]


def test_unlinked_reference_stays_not_validated(suspension):
    res = run_validation(suspension)
    assert _check(res, "Experimental comparison")["status"] == "not_validated"
    assert _check(res, "Mesh convergence")["status"] == "not_validated"


def test_analytical_comparison_uses_the_stored_reference(bracket):
    c = _check(run_validation(bracket), "Analytical comparison")
    assert c["status"] in ("verified", "warning")
    labels = {e["label"] for e in c["evidence"]}
    assert {"reference", "simulation", "difference"} <= labels


def test_mesh_convergence_with_two_levels_is_a_warning(plate):
    c = _check(run_validation(plate), "Mesh convergence")
    assert c["status"] == "warning"
    assert "3" in c["message"] or "levels" in c["message"]


def test_residual_above_criterion_is_flagged(aero):
    c = _check(run_validation(aero), "Solver convergence")
    assert c["status"] == "warning"
    assert any(e["label"] == "criterion" for e in c["evidence"])


def test_limit_breach_produces_a_critical_finding(plate):
    diag = run_diagnostics(plate)
    crit = [f for f in diag["findings"] if f["severity"] == "critical"]
    assert crit, "cooling plate exceeds its 55 C limit and should be flagged"
    f = crit[0]
    assert f["evidence"] and f["possible_cause"] and f["suggested_investigation"]
    assert "node" in f["location"]


def test_clean_case_has_no_critical_findings(suspension):
    assert run_diagnostics(suspension)["counts"]["critical"] == 0


def test_findings_are_ordered_by_severity(aero):
    order = {"critical": 0, "warning": 1, "info": 2}
    sev = [order[f["severity"]] for f in run_diagnostics(aero)["findings"]]
    assert sev == sorted(sev)


def test_nan_values_are_detected(bracket):
    bracket.fields["von_mises"].values[0, 0] = np.nan
    try:
        diag = run_diagnostics(bracket)
        assert any(f["rule"] == "missing_data" for f in diag["findings"])
        val = run_validation(bracket)
        assert _check(val, "Missing data")["status"] == "investigate"
    finally:
        bracket.fields["von_mises"].values[0, 0] = 0.0


def test_inconsistent_units_are_critical(bracket):
    original = bracket.units.stress
    bracket.units.stress = "psi"
    try:
        diag = run_diagnostics(bracket)
        assert any(f["rule"] == "unit_consistency" for f in diag["findings"])
    finally:
        bracket.units.stress = original


def test_stress_concentration_rule_reports_a_ratio(bracket):
    findings = [f for f in run_diagnostics(bracket)["findings"]
                if f["rule"] == "stress_concentration"]
    if findings:
        labels = {e["label"] for e in findings[0]["evidence"]}
        assert "peak / neighbourhood ratio" in labels
