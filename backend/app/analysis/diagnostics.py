"""Diagnostic rules.

Every finding is Finding -> Severity -> Evidence -> Location -> Possible cause
-> Suggested investigation. Rules describe what the data shows and what to check
next; they do not assert that a design is safe or unsafe.
"""
from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any, Callable, Dict, List

import numpy as np

from app.analysis.statistics import field_statistics
from app.core.model import FieldLocation, Simulation


@dataclass
class Finding:
    title: str
    severity: str             # "critical" | "warning" | "info"
    location: str
    evidence: List[Dict[str, Any]]
    possible_cause: str
    suggested_investigation: str
    rule: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title, "severity": self.severity, "location": self.location,
            "evidence": self.evidence, "possible_cause": self.possible_cause,
            "suggested_investigation": self.suggested_investigation, "rule": self.rule,
        }


def _ev(label: str, value: Any) -> Dict[str, Any]:
    return {"label": label, "value": value}


# ---------------------------------------------------------------------- rules
def rule_limit_exceedance(sim: Simulation) -> List[Finding]:
    out = []
    for name, f in sim.fields.items():
        lim = (f.limits or {}).get("max_allowed")
        if lim is None:
            continue
        st = field_statistics(sim, name)
        if st.maximum.value <= lim:
            continue
        values = f.step(-1)
        above = int(np.count_nonzero(values > lim))
        out.append(Finding(
            title=f"{f.label} exceeds its declared limit",
            severity="critical",
            location=(f"node {st.maximum.node_id} at "
                      f"({', '.join(f'{c:.1f}' for c in st.maximum.coordinates)})"
                      if st.maximum.coordinates else "peak entity"),
            evidence=[_ev("maximum", f"{st.maximum.value:.4g} {f.unit}"),
                      _ev("declared limit", f"{lim:.4g} {f.unit}"),
                      _ev("exceedance", f"{st.maximum.value - lim:+.3g} {f.unit}"),
                      _ev("entities above the limit", f"{above} of {values.size} "
                          f"({above / values.size * 100:.2f} %)")],
            possible_cause=("The field exceeds the limit recorded with the case. This is a "
                            "statement about the result and the declared limit, not about whether "
                            "the limit itself is correct for this application."),
            suggested_investigation=("Confirm the limit with the requirement owner, check the "
                                     "mesh convergence of the peak region, and evaluate the other "
                                     "load cases or operating points defined in this project."),
            rule="limit_exceedance"))
    return out


def rule_stress_concentration(sim: Simulation, ratio_threshold: float = 2.0) -> List[Finding]:
    name = next((n for n in ("von_mises", "stress", "max_principal") if n in sim.fields), None)
    if name is None:
        return []
    st = field_statistics(sim, name)
    f = sim.field(name)
    values = f.step(-1)
    if f.location is not FieldLocation.NODAL or st.maximum.coordinates is None:
        return []
    peak_xyz = np.asarray(st.maximum.coordinates)
    d = np.linalg.norm(sim.mesh.nodes - peak_xyz, axis=1)
    radius = max(float(np.percentile(d, 2)), 1e-6)
    near = values[d <= radius * 3]
    if near.size < 5:
        return []
    ratio = st.maximum.value / max(float(near.mean()), 1e-9)
    if ratio < ratio_threshold:
        return []
    return [Finding(
        title=f"Local concentration in {f.label}",
        severity="warning",
        location=f"node {st.maximum.node_id} at ({', '.join(f'{c:.1f}' for c in peak_xyz)})",
        evidence=[_ev("peak", f"{st.maximum.value:.4g} {f.unit}"),
                  _ev("neighbourhood mean", f"{near.mean():.4g} {f.unit}"),
                  _ev("peak / neighbourhood ratio", f"{ratio:.2f}"),
                  _ev("field P95", f"{st.p95:.4g} {f.unit}"),
                  _ev("sample radius", f"{radius * 3:.2f} {sim.units.length}")],
        possible_cause=("A steep local gradient. This is characteristic of either a genuine "
                        "stress riser at a small feature or a mesh-driven singularity at a sharp "
                        "corner; the two cannot be separated from a single mesh."),
        suggested_investigation=("Compare the peak across refinement levels. If it keeps rising "
                                 "without settling, treat it as a singularity and use a "
                                 "path-averaged value over twice the wall thickness instead."),
        rule="stress_concentration")]


