"""Native result-model adapter (.caer.json).

This is the interchange format the sample datasets ship in and the format the
application writes when it saves a simulation.
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any, Dict

import numpy as np

from app.adapters.base import AdapterError, AdapterInfo, BaseAdapter
from app.core.model import (
    BoundaryCondition,
    ConvergenceHistory,
    Domain,
    FieldLocation,
    FieldType,
    Load,
    Material,
    Mesh,
    ResultField,
    Simulation,
    UnitSystem,
)

FORMAT_VERSION = 1


def _open(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return open(path, "r", encoding="utf-8")


class NativeJSONAdapter(BaseAdapter):
    info = AdapterInfo(
        key="native-json",
        name="Native CAE result model",
        solver="CAE Results Analyzer",
        extensions=[".json", ".caer.json", ".gz"],
        status="implemented",
        notes="Interchange format used by the sample datasets and by project save/load.",
    )

    def read(self, path: Path, **kwargs) -> Simulation:
        with _open(path) as fh:
            raw = json.load(fh)
        return self.from_dict(raw)

    # ---------------------------------------------------------------- reading
    @staticmethod
    def from_dict(raw: Dict[str, Any]) -> Simulation:
        if raw.get("format") != "caer-result":
            raise AdapterError("not a CAE Results Analyzer result file")
        if int(raw.get("version", 0)) > FORMAT_VERSION:
            raise AdapterError(
                f"file format version {raw['version']} is newer than supported "
                f"version {FORMAT_VERSION}"
            )
        m = raw["mesh"]
        mesh = Mesh(
            nodes=np.asarray(m["nodes"], dtype=np.float64),
            triangles=np.asarray(m["triangles"], dtype=np.int32),
            node_ids=np.asarray(m["node_ids"]) if m.get("node_ids") is not None else None,
            elements=m.get("elements", []),
            metrics=m.get("metrics", {}),
            part_ids=np.asarray(m["part_ids"], dtype=np.int32) if m.get("part_ids") else None,
            parts=m.get("parts", []),
        )
        sim = Simulation(
            id=raw["id"],
            name=raw["name"],
            domain=Domain(raw["domain"]),
            analysis_type=raw.get("analysis_type", ""),
            solver=raw.get("solver", ""),
            units=UnitSystem(**raw.get("units", {})),
            mesh=mesh,
            materials=[Material(**x) for x in raw.get("materials", [])],
            boundary_conditions=[BoundaryCondition(**x) for x in raw.get("boundary_conditions", [])],
            loads=[Load(**x) for x in raw.get("loads", [])],
            load_cases=raw.get("load_cases", []),
            metadata=raw.get("metadata", {}),
            is_sample_data=raw.get("is_sample_data", True),
        )
        for f in raw.get("fields", []):
            sim.add_field(
                ResultField(
                    name=f["name"],
                    label=f.get("label", f["name"]),
                    unit=f.get("unit", ""),
                    values=np.asarray(f["values"], dtype=np.float64),
                    location=FieldLocation(f.get("location", "nodal")),
                    field_type=FieldType(f.get("type", "scalar")),
                    category=f.get("category", "General"),
                    steps=f.get("steps"),
                    derived=f.get("derived", False),
                    provenance=f.get("provenance", ""),
                    limits=f.get("limits", {}),
                )
            )
        c = raw.get("convergence")
        if c:
            sim.convergence = ConvergenceHistory(
                iterations=c["iterations"],
                monitors=c["monitors"],
                converged=c.get("converged"),
                criterion=c.get("criterion"),
            )
        return sim

    # ---------------------------------------------------------------- writing
    @staticmethod
    def to_dict(sim: Simulation, decimals: int = 5) -> Dict[str, Any]:
        r = lambda a: np.round(np.asarray(a), decimals).tolist()  # noqa: E731
        return {
            "format": "caer-result",
            "version": FORMAT_VERSION,
            "id": sim.id,
            "name": sim.name,
            "domain": sim.domain.value,
            "analysis_type": sim.analysis_type,
            "solver": sim.solver,
            "units": sim.units.to_dict(),
            "is_sample_data": sim.is_sample_data,
            "load_cases": sim.load_cases,
            "metadata": sim.metadata,
            "mesh": {
                "nodes": r(sim.mesh.nodes),
                "triangles": sim.mesh.triangles.tolist(),
                # Never promote generated display indices into solver Node IDs on save.
                "node_ids": sim.mesh.node_ids.tolist() if sim.mesh.node_ids_explicit else None,
                "parts": sim.mesh.parts,
                "part_ids": sim.mesh.part_ids.tolist() if sim.mesh.part_ids is not None else None,
                "metrics": sim.mesh.metrics,
                "elements": sim.mesh.elements,
            },
            "fields": [
                {
                    "name": f.name,
                    "label": f.label,
                    "unit": f.unit,
                    "category": f.category,
                    "location": f.location.value,
                    "type": f.field_type.value,
                    "steps": f.steps,
                    "derived": f.derived,
                    "provenance": f.provenance,
                    "limits": f.limits,
                    "values": r(f.values),
                }
                for f in sim.fields.values()
            ],
            "materials": [{"name": m.name, "properties": m.properties} for m in sim.materials],
            "boundary_conditions": [
                {"name": b.name, "kind": b.kind, "definition": b.definition}
                for b in sim.boundary_conditions
            ],
            "loads": [{"name": l.name, "definition": l.definition} for l in sim.loads],
            "convergence": (
                {
                    "iterations": sim.convergence.iterations,
                    "monitors": sim.convergence.monitors,
                    "converged": sim.convergence.converged,
                    "criterion": sim.convergence.criterion,
                }
                if sim.convergence
                else None
            ),
        }

    @classmethod
    def write(cls, sim: Simulation, path: Path, decimals: int = 5) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = cls.to_dict(sim, decimals=decimals)
        if path.suffix == ".gz":
            with gzip.open(path, "wt", encoding="utf-8") as fh:
                json.dump(payload, fh, separators=(",", ":"))
        else:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, separators=(",", ":"))
        return path
