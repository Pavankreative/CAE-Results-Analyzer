"""Simulation A vs B comparison."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from app.analysis.calculations import standard_calculations
from app.analysis.statistics import envelope, field_statistics
from app.core.model import Simulation


def _pct(a: float, b: float) -> Optional[float]:
    if a == 0:
        return None
    return (b - a) / abs(a) * 100.0


def compare(sim_a: Simulation, sim_b: Simulation, fields: Optional[List[str]] = None,
            step: int = -1) -> Dict[str, Any]:
    """Scalar deltas, field difference statistics and overlay series.

    Field-by-field difference contours are only produced when both simulations
    share a node count; otherwise the comparison stays scalar and says so.
    """
    shared = [f for f in (fields or sim_a.fields) if f in sim_b.fields]
    same_mesh = sim_a.mesh.n_nodes == sim_b.mesh.n_nodes
    scalars: List[Dict[str, Any]] = []
    for name in shared:
        sa, sb = field_statistics(sim_a, name, step), field_statistics(sim_b, name, step)
        for metric, va, vb in (("maximum", sa.maximum.value, sb.maximum.value),
                               ("mean", sa.mean, sb.mean),
                               ("P95", sa.p95, sb.p95)):
            scalars.append({
                "field": name, "label": sa.label, "metric": metric, "unit": sa.unit,
                "a": round(va, 6), "b": round(vb, 6),
                "delta": round(vb - va, 6), "percent": (None if _pct(va, vb) is None
                                                        else round(_pct(va, vb), 3)),
            })

    diffs: List[Dict[str, Any]] = []
    if same_mesh:
        for name in shared:
            d = sim_b.field(name).step(step) - sim_a.field(name).step(step)
            finite = d[np.isfinite(d)]
            if finite.size == 0:
                continue
            diffs.append({
                "field": name, "unit": sim_a.field(name).unit,
                "min": float(finite.min()), "max": float(finite.max()),
                "mean": float(finite.mean()), "abs_max": float(np.abs(finite).max()),
                "rms": float(np.sqrt((finite ** 2).mean())),
            })

    overlays = []
    for name in shared:
        if sim_a.field(name).n_steps > 1 and sim_b.field(name).n_steps > 1:
            ea, eb = envelope(sim_a, name), envelope(sim_b, name)
            overlays.append({"field": name, "unit": sim_a.field(name).unit,
                             "a": {"steps": ea["steps"], "values": ea["max"]},
                             "b": {"steps": eb["steps"], "values": eb["max"]}})
    if sim_a.convergence and sim_b.convergence:
        for k in set(sim_a.convergence.monitors) & set(sim_b.convergence.monitors):
            overlays.append({
                "field": f"monitor:{k}", "unit": "",
                "a": {"steps": sim_a.convergence.iterations, "values": sim_a.convergence.monitors[k]},
                "b": {"steps": sim_b.convergence.iterations, "values": sim_b.convergence.monitors[k]},
            })

    calc_a = {c.name: c for c in standard_calculations(sim_a)}
    calc_b = {c.name: c for c in standard_calculations(sim_b)}
    calcs = []
    for name in sorted(set(calc_a) & set(calc_b)):
        a, b = calc_a[name].result, calc_b[name].result
        calcs.append({"name": name, "unit": calc_a[name].unit, "a": round(a, 6),
                      "b": round(b, 6), "delta": round(b - a, 6),
                      "percent": (None if _pct(a, b) is None else round(_pct(a, b), 3))})

    return {
        "a": {"id": sim_a.id, "name": sim_a.name, "solver": sim_a.solver,
              "analysis_type": sim_a.analysis_type},
        "b": {"id": sim_b.id, "name": sim_b.name, "solver": sim_b.solver,
              "analysis_type": sim_b.analysis_type},
        "shared_fields": shared,
        "same_mesh": same_mesh,
        "mesh_note": ("Both results share a node count, so pointwise differences are computed."
                      if same_mesh else
                      "Node counts differ, so only scalar comparison is available; a mapped "
                      "difference field would require interpolation between the two meshes."),
        "scalars": scalars,
        "field_differences": diffs,
        "overlays": overlays,
        "calculations": calcs,
    }
