#!/usr/bin/env python3
"""Generate the four sample datasets in samples/.

The fields are analytic constructions, not solver output: they are shaped to
look like the results they stand in for so the whole workflow (statistics,
filtering, validation, diagnostics, comparison, reporting) can be exercised.
Every dataset is written with is_sample_data = True and the application labels
it as sample data wherever it is shown.

    python scripts/generate_samples.py [--out samples]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

from geometry import box_surface, cylinder_surface, ellipsoid_surface, merge  # noqa: E402

from app.adapters.native import NativeJSONAdapter  # noqa: E402
from app.core.model import (  # noqa: E402
    BoundaryCondition,
    ConvergenceHistory,
    Domain,
    FieldType,
    Load,
    Material,
    Mesh,
    ResultField,
    Simulation,
    UnitSystem,
)

RNG = np.random.default_rng(20260919)


def gauss(d, s):
    return np.exp(-(d ** 2) / (2 * s ** 2))


def steps_scale(n=5):
    """Load fraction per step, ending at the full load."""
    return np.linspace(0.2, 1.0, n)


def noise(shape, amplitude):
    return RNG.normal(0.0, amplitude, shape)


# --------------------------------------------------------------------- FEA
def bracket() -> Simulation:
    parts = [
        ("Base plate", *box_surface((90, 8, 60), (0, -16, 0), (26, 5, 18))),
        ("Vertical flange", *box_surface((8, 70, 60), (-41, 15, 0), (5, 22, 18))),
        ("Rib +Z", *box_surface((5, 40, 30), (-26, -2, 18), (4, 14, 10))),
        ("Rib -Z", *box_surface((5, 40, 30), (-26, -2, -18), (4, 14, 10))),
    ]
    for i, (x, z) in enumerate([(36, 24), (36, -24), (-6, 24), (-6, -24)]):
        parts.append((f"Bolt boss {i + 1}", *cylinder_surface(8, 10, (x, -15, z), "y", 18, 4)))
    nodes, tris, pids, names = merge(parts)
    x, y, z = nodes[:, 0], nodes[:, 1], nodes[:, 2]

    d_fillet = np.sqrt((x + 34) ** 2 + (y - 6) ** 2 + (z * 0.35) ** 2)
    base = 0.08 + 0.92 * gauss(d_fillet / 30, 0.62) + 0.14 * gauss(
        np.sqrt((x - 30) ** 2 + (y - 52) ** 2) / 40, 0.5)
    base = np.clip(base + noise(base.shape, 0.012), 0, None)
    scale = steps_scale()

    vm = np.clip(np.outer(scale, base) * 214.6 / base.max(), 0.4, None)
    s1 = vm * (0.86 + 0.05 * np.cos(z / 20))
    strain = vm / 68900.0
    defo = np.outer(scale, ((y + 26) / 100) ** 1.5 * 0.42 + 0.01)
    contact = np.outer(scale, gauss(np.abs(y + 15) / 12, 0.4) * gauss(np.abs(x - 18) / 40, 0.7) * 96.4)
    energy = 0.5 * vm * strain

    mesh = Mesh(nodes=nodes, triangles=tris, part_ids=pids, parts=names,
                metrics={"Nodes": len(nodes), "Elements": int(len(tris)),
                         "Element type": "SOLID187 / CONTA174 (surface skin exported)",
                         "Average quality": 0.842, "Max skewness": 0.61,
                         "Min orthogonality": 0.38})
    sim = Simulation(
        id="brk-114", name="EV Battery Mounting Bracket", domain=Domain.FEA,
        analysis_type="Linear static, bolt pretension, frictional contact",
        solver="Sample generator (stands in for a structural solver)",
        units=UnitSystem(), mesh=mesh,
        load_cases=["LC1 3g vertical", "LC2 1.5g longitudinal", "LC3 combined"],
        materials=[
            Material("AA6061-T6 bracket", {"E": 68900.0, "nu": 0.33, "density": 2700.0,
                                           "yield_strength": 276.0, "ultimate_strength": 310.0,
                                           "unit_stress": "MPa"}),
            Material("Steel 10.9 fasteners", {"E": 210000.0, "nu": 0.30, "density": 7850.0,
                                              "yield_strength": 940.0, "unit_stress": "MPa"}),
        ],
        boundary_conditions=[
            BoundaryCondition("Fixed support", "displacement", "4 bolt seat faces, all DOF"),
            BoundaryCondition("Frictional contact", "contact", "mu = 0.15, bracket to chassis rail"),
            BoundaryCondition("Bolt pretension", "preload", "M10 x 4, 21 kN each"),
        ],
        loads=[Load("Battery pack inertia", "92 kg x 3 g vertical (-Y)"),
               Load("Longitudinal shock", "1.5 g (-X), 18 ms half sine"),
               Load("Gravity", "9806.6 mm/s^2, -Y")],
        metadata={
            "owner": "sample data", "run": "2026-09-16 09:41", "wall_time": "00:11:24",
            "mesh_convergence": {"unit": "MPa", "target_percent": 2.0, "levels": [
                {"nodes": 112000, "value": 186.4}, {"nodes": 248000, "value": 201.9},
                {"nodes": 412000, "value": 209.8}, {"nodes": 612000, "value": 214.6},
                {"nodes": 864000, "value": 216.1}]},
            "analytical_reference": {
                "description": "Cantilever idealisation of the vertical flange",
                "value": 198.5, "unit": "MPa", "field": "von_mises",
                "acceptance_percent": 15.0,
                "source": "hand calculation sigma = M*c/I"},
        },
    )
    f = lambda **kw: sim.add_field(ResultField(**kw))  # noqa: E731
    f(name="von_mises", label="Equivalent (von Mises) stress", unit="MPa", values=vm,
      category="Stress", limits={"yield": 276.0, "max_allowed": 276.0},
      provenance="sample dataset")
    f(name="max_principal", label="Maximum principal stress", unit="MPa", values=s1, category="Stress")
    f(name="equivalent_strain", label="Equivalent elastic strain", unit="mm/mm", values=strain,
      category="Strain")
    f(name="displacement", label="Total deformation", unit="mm", values=defo, category="Displacement")
    f(name="contact_pressure", label="Contact pressure", unit="MPa", values=contact, category="Contact")
    f(name="strain_energy", label="Strain energy density", unit="mJ/mm^3", values=energy,
      category="Energy")
    sim.metadata["reaction_force_N"] = 4812.0
    return sim


# --------------------------------------------------------------------- CFD
def aero_body() -> Simulation:
    body_n, body_t = ellipsoid_surface((2.15, 0.52, 0.86), (0, 0.58, 0), 46, 26)
    cab_n, cab_t = ellipsoid_surface((1.05, 0.42, 0.72), (-0.1, 0.92, 0), 34, 18)
    parts = [("Body shell", body_n, body_t), ("Cabin", cab_n, cab_t)]
    for i, (px, pz) in enumerate([(1.35, 0.62), (1.35, -0.62), (-1.35, 0.62), (-1.35, -0.62)]):
        parts.append((f"Wheel {i + 1}", *cylinder_surface(0.35, 0.22, (px, 0.35, pz), "z", 18, 4)))
    nodes, tris, pids, names = merge(parts)
    x, y, z = nodes[:, 0], nodes[:, 1], nodes[:, 2]

    v_inf, rho = 27.78, 1.225
    q = 0.5 * rho * v_inf ** 2
    cp = np.tanh((x - 0.35) * 2.2) * 0.9 - 1.1 * gauss(np.hypot(x - 0.15, y - 1.0) / 1.1, 0.42)
    cp = np.clip(cp, -3.18, 1.0)
    pressure = cp * q
    velocity = np.clip(v_inf * np.sqrt(np.clip(1 - cp, 0, None)), 0, 41.3)
    wall_shear = np.clip(0.0045 * rho * velocity ** 2 * (0.6 + 0.4 * np.abs(z)), 0, 18.4)
    yplus = np.clip(14 + 6.5 * velocity * (0.7 + 0.5 * gauss(np.abs(x - 0.2) / 2.4, 0.9)), 0.9, 118)
    temperature = 20.0 + 0.5 * (v_inf ** 2 - velocity ** 2) / 1005.0 * 1000 * 0.02
    vorticity = np.clip(240 + 2600 * gauss(np.abs(x - 1.5) / 1.6, 0.55) * (0.5 + 0.5 * np.abs(z)), 0, 2840)

    it = list(range(0, 1300, 20))
    def decay(a0, a1, k):
        return [float(a1 + (a0 - a1) * np.exp(-k * i / 1240)) for i in it]
    conv = ConvergenceHistory(
        iterations=[float(i) for i in it],
        monitors={
            "continuity": [10 ** v for v in decay(-0.3, -4.06, 4.2)],
            "x_velocity": [10 ** v for v in decay(-0.6, -5.4, 4.6)],
            "k": [10 ** v for v in decay(-0.4, -5.0, 4.4)],
            "cd": decay(0.62, 0.284, 5.0),
        },
        converged=False, criterion=1e-5)

    mesh = Mesh(nodes=nodes, triangles=tris, part_ids=pids, parts=names,
                metrics={"Nodes": len(nodes), "Elements": int(len(tris)),
                         "Element type": "Poly-hexcore (surface skin exported)",
                         "Prism layers": 12, "Max skewness": 0.84,
                         "Min orthogonal quality": 0.11})
    sim = Simulation(
        id="aer-207", name="EV Aerodynamic Body", domain=Domain.CFD,
        analysis_type="External flow, steady RANS, k-omega SST",
        solver="Sample generator (stands in for a finite-volume solver)",
        units=UnitSystem(length="m", stress="Pa", force="N"), mesh=mesh,
        load_cases=["Baseline body", "Rear spoiler +15 mm", "Underbody tray"],
        materials=[Material("Air", {"density": 1.225, "viscosity": 1.7894e-5, "temperature_C": 20})],
        boundary_conditions=[
            BoundaryCondition("Velocity inlet", "inlet", "27.78 m/s (100 km/h), I = 1 %"),
            BoundaryCondition("Pressure outlet", "outlet", "0 Pa gauge"),
            BoundaryCondition("Moving ground", "wall", "27.78 m/s, no slip"),
            BoundaryCondition("Rotating wheels", "wall", "omega = 84.2 rad/s, MRF"),
        ],
        loads=[Load("Turbulence model", "k-omega SST with curvature correction"),
               Load("Discretisation", "Second-order upwind")],
        convergence=conv,
        metadata={
            "owner": "sample data", "run": "2026-09-17 22:08", "wall_time": "04:37:11",
            "operating_point": {"density": rho, "velocity": v_inf, "viscosity": 1.7894e-5,
                                "reference_length": 4.2, "frontal_area": 2.18, "cd": 0.284,
                                "cl": -0.061, "probe_pressure": float(pressure.max())},
            "experimental_reference": {"value": 0.291, "simulation_value": 0.284, "unit": "-",
                                       "acceptance_percent": 5.0,
                                       "source": "sample wind-tunnel value"},
        },
    )
    add = lambda **kw: sim.add_field(ResultField(**kw))  # noqa: E731
    add(name="pressure", label="Static pressure", unit="Pa", values=pressure, category="Pressure")
    add(name="cp", label="Pressure coefficient", unit="-", values=cp, category="Pressure")
    add(name="velocity", label="Velocity magnitude", unit="m/s", values=velocity, category="Velocity")
    add(name="wall_shear", label="Wall shear stress", unit="Pa", values=wall_shear, category="Wall")
    add(name="y_plus", label="Wall y+", unit="-", values=yplus, category="Wall",
        limits={"max_allowed": 300.0})
    add(name="temperature", label="Static temperature", unit="C", values=temperature, category="Thermal")
    add(name="vorticity", label="Vorticity magnitude", unit="1/s", values=vorticity, category="Turbulence")
    return sim


# ----------------------------------------------------------------- thermal
def cold_plate() -> Simulation:
    parts = [("Plate", *box_surface((120, 6, 80), (0, 0, 0), (46, 4, 32)))]
    for i, zc in enumerate([-28, -9, 9, 28]):
        parts.append((f"Channel pass {i + 1}", *cylinder_surface(4, 104, (0, 0, zc), "x", 16, 6)))
    for i in range(8):
        parts.append((f"Cell {i + 1} footprint", *box_surface((12, 3, 32), (-52 + i * 15, 4.4, 0), (5, 2, 8))))
    nodes, tris, pids, names = merge(parts)
    x, z = nodes[:, 0], nodes[:, 2]

    scale = steps_scale()
    path = (x + 60) / 120.0
    channel = gauss(np.abs(np.sin(z / 14.0)), 0.45)
    base_t = 24.8 + 22.0 * path + 9.5 * (1 - channel) + noise(x.shape, 0.25)
    temp = 24.8 + np.outer(scale, base_t - 24.8) * (33.5 / (base_t.max() - 24.8))
    flux = np.outer(scale, 0.4 + 42.2 * channel)
    grad = np.outer(scale, 0.1 + 6.7 * gauss(np.abs(np.cos(z / 14.0)), 0.3))
    htc = np.tile(180 + 4080 * gauss(np.abs(np.sin(z / 14.0 + 0.5)), 0.4), (len(scale), 1))

    mesh = Mesh(nodes=nodes, triangles=tris, part_ids=pids, parts=names,
                metrics={"Nodes": len(nodes), "Elements": int(len(tris)),
                         "Element type": "Poly + hex channel (surface skin exported)",
                         "Solid/fluid interfaces": 2, "Average quality": 0.79})
    sim = Simulation(
        id="thm-088", name="Battery Cooling Plate", domain=Domain.THERMAL,
        analysis_type="Conjugate heat transfer, steady",
        solver="Sample generator (stands in for a CHT solver)",
        units=UnitSystem(temperature="C"), mesh=mesh,
        load_cases=["6 L/min baseline", "9 L/min", "Reversed flow"],
        materials=[
            Material("AA3003 plate", {"conductivity": 155.0, "density": 2730.0, "cp": 893.0}),
            Material("50/50 water-glycol", {"density": 1050.0, "cp": 3300.0,
                                            "conductivity": 0.39, "viscosity": 0.0032}),
        ],
        boundary_conditions=[
            BoundaryCondition("Inlet", "inlet", "6 L/min, 25 C"),
            BoundaryCondition("Outlet", "outlet", "0 Pa gauge"),
            BoundaryCondition("Cell heat load", "source", "8 x 230 W footprint sources"),
            BoundaryCondition("External walls", "convection", "h = 8 W/m^2.K, 25 C ambient"),
        ],
        loads=[Load("Total heat load", "1840 W"), Load("Flow regime", "channel Re = 1957")],
        metadata={
            "owner": "sample data", "run": "2026-09-18 14:02", "wall_time": "01:52:40",
            "operating_point": {"heat_load": 1840.0, "mass_flow": 0.105, "cp": 3300.0,
                                "density": 1050.0, "channel_velocity": 0.42,
                                "hydraulic_diameter": 0.0142, "viscosity": 0.0032,
                                "conductivity": 0.39, "nusselt": 4.36,
                                "inlet_temperature": 25.0, "cell_power": 230.0},
            "mesh_convergence": {"unit": "C", "target_percent": 2.0, "levels": [
                {"nodes": 3100000, "value": 56.9}, {"nodes": 6200000, "value": 58.3}]},
            "analytical_reference": {"description": "Coolant temperature rise from Q = m_dot cp dT",
                                     "value": 5.40, "unit": "K", "simulation_value": 5.30,
                                     "acceptance_percent": 10.0, "source": "hand calculation"},
        },
    )
    add = lambda **kw: sim.add_field(ResultField(**kw))  # noqa: E731
    add(name="temperature", label="Temperature", unit="C", values=temp, category="Temperature",
        limits={"max_allowed": 55.0})
    add(name="heat_flux", label="Total heat flux", unit="kW/m^2", values=flux, category="Heat flux")
    add(name="thermal_gradient", label="Thermal gradient", unit="K/mm", values=grad, category="Gradient")
    add(name="htc", label="Heat transfer coefficient", unit="W/m^2.K", values=htc, category="Convection")
    return sim


# --------------------------------------------------------------------- MBD
def suspension() -> Simulation:
    parts = [
        ("Chassis mount", *box_surface((16, 48, 14), (-52, 4, 0), (4, 10, 4))),
        ("Lower control arm", *box_surface((62, 7, 9), (-14, -24, 0), (16, 3, 3))),
        ("Upper control arm", *box_surface((46, 6, 8), (-20, 16, 0), (14, 3, 3))),
        ("Upright", *box_surface((11, 50, 12), (16, -4, 0), (4, 12, 4))),
        ("Wheel", *cylinder_surface(30, 16, (34, -4, 0), "x", 26, 5)),
        ("Damper", *cylinder_surface(5, 54, (-6, 6, 0), "y", 14, 6)),
        ("Tie rod", *box_surface((38, 5, 5), (-2, -12, 10), (10, 2, 2))),
    ]
    nodes, tris, pids, names = merge(parts)
    y = nodes[:, 1]
    x = nodes[:, 0]

    t = np.linspace(0, 2.0, 21)
    phase = np.sin(2 * np.pi * 0.7 * t) * np.linspace(0.45, 1.0, len(t))
    arm = (y + 40) / 80.0
    disp = np.outer(np.abs(phase) * 78.2, arm)
    vel = np.outer(np.abs(np.cos(2 * np.pi * 0.7 * t)) * 612, arm)
    acc = np.outer(np.abs(phase) * 12.4, 0.4 + 0.6 * arm)
    force_shape = 0.25 + 0.75 * gauss(np.hypot(x - 18, y + 22) / 55, 0.6)
    force = np.outer(2000 + 4842 * np.abs(phase), force_shape / force_shape.max())
    torque = force * 0.045

    mesh = Mesh(nodes=nodes, triangles=tris, part_ids=pids, parts=names,
                metrics={"Nodes": len(nodes), "Elements": int(len(tris)), "Bodies": 9,
                         "Joints": 11, "Degrees of freedom": 2, "Integrator": "GSTIFF I3"})
    sim = Simulation(
        id="mbd-052", name="Vehicle Suspension - Double Wishbone", domain=Domain.MBD,
        analysis_type="Rigid multibody dynamics, transient",
        solver="Sample generator (stands in for an MBD solver)",
        units=UnitSystem(), mesh=mesh,
        load_cases=["Swept sine ride", "Single 60 mm bump", "Cornering 0.6 g"],
        materials=[Material("Rigid bodies", {"note": "mass and inertia per body, no flexibility"}),
                   Material("Spring", {"rate_N_per_mm": 32.0, "free_length_mm": 260.0}),
                   Material("Damper", {"bump_Ns_per_m": 2400.0, "rebound_Ns_per_m": 3600.0})],
        boundary_conditions=[
            BoundaryCondition("Ground constraints", "joint", "chassis pick-up points fixed"),
            BoundaryCondition("Revolute joints", "joint", "upper and lower arm inboard, 4 total"),
            BoundaryCondition("Spherical joints", "joint", "ball joints, 2 total"),
        ],
        loads=[Load("Road input", "swept sine 0.5 to 12 Hz, 25 mm amplitude"),
               Load("Corner mass", "412 kg sprung, 48 kg unsprung")],
        metadata={
            "owner": "sample data", "run": "2026-09-15 17:20", "wall_time": "00:04:12",
            "operating_point": {"spring_travel": 46.9, "wheel_travel": 78.2,
                                "spring_rate": 32.0, "sprung_mass": 412.0,
                                "joint_rating": 7400.0},
        },
    )
    add = lambda **kw: sim.add_field(ResultField(**kw))  # noqa: E731
    add(name="displacement", label="Displacement magnitude", unit="mm", values=disp,
        category="Kinematics", steps=[float(v) for v in t])
    add(name="velocity", label="Velocity magnitude", unit="mm/s", values=vel,
        category="Kinematics", steps=[float(v) for v in t])
    add(name="acceleration", label="Acceleration magnitude", unit="m/s^2", values=acc,
        category="Kinematics", steps=[float(v) for v in t])
    add(name="joint_force", label="Joint reaction force", unit="N", values=force,
        category="Forces", steps=[float(v) for v in t], limits={"max_allowed": 7400.0})
    add(name="joint_torque", label="Joint reaction torque", unit="N.m", values=torque,
        category="Forces", steps=[float(v) for v in t])
    return sim


BUILDERS = {"brk-114": bracket, "aer-207": aero_body, "thm-088": cold_plate, "mbd-052": suspension}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(ROOT / "samples"))
    ap.add_argument("--only", nargs="*", choices=sorted(BUILDERS))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for key in args.only or sorted(BUILDERS):
        sim = BUILDERS[key]()
        path = NativeJSONAdapter.write(sim, out / f"{sim.id}.json", decimals=4)
        size = path.stat().st_size / 1e6
        print(f"{sim.id:10s} {sim.domain.value:9s} {sim.mesh.n_nodes:6d} nodes  "
              f"{len(sim.fields)} fields  {size:.2f} MB  -> {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
