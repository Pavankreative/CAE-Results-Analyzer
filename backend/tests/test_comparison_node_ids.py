"""Regression checks for physical Node-ID correspondence, not array position."""
import copy
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from app.adapters.native import NativeJSONAdapter
from app.analysis.comparison import ComparisonValidationError, compare
from app.core.model import Domain, FieldLocation, Mesh, ResultField, Simulation, UnitSystem


@pytest.fixture
def nodal_case():
    sim = Simulation(
        id="reference", name="three-node benchmark", domain=Domain.FEA,
        analysis_type="static", solver="analytical fixture", units=UnitSystem(),
        mesh=Mesh(nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0]],
                  triangles=[[0, 1, 2]], node_ids=[90, 10, 30]),
    )
    sim.add_field(ResultField(name="von_mises", label="Equivalent stress", unit="MPa",
                              values=[10., 20., 30.], steps=[1.]))
    return sim


def _reorder(sim, order):
    result = copy.deepcopy(sim)
    order = np.asarray(order)
    inverse = np.argsort(order)
    result.mesh.nodes = result.mesh.nodes[order]
    result.mesh.node_ids = result.mesh.node_ids[order]
    result.mesh.triangles = inverse[result.mesh.triangles]
    for field in result.fields.values():
        field.values = field.values[:, order]
    return result


def test_reordered_identical_nodes_are_exactly_zero(nodal_case):
    other = _reorder(nodal_case, [2, 0, 1])
    result = compare(nodal_case, other)
    assert result["same_mesh"] is True
    assert result["field_differences"][0] == {
        "field": "von_mises", "unit": "MPa", "min": 0.0, "max": 0.0,
        "mean": 0.0, "abs_max": 0.0, "rms": 0.0,
    }


def test_real_deltas_follow_node_ids_and_b_minus_a(nodal_case):
    other = copy.deepcopy(nodal_case)
    other.field("von_mises").values += np.array([3., -4., 0.])
    other = _reorder(other, [1, 2, 0])
    delta = compare(nodal_case, other)["field_differences"][0]
    assert delta["min"] == -4.
    assert delta["max"] == 3.
    assert delta["abs_max"] == 4.
    assert delta["mean"] == pytest.approx(-1 / 3)
    assert delta["rms"] == pytest.approx(np.sqrt(25 / 3))


def test_original_bracket_false_196_mpa_difference_is_zero(bracket):
    order = np.random.default_rng(17).permutation(bracket.mesh.n_nodes)
    other = _reorder(bracket, order)
    result = compare(bracket, other, fields=["von_mises"])
    assert result["field_differences"][0]["abs_max"] == 0.0
    assert result["field_differences"][0]["rms"] == 0.0


@pytest.mark.parametrize("unit", ["Pa", "", "ksi"])
def test_field_units_rejected_before_subtraction(nodal_case, unit):
    other = copy.deepcopy(nodal_case)
    other.field("von_mises").unit = unit
    with pytest.raises(ComparisonValidationError, match="field units"):
        compare(nodal_case, other)


@pytest.mark.parametrize("attribute,value", [("length", "m"), ("stress", "Pa"),
                                           ("time", "ms"), ("temperature", "K")])
def test_unit_system_mismatch_is_rejected(nodal_case, attribute, value):
    other = copy.deepcopy(nodal_case)
    setattr(other.units, attribute, value)
    with pytest.raises(ComparisonValidationError, match="Unit systems"):
        compare(nodal_case, other)


@pytest.mark.parametrize("ids", [None, [90, 10], [90, 10, 10], [90., 10., 30.],
                                [[90, 10, 30]]])
def test_missing_malformed_or_duplicate_ids_raise(nodal_case, ids):
    other = copy.deepcopy(nodal_case)
    other.mesh.node_ids = None if ids is None else np.asarray(ids)
    with pytest.raises(ComparisonValidationError, match="Node ID"):
        compare(nodal_case, other)


def test_equal_node_counts_with_different_ids_raise(nodal_case):
    other = copy.deepcopy(nodal_case)
    other.mesh.node_ids[0] = 777
    with pytest.raises(ComparisonValidationError, match="Node ID sets differ"):
        compare(nodal_case, other)


def test_missing_node_from_other_result_raises(nodal_case):
    other = copy.deepcopy(nodal_case)
    other.mesh.nodes = other.mesh.nodes[:2]
    other.mesh.node_ids = other.mesh.node_ids[:2]
    other.field("von_mises").values = other.field("von_mises").values[:, :2]
    with pytest.raises(ComparisonValidationError, match="Node ID sets differ"):
        compare(nodal_case, other)


def test_generated_display_indices_are_not_solver_ids(nodal_case):
    other = copy.deepcopy(nodal_case)
    other.mesh = Mesh(nodes=other.mesh.nodes, triangles=other.mesh.triangles)
    with pytest.raises(ComparisonValidationError, match="explicit solver Node IDs"):
        compare(other, other)


