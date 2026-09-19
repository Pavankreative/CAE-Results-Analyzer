"""Registered-but-unimplemented formats.

These exist so the application can report honestly what it cannot yet read, and
so a contributor has an obvious place to add a parser. Calling one raises
UnsupportedFormatError with an explanation.
"""
from __future__ import annotations

from app.adapters.base import AdapterInfo, PlannedAdapter


def _planned(key, name, solver, exts, notes):
    cls = type(
        f"{key.replace('-', '_').title()}Adapter",
        (PlannedAdapter,),
        {"info": AdapterInfo(key=key, name=name, solver=solver, extensions=exts,
                             status="planned", notes=notes)},
    )
    return cls()


PLANNED_ADAPTERS = [
    _planned("ansys-rst", "ANSYS Mechanical result", "ANSYS Mechanical", [".rst", ".rth"],
             "Binary result file; a reader would map nodal/elemental results and load steps."),
    _planned("fluent-cas-dat", "ANSYS Fluent case/data", "ANSYS Fluent", [".cas", ".dat"],
             "Cell and face data plus residual history."),
    _planned("cfx-res", "ANSYS CFX result", "ANSYS CFX", [".res"],
             "CFX result file with boundary and monitor data."),
    _planned("abaqus-odb", "Abaqus output database", "Abaqus", [".odb"],
             "Requires the Abaqus Python API or a third-party ODB reader."),
    _planned("nastran-op2", "Nastran OP2", "MSC/NX Nastran", [".op2", ".f06"],
             "Displacement, stress and modal blocks."),
    _planned("lsdyna-d3plot", "LS-DYNA d3plot", "LS-DYNA", [".d3plot"],
             "Explicit dynamics state database."),
    _planned("openfoam-case", "OpenFOAM case directory", "OpenFOAM", [".foam"],
             "Time directories; VTK legacy export is supported today via foamToVTK."),
    _planned("starccm-sim", "STAR-CCM+ simulation", "Simcenter STAR-CCM+", [".sim"],
             "Requires the STAR-CCM+ java macro API for export."),
    _planned("comsol-mph", "COMSOL model", "COMSOL Multiphysics", [".mph"],
             "Requires COMSOL server export."),
    _planned("adams-res", "Adams result", "MSC Adams", [".res", ".req"],
             "Body, joint and force channels."),
    _planned("cgns", "CGNS", "Neutral exchange", [".cgns"],
             "Needs the CGNS/HDF5 library."),
]
