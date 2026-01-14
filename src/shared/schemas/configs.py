"""Configuration-related schemas"""

from typing import Optional, List
from pydantic import BaseModel, Field


class Config(BaseModel):
    """TestRail Configuration schema"""
    id: int
    name: str
    group_id: int


class ConfigGroup(BaseModel):
    """TestRail Configuration Group schema"""
    id: int
    name: str
    project_id: int
    configs: List[Config] = Field(default_factory=list)


class GetConfigsInput(BaseModel):
    """Input schema for getting configurations"""
    project_id: str = Field(..., description="Project ID")


class AddConfigGroupInput(BaseModel):
    """Input schema for adding a configuration group"""
    project_id: str = Field(..., description="Project ID")
    name: str = Field(..., description="Configuration group name")


class AddConfigInput(BaseModel):
    """Input schema for adding a configuration"""
    config_group_id: str = Field(..., description="Configuration group ID")
    name: str = Field(..., description="Configuration name")
