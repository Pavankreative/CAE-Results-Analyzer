import math

import pytest

from app.analysis import calculations as c
from app.analysis.statistics import field_statistics


def test_factor_of_safety_uses_material_yield(bracket):
    calc = c.factor_of_safety(bracket)
    peak = field_statistics(bracket, "von_mises").maximum.value
    assert calc.result == pytest.approx(276.0 / peak)
    assert calc.formula.startswith("FoS =")
    assert calc.assumptions


def test_stress_ratio_is_the_inverse_percentage(bracket):
    fos = c.factor_of_safety(bracket)
    ratio = c.stress_ratio(bracket)
    assert ratio.result == pytest.approx(100.0 / fos.result)


def test_safety_factor_field_is_derived_and_capped(bracket):
    f = c.safety_factor_field(bracket, cap=15.0)
    assert f.derived is True
    assert f.values.max() <= 15.0
    assert f.values.shape == bracket.field("von_mises").values.shape
    assert "S_y" in f.provenance or "276" in f.provenance


def test_missing_yield_strength_is_an_error():
    from app.core.model import Domain, Mesh, ResultField, Simulation, UnitSystem
    import numpy as np
    sim = Simulation(id="x", name="x", domain=Domain.FEA, analysis_type="", solver="",
                     units=UnitSystem(),
                     mesh=Mesh(nodes=np.zeros((2, 3)), triangles=np.zeros((0, 3), np.int32)))
    sim.add_field(ResultField(name="von_mises", label="s", unit="MPa", values=np.ones((1, 2))))
    with pytest.raises(ValueError):
        c.factor_of_safety(sim)


def test_reynolds_number_known_value():
    calc = c.reynolds_number(1.225, 27.78, 4.2, 1.7894e-5)
    assert calc.result == pytest.approx(1.225 * 27.78 * 4.2 / 1.7894e-5, rel=1e-9)
    assert calc.result == pytest.approx(7.99e6, rel=0.01)


def test_drag_force_and_power_are_consistent():
    d = c.drag_force(1.225, 27.78, 2.18, 0.284)
    assert d.result == pytest.approx(0.5 * 1.225 * 27.78 ** 2 * 2.18 * 0.284)
    p = c.aerodynamic_power(d.result, 27.78)
    assert p.result == pytest.approx(d.result * 27.78 / 1000.0)


def test_pressure_coefficient_at_stagnation_is_one():
    q = 0.5 * 1.225 * 27.78 ** 2
    assert c.pressure_coefficient(q, 0.0, 1.225, 27.78).result == pytest.approx(1.0)


def test_coolant_temperature_rise():
    calc = c.coolant_temperature_rise(1840.0, 0.105, 3300.0)
    assert calc.result == pytest.approx(1840.0 / (0.105 * 3300.0))
    assert calc.result == pytest.approx(5.31, abs=0.02)


def test_channel_reynolds_flags_laminar():
    calc = c.channel_reynolds(1050.0, 0.42, 0.0142, 0.0032)
    assert calc.note == "laminar"
    assert calc.result < 2300


def test_ride_frequency_quarter_car():
    mr = c.motion_ratio(46.9, 78.2)
    wr = c.wheel_rate(32.0, mr.result)
    f = c.ride_frequency(wr.result * 1000.0, 412.0)
    assert mr.result == pytest.approx(0.5997, abs=1e-3)
    assert wr.result == pytest.approx(32.0 * mr.result ** 2)
    assert f.result == pytest.approx(math.sqrt(wr.result * 1000 / 412.0) / (2 * math.pi))


def test_standard_calculations_per_domain(bracket, aero, plate, suspension):
    assert any("Factor of safety" in x.name for x in c.standard_calculations(bracket))
    assert any("Reynolds" in x.name for x in c.standard_calculations(aero))
    assert any("temperature rise" in x.name for x in c.standard_calculations(plate))
    assert any("Wheel rate" in x.name for x in c.standard_calculations(suspension))


def test_every_calculation_reports_formula_inputs_and_assumptions(bracket):
    for calc in c.standard_calculations(bracket):
        d = calc.to_dict()
        assert d["formula"] and d["assumptions"]
        assert d["inputs"] and all("name" in i for i in d["inputs"])
