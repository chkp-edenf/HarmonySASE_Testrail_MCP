"""Custom exception classes for TestRail API errors"""

from typing import Any, Optional


class TestRailError(Exception):
    """Base exception for all TestRail errors"""
    
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class TestRailAPIError(TestRailError):
    """HTTP API error with status code and response data"""
    
    def __init__(self, status: int, message: str, data: Optional[Any] = None):
        super().__init__(message)
        self.status = status
        self.data = data
    
    def __str__(self) -> str:
        return f"API Error {self.status}: {self.message}"


class TestRailTimeoutError(TestRailError):
    """Request timeout error"""
    
    def __init__(self, message: str = "Request timed out"):
        super().__init__(message)


class TestRailNetworkError(TestRailError):
    """Network connectivity error"""
    
    def __init__(self, message: str = "Network error occurred"):
        super().__init__(message)


class TestRailAuthenticationError(TestRailAPIError):
    """Authentication failed (401)"""
    
    def __init__(self, message: str = "Authentication failed", data: Optional[Any] = None):
        super().__init__(401, message, data)


class TestRailPermissionError(TestRailAPIError):
    """Permission denied (403)"""
    
    def __init__(self, message: str = "Permission denied", data: Optional[Any] = None):
        super().__init__(403, message, data)


class TestRailNotFoundError(TestRailAPIError):
    """Resource not found (404)"""
    
    def __init__(self, message: str = "Resource not found", data: Optional[Any] = None):
        super().__init__(404, message, data)


class TestRailBadRequestError(TestRailAPIError):
    """Bad request (400)"""
    
    def __init__(self, message: str = "Bad request", data: Optional[Any] = None):
        super().__init__(400, message, data)


class TestRailRateLimitError(TestRailAPIError):
    """Rate limit exceeded (429)"""
    
    def __init__(self, message: str = "Rate limit exceeded", data: Optional[Any] = None):
        super().__init__(429, message, data)


class TestRailServerError(TestRailAPIError):
    """TestRail server error (5xx)"""
    
    def __init__(self, status: int, message: str = "TestRail server error", data: Optional[Any] = None):
        super().__init__(status, message, data)
