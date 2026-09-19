import io
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
EXTERNAL = ROOT / "samples" / "external"


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["simulations"] >= 4


def test_adapters_endpoint_separates_implemented_and_planned(client):
    d = client.get("/api/adapters").json()
    assert "native-json" in d["implemented"]
    assert "ansys-rst" not in d["implemented"]
    assert any(a["status"] == "planned" for a in d["adapters"])


def test_list_and_filter_simulations(client):
    all_sims = client.get("/api/simulations").json()
    assert len(all_sims) >= 4
    fea = client.get("/api/simulations?domain=FEA").json()
    assert {s["id"] for s in fea} == {"brk-114"}


def test_simulation_detail(client):
    d = client.get("/api/simulations/brk-114").json()
    assert d["materials"][0]["yield_strength"] == 276.0
    assert d["mesh_metrics"]["Nodes"] > 0
    assert d["project_id"]


def test_missing_simulation_is_404(client):
    assert client.get("/api/simulations/nope").status_code == 404


def test_mesh_payload_is_flat_arrays(client):
    m = client.get("/api/simulations/brk-114/mesh").json()
    assert len(m["nodes"]) == m["node_count"] * 3
    assert len(m["triangles"]) == m["triangle_count"] * 3
    assert len(m["part_ids"]) == m["triangle_count"]


def test_field_values_and_statistics(client):
    v = client.get("/api/simulations/brk-114/fields/von_mises/values").json()
    assert len(v["values"]) == 3800
    s = client.get("/api/simulations/brk-114/fields/von_mises/statistics").json()
    assert s["maximum"]["value"] == pytest.approx(v["max"], rel=1e-6)
    assert sum(s["histogram"]["counts"]) == s["count"]


def test_unknown_field_is_404(client):
    assert client.get("/api/simulations/brk-114/fields/nope/values").status_code == 404


def test_out_of_range_step_is_400(client):
    assert client.get("/api/simulations/brk-114/fields/von_mises/values?step=99").status_code == 400


def test_filter_endpoint(client):
    r = client.post("/api/simulations/brk-114/filter",
                    json={"field": "von_mises", "fraction_of_max": 0.8})
    body = r.json()
    assert r.status_code == 200
    assert 0 < body["selected"] < body["total"]


def test_calculations_endpoint(client):
    calcs = client.post and client.get("/api/simulations/brk-114/calculations").json()
    assert any(c["name"].startswith("Factor of safety") for c in calcs)
    assert all(c["assumptions"] for c in calcs)


def test_derived_field_is_created(client):
    r = client.post("/api/simulations/brk-114/derived-field",
                    json={"kind": "safety_factor", "source_field": "von_mises"})
    assert r.status_code == 200
    assert r.json()["created"] == "safety_factor"
    stats = client.get("/api/simulations/brk-114/fields/safety_factor/statistics").json()
    assert stats["minimum"]["value"] > 0


def test_validation_and_diagnostics_endpoints(client):
    v = client.get("/api/simulations/thm-088/validation").json()
    assert v["overall"] in ("verified", "warning", "investigate", "not_validated")
    d = client.get("/api/simulations/thm-088/diagnostics").json()
    assert d["counts"]["critical"] >= 1


def test_compare_endpoint(client):
    r = client.post("/api/compare", json={"simulation_a": "brk-114", "simulation_b": "brk-114"})
    assert r.status_code == 200
    assert r.json()["same_mesh"] is True


def test_assistant_endpoint(client):
    r = client.post("/api/assistant/query",
                    json={"simulation_id": "brk-114", "question": "Where is maximum stress?"})
    body = r.json()
    assert r.status_code == 200
    assert body["blocks"][0]["label"] == "Simulation data"
    assert body["evidence"]


def test_report_formats(client):
    md = client.post("/api/reports", json={"simulation_id": "brk-114", "format": "markdown"})
    assert md.status_code == 200 and md.text.startswith("# ")
    html = client.post("/api/reports", json={"simulation_id": "brk-114", "format": "html"})
    assert "<h1>" in html.text
    js = client.post("/api/reports", json={"simulation_id": "brk-114", "format": "json"})
    assert "body" in js.json()


def test_project_crud(client):
    created = client.post("/api/projects", json={"name": "Test project",
                                                 "simulation_ids": ["brk-114"]})
    assert created.status_code == 201
    pid = created.json()["id"]
    got = client.get(f"/api/projects/{pid}").json()
    assert got["simulations"][0]["id"] == "brk-114"
    upd = client.put(f"/api/projects/{pid}", json={"description": "updated"})
    assert upd.json()["description"] == "updated"
    assert client.delete(f"/api/projects/{pid}").status_code == 204
    assert client.get(f"/api/projects/{pid}").status_code == 404


def test_project_with_unknown_simulation_is_rejected(client):
    r = client.post("/api/projects", json={"name": "bad", "simulation_ids": ["ghost"]})
    assert r.status_code == 404


def test_import_vtk_through_the_api(client):
    data = (EXTERNAL / "plate_patch.vtk").read_bytes()
    r = client.post("/api/import", files={"file": ("plate_patch.vtk", io.BytesIO(data),
                                                   "application/octet-stream")})
    assert r.status_code == 201
    assert r.json()["nodes"] == 6


def test_import_of_a_planned_format_is_rejected_clearly(client):
    r = client.post("/api/import", files={"file": ("model.odb", io.BytesIO(b"binary"),
                                                   "application/octet-stream")})
    assert r.status_code == 422
    assert "planned" in r.json()["detail"].lower()
