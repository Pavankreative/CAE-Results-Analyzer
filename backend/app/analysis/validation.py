"""Validation framework.

Each check returns a status plus the evidence that produced it. A check with no
data stays NOT_VALIDATED — it never defaults to a pass.
"""
from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any, Callable, Dict, List

import numpy as np

from app.analysis.statistics import field_statistics
from app.core.model import Simulation, ValidationStatus


@dataclass
class ValidationResult:
    name: str
    status: ValidationStatus
    message: str
    evidence: List[Dict[str, Any]] = dc_field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "status": self.status.value,
                "message": self.message, "evidence": self.evidence}


def _ev(label: str, value: Any) -> Dict[str, Any]:
    return {"label": label, "value": value}


# --------------------------------------------------------------------- checks
def check_units(sim: Simulation) -> ValidationResult:
    u = sim.units
    ev = [_ev(k, v) for k, v in u.to_dict().items()]
    if u.consistent:
        return ValidationResult("Unit consistency", ValidationStatus.VERIFIED,
                                "The declared unit system is internally consistent.", ev)
    return ValidationResult(
        "Unit consistency", ValidationStatus.INVESTIGATE,
        "The declared units do not form a recognised consistent system; results may be "
        "scaled incorrectly.", ev)


def check_missing_data(sim: Simulation) -> ValidationResult:
    ev, bad = [], 0
    for name, f in sim.fields.items():
        n_nan = int((~np.isfinite(f.values)).sum())
        bad += n_nan
        ev.append(_ev(f"{name}: non-finite values", n_nan))
    ev.append(_ev("Fields checked", len(sim.fields)))
    if not sim.fields:
        return ValidationResult("Missing data", ValidationStatus.NOT_VALIDATED,
                                "The simulation carries no result fields.", ev)
    if bad == 0:
        return ValidationResult("Missing data", ValidationStatus.VERIFIED,
                                "All result fields are fully populated with finite values.", ev)
    return ValidationResult("Missing data", ValidationStatus.INVESTIGATE,
                            f"{bad} non-finite values found across the result fields.", ev)


def check_ranges(sim: Simulation) -> ValidationResult:
    """Physical plausibility against limits declared on each field."""
    ev, breaches, checked = [], 0, 0
    for name, f in sim.fields.items():
        lim = f.limits or {}
        if not lim:
            continue
        st = field_statistics(sim, name)
        checked += 1
        if "max_allowed" in lim:
            ev.append(_ev(f"{f.label} max", f"{st.maximum.value:.4g} {f.unit}"))
            ev.append(_ev(f"{f.label} limit", f"{lim['max_allowed']:.4g} {f.unit}"))
            if st.maximum.value > lim["max_allowed"]:
                breaches += 1
        if "min_allowed" in lim:
            ev.append(_ev(f"{f.label} min", f"{st.minimum.value:.4g} {f.unit}"))
            if st.minimum.value < lim["min_allowed"]:
                breaches += 1
    if checked == 0:
        return ValidationResult("Range and limit check", ValidationStatus.NOT_VALIDATED,
                                "No design limits are declared on any field.", ev)
    if breaches:
        return ValidationResult("Range and limit check", ValidationStatus.INVESTIGATE,
                                f"{breaches} declared limit(s) exceeded.", ev)
    return ValidationResult("Range and limit check", ValidationStatus.VERIFIED,
                            "All declared limits are respected.", ev)


def check_convergence(sim: Simulation) -> ValidationResult:
    c = sim.convergence
    if c is None:
        return ValidationResult("Solver convergence", ValidationStatus.NOT_VALIDATED,
                                "No convergence history is attached to this simulation.", [])
    ev = [_ev("Iterations / steps", len(c.iterations))]
    worst_name, worst = "", -np.inf
    for k, series in c.monitors.items():
        last = float(series[-1])
        ev.append(_ev(f"final {k}", f"{last:.3g}"))
        if k.lower() not in ("cd", "cl", "outlet_temperature") and last > worst:
            worst, worst_name = last, k
    if c.criterion is None:
        return ValidationResult("Solver convergence", ValidationStatus.NOT_VALIDATED,
                                "No convergence criterion is declared for this run.", ev)
    ev.append(_ev("criterion", f"{c.criterion:.1e}"))
    if worst <= c.criterion:
        return ValidationResult("Solver convergence", ValidationStatus.VERIFIED,
                                "All residual monitors reach the declared criterion.", ev)
    return ValidationResult(
        "Solver convergence", ValidationStatus.WARNING,
        f"Residual '{worst_name}' stops at {worst:.2g}, above the {c.criterion:.1e} criterion.", ev)


