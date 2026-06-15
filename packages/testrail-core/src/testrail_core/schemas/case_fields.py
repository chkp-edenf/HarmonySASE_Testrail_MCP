"""Case field-related schemas"""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class CaseFieldConfig(BaseModel):
    """Case field configuration"""
    context: dict[str, Any] | None = None
    options: dict[str, Any] | None = None
    id: str | None = None


class CaseField(BaseModel):
    """TestRail Case Field schema"""
    id: int
    name: str
    system_name: str
    label: str | None = None
    description: str | None = None
    type_id: int
    location_id: int | None = None
    display_order: int | None = None
    configs: list[CaseFieldConfig] | None = None
    is_active: bool | None = None
    is_required: bool | None = None
    is_global: bool | None = None
    is_system: bool | None = None
    entity_id: int | None = None
    template_ids: list[int] | None = None
    include_all: bool | None = None


class CaseFieldsResponse(BaseModel):
    """Response for get_case_fields endpoint"""
    fields: list[CaseField] = Field(default_factory=list)
    count: int = 0


class CaseType(BaseModel):
    """TestRail Case Type schema"""
    id: int
    name: str
    is_default: bool | None = None


class CaseTypesResponse(BaseModel):
    """Response for get_case_types endpoint"""
    model_config = ConfigDict(populate_by_name=True)

    types: list[CaseType] = Field(default_factory=list, alias="case_types")
    count: int = 0


class Priority(BaseModel):
    """TestRail Priority schema"""
    id: int
    name: str
    priority: int | None = None
    short_name: str | None = None
    is_default: bool | None = None


class PrioritiesResponse(BaseModel):
    """Response for get_priorities endpoint"""
    priorities: list[Priority] = Field(default_factory=list)
    count: int = 0


class Template(BaseModel):
    """TestRail Template schema"""
    id: int
    name: str
    is_default: bool | None = None


class TemplatesResponse(BaseModel):
    """Response for get_templates endpoint"""
    templates: list[Template] = Field(default_factory=list)
    count: int = 0
