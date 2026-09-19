"""Adapter architecture.

    CAE file -> Adapter -> parser -> validation -> common model -> analysis

An adapter is registered with a status. ``implemented`` means a real parser
exists in this repository; ``planned`` means the interface is reserved and the
adapter raises a clear error when called. Nothing claims support it does not
have.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from app.core.model import Simulation


class AdapterError(RuntimeError):
    pass


class UnsupportedFormatError(AdapterError):
    pass


@dataclass
class AdapterInfo:
    key: str
    name: str
    solver: str
    extensions: List[str]
    status: str           # "implemented" | "planned"
    notes: str = ""


class BaseAdapter(abc.ABC):
    info: AdapterInfo

    @classmethod
    def can_read(cls, path: Path) -> bool:
        return path.suffix.lower() in cls.info.extensions or "".join(
            path.suffixes[-2:]
        ).lower() in cls.info.extensions

    @abc.abstractmethod
    def read(self, path: Path, **kwargs) -> Simulation:
        """Parse a result file into the common model."""


class PlannedAdapter(BaseAdapter):
    """Reserved interface for a format with no parser in this repository yet."""

    def read(self, path: Path, **kwargs) -> Simulation:
        raise UnsupportedFormatError(
            f"No parser is implemented for {self.info.solver} "
            f"({', '.join(self.info.extensions)}). This adapter is registered with "
            f"status 'planned'. {self.info.notes}".strip()
        )


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: Dict[str, BaseAdapter] = {}

    def register(self, adapter: BaseAdapter) -> None:
        self._adapters[adapter.info.key] = adapter

    def get(self, key: str) -> BaseAdapter:
        if key not in self._adapters:
            raise UnsupportedFormatError(f"unknown adapter '{key}'")
        return self._adapters[key]

    def all(self) -> List[AdapterInfo]:
        return [a.info for a in self._adapters.values()]

    def implemented(self) -> List[AdapterInfo]:
        return [i for i in self.all() if i.status == "implemented"]

    def find_for(self, path: Path) -> Optional[BaseAdapter]:
        """First implemented adapter that recognises the file, else a planned one."""
        planned = None
        for a in self._adapters.values():
            if a.__class__.can_read(path):
                if a.info.status == "implemented":
                    return a
                planned = planned or a
        return planned

    def read(self, path: Path, key: Optional[str] = None, **kwargs) -> Simulation:
        adapter = self.get(key) if key else self.find_for(path)
        if adapter is None:
            raise UnsupportedFormatError(
                f"no adapter recognises '{path.name}'. Implemented formats: "
                + ", ".join(sorted({e for i in self.implemented() for e in i.extensions}))
            )
        sim = adapter.read(path, **kwargs)
        sim.adapter = adapter.info.key
        sim.source_file = path.name
        return sim
