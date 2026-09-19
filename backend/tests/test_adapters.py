from pathlib import Path

import numpy as np
import pytest

from app.adapters import NativeJSONAdapter, UnsupportedFormatError, registry

ROOT = Path(__file__).resolve().parents[2]
EXTERNAL = ROOT / "samples" / "external"


def test_registry_reports_status_honestly():
    infos = {i.key: i for i in registry.all()}
    assert infos["native-json"].status == "implemented"
    assert infos["vtk-legacy"].status == "implemented"
    assert infos["csv-points"].status == "implemented"
    assert infos["ansys-rst"].status == "planned"
    assert infos["abaqus-odb"].status == "planned"


def test_planned_adapter_raises_a_clear_error(tmp_path):
    f = tmp_path / "model.odb"
    f.write_bytes(b"not really an odb")
    with pytest.raises(UnsupportedFormatError) as exc:
        registry.read(f)
    assert "planned" in str(exc.value).lower()


def test_unknown_extension_is_rejected(tmp_path):
    f = tmp_path / "thing.xyz"
    f.write_text("nope")
    with pytest.raises(UnsupportedFormatError):
        registry.read(f)


def test_native_roundtrip_preserves_values(bracket, tmp_path):
    out = NativeJSONAdapter.write(bracket, tmp_path / "rt.json", decimals=6)
    again = registry.read(out, key="native-json")
    assert again.mesh.n_nodes == bracket.mesh.n_nodes
    assert set(again.fields) == set(bracket.fields)
    a = bracket.field("von_mises").values
    b = again.field("von_mises").values
    assert np.allclose(a, b, atol=1e-5)
    assert again.materials[0].properties["yield_strength"] == 276.0


def test_native_rejects_foreign_json(tmp_path):
    f = tmp_path / "other.json"
    f.write_text('{"format": "something-else"}')
    with pytest.raises(Exception):
        registry.read(f, key="native-json")


def test_vtk_legacy_reads_points_cells_and_fields():
    sim = registry.read(EXTERNAL / "plate_patch.vtk")
    assert sim.adapter == "vtk-legacy"
    assert sim.mesh.n_nodes == 6
    assert sim.mesh.n_triangles == 4          # two quads -> four triangles
    assert "temperature" in sim.fields
    assert sim.field("temperature").step(0).max() == pytest.approx(33.4)
    assert sim.field("displacement").step(0).max() == pytest.approx(0.036, abs=1e-3)
    assert sim.is_sample_data is False


def test_csv_adapter_reads_columns_and_units():
    sim = registry.read(EXTERNAL / "probe_points.csv")
    assert sim.mesh.n_nodes == 5
    assert "von_mises" in sim.fields
    assert sim.field("von_mises").unit == "MPa"
    assert sim.field("von_mises").step(0).max() == pytest.approx(214.6)


def test_csv_without_coordinates_is_rejected(tmp_path):
    f = tmp_path / "bad.csv"
    f.write_text("a,b\n1,2\n")
    with pytest.raises(Exception):
        registry.read(f)


def test_store_import_persists_the_file(store):
    sim = store.import_file(EXTERNAL / "plate_patch.vtk")
    assert sim.id in store.simulation_ids()
    assert store.get_simulation(sim.id).mesh.n_nodes == 6


def test_sample_datasets_are_read_only(store):
    with pytest.raises(PermissionError):
        store.delete_simulation("brk-114")
