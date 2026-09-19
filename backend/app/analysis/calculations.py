"""Derived engineering calculations.

Every calculation reports formula, inputs with units, assumptions and result, so
a number can always be traced back to what produced it.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field as dc_field
from typing import Any, Callable, Dict, List, Optional

import numpy as np

from app.analysis.statistics import field_statistics
from app.core.model import ResultField, Simulation


@dataclass
class Calculation:
    name: str
    formula: str
    inputs: List[Dict[str, Any]]
    result: float
    unit: str
    assumptions: str
    category: str = "General"
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name, "formula": self.formula, "inputs": self.inputs,
            "result": round(float(self.result), 6), "unit": self.unit,
            "assumptions": self.assumptions, "category": self.category, "note": self.note,
        }


def _inp(name: str, value: Any, unit: str = "") -> Dict[str, Any]:
    return {"name": name, "value": value, "unit": unit}


# --------------------------------------------------------------- structural
def factor_of_safety(sim: Simulation, stress_field: str = "von_mises",
                     yield_strength: Optional[float] = None) -> Calculation:
    stats = field_statistics(sim, stress_field)
    sy = yield_strength or sim.field(stress_field).limits.get("yield")
    if sy is None:
        for m in sim.materials:
            if "yield_strength" in m.properties:
                sy = float(m.properties["yield_strength"])
                break
    if sy is None:
        raise ValueError("no yield strength available for a factor-of-safety calculation")
    return Calculation(
        name="Factor of safety against yield",
        formula="FoS = S_y / sigma_max",
        inputs=[_inp("S_y", sy, sim.units.stress),
                _inp("sigma_max", round(stats.maximum.value, 4), stats.unit),
                _inp("location", f"node {stats.maximum.node_id}", "")],
        result=sy / stats.maximum.value,
        unit="-",
        assumptions=("Yield-based static check at the peak value. No knock-down for surface "
                     "finish, weld or temperature. Not valid where the peak is a mesh singularity."),
        category="Structural",
    )


def stress_ratio(sim: Simulation, stress_field: str = "von_mises",
                 yield_strength: Optional[float] = None) -> Calculation:
    fos = factor_of_safety(sim, stress_field, yield_strength)
    return Calculation(
        name="Stress ratio at the critical entity",
        formula="R = sigma_max / S_y * 100",
        inputs=fos.inputs,
        result=100.0 / fos.result,
        unit="% of yield",
        assumptions="Reported at the peak location; compare against the programme screening limit.",
        category="Structural",
    )


def safety_factor_field(sim: Simulation, stress_field: str = "von_mises",
                        yield_strength: Optional[float] = None, cap: float = 15.0) -> ResultField:
    """Pointwise FoS as a new derived field."""
    f = sim.field(stress_field)
    sy = yield_strength or f.limits.get("yield")
    if sy is None:
        for m in sim.materials:
            if "yield_strength" in m.properties:
                sy = float(m.properties["yield_strength"])
                break
    if sy is None:
        raise ValueError("no yield strength available")
    with np.errstate(divide="ignore", invalid="ignore"):
        vals = np.where(f.values > 1e-9, sy / np.maximum(f.values, 1e-9), cap)
    return ResultField(
        name="safety_factor", label="Safety factor (yield)", unit="-",
        values=np.clip(vals, 0, cap), category="Derived", derived=True,
        steps=list(f.steps),
        provenance=f"computed as S_y / {stress_field} with S_y = {sy} {sim.units.stress}",
    )


# -------------------------------------------------------------------- fluid
def reynolds_number(density: float, velocity: float, length: float, viscosity: float) -> Calculation:
    return Calculation(
        name="Reynolds number", formula="Re = rho * V * L / mu",
        inputs=[_inp("rho", density, "kg/m^3"), _inp("V", velocity, "m/s"),
                _inp("L", length, "m"), _inp("mu", viscosity, "Pa.s")],
        result=density * velocity * length / viscosity, unit="-",
        assumptions="Reference length as stated; fully developed or fully turbulent assumption depends on the case.",
        category="Fluid",
    )


def drag_force(density: float, velocity: float, area: float, cd: float) -> Calculation:
    return Calculation(
        name="Drag force", formula="F_d = 0.5 * rho * V^2 * A * C_d",
        inputs=[_inp("rho", density, "kg/m^3"), _inp("V", velocity, "m/s"),
                _inp("A", area, "m^2"), _inp("C_d", cd, "-")],
        result=0.5 * density * velocity ** 2 * area * cd, unit="N",
        assumptions="Excludes cooling-flow drag and any component outside the simulated domain.",
        category="Fluid",
    )


def pressure_coefficient(pressure: float, reference_pressure: float,
                         density: float, velocity: float) -> Calculation:
    q = 0.5 * density * velocity ** 2
    return Calculation(
        name="Pressure coefficient", formula="C_p = (p - p_inf) / (0.5 * rho * V^2)",
        inputs=[_inp("p", pressure, "Pa"), _inp("p_inf", reference_pressure, "Pa"),
                _inp("0.5*rho*V^2", round(q, 3), "Pa")],
        result=(pressure - reference_pressure) / q, unit="-",
        assumptions="Freestream reference conditions taken from the boundary definition.",
        category="Fluid",
    )


def mass_flow(density: float, velocity: float, area: float) -> Calculation:
    return Calculation(
        name="Mass flow rate", formula="m_dot = rho * V * A",
        inputs=[_inp("rho", density, "kg/m^3"), _inp("V", velocity, "m/s"), _inp("A", area, "m^2")],
        result=density * velocity * area, unit="kg/s",
        assumptions="Uniform velocity over the reference area.", category="Fluid",
    )


def aerodynamic_power(drag: float, velocity: float) -> Calculation:
    return Calculation(
        name="Aerodynamic power", formula="P = F_d * V",
        inputs=[_inp("F_d", drag, "N"), _inp("V", velocity, "m/s")],
        result=drag * velocity / 1000.0, unit="kW",
        assumptions="Aerodynamic component only; rolling and driveline losses excluded.",
        category="Fluid",
    )


# ------------------------------------------------------------------ thermal
def coolant_temperature_rise(heat: float, mass_flow_rate: float, cp: float) -> Calculation:
    return Calculation(
        name="Coolant temperature rise", formula="dT = Q / (m_dot * c_p)",
        inputs=[_inp("Q", heat, "W"), _inp("m_dot", mass_flow_rate, "kg/s"), _inp("c_p", cp, "J/kg.K")],
        result=heat / (mass_flow_rate * cp), unit="K",
        assumptions="All heat enters the coolant; constant properties over the temperature range.",
        category="Thermal",
    )


def channel_reynolds(density: float, velocity: float, d_h: float, viscosity: float) -> Calculation:
    c = reynolds_number(density, velocity, d_h, viscosity)
    c.name = "Channel Reynolds number"
    c.formula = "Re = rho * v * D_h / mu"
    c.assumptions = "Hydraulic diameter as the reference length; transition taken at Re = 2300."
    c.note = "laminar" if c.result < 2300 else "turbulent"
    c.category = "Thermal"
    return c


def convection_coefficient(nusselt: float, conductivity: float, d_h: float) -> Calculation:
    return Calculation(
        name="Convective heat transfer coefficient", formula="h = Nu * k / D_h",
        inputs=[_inp("Nu", nusselt, "-"), _inp("k", conductivity, "W/m.K"), _inp("D_h", d_h, "m")],
        result=nusselt * conductivity / d_h, unit="W/m^2.K",
        assumptions="Correlation value for the stated flow regime; not valid at bends or entrances.",
        category="Thermal",
    )


def thermal_resistance(t_hot: float, t_cold: float, power: float) -> Calculation:
    return Calculation(
        name="Thermal resistance", formula="R_th = (T_hot - T_cold) / Q",
        inputs=[_inp("T_hot", t_hot, "C"), _inp("T_cold", t_cold, "C"), _inp("Q", power, "W")],
        result=(t_hot - t_cold) / power, unit="K/W",
        assumptions="Lumped path resistance; interface contact resistance assumed ideal.",
        category="Thermal",
    )


# ---------------------------------------------------------------------- MBD
def motion_ratio(spring_travel: float, wheel_travel: float) -> Calculation:
    return Calculation(
        name="Motion ratio", formula="MR = dx_spring / dx_wheel",
        inputs=[_inp("dx_spring", spring_travel, "mm"), _inp("dx_wheel", wheel_travel, "mm")],
        result=spring_travel / wheel_travel, unit="-",
        assumptions="Evaluated at peak travel and treated as constant through the stroke.",
        category="MBD",
    )


def wheel_rate(spring_rate: float, ratio: float) -> Calculation:
    return Calculation(
        name="Wheel rate", formula="k_w = k_s * MR^2",
        inputs=[_inp("k_s", spring_rate, "N/mm"), _inp("MR", ratio, "-")],
        result=spring_rate * ratio ** 2, unit="N/mm",
        assumptions="Rigid links and frictionless joints; tyre stiffness excluded.",
        category="MBD",
    )


def ride_frequency(wheel_rate_n_per_m: float, sprung_mass: float) -> Calculation:
    return Calculation(
        name="Ride frequency", formula="f = (1 / 2*pi) * sqrt(k_w / m_s)",
        inputs=[_inp("k_w", wheel_rate_n_per_m, "N/m"), _inp("m_s", sprung_mass, "kg")],
        result=math.sqrt(wheel_rate_n_per_m / sprung_mass) / (2 * math.pi), unit="Hz",
        assumptions="Undamped quarter-car idealisation at one corner.", category="MBD",
    )


def utilisation(peak: float, rating: float, label: str = "Component utilisation") -> Calculation:
    return Calculation(
        name=label, formula="U = F_max / F_rated * 100",
        inputs=[_inp("F_max", peak, "N"), _inp("F_rated", rating, "N")],
        result=peak / rating * 100.0, unit="%",
        assumptions="Static rating comparison; fatigue duty assessed separately.",
        category="MBD",
    )


CALCULATORS: Dict[str, Callable[..., Calculation]] = {
    "factor_of_safety": factor_of_safety,
    "stress_ratio": stress_ratio,
    "reynolds_number": reynolds_number,
    "drag_force": drag_force,
    "pressure_coefficient": pressure_coefficient,
    "mass_flow": mass_flow,
    "aerodynamic_power": aerodynamic_power,
    "coolant_temperature_rise": coolant_temperature_rise,
    "channel_reynolds": channel_reynolds,
    "convection_coefficient": convection_coefficient,
    "thermal_resistance": thermal_resistance,
    "motion_ratio": motion_ratio,
    "wheel_rate": wheel_rate,
    "ride_frequency": ride_frequency,
    "utilisation": utilisation,
}


def standard_calculations(sim: Simulation) -> List[Calculation]:
    """Calculations that can be evaluated from what the simulation actually holds."""
    out: List[Calculation] = []
    p = sim.metadata.get("operating_point", {})
    d = sim.domain.value
    try:
        if d == "FEA" and "von_mises" in sim.fields:
            out.append(factor_of_safety(sim))
            out.append(stress_ratio(sim))
        if d == "CFD" and p:
            out.append(reynolds_number(p["density"], p["velocity"], p["reference_length"], p["viscosity"]))
            fd = drag_force(p["density"], p["velocity"], p["frontal_area"], p["cd"])
            out.append(fd)
            out.append(aerodynamic_power(fd.result, p["velocity"]))
            if "probe_pressure" in p:
                out.append(pressure_coefficient(p["probe_pressure"], 0.0, p["density"], p["velocity"]))
        if d == "Thermal" and p:
            out.append(coolant_temperature_rise(p["heat_load"], p["mass_flow"], p["cp"]))
            out.append(channel_reynolds(p["density"], p["channel_velocity"], p["hydraulic_diameter"], p["viscosity"]))
            out.append(convection_coefficient(p.get("nusselt", 4.36), p["conductivity"], p["hydraulic_diameter"]))
            if "temperature" in sim.fields:
                t_max = field_statistics(sim, "temperature").maximum.value
                out.append(thermal_resistance(t_max, p["inlet_temperature"], p["cell_power"]))
        if d == "MBD" and p:
            mr = motion_ratio(p["spring_travel"], p["wheel_travel"])
            wr = wheel_rate(p["spring_rate"], mr.result)
            out.extend([mr, wr, ride_frequency(wr.result * 1000.0, p["sprung_mass"])])
            if "joint_force" in sim.fields and "joint_rating" in p:
                peak = field_statistics(sim, "joint_force").maximum.value
                out.append(utilisation(peak, p["joint_rating"], "Ball joint utilisation"))
    except (KeyError, ValueError) as exc:  # a missing input is reported, not guessed
        out.append(Calculation(
            name="Incomplete input", formula="-", inputs=[_inp("missing", str(exc))],
            result=float("nan"), unit="-",
            assumptions="A calculation was skipped because the simulation does not carry the required input.",
        ))
    return out
