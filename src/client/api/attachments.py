"""TestRail Attachments API client"""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class AttachmentsClient:
    """Client for TestRail Attachments API"""

    def __init__(self, client):
        self._client = client

    async def add_attachment_to_case(self, case_id: int, file_data: bytes, filename: str) -> Dict[str, Any]:
        """Upload attachment to a test case"""
        return await self._client.upload_file(f"add_attachment_to_case/{case_id}", file_data, filename)

    async def add_attachment_to_result(self, result_id: int, file_data: bytes, filename: str) -> Dict[str, Any]:
        """Upload attachment to a test result"""
        return await self._client.upload_file(f"add_attachment_to_result/{result_id}", file_data, filename)

    async def add_attachment_to_run(self, run_id: int, file_data: bytes, filename: str) -> Dict[str, Any]:
        """Upload attachment to a test run"""
        return await self._client.upload_file(f"add_attachment_to_run/{run_id}", file_data, filename)

    async def add_attachment_to_plan(self, plan_id: int, file_data: bytes, filename: str) -> Dict[str, Any]:
        """Upload attachment to a test plan"""
        return await self._client.upload_file(f"add_attachment_to_plan/{plan_id}", file_data, filename)

    async def add_attachment_to_plan_entry(self, plan_id: int, entry_id: int, file_data: bytes, filename: str) -> Dict[str, Any]:
        """Upload attachment to a plan entry"""
        return await self._client.upload_file(f"add_attachment_to_plan_entry/{plan_id}/{entry_id}", file_data, filename)

    async def get_attachments_for_case(self, case_id: int) -> Dict[str, Any]:
        """Get attachments for a test case"""
        result = await self._client.get(f"get_attachments_for_case/{case_id}")
        if isinstance(result, list):
            return {"attachments": result}
        return result

    async def get_attachments_for_run(self, run_id: int) -> Dict[str, Any]:
        """Get attachments for a test run"""
        result = await self._client.get(f"get_attachments_for_run/{run_id}")
        if isinstance(result, list):
            return {"attachments": result}
        return result

    async def get_attachments_for_plan(self, plan_id: int) -> Dict[str, Any]:
        """Get attachments for a test plan"""
        result = await self._client.get(f"get_attachments_for_plan/{plan_id}")
        if isinstance(result, list):
            return {"attachments": result}
        return result

    async def get_attachments_for_test(self, test_id: int) -> Dict[str, Any]:
        """Get attachments for a test"""
        result = await self._client.get(f"get_attachments_for_test/{test_id}")
        if isinstance(result, list):
            return {"attachments": result}
        return result

    async def get_attachment(self, attachment_id: str) -> Dict[str, Any]:
        """Get a specific attachment (ID may be numeric or alphanumeric UUID on TestRail 7.1+)"""
        return await self._client.get(f"get_attachment/{attachment_id}")

    async def delete_attachment(self, attachment_id: str) -> Dict[str, Any]:
        """Delete an attachment (ID may be numeric or alphanumeric UUID on TestRail 7.1+)"""
        return await self._client.post(f"delete_attachment/{attachment_id}", {})
