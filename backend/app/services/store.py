"""Project and simulation store.

Projects are JSON documents on disk; simulations are native result files. The
store keeps an in-memory cache of parsed simulations because result arrays are
expensive to re-parse on every request.
"""
from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.adapters import NativeJSONAdapter, registry
from app.core.config import settings
from app.core.model import Project, Simulation


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


class Store:
    def __init__(self, data_dir: Optional[Path] = None, samples_dir: Optional[Path] = None) -> None:
        self.data_dir = Path(data_dir or settings.data_dir)
        self.samples_dir = Path(samples_dir or settings.samples_dir)
        self.projects_dir = self.data_dir / "projects"
        self.sims_dir = self.data_dir / "simulations"
        for d in (self.projects_dir, self.sims_dir):
            d.mkdir(parents=True, exist_ok=True)
        self._sim_cache: Dict[str, Simulation] = {}
        self._sim_paths: Dict[str, Path] = {}
        self.reindex()

    # ------------------------------------------------------------- indexing
    def reindex(self) -> None:
        self._sim_paths.clear()
        for d in (self.samples_dir, self.sims_dir):
            if not d.exists():
                continue
            for p in sorted(d.glob("*.json")) + sorted(d.glob("*.json.gz")):
                sid = p.name.split(".")[0]
                self._sim_paths[sid] = p

    # ------------------------------------------------------------- projects
    def list_projects(self) -> List[Project]:
        out = []
        for p in sorted(self.projects_dir.glob("*.json")):
            out.append(Project.from_dict(json.loads(p.read_text())))
        return out

    def get_project(self, pid: str) -> Project:
        path = self.projects_dir / f"{pid}.json"
        if not path.exists():
            raise KeyError(f"project '{pid}' not found")
        return Project.from_dict(json.loads(path.read_text()))

    def save_project(self, project: Project) -> Project:
        project.modified = _now()
        if not project.created:
            project.created = project.modified
        (self.projects_dir / f"{project.id}.json").write_text(
            json.dumps(project.to_dict(), indent=2)
        )
        return project

    def create_project(self, name: str, description: str = "", owner: str = "",
                       simulation_ids: Optional[List[str]] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> Project:
        pid = f"prj-{uuid.uuid4().hex[:8]}"
        return self.save_project(Project(
            id=pid, name=name, description=description, owner=owner,
            simulation_ids=list(simulation_ids or []), metadata=dict(metadata or {})))

    def delete_project(self, pid: str) -> None:
        path = self.projects_dir / f"{pid}.json"
        if not path.exists():
            raise KeyError(f"project '{pid}' not found")
        path.unlink()

    # ---------------------------------------------------------- simulations
    def simulation_ids(self) -> List[str]:
        return sorted(self._sim_paths)

    def get_simulation(self, sid: str) -> Simulation:
        if sid in self._sim_cache:
            return self._sim_cache[sid]
        if sid not in self._sim_paths:
            self.reindex()
        if sid not in self._sim_paths:
            raise KeyError(f"simulation '{sid}' not found")
        sim = registry.read(self._sim_paths[sid], key="native-json")
        self._sim_cache[sid] = sim
        return sim

    def list_simulations(self) -> List[Dict[str, Any]]:
        return [self.get_simulation(s).summary() for s in self.simulation_ids()]

    def import_file(self, path: Path, adapter_key: Optional[str] = None,
                    **kwargs) -> Simulation:
        sim = registry.read(path, key=adapter_key, **kwargs)
        target = self.sims_dir / f"{sim.id}.json"
        NativeJSONAdapter.write(sim, target)
        self._sim_paths[sim.id] = target
        self._sim_cache[sim.id] = sim
        return sim

    def save_simulation(self, sim: Simulation) -> Path:
        target = self.sims_dir / f"{sim.id}.json"
        NativeJSONAdapter.write(sim, target)
        self._sim_paths[sim.id] = target
        self._sim_cache[sim.id] = sim
        return target

    def delete_simulation(self, sid: str) -> None:
        path = self._sim_paths.get(sid)
        if path is None:
            raise KeyError(f"simulation '{sid}' not found")
        if path.parent == self.samples_dir:
            raise PermissionError("sample datasets are read-only")
        path.unlink()
        self._sim_paths.pop(sid, None)
        self._sim_cache.pop(sid, None)

    def project_of(self, sid: str) -> Optional[Project]:
        for p in self.list_projects():
            if sid in p.simulation_ids:
                return p
        return None

    def bootstrap_sample_projects(self) -> List[Project]:
        """Create one project per sample dataset the first time the app runs."""
        existing = {p.metadata.get("sample_for") for p in self.list_projects()}
        created = []
        for sid in self.simulation_ids():
            if sid in existing:
                continue
            sim = self.get_simulation(sid)
            created.append(self.save_project(Project(
                id=f"prj-{sid}", name=sim.name,
                description=f"{sim.domain.value} sample dataset - {sim.analysis_type}.",
                owner=sim.metadata.get("owner", "sample data"),
                created=_now(), modified=_now(),
                simulation_ids=[sid], metadata={"sample_for": sid, "is_sample": True})))
        return created


_store: Optional[Store] = None


def get_store() -> Store:
    global _store
    if _store is None:
        _store = Store()
        _store.bootstrap_sample_projects()
    return _store


def reset_store(data_dir: Optional[Path] = None, samples_dir: Optional[Path] = None) -> Store:
    global _store
    _store = Store(data_dir=data_dir, samples_dir=samples_dir)
    _store.bootstrap_sample_projects()
    return _store