def test_native_roundtrip_does_not_promote_missing_ids(nodal_case, tmp_path):
    nodal_case.mesh = Mesh(nodes=nodal_case.mesh.nodes, triangles=nodal_case.mesh.triangles)
    path = NativeJSONAdapter.write(nodal_case, tmp_path / "generated.json")
    restored = NativeJSONAdapter().read(path)
    assert restored.mesh.node_ids_explicit is False
    with pytest.raises(ComparisonValidationError, match="explicit solver Node IDs"):
        compare(restored, restored)


def test_native_roundtrip_preserves_explicit_ids(nodal_case, tmp_path):
    restored = NativeJSONAdapter().read(NativeJSONAdapter.write(nodal_case, tmp_path / "explicit.json"))
    assert restored.mesh.node_ids_explicit is True
    assert compare(nodal_case, restored)["field_differences"][0]["abs_max"] == 0.0


@pytest.mark.parametrize("ids", [[1, 1, 2], [1.5, 2, 3], [True, False, True], [1, 2]])
def test_mesh_constructor_rejects_lossy_or_invalid_ids(nodal_case, ids):
    with pytest.raises(ValueError, match="unique integer Node ID"):
        Mesh(nodes=nodal_case.mesh.nodes, triangles=nodal_case.mesh.triangles, node_ids=ids)


def test_same_ids_on_different_geometry_are_rejected(nodal_case):
    other = copy.deepcopy(nodal_case)
    other.mesh.nodes[0, 0] += 1
    with pytest.raises(ComparisonValidationError, match="Reference coordinates"):
        compare(nodal_case, other)


@pytest.mark.parametrize("bad", [float("nan"), float("inf")])
def test_nonfinite_data_is_rejected(nodal_case, bad):
    other = copy.deepcopy(nodal_case)
    other.field("von_mises").values[0, 0] = bad
    with pytest.raises(ComparisonValidationError, match="finite"):
        compare(nodal_case, other)


def test_load_step_mismatch_is_rejected(nodal_case):
    other = copy.deepcopy(nodal_case)
    other.field("von_mises").steps = [2.]
    with pytest.raises(ComparisonValidationError, match="load-step/time"):
        compare(nodal_case, other)


@pytest.mark.parametrize("step", [1, -2])
def test_out_of_range_steps_raise_validation_exception(nodal_case, step):
    with pytest.raises(ComparisonValidationError, match="out of range"):
        compare(nodal_case, nodal_case, step=step)


def test_elemental_data_cannot_be_aligned_by_node_id(nodal_case):
    other = copy.deepcopy(nodal_case)
    other.field("von_mises").location = FieldLocation.ELEMENTAL
    with pytest.raises(ComparisonValidationError, match="only nodal"):
        compare(nodal_case, other)


@pytest.mark.parametrize("fields", [[], ["not_present"]])
def test_empty_or_missing_field_selection_is_rejected(nodal_case, fields):
    with pytest.raises(ComparisonValidationError):
        compare(nodal_case, nodal_case, fields=fields)


def test_api_returns_422_for_incompatible_results(client, store, nodal_case):
    other = copy.deepcopy(nodal_case)
    other.id = "incompatible"
    other.field("von_mises").unit = "Pa"
    store.save_simulation(nodal_case)
    store.save_simulation(other)
    response = client.post("/api/compare", json={"simulation_a": nodal_case.id,
                                                "simulation_b": other.id})
    assert response.status_code == 422
    assert "field units" in response.json()["detail"]


def test_api_reordered_identical_result_is_zero(client, store, nodal_case):
    other = _reorder(nodal_case, [2, 1, 0])
    other.id = "reordered"
    store.save_simulation(nodal_case)
    store.save_simulation(other)
    response = client.post("/api/compare", json={"simulation_a": nodal_case.id,
                                                "simulation_b": other.id})
    assert response.status_code == 200
    assert response.json()["field_differences"][0]["abs_max"] == 0.0


def test_report_api_returns_422_for_incompatible_comparison(client, store, nodal_case):
    other = copy.deepcopy(nodal_case)
    other.id = "wrong-units"
    other.field("von_mises").unit = "Pa"
    store.save_simulation(nodal_case)
    store.save_simulation(other)
    response = client.post("/api/reports", json={"simulation_id": nodal_case.id,
                                                "compare_with": other.id, "format": "json"})
    assert response.status_code == 422
    assert "field units" in response.json()["detail"]


def test_regenerated_samples_have_explicit_ids_and_zero_self_difference(tmp_path):
    root = Path(__file__).resolve().parents[2]
    completed = subprocess.run([sys.executable, str(root / "scripts/generate_samples.py"),
                                "--out", str(tmp_path)], capture_output=True, text=True)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    paths = list(tmp_path.glob("*.json"))
    assert len(paths) == 4
    for path in paths:
        sim = NativeJSONAdapter().read(path)
        assert sim.mesh.node_ids_explicit
        assert all(d["abs_max"] == 0.0 for d in compare(sim, sim)["field_differences"])
