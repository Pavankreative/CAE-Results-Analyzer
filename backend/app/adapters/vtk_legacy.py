"""VTK legacy ASCII reader (unstructured grid / polydata).

A real parser: it reads POINTS, CELLS/CELL_TYPES or POLYGONS, and nodal
POINT_DATA SCALARS/VECTORS, and maps them into the common model. VTK legacy is
the exchange format most solvers (including OpenFOAM via foamToVTK) can write,
so it is the practical entry point for external data.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import numpy as np

from app.adapters.base import AdapterError, AdapterInfo, BaseAdapter
from app.core.model import (
    Domain,
    FieldType,
    Mesh,
    ResultField,
    Simulation,
    UnitSystem,
)

# VTK cell type -> the triangles of its surface, expressed as local node indices
_TRI_OF = {
    5: [(0, 1, 2)],                                           # triangle
    9: [(0, 1, 2), (0, 2, 3)],                                # quad
    10: [(0, 1, 2), (0, 1, 3), (1, 2, 3), (0, 2, 3)],         # tetra
    12: [(0, 1, 2), (0, 2, 3), (4, 5, 6), (4, 6, 7),          # hexahedron
         (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5),
         (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)],
    13: [(0, 1, 2), (3, 4, 5), (0, 1, 4), (0, 4, 3),          # wedge
         (1, 2, 5), (1, 5, 4), (0, 2, 5), (0, 5, 3)],
}


def _tokens(text: str) -> List[str]:
    return text.split()


class VTKLegacyAdapter(BaseAdapter):
    info = AdapterInfo(
        key="vtk-legacy",
        name="VTK legacy ASCII",
        solver="Neutral exchange (OpenFOAM, ParaView, VisIt)",
        extensions=[".vtk"],
        status="implemented",
        notes="ASCII unstructured grid and polydata with nodal scalar/vector data.",
    )

    def read(self, path: Path, domain: str = "Multiphysics", **kwargs) -> Simulation:
        text = path.read_text(errors="ignore")
        if "# vtk DataFile Version" not in text.splitlines()[0]:
            raise AdapterError("not a VTK legacy file")
        if "ASCII" not in text:
            raise AdapterError("only ASCII VTK legacy files are supported")

        title = text.splitlines()[1].strip() or path.stem
        nodes = self._points(text)
        triangles = self._triangles(text, len(nodes))
        fields = self._point_data(text, len(nodes))
        if not len(nodes):
            raise AdapterError("no POINTS section found")

        mesh = Mesh(nodes=nodes, triangles=triangles, parts=["Imported mesh"],
                    part_ids=np.zeros(len(triangles), dtype=np.int32),
                    metrics={"Nodes": len(nodes), "Surface triangles": len(triangles)})
        sim = Simulation(
            id=path.stem,
            name=title,
            domain=Domain(domain) if domain in Domain._value2member_map_ else Domain.MULTIPHYSICS,
            analysis_type="Imported result",
            solver="Imported via VTK legacy",
            units=UnitSystem(),
            mesh=mesh,
            is_sample_data=False,
        )
        for name, (values, kind) in fields.items():
            sim.add_field(
                ResultField(
                    name=name,
                    label=name.replace("_", " "),
                    unit="",
                    values=values[None, ...],
                    field_type=FieldType.VECTOR if kind == "vector" else FieldType.SCALAR,
                    category="Imported",
                    provenance=f"POINT_DATA in {path.name}",
                )
            )
        return sim

    # ------------------------------------------------------------------ parts
    @staticmethod
    def _points(text: str) -> np.ndarray:
        i = text.find("POINTS")
        if i < 0:
            return np.zeros((0, 3))
        header, rest = text[i:].split("\n", 1)
        n = int(_tokens(header)[1])
        vals: List[float] = []
        for line in rest.splitlines():
            vals.extend(float(v) for v in _tokens(line))
            if len(vals) >= 3 * n:
                break
        return np.asarray(vals[: 3 * n], dtype=np.float64).reshape(n, 3)

    @staticmethod
    def _cells(text: str, key: str) -> List[List[int]]:
        i = text.find(key)
        if i < 0:
            return []
        header, rest = text[i:].split("\n", 1)
        n = int(_tokens(header)[1])
        out: List[List[int]] = []
        buf: List[int] = []
        for line in rest.splitlines():
            buf.extend(int(v) for v in _tokens(line))
            while buf:
                size = buf[0]
                if len(buf) < size + 1:
                    break
                out.append(buf[1 : size + 1])
                buf = buf[size + 1 :]
            if len(out) >= n:
                break
        return out[:n]

    @classmethod
    def _triangles(cls, text: str, n_nodes: int) -> np.ndarray:
        cells = cls._cells(text, "CELLS")
        tris: List[List[int]] = []
        if cells:
            types_i = text.find("CELL_TYPES")
            types: List[int] = []
            if types_i >= 0:
                _, rest = text[types_i:].split("\n", 1)
                for line in rest.splitlines():
                    types.extend(int(v) for v in _tokens(line))
                    if len(types) >= len(cells):
                        break
            for cell, ctype in zip(cells, types or [5] * len(cells)):
                for combo in _TRI_OF.get(ctype, []):
                    if max(combo) < len(cell):
                        tris.append([cell[k] for k in combo])
        else:
            for poly in cls._cells(text, "POLYGONS"):
                for k in range(1, len(poly) - 1):
                    tris.append([poly[0], poly[k], poly[k + 1]])
        arr = np.asarray(tris, dtype=np.int32).reshape(-1, 3)
        if len(arr):
            arr = arr[(arr < n_nodes).all(axis=1)]
        return arr

    @staticmethod
    def _point_data(text: str, n_nodes: int) -> Dict[str, tuple]:
        out: Dict[str, tuple] = {}
        i = text.find("POINT_DATA")
        if i < 0:
            return out
        block = text[i:]
        lines = block.splitlines()
        k = 0
        while k < len(lines):
            tok = _tokens(lines[k])
            if tok and tok[0] in ("SCALARS", "VECTORS"):
                kind = "scalar" if tok[0] == "SCALARS" else "vector"
                name = tok[1]
                k += 1
                if k < len(lines) and _tokens(lines[k])[:1] == ["LOOKUP_TABLE"]:
                    k += 1
                want = n_nodes * (3 if kind == "vector" else 1)
                vals: List[float] = []
                while k < len(lines) and len(vals) < want:
                    t = _tokens(lines[k])
                    if t and not t[0].replace("-", "").replace(".", "").replace("e", "").replace("E", "").replace("+", "").isdigit():
                        try:
                            float(t[0])
                        except ValueError:
                            break
                    vals.extend(float(v) for v in t)
                    k += 1
                if len(vals) >= want:
                    arr = np.asarray(vals[:want], dtype=np.float64)
                    out[name] = (arr.reshape(n_nodes, 3) if kind == "vector" else arr, kind)
                continue
            k += 1
        return out