def rule_residual_plateau(sim: Simulation) -> List[Finding]:
    c = sim.convergence
    if c is None or c.criterion is None:
        return []
    out = []
    for k, series in c.monitors.items():
        arr = np.asarray(series, dtype=float)
        if arr.size < 20 or k.lower() in ("cd", "cl", "outlet_temperature"):
            continue
        last, tail = float(arr[-1]), arr[-max(5, arr.size // 5):]
        drop = abs(float(tail[0] - tail[-1])) / max(abs(float(tail[0])), 1e-30)
        if last > c.criterion and drop < 0.25:
            out.append(Finding(
                title=f"Residual '{k}' plateaus above the criterion",
                severity="warning",
                location=f"global, last {tail.size} of {arr.size} iterations",
                evidence=[_ev("final residual", f"{last:.3g}"),
                          _ev("criterion", f"{c.criterion:.1e}"),
                          _ev("relative drop over the tail", f"{drop * 100:.1f} %"),
                          _ev("iterations", arr.size)],
                possible_cause=("A flat residual with otherwise stable behaviour usually points to "
                                "a locally unsteady region that a steady formulation cannot settle, "
                                "or to poor cells limiting the attainable residual floor."),
                suggested_investigation=("Check whether the integrated monitors are stable over the "
                                         "same window, run the case unsteady for a short physical "
                                         "time, and inspect mesh quality where the residual is "
                                         "concentrated."),
                rule="residual_plateau"))
    return out


def rule_monitor_stability(sim: Simulation) -> List[Finding]:
    c = sim.convergence
    if c is None:
        return []
    out = []
    for k, series in c.monitors.items():
        if k.lower() not in ("cd", "cl", "outlet_temperature"):
            continue
        arr = np.asarray(series, dtype=float)
        tail = arr[-max(3, arr.size // 5):]
        spread = (tail.max() - tail.min()) / max(abs(float(tail.mean())), 1e-12) * 100
        sev = "info" if spread < 1.0 else "warning"
        out.append(Finding(
            title=f"Monitored quantity '{k}' variation over the final window",
            severity=sev,
            location=f"global, last {tail.size} samples",
            evidence=[_ev("final value", f"{arr[-1]:.5g}"),
                      _ev("spread over the window", f"{spread:.2f} %"),
                      _ev("window length", tail.size)],
            possible_cause=("Monitor variation of this size is what an integrated quantity shows "
                            "when the solution is settled (below about 1 %) or still moving."),
            suggested_investigation=("Read this together with the residual history before quoting "
                                     "the value to more significant figures than the spread "
                                     "supports."),
            rule="monitor_stability"))
    return out


def rule_outliers(sim: Simulation, sigma: float = 6.0) -> List[Finding]:
    out = []
    for name, f in sim.fields.items():
        st = field_statistics(sim, name)
        if st.std <= 0:
            continue
        z = (st.maximum.value - st.mean) / st.std
        if z > sigma:
            out.append(Finding(
                title=f"Numerical outlier in {f.label}",
                severity="info",
                location=f"node {st.maximum.node_id}" if st.maximum.node_id else "peak entity",
                evidence=[_ev("peak", f"{st.maximum.value:.4g} {f.unit}"),
                          _ev("mean", f"{st.mean:.4g} {f.unit}"),
                          _ev("standard deviation", f"{st.std:.4g} {f.unit}"),
                          _ev("z-score of the peak", f"{z:.1f}")],
                possible_cause=("The extreme value sits far outside the bulk distribution, which "
                                "happens at genuine singular points and also at isolated bad "
                                "elements."),
                suggested_investigation=("Inspect the element quality at that location and compare "
                                         "against the P99 value before using the peak."),
                rule="outlier"))
    return out


def rule_unit_consistency(sim: Simulation) -> List[Finding]:
    if sim.units.consistent:
        return []
    return [Finding(
        title="Inconsistent unit system declared",
        severity="critical",
        location="simulation metadata",
        evidence=[_ev(k, v) for k, v in sim.units.to_dict().items()],
        possible_cause="The declared units do not form a recognised consistent set.",
        suggested_investigation=("Confirm the solver's working units and re-import with the correct "
                                 "unit system. Derived quantities are not trustworthy until this "
                                 "is resolved."),
        rule="unit_consistency")]


def rule_missing_data(sim: Simulation) -> List[Finding]:
    out = []
    for name, f in sim.fields.items():
        n_bad = int((~np.isfinite(f.values)).sum())
        if n_bad:
            out.append(Finding(
                title=f"Non-finite values in {f.label}",
                severity="critical",
                location=f"field '{name}'",
                evidence=[_ev("non-finite entries", n_bad),
                          _ev("total entries", int(f.values.size))],
                possible_cause="NaN or infinite values usually indicate a failed step or an unmapped region.",
                suggested_investigation="Re-export the field and confirm the solver completed the step.",
                rule="missing_data"))
    return out


RULES: List[Callable[[Simulation], List[Finding]]] = [
    rule_unit_consistency, rule_missing_data, rule_limit_exceedance,
    rule_stress_concentration, rule_residual_plateau, rule_monitor_stability, rule_outliers,
]

_SEV = {"critical": 0, "warning": 1, "info": 2}


def run_diagnostics(sim: Simulation) -> Dict[str, Any]:
    findings: List[Finding] = []
    for rule in RULES:
        findings.extend(rule(sim))
    findings.sort(key=lambda f: _SEV.get(f.severity, 3))
    return {
        "simulation_id": sim.id,
        "counts": {s: sum(1 for f in findings if f.severity == s) for s in ("critical", "warning", "info")},
        "findings": [f.to_dict() for f in findings],
    }
