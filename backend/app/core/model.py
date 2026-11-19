"""Common CAE result model.

Every adapter maps solver output into these structures. Nothing downstream
(analysis, validation, diagnostics, comparison, reporting) knows which solver
produced the data.
"""
from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence

import numpy as np


class Domain(str, Enum):
    FEA = "FEA"
    CFD = "CFD"
    THERMAL = "Thermal"
    MBD = "MBD"
    MULTIPHYSICS = "Multiphysics"
    ELECTROMAGNETIC = "Electromagnetic"
    BATTERY = "Battery"
    ACOUSTICS = "Acoustics"
    MANUFACTURING = "Manufacturing"


class FieldLocation(str, Enum):
    NODAL = "nodal"
    ELEMENTAL = "elemental"


class FieldType(str, Enum):
    SCALAR = "scalar"
    VECTOR = "vector"


class ValidationStatus(str, Enum):
    VERIFIED = "verified"
    WARNING = "warning"
    INVESTIGATE = "investigate"
    NOT_VALIDATED = "not_validated"


@dataclass
class UnitSystem:
    """Unit system of a result set. Conversion is explicit, never implied."""

    length: str = "mm"
    mass: str = "kg"
    time: str = "s"
    force: str = "N"
    stress: str = "MPa"
    temperature: str = "C"

    @property
    def consistent(self) -> bool:
        known = {
            ("mm", "kg", "s", "N", "MPa"),
            ("m", "kg", "s", "N", "Pa"),
            ("in", "lb", "s", "lbf", "psi"),
        }
        return (self.length, self.mass, self.time, self.force, self.stress) in known

    def to_dict(self) -> Dict[str, str]:
        return {
            "length": self.length,
            "mass": self.mass,
            "time": self.time,
            "force": self.force,
            "stress": self.stress,
            "temperature": self.temperature,
        }


@dataclass
class Mesh:
    """Node coordinates plus a surface triangulation used for visualisation.

    ``elements`` holds the solver's volume/shell elements when the adapter can
    read them; ``triangles`` is the render-ready surface skin.
    """

    nodes: np.ndarray                      # (n_nodes, 3) float64
    triangles: np.ndarray                  # (n_tris, 3) int32, index into nodes
    node_ids: Optional[np.ndarray] = None  # solver node numbering
    elements: List[Dict[str, Any]] = dc_field(default_factory=list)
    metrics: Dict[str, Any] = dc_field(default_factory=dict)
    part_ids: Optional[np.ndarray] = None  # (n_tris,) part index per triangle
    parts: List[str] = dc_field(default_factory=list)
    node_ids_explicit: bool = dc_field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.nodes = np.asarray(self.nodes, dtype=np.float64)
        self.triangles = np.asarray(self.triangles, dtype=np.int32)
        self.node_ids_explicit = self.node_ids is not None
        if self.node_ids is None:
            self.node_ids = np.arange(1, len(self.nodes) + 1, dtype=np.int64)
        else:
            self.node_ids = np.asarray(self.node_ids)
            if (self.node_ids.ndim != 1 or len(self.node_ids) != len(self.nodes)
                    or self.node_ids.dtype.kind not in "iu"
                    or len(np.unique(self.node_ids)) != len(self.node_ids)):
                raise ValueError("node_ids must contain one unique integer Node ID per node")
        if self.nodes.ndim != 2 or self.nodes.shape[1] != 3:
            raise ValueError("nodes must have shape (n, 3)")
        if len(self.triangles) and self.triangles.max() >= len(self.nodes):
            raise ValueError("triangle references a node index outside the node array")

    @property
    def n_nodes(self) -> int:
        return int(len(self.nodes))

    @property
    def n_triangles(self) -> int:
        return int(len(self.triangles))

    def bounds(self) -> Dict[str, List[float]]:
        return {
            "min": self.nodes.min(axis=0).tolist(),
            "max": self.nodes.max(axis=0).tolist(),
        }


