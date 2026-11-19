from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse

from app.adapters import AdapterError, registry
from app.analysis import calculations as calc
from app.analysis import statistics as stats
from app.analysis.comparison import ComparisonValidationError, compare
from app.analysis.diagnostics import run_diagnostics
from app.analysis.validation import run_validation
from app.api.schemas import (
    AssistantRequest,
    CompareRequest,
    DerivedFieldRequest,
    FilterRequest,
    ProjectCreate,
    ProjectUpdate,
    ReportRequest,
)
from app.core.config import settings
from app.core.model import Project
from app.services import assistant as assistant_service
from app.services import reports as report_service
from app.services.store import Store, get_store

log = logging.getLogger("caer.api")
router = APIRouter()


def store_dep() -> Store:
    return get_store()


def _sim(store: Store, sid: str):
    try:
        return store.get_simulation(sid)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------- meta
@router.get("/health")
def health(store: Store = Depends(store_dep)) -> Dict[str, Any]:
    return {"status": "ok", "app": settings.app_name, "version": settings.version,
            "simulations": len(store.simulation_ids()),
            "projects": len(store.list_projects())}


@router.get("/adapters")
def adapters() -> Dict[str, Any]:
    infos = [i.__dict__ for i in registry.all()]
    return {"adapters": infos,
            "implemented": [i["key"] for i in infos if i["status"] == "implemented"],
            "note": ("Formats with status 'planned' have a registered interface but no parser in "
                     "this repository; calling them returns an explicit error.")}


@router.get("/domains")
def domains() -> Dict[str, Any]:
    from app.core.model import Domain
    implemented = {"FEA", "CFD", "Thermal", "MBD"}
    return {"domains": [{"key": d.value, "status": "implemented" if d.value in implemented
                         else "planned"} for d in Domain]}


# ------------------------------------------------------------ projects
@router.get("/projects")
def list_projects(store: Store = Depends(store_dep)) -> List[Dict[str, Any]]:
    return [p.to_dict() for p in store.list_projects()]


@router.post("/projects", status_code=201)
def create_project(body: ProjectCreate, store: Store = Depends(store_dep)) -> Dict[str, Any]:
    for sid in body.simulation_ids:
        _sim(store, sid)
    return store.create_project(**body.model_dump()).to_dict()


@router.get("/projects/{pid}")
def get_project(pid: str, store: Store = Depends(store_dep)) -> Dict[str, Any]:
    try:
        p = store.get_project(pid)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {**p.to_dict(),
            "simulations": [store.get_simulation(s).summary() for s in p.simulation_ids
                            if s in store.simulation_ids()]}


@router.put("/projects/{pid}")
def update_project(pid: str, body: ProjectUpdate, store: Store = Depends(store_dep)) -> Dict[str, Any]:
    try:
        p = store.get_project(pid)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(p, k, v)
    return store.save_project(p).to_dict()


@router.delete("/projects/{pid}", status_code=204)
def delete_project(pid: str, store: Store = Depends(store_dep)) -> None:
    try:
        store.delete_project(pid)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# --------------------------------------------------------- simulations
@router.get("/simulations")
def list_simulations(domain: Optional[str] = None,
                     store: Store = Depends(store_dep)) -> List[Dict[str, Any]]:
    out = store.list_simulations()
    if domain:
        out = [s for s in out if s["domain"].lower() == domain.lower()]
    return out


@router.get("/simulations/{sid}")
def get_simulation(sid: str, store: Store = Depends(store_dep)) -> Dict[str, Any]:
    sim = _sim(store, sid)
    project = store.project_of(sid)
    return {**sim.summary(),
            "project_id": project.id if project else None,
            "materials": [{"name": m.name, **m.properties} for m in sim.materials],
            "boundary_conditions": [b.__dict__ for b in sim.boundary_conditions],
            "loads": [l.__dict__ for l in sim.loads],
            "mesh_metrics": sim.mesh.metrics,
            "bounds": sim.mesh.bounds(),
            "parts": sim.mesh.parts,
            "convergence": (None if not sim.convergence else
                            {"iterations": sim.convergence.iterations,
                             "monitors": sim.convergence.monitors,
                             "criterion": sim.convergence.criterion,
                             "converged": sim.convergence.converged})}


@router.get("/simulations/{sid}/mesh")
def get_mesh(sid: str, store: Store = Depends(store_dep)) -> Dict[str, Any]:
    sim = _sim(store, sid)
    m = sim.mesh
    return {"nodes": m.nodes.round(4).ravel().tolist(),
            "triangles": m.triangles.ravel().tolist(),
            "node_count": m.n_nodes, "triangle_count": m.n_triangles,
            "parts": m.parts,
            "part_ids": m.part_ids.tolist() if m.part_ids is not None else [],
            "bounds": m.bounds()}


@router.get("/simulations/{sid}/fields/{field}/values")
def field_values(sid: str, field: str, step: int = -1,
                 store: Store = Depends(store_dep)) -> Dict[str, Any]:
    sim = _sim(store, sid)
    try:
        f = sim.field(field)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if step >= f.n_steps:
        raise HTTPException(status_code=400, detail=f"step {step} out of range (0..{f.n_steps - 1})")
    st = stats.field_statistics(sim, field, step)
    return {"field": field, "label": f.label, "unit": f.unit, "step": step,
            "steps": f.steps, "values": f.step(step).round(5).tolist(),
            "min": st.minimum.value, "max": st.maximum.value,
            "limits": f.limits, "derived": f.derived}


