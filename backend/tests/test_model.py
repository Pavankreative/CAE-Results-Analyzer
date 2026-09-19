import numpy as np
import pytest

from app.core.model import (
    FieldType, Mesh, ResultField, Simulation, UnitSystem, Domain,
)


def _mesh(n=4):
    nodes = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]], dtype=float)[:n]
    tris = np.array([[0, 1, 2]], dtype=np.int32) if n >= 3 else np.zeros((0, 3), np.int32)
    return Mesh(nodes=nodes, triangles=tris)


def test_mesh_rejects_bad_triangle_index():
    with pytest.raises(ValueError):
        Mesh(nodes=np.zeros((3, 3)), triangles=np.array([[0, 1, 9]]))


def test_mesh_defaults_node_ids_and_bounds():
    m = _mesh()
    assert m.node_ids.tolist() == [1, 2, 3, 4]
    assert m.bounds()["max"] == [1.0, 1.0, 0.0]


def test_single_step_field_is_promoted_to_two_dimensions():
    f = ResultField(name="t", label="T", unit="C", values=np.array([1.0, 2.0, 3.0, 4.0]))
    assert f.values.shape == (1, 4)
    assert f.n_steps == 1


def test_vector_field_step_returns_magnitude():
    v = np.zeros((1, 4, 3))
    v[0, 0] = [3.0, 4.0, 0.0]
    f = ResultField(name="u", label="U", unit="mm", values=v, field_type=FieldType.VECTOR)
    assert f.step(0)[0] == pytest.approx(5.0)


def test_field_step_count_must_match_steps():
    with pytest.raises(ValueError):
        ResultField(name="t", label="T", unit="C", values=np.zeros((2, 4)), steps=[0.0])


def test_add_field_rejects_wrong_length():
    sim = Simulation(id="s", name="s", domain=Domain.FEA, analysis_type="", solver="",
                     units=UnitSystem(), mesh=_mesh())
    with pytest.raises(ValueError):
        sim.add_field(ResultField(name="t", label="T", unit="C", values=np.zeros((1, 7))))


def test_unit_system_consistency():
    assert UnitSystem().consistent
    assert UnitSystem(length="m", stress="Pa").consistent
    assert not UnitSystem(length="m", stress="MPa").consistent


def test_summary_lists_fields(bracket):
    s = bracket.summary()
    assert s["domain"] == "FEA"
    assert s["is_sample_data"] is True
    assert {f["name"] for f in s["fields"]} >= {"von_mises", "displacement"}
