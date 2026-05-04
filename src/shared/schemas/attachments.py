"""Re-export shim — relocated to testrail_core.schemas.attachments (plan-004 phase 5)."""
from testrail_core.schemas.attachments import (
    DeleteAttachmentInput,
    GetAttachmentInput,
    ListAttachmentsInput,
    UploadAttachmentInput,
)

__all__ = [
    "DeleteAttachmentInput",
    "GetAttachmentInput",
    "ListAttachmentsInput",
    "UploadAttachmentInput",
]
