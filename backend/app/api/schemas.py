"""Request/response models for the HTTP API."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    owner: str = ""
    simulation_ids: List[str] = []
    metadata: Dict[str, Any] = {}


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    owner: Optional[str] = None
    simulation_ids: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class FilterRequest(BaseModel):
    field: str
    step: int = -1
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    fraction_of_max: Optional[float] = Field(None, ge=0, le=1)


class CompareRequest(BaseModel):
    simulation_a: str
    simulation_b: str
    fields: Optional[List[str]] = None
    step: int = -1


class AssistantRequest(BaseModel):
    simulation_id: str
    question: str = Field(..., min_length=1, max_length=500)


class ReportRequest(BaseModel):
    simulation_id: str
    project_id: Optional[str] = None
    sections: Optional[List[str]] = None
    compare_with: Optional[str] = None
    format: str = Field("markdown", pattern="^(markdown|html|json)$")


class DerivedFieldRequest(BaseModel):
    kind: str = Field("safety_factor", pattern="^(safety_factor)$")
    source_field: str = "von_mises"
    yield_strength: Optional[float] = None
