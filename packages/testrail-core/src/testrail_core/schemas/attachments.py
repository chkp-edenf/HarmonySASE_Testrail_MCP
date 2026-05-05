"""Pydantic schemas for attachment operations"""

from typing import Optional
from pydantic import BaseModel


class UploadAttachmentInput(BaseModel):
    """Input schema for uploading an attachment"""
    entity_type: str
    entity_id: str
    file_path: str
    filename: Optional[str] = None


class ListAttachmentsInput(BaseModel):
    """Input schema for listing attachments"""
    entity_type: str
    entity_id: str


class GetAttachmentInput(BaseModel):
    """Input schema for getting an attachment"""
    attachment_id: str


class DeleteAttachmentInput(BaseModel):
    """Input schema for deleting an attachment"""
    attachment_id: str