@dataclass
class ResultField:
    """One result variable over one or more steps."""

    name: str
    label: str
    unit: str
    values: np.ndarray                      # (n_steps, n_entities) or (n_steps, n_entities, 3)
    location: FieldLocation = FieldLocation.NODAL
    field_type: FieldType = FieldType.SCALAR
    category: str = "General"
    steps: Optional[List[float]] = None
    derived: bool = False
    provenance: str = ""
    limits: Dict[str, float] = dc_field(default_factory=dict)

    def __post_init__(self) -> None:
        self.values = np.asarray(self.values, dtype=np.float64)
        if self.values.ndim == 1:                      # single step, scalar
            self.values = self.values[None, :]
        if self.steps is None:
            self.steps = [float(i) for i in range(self.values.shape[0])]
        if len(self.steps) != self.values.shape[0]:
            raise ValueError(f"field '{self.name}': steps do not match the value array")

    @property
    def n_steps(self) -> int:
        return int(self.values.shape[0])

    def step(self, index: int = -1) -> np.ndarray:
        """Scalar values for one step (vector fields collapse to magnitude)."""
        v = self.values[index]
        if self.field_type is FieldType.VECTOR:
            return np.linalg.norm(v, axis=-1)
        return v


@dataclass
class Material:
    name: str
    properties: Dict[str, Any] = dc_field(default_factory=dict)


@dataclass
class BoundaryCondition:
    name: str
    kind: str
    definition: str


@dataclass
class Load:
    name: str
    definition: str


@dataclass
class ConvergenceHistory:
    """Solver convergence record: iteration/step against one or more monitors."""

    iterations: List[float]
    monitors: Dict[str, List[float]]
    converged: Optional[bool] = None
    criterion: Optional[float] = None


@dataclass
class Simulation:
    """One solved case inside a project."""

    id: str
    name: str
    domain: Domain
    analysis_type: str
    solver: str
    units: UnitSystem
    mesh: Mesh
    fields: Dict[str, ResultField] = dc_field(default_factory=dict)
    materials: List[Material] = dc_field(default_factory=list)
    boundary_conditions: List[BoundaryCondition] = dc_field(default_factory=list)
    loads: List[Load] = dc_field(default_factory=list)
    convergence: Optional[ConvergenceHistory] = None
    load_cases: List[str] = dc_field(default_factory=list)
    metadata: Dict[str, Any] = dc_field(default_factory=dict)
    is_sample_data: bool = True
    source_file: str = ""
    adapter: str = ""

    def field(self, name: str) -> ResultField:
        if name not in self.fields:
            raise KeyError(f"simulation '{self.id}' has no field '{name}'")
        return self.fields[name]

    def add_field(self, f: ResultField) -> None:
        if f.location is FieldLocation.NODAL and f.values.shape[1] != self.mesh.n_nodes:
            raise ValueError(
                f"field '{f.name}' has {f.values.shape[1]} values for "
                f"{self.mesh.n_nodes} nodes"
            )
        self.fields[f.name] = f

    def summary(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "domain": self.domain.value,
            "analysis_type": self.analysis_type,
            "solver": self.solver,
            "units": self.units.to_dict(),
            "nodes": self.mesh.n_nodes,
            "triangles": self.mesh.n_triangles,
            "fields": [
                {
                    "name": f.name,
                    "label": f.label,
                    "unit": f.unit,
                    "category": f.category,
                    "steps": f.n_steps,
                    "derived": f.derived,
                    "type": f.field_type.value,
                    "location": f.location.value,
                }
                for f in self.fields.values()
            ],
            "load_cases": self.load_cases,
            "is_sample_data": self.is_sample_data,
            "source_file": self.source_file,
            "adapter": self.adapter,
            "metadata": self.metadata,
        }


@dataclass
class Project:
    id: str
    name: str
    description: str = ""
    owner: str = ""
    created: str = ""
    modified: str = ""
    simulation_ids: List[str] = dc_field(default_factory=list)
    metadata: Dict[str, Any] = dc_field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "owner": self.owner,
            "created": self.created,
            "modified": self.modified,
            "simulation_ids": list(self.simulation_ids),
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Project":
        return Project(
            id=d["id"],
            name=d["name"],
            description=d.get("description", ""),
            owner=d.get("owner", ""),
            created=d.get("created", ""),
            modified=d.get("modified", ""),
            simulation_ids=list(d.get("simulation_ids", [])),
            metadata=dict(d.get("metadata", {})),
        )


def sequence_to_list(x: Sequence[float]) -> List[float]:
    return [float(v) for v in x]
