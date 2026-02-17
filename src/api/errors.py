"""Custom exception classes for API error handling.

Provides domain-specific exceptions with HTTP status codes and
structured error responses for consistent API error formatting.
"""


class APIError(Exception):
    """Base exception for all API errors.

    All custom exceptions inherit from this class for consistent
    error handling across the application.
    """

    def __init__(self, message: str, status_code: int = 500, payload: dict = None):
        """Initialize API error.

        Args:
            message: Human-readable error description
            status_code: HTTP status code (default 500)
            payload: Optional additional error context
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload or {}

    def to_dict(self) -> dict:
        """Convert exception to JSON-serializable dict.

        Returns:
            dict: {"error": message, "code": status_code, ...payload}
        """
        result = {"error": self.message, "code": self.status_code}
        result.update(self.payload)
        return result

    def __str__(self) -> str:
        """String representation for logging."""
        if self.payload:
            return f"{self.message} (status={self.status_code}, payload={self.payload})"
        return f"{self.message} (status={self.status_code})"


class ValidationError(APIError):
    """Exception for invalid input data (400 Bad Request).

    Use when user input fails validation checks.
    """

    def __init__(self, message: str, field: str = None):
        """Initialize validation error.

        Args:
            message: Validation error description
            field: Optional field name that failed validation
        """
        payload = {"field": field} if field else {}
        super().__init__(message, status_code=400, payload=payload)


class NotFoundError(APIError):
    """Exception for resource not found (404 Not Found).

    Formats error message as "{resource_type} {resource_id} not found".
    """

    def __init__(self, resource_type: str, resource_id: str):
        """Initialize not found error.

        Args:
            resource_type: Type of resource (e.g., "Course", "Activity")
            resource_id: Identifier of missing resource
        """
        message = f"{resource_type} {resource_id} not found"
        payload = {"resource_type": resource_type, "resource_id": resource_id}
        super().__init__(message, status_code=404, payload=payload)


class AuthorizationError(APIError):
    """Exception for permission denied (403 Forbidden).

    Use when authenticated user lacks required permissions.
    """

    def __init__(self, message: str = "Permission denied"):
        """Initialize authorization error.

        Args:
            message: Permission error description
        """
        super().__init__(message, status_code=403)


class RateLimitError(APIError):
    """Exception for rate limit exceeded (429 Too Many Requests).

    Includes Retry-After header in response.
    """

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = 60):
        """Initialize rate limit error.

        Args:
            message: Rate limit error description
            retry_after: Seconds until client can retry (default 60)
        """
        payload = {"retry_after": retry_after}
        super().__init__(message, status_code=429, payload=payload)
        self.retry_after = retry_after


class AIServiceError(APIError):
    """Exception for AI service failures (502 Bad Gateway).

    Use when Claude API or other AI services fail.
    """

    def __init__(self, message: str = "AI service temporarily unavailable", original_error: Exception = None):
        """Initialize AI service error.

        Args:
            message: AI error description
            original_error: Optional underlying exception for logging
        """
        payload = {}
        if original_error:
            payload["original_error"] = str(original_error)
        super().__init__(message, status_code=502, payload=payload)
        self.original_error = original_error