@router.get("/simulations/{sid}/fields/{field}/statistics")
def field_stats(sid: str, field: str, step: int = -1,
                store: Store = Depends(store_dep)) -> Dict[str, Any]:
    sim = _sim(store, sid)
    try:
        return {**stats.field_statistics(sim, field, step).to_dict(),
                "histogram": stats.histogram(sim, field, step),
                "envelope": stats.envelope(sim, field)}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/simulations/{sid}/statistics")
def all_stats(sid: str, step: int = -1, store: Store = Depends(store_dep)) -> List[Dict[str, Any]]:
    return stats.all_statistics(_sim(store, sid), step)


@router.post("/simulations/{sid}/filter")
def filter_values(sid: str, body: FilterRequest, store: Store = Depends(store_dep)) -> Dict[str, Any]:
    sim = _sim(store, sid)
    try:
        return stats.filter_field(sim, body.field, body.step, body.minimum,
                                  body.maximum, body.fraction_of_max)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/simulations/{sid}/calculations")
def calculations(sid: str, store: Store = Depends(store_dep)) -> List[Dict[str, Any]]:
    return [c.to_dict() for c in calc.standard_calculations(_sim(store, sid))]


@router.post("/simulations/{sid}/derived-field")
def derived_field(sid: str, body: DerivedFieldRequest,
                  store: Store = Depends(store_dep)) -> Dict[str, Any]:
    sim = _sim(store, sid)
    try:
        f = calc.safety_factor_field(sim, body.source_field, body.yield_strength)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    sim.add_field(f)
    return {"created": f.name, "label": f.label, "unit": f.unit,
            "provenance": f.provenance, "steps": f.n_steps}


@router.get("/simulations/{sid}/validation")
def validation(sid: str, store: Store = Depends(store_dep)) -> Dict[str, Any]:
    return run_validation(_sim(store, sid))


@router.get("/simulations/{sid}/diagnostics")
def diagnostics(sid: str, store: Store = Depends(store_dep)) -> Dict[str, Any]:
    return run_diagnostics(_sim(store, sid))


@router.delete("/simulations/{sid}", status_code=204)
def delete_simulation(sid: str, store: Store = Depends(store_dep)) -> None:
    try:
        store.delete_simulation(sid)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


# ------------------------------------------------------------- analysis
@router.post("/compare")
def compare_simulations(body: CompareRequest, store: Store = Depends(store_dep)) -> Dict[str, Any]:
    a, b = _sim(store, body.simulation_a), _sim(store, body.simulation_b)
    try:
        return compare(a, b, body.fields, body.step)
    except ComparisonValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/assistant/query")
def assistant_query(body: AssistantRequest, store: Store = Depends(store_dep)) -> Dict[str, Any]:
    return assistant_service.ask(_sim(store, body.simulation_id), body.question)


@router.get("/assistant/suggestions")
def assistant_suggestions() -> Dict[str, Any]:
    return {"suggestions": assistant_service.SUGGESTIONS,
            "block_kinds": assistant_service.BLOCK_LABELS}


@router.post("/reports")
def build_report(body: ReportRequest, store: Store = Depends(store_dep)):
    sim = _sim(store, body.simulation_id)
    project: Optional[Project] = None
    if body.project_id:
        try:
            project = store.get_project(body.project_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    else:
        project = store.project_of(sim.id)
    other = _sim(store, body.compare_with) if body.compare_with else None
    try:
        report = report_service.build_report(sim, project, body.sections, other)
    except ComparisonValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if body.format == "json":
        return report
    if body.format == "html":
        return HTMLResponse(report_service.to_html(report))
    return PlainTextResponse(report_service.to_markdown(report))


@router.get("/reports/sections")
def report_sections() -> Dict[str, Any]:
    return {"sections": report_service.SECTIONS, "titles": report_service.SECTION_TITLES}


# --------------------------------------------------------------- import
@router.post("/import", status_code=201)
async def import_result(file: UploadFile = File(...), adapter: Optional[str] = Query(None),
                        store: Store = Depends(store_dep)) -> Dict[str, Any]:
    suffix = Path(file.filename or "upload").suffix
    tmp = Path(tempfile.mkdtemp()) / (file.filename or f"upload{suffix}")
    size = 0
    with open(tmp, "wb") as fh:
        while chunk := await file.read(1 << 20):
            size += len(chunk)
            if size > settings.max_upload_mb * 1024 * 1024:
                shutil.rmtree(tmp.parent, ignore_errors=True)
                raise HTTPException(status_code=413,
                                    detail=f"file exceeds {settings.max_upload_mb} MB")
            fh.write(chunk)
    try:
        sim = store.import_file(tmp, adapter_key=adapter)
        log.info("imported %s via %s (%d nodes)", file.filename, sim.adapter, sim.mesh.n_nodes)
        return sim.summary()
    except AdapterError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # parser failure is a client-data problem, not a crash
        log.exception("import failed")
        raise HTTPException(status_code=422, detail=f"could not parse file: {exc}") from exc
    finally:
        shutil.rmtree(tmp.parent, ignore_errors=True)
