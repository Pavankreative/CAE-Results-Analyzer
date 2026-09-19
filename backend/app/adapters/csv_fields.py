"""CSV point-cloud adapter.

Reads a table of node coordinates plus one column per result variable:

    x,y,z,von_mises[MPa],displacement[mm]

A Delaunay-free convex surface is not attempted; the adapter builds a mesh with
no triangles, which the API serves as a point set. Useful for probe exports and
measurement data.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import List

import numpy as np

from app.adapters.base import AdapterError, AdapterInfo, BaseAdapter
from app.core.model import Domain, Mesh, ResultField, Simulation, UnitSystem

_UNIT = re.compile(r"^(?P<name>[^\[]+?)\s*(\[(?P<unit>[^\]]*)\])?$")


class CSVPointAdapter(BaseAdapter):
    info = AdapterInfo(
        key="csv-points",
        name="CSV point data",
        solver="Generic tabular export",
        extensions=[".csv"],
        status="implemented",
        notes="Columns x,y,z followed by one column per scalar variable.",
    )

    def read(self, path: Path, domain: str = "Multiphysics", **kwargs) -> Simulation:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            rows = list(csv.reader(fh))
        if len(rows) < 2:
            raise AdapterError("CSV file has no data rows")
        header = [h.strip() for h in rows[0]]
        lower = [h.lower() for h in header]
        for axis in ("x", "y", "z"):
            if axis not in lower:
                raise AdapterError("CSV must contain x, y and z columns")
        ix, iy, iz = lower.index("x"), lower.index("y"), lower.index("z")
        data = np.asarray(
            [[float(v) if v.strip() else np.nan for v in r] for r in rows[1:] if any(r)],
            dtype=np.float64,
        )
        nodes = data[:, [ix, iy, iz]]
        mesh = Mesh(nodes=nodes, triangles=np.zeros((0, 3), dtype=np.int32),
                    parts=["Point set"], metrics={"Nodes": len(nodes), "Surface triangles": 0})
        sim = Simulation(
            id=path.stem, name=path.stem, domain=Domain(domain) if domain in Domain._value2member_map_
            else Domain.MULTIPHYSICS,
            analysis_type="Imported point data", solver="Imported via CSV",
            units=UnitSystem(), mesh=mesh, is_sample_data=False,
        )
        for i, col in enumerate(header):
            if i in (ix, iy, iz):
                continue
            m = _UNIT.match(col)
            name = (m.group("name") if m else col).strip()
            unit = (m.group("unit") or "") if m else ""
            sim.add_field(
                ResultField(name=name.lower().replace(" ", "_"), label=name, unit=unit,
                            values=data[:, i][None, :], category="Imported",
                            provenance=f"column '{col}' of {path.name}")
            )
        if not sim.fields:
            raise AdapterError("CSV contains coordinates but no result columns")
        return sim
