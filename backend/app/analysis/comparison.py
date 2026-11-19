"""Simulation A vs B comparison."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from app.analysis.calculations import standard_calculations
from app.analysis.statistics import envelope, field_statistics
from app.core.model import FieldLocation, Simulation


class ComparisonValidationError(ValueError):
    """Result sets cannot be compared without explicit conversion or mapping."""


def _node_alignment(sim_a: Simulation, sim_b: Simulation) -> np.ndarray:
    """Return B's row indices in A's Node-ID order; never infer identity from size."""
    if sim_a.units.to_dict() != sim_b.units.to_dict():
        raise ComparisonValidationError("Unit systems differ; convert units explicitly before comparison")
    for sim in (sim_a, sim_b):
        ids = sim.mesh.node_ids
        if not sim.mesh.node_ids_explicit or ids is None:
            raise ComparisonValidationError(f"{sim.id}: explicit solver Node IDs are required")
        ids = np.asarray(ids)
        if (ids.ndim != 1 or len(ids) != sim.mesh.n_nodes or ids.dtype.kind not in "iu"
                or len(np.unique(ids)) != len(ids) or len(ids) == 0):
            raise ComparisonValidationError(f"{sim.id}: Node IDs must be nonempty, unique integers, one per node")
        if not np.isfinite(sim.mesh.nodes).all():
            raise ComparisonValidationError(f"{sim.id}: reference node coordinates must be finite")
    a_ids, b_ids = sim_a.mesh.node_ids, sim_b.mesh.node_ids
    if set(a_ids.tolist()) != set(b_ids.tolist()):
        raise ComparisonValidationError("Node ID sets differ; missing or extra nodes require explicit mesh mapping")
    b_rows = {int(node_id): row for row, node_id in enumerate(b_ids)}
    order = np.asarray([b_rows[int(node_id)] for node_id in a_ids], dtype=np.intp)
    if not np.allclose(sim_a.mesh.nodes, sim_b.mesh.nodes[order], rtol=0, atol=1e-9):
        raise ComparisonValidationError("Reference coordinates differ for matching Node IDs; explicit mesh mapping is required")
    return order


def _validate_fields(sim_a: Simulation, sim_b: Simulation, shared: List[str], step: int) -> None:
    for name in shared:
        a, b = sim_a.field(name), sim_b.field(name)
        if not a.unit.strip() or a.unit != b.unit:
            raise ComparisonValidationError(f"{name}: field units must be explicit and identical ({a.unit!r} vs {b.unit!r})")
        if a.location is not FieldLocation.NODAL or b.location is not FieldLocation.NODAL:
            raise ComparisonValidationError(f"{name}: only nodal fields support Node-ID comparison")
        if a.field_type is not b.field_type:
            raise ComparisonValidationError(f"{name}: field types differ")
        for sim, field in ((sim_a, a), (sim_b, b)):
            if not -field.n_steps <= step < field.n_steps:
                raise ComparisonValidationError(f"{name}: step {step} is out of range in {sim.id}")
            if field.values.shape[1] != sim.mesh.n_nodes:
                raise ComparisonValidationError(f"{name}: result length does not match the node table")
            if not np.isfinite(field.values).all():
                raise ComparisonValidationError(f"{name}: result values must be finite")
        if not np.isfinite([a.steps[step], b.steps[step]]).all() or not np.isclose(
                a.steps[step], b.steps[step], rtol=0, atol=1e-12):
            raise ComparisonValidationError(f"{name}: selected load-step/time values differ")


def _pct(a: float, b: float) -> Optional[float]:
    if a == 0:
        return None
    return (b - a) / abs(a) * 100.0


def compare(sim_a: Simulation, sim_b: Simulation, fields: Optional[List[str]] = None,
            step: int = -1) -> Dict[str, Any]:
    """Scalar deltas, field difference statistics and overlay series.

    Pointwise differences are B minus A after explicit Node-ID alignment.
    Incompatible data raises ComparisonValidationError; no implicit conversion,
    intersection-only comparison, or scalar-only fallback is performed.
    """
    if fields is not None and any(f not in sim_a.fields or f not in sim_b.fields for f in fields):
        raise ComparisonValidationError("Requested fields must exist in both simulations")
    shared = list(dict.fromkeys(fields)) if fields is not None else [f for f in sim_a.fields if f in sim_b.fields]
    if not shared:
        raise ComparisonValidationError("No common result fields selected")
    order_b = _node_alignment(sim_a, sim_b)
    _validate_fields(sim_a, sim_b, shared, step)
    same_mesh = True  # Node identity and reference coordinates have been checked above.
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
            d = sim_b.field(name).step(step)[order_b] - sim_a.field(name).step(step)
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
        if calc_a[name].unit != calc_b[name].unit:
            raise ComparisonValidationError(f"{name}: derived-calculation units differ")
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
        "mesh_note": "Pointwise differences use explicit Node-ID alignment (B minus A); "
                     "node sets, reference coordinates, units and selected steps were checked. "
                     "Vector fields compare magnitudes, not component-wise vector differences.",
        "scalars": scalars,
        "field_differences": diffs,
        "overlays": overlays,
        "calculations": calcs,
    }
