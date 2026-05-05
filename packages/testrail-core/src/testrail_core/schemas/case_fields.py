"""Case field-related schemas"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class CaseFieldConfig(BaseModel):
    """Case field configuration"""
    context: Optional[Dict[str, Any]] = None
    options: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


class CaseField(BaseModel):
    """TestRail Case Field schema"""
    id: int
    name: str
    system_name: str
    label: Optional[str] = None
    description: Optional[str] = None
    type_id: int
    location_id: Optional[int] = None
    display_order: Optional[int] = None
    configs: Optional[List[CaseFieldConfig]] = None
    is_active: Optional[bool] = None
    is_required: Optional[bool] = None
    is_global: Optional[bool] = None
    is_system: Optional[bool] = None
    entity_id: Optional[int] = None
    template_ids: Optional[List[int]] = None
    include_all: Optional[bool] = None


class CaseFieldsResponse(BaseModel):
    """Response for get_case_fields endpoint"""
    fields: List[CaseField] = Field(default_factory=list)
    count: int = 0


class CaseType(BaseModel):
    """TestRail Case Type schema"""
    id: int
    name: str
    is_default: Optional[bool] = None


class CaseTypesResponse(BaseModel):
    """Response for get_case_types endpoint"""
    types: List[CaseType] = Field(default_factory=list, alias="case_types")
    count: int = 0
    
    class Config:
        populate_by_name = True


class Priority(BaseModel):
    """TestRail Priority schema"""
    id: int
    name: str
    priority: Optional[int] = None
    short_name: Optional[str] = None
    is_default: Optional[bool] = None


class PrioritiesResponse(BaseModel):
    """Response for get_priorities endpoint"""
    priorities: List[Priority] = Field(default_factory=list)
    count: int = 0


class Template(BaseModel):
    """TestRail Template schema"""
    id: int
    name: str
    is_default: Optional[bool] = None


class TemplatesResponse(BaseModel):
    """Response for get_templates endpoint"""
    templates: List[Template] = Field(default_factory=list)
    count: int = 0
