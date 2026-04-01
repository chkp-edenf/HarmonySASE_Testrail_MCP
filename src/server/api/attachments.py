"""Handlers for TestRail attachment operations"""

import json
import logging
import os
from mcp.types import TextContent
from .utils import create_success_response, create_error_response, require_fields

logger = logging.getLogger(__name__)

# Security: allowed file extensions for uploads
ALLOWED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp",  # images
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",           # documents
    ".txt", ".csv", ".log", ".json", ".xml",             # text
    ".zip", ".tar", ".gz",                               # archives
    ".mp4", ".mov", ".avi",                              # video
}

# Security: blocked path patterns (case-insensitive check)
BLOCKED_PATHS = [
    ".ssh", ".gnupg", ".aws", ".azure", ".gcloud",
    ".env", ".git/config", ".netrc", ".npmrc", ".pypirc",
    "credentials", "secrets", "private_key", "id_rsa", "id_ed25519",
    ".kube/config", ".docker/config",
]

# Map entity_type to the appropriate client method names
UPLOAD_METHODS = {
    "case": "add_attachment_to_case",
    "result": "add_attachment_to_result",
    "run": "add_attachment_to_run",
    "plan": "add_attachment_to_plan",
}

LIST_METHODS = {
    "case": "get_attachments_for_case",
    "result": None,  # TestRail doesn't have get_attachments_for_result
    "run": "get_attachments_for_run",
    "plan": "get_attachments_for_plan",
    "test": "get_attachments_for_test",
}


def _validate_file_path(file_path: str) -> None:
    """Validate file path for security and allowed extensions."""
    normalized = os.path.normpath(os.path.abspath(file_path))
    lower_path = normalized.lower()

    # Block sensitive paths
    for blocked in BLOCKED_PATHS:
        if blocked.lower() in lower_path:
            raise ValueError(f"Upload blocked: path contains sensitive pattern '{blocked}'")

    # Check file extension
    _, ext = os.path.splitext(normalized)
    if ext.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Upload blocked: extension '{ext}' not allowed. "
            f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # Verify file exists and is a regular file
    if not os.path.isfile(normalized):
        raise ValueError(f"File not found: {file_path}")


async def handle_upload_attachment(arguments: dict, client) -> list[TextContent]:
    """Upload an attachment to a TestRail entity"""
    try:
        require_fields(arguments, ["entity_type", "entity_id", "file_path"], "upload_attachment")

        entity_type = arguments["entity_type"]
        entity_id = int(arguments["entity_id"])
        file_path = arguments["file_path"]

        _validate_file_path(file_path)

        filename = arguments.get("filename", os.path.basename(file_path))
        with open(file_path, "rb") as f:
            file_data = f.read()

        method_name = UPLOAD_METHODS.get(entity_type)
        if not method_name:
            raise ValueError(f"Upload not supported for entity_type '{entity_type}'. Valid: {', '.join(UPLOAD_METHODS.keys())}")

        method = getattr(client.attachments, method_name)
        result = await method(entity_id, file_data, filename)

        response = create_success_response(
            f"Attachment '{filename}' uploaded to {entity_type} {entity_id}",
            result
        )
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
    except Exception as e:
        logger.error(f"Error uploading attachment: {str(e)}")
        response = create_error_response("Attachment upload failed", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_list_attachments(arguments: dict, client) -> list[TextContent]:
    """List attachments for a TestRail entity"""
    try:
        require_fields(arguments, ["entity_type", "entity_id"], "list_attachments")

        entity_type = arguments["entity_type"]
        entity_id = int(arguments["entity_id"])

        method_name = LIST_METHODS.get(entity_type)
        if not method_name:
            raise ValueError(f"Listing not supported for entity_type '{entity_type}'. Valid: {', '.join(k for k, v in LIST_METHODS.items() if v)}")

        method = getattr(client.attachments, method_name)
        result = await method(entity_id)

        attachments = result.get("attachments", [])
        response = create_success_response(
            f"Found {len(attachments)} attachment(s) for {entity_type} {entity_id}",
            result
        )
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
    except Exception as e:
        logger.error(f"Error listing attachments: {str(e)}")
        response = create_error_response("List attachments failed", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_get_attachment(arguments: dict, client) -> list[TextContent]:
    """Get attachment info"""
    try:
        require_fields(arguments, ["attachment_id"], "get_attachment")

        attachment_id = arguments["attachment_id"]
        result = await client.attachments.get_attachment(attachment_id)

        response = create_success_response(
            f"Attachment {attachment_id} details",
            result
        )
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
    except Exception as e:
        logger.error(f"Error getting attachment: {str(e)}")
        response = create_error_response("Get attachment failed", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_delete_attachment(arguments: dict, client) -> list[TextContent]:
    """Delete an attachment"""
    try:
        require_fields(arguments, ["attachment_id"], "delete_attachment")

        attachment_id = arguments["attachment_id"]
        await client.attachments.delete_attachment(attachment_id)

        response = create_success_response(
            f"Attachment {attachment_id} deleted",
            {"attachment_id": attachment_id}
        )
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
    except Exception as e:
        logger.error(f"Error deleting attachment: {str(e)}")
        response = create_error_response("Delete attachment failed", e)
        return [TextContent(type="text", text=json.dumps(response, indent=2))]