def check_mesh_metadata(sim: Simulation) -> ValidationResult:
    required = ["Nodes", "Elements"]
    ev = [_ev(k, v) for k, v in sim.mesh.metrics.items()]
    ev.append(_ev("Surface triangles", sim.mesh.n_triangles))
    missing = [k for k in required if k not in sim.mesh.metrics]
    if missing:
        return ValidationResult("Mesh metadata", ValidationStatus.WARNING,
                                f"Mesh metadata is incomplete: missing {', '.join(missing)}.", ev)
    return ValidationResult("Mesh metadata", ValidationStatus.VERIFIED,
                            "Mesh metadata is present and readable.", ev)


def check_mesh_convergence(sim: Simulation) -> ValidationResult:
    """Uses a refinement study stored in metadata, when the project supplies one."""
    study = sim.metadata.get("mesh_convergence")
    if not study:
        return ValidationResult("Mesh convergence", ValidationStatus.NOT_VALIDATED,
                                "No mesh refinement study is linked to this simulation.", [])
    levels = study["levels"]
    ev = [_ev(f"{l['nodes']:,} nodes", f"{l['value']:.4g} {study.get('unit','')}") for l in levels]
    if len(levels) < 3:
        return ValidationResult("Mesh convergence", ValidationStatus.WARNING,
                                f"Only {len(levels)} refinement level(s) available; at least 3 are "
                                "needed to judge convergence.", ev)
    a, b = levels[-2]["value"], levels[-1]["value"]
    change = abs(b - a) / abs(a) * 100.0
    ev.append(_ev("change over the last refinement", f"{change:.2f} %"))
    target = study.get("target_percent", 2.0)
    ev.append(_ev("acceptance", f"<= {target} %"))
    status = ValidationStatus.VERIFIED if change <= target else ValidationStatus.WARNING
    return ValidationResult("Mesh convergence", status,
                            f"The monitored quantity changes by {change:.2f} % over the last "
                            f"refinement step.", ev)


def check_analytical(sim: Simulation) -> ValidationResult:
    """Comparison against a known/analytical value supplied with the case."""
    ref = sim.metadata.get("analytical_reference")
    if not ref:
        return ValidationResult("Analytical comparison", ValidationStatus.NOT_VALIDATED,
                                "No analytical or reference value is linked to this simulation.", [])
    sim_value = ref.get("simulation_value")
    if sim_value is None and ref.get("field"):
        sim_value = field_statistics(sim, ref["field"]).maximum.value
    diff = (sim_value - ref["value"]) / abs(ref["value"]) * 100.0
    band = ref.get("acceptance_percent", 10.0)
    ev = [_ev("reference", f"{ref['value']:.4g} {ref.get('unit','')}"),
          _ev("simulation", f"{sim_value:.4g} {ref.get('unit','')}"),
          _ev("difference", f"{diff:+.2f} %"),
          _ev("acceptance band", f"+/-{band} %"),
          _ev("source", ref.get("source", "supplied with the case"))]
    status = ValidationStatus.VERIFIED if abs(diff) <= band else ValidationStatus.WARNING
    return ValidationResult("Analytical comparison", status,
                            f"{ref.get('description','Reference comparison')}: {diff:+.1f} % against "
                            f"the reference value.", ev)


def check_experimental(sim: Simulation) -> ValidationResult:
    ref = sim.metadata.get("experimental_reference")
    if not ref:
        return ValidationResult("Experimental comparison", ValidationStatus.NOT_VALIDATED,
                                "No test data is linked to this simulation.", [])
    diff = (ref["simulation_value"] - ref["value"]) / abs(ref["value"]) * 100.0
    band = ref.get("acceptance_percent", 5.0)
    ev = [_ev("test value", f"{ref['value']:.4g} {ref.get('unit','')}"),
          _ev("simulation", f"{ref['simulation_value']:.4g} {ref.get('unit','')}"),
          _ev("difference", f"{diff:+.2f} %"), _ev("acceptance band", f"+/-{band} %"),
          _ev("data", ref.get("source", "sample data"))]
    status = ValidationStatus.VERIFIED if abs(diff) <= band else ValidationStatus.WARNING
    return ValidationResult("Experimental comparison", status,
                            f"Simulation differs from the test value by {diff:+.1f} %.", ev)


CHECKS: List[Callable[[Simulation], ValidationResult]] = [
    check_units, check_missing_data, check_ranges, check_convergence,
    check_mesh_metadata, check_mesh_convergence, check_analytical, check_experimental,
]

_ORDER = {ValidationStatus.INVESTIGATE: 3, ValidationStatus.WARNING: 2,
          ValidationStatus.VERIFIED: 1, ValidationStatus.NOT_VALIDATED: 0}


def run_validation(sim: Simulation) -> Dict[str, Any]:
    results = [c(sim) for c in CHECKS]
    worst = max(results, key=lambda r: _ORDER[r.status]).status
    if worst is ValidationStatus.NOT_VALIDATED:
        overall = ValidationStatus.NOT_VALIDATED
    else:
        overall = worst
    return {
        "simulation_id": sim.id,
        "overall": overall.value,
        "counts": {s.value: sum(1 for r in results if r.status is s) for s in ValidationStatus},
        "checks": [r.to_dict() for r in results],
    }
