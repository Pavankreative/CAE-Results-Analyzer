"""Field statistics and filtering. Pure numpy, no solver knowledge."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

import numpy as np

from app.core.model import FieldLocation, ResultField, Simulation


@dataclass
class Extremum:
    value: float
    index: int
    node_id: Optional[int]
    coordinates: Optional[List[float]]


@dataclass
class FieldStatistics:
    field: str
    label: str
    unit: str
    step: int
    count: int
    minimum: Extremum
    maximum: Extremum
    mean: float
    std: float
    median: float
    p95: float
    p99: float
    nan_count: int

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


def field_statistics(sim: Simulation, field_name: str, step: int = -1) -> FieldStatistics:
    f = sim.field(field_name)
    values = f.step(step)
    finite = np.isfinite(values)
    clean = values[finite]
    if clean.size == 0:
        raise ValueError(f"field '{field_name}' has no finite values at step {step}")

    def extremum(idx_in_clean: int, is_min: bool) -> Extremum:
        target = clean.min() if is_min else clean.max()
        idx = int(np.flatnonzero(finite)[np.argmin(np.abs(clean - target))])
        node_id, coords = None, None
        if f.location is FieldLocation.NODAL and idx < sim.mesh.n_nodes:
            node_id = int(sim.mesh.node_ids[idx])
            coords = [round(float(c), 4) for c in sim.mesh.nodes[idx]]
        return Extremum(float(target), idx, node_id, coords)

    return FieldStatistics(
        field=f.name,
        label=f.label,
        unit=f.unit,
        step=(step if step >= 0 else f.n_steps + step),
        count=int(clean.size),
        minimum=extremum(0, True),
        maximum=extremum(0, False),
        mean=float(clean.mean()),
        std=float(clean.std(ddof=0)),
        median=float(np.median(clean)),
        p95=float(np.percentile(clean, 95)),
        p99=float(np.percentile(clean, 99)),
        nan_count=int((~finite).sum()),
    )


def histogram(sim: Simulation, field_name: str, step: int = -1, bins: int = 24) -> Dict[str, Any]:
    values = sim.field(field_name).step(step)
    values = values[np.isfinite(values)]
    counts, edges = np.histogram(values, bins=bins)
    return {"counts": counts.tolist(), "edges": [float(e) for e in edges]}


def filter_field(
    sim: Simulation,
    field_name: str,
    step: int = -1,
    minimum: Optional[float] = None,
    maximum: Optional[float] = None,
    fraction_of_max: Optional[float] = None,
) -> Dict[str, Any]:
    """Select entities inside a value band.

    ``fraction_of_max`` selects everything at or above a fraction of the step
    maximum, which is how the "above 80 % of peak" screening filter works.
    """
    f = sim.field(field_name)
    values = f.step(step)
    lo = -np.inf if minimum is None else float(minimum)
    hi = np.inf if maximum is None else float(maximum)
    if fraction_of_max is not None:
        lo = max(lo, float(np.nanmax(values)) * float(fraction_of_max))
    mask = np.isfinite(values) & (values >= lo) & (values <= hi)
    idx = np.flatnonzero(mask)
    return {
        "field": field_name,
        "step": step,
        "lower": None if lo == -np.inf else lo,
        "upper": None if hi == np.inf else hi,
        "selected": int(idx.size),
        "total": int(values.size),
        "fraction": float(idx.size / values.size) if values.size else 0.0,
        "indices": idx[:5000].tolist(),
        "node_ids": (
            sim.mesh.node_ids[idx[:5000]].tolist()
            if f.location is FieldLocation.NODAL and idx.size and idx.max() < sim.mesh.n_nodes
            else []
        ),
    }


def time_history(sim: Simulation, field_name: str, index: int) -> Dict[str, Any]:
    """Value of one entity across all steps."""
    f = sim.field(field_name)
    series = [float(f.step(s)[index]) for s in range(f.n_steps)]
    return {"field": field_name, "index": index, "steps": f.steps, "values": series,
            "unit": f.unit, "label": f.label}


def envelope(sim: Simulation, field_name: str) -> Dict[str, Any]:
    """Per-step min/max/mean — the basis of the timeline plot."""
    f = sim.field(field_name)
    out = {"steps": f.steps, "min": [], "max": [], "mean": []}
    for s in range(f.n_steps):
        v = f.step(s)
        v = v[np.isfinite(v)]
        out["min"].append(float(v.min()))
        out["max"].append(float(v.max()))
        out["mean"].append(float(v.mean()))
    return out


def all_statistics(sim: Simulation, step: int = -1) -> List[Dict[str, Any]]:
    out = []
    for name in sim.fields:
        try:
            out.append(field_statistics(sim, name, step).to_dict())
        except ValueError:
            continue
    return out
