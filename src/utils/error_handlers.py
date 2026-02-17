"""Flask error handler registration.

Registers global error handlers for consistent JSON error responses
across all API endpoints.
"""

import logging
import traceback
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException
from src.api.errors import APIError, RateLimitError

logger = logging.getLogger(__name__)


def register_error_handlers(app: Flask) -> None:
    """Register global error handlers with Flask app.

    Converts all exceptions to JSON responses with consistent structure:
    {"error": message, "code": status_code}

    Args:
        app: Flask application instance
    """

    @app.errorhandler(APIError)
    def handle_api_error(error: APIError):
        """Handle custom API exceptions.

        Converts APIError subclasses (ValidationError, NotFoundError, etc.)
        to JSON responses with appropriate status codes.
        """
        # Log 5xx errors with full context
        if error.status_code >= 500:
            logger.error(
                f"API error: {error.message}",
                extra={
                    "status_code": error.status_code,
                    "path": request.path,
                    "method": request.method,
                    "user_id": getattr(request, "user_id", None),
                    "payload": error.payload
                }
            )

        response = jsonify(error.to_dict())
        response.status_code = error.status_code

        # Add Retry-After header for rate limit errors
        if isinstance(error, RateLimitError):
            response.headers["Retry-After"] = str(error.retry_after)

        return response

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        """Handle Werkzeug HTTP exceptions (abort(404), etc.).

        Converts Flask's built-in HTTP exceptions to JSON format
        for API consistency.
        """
        # Log 5xx errors
        if error.code >= 500:
            logger.error(
                f"HTTP exception: {error.description}",
                extra={
                    "status_code": error.code,
                    "path": request.path,
                    "method": request.method
                }
            )

        response = jsonify({
            "error": error.description or error.name,
            "code": error.code
        })
        response.status_code = error.code
        return response

    @app.errorhandler(Exception)
    def handle_unexpected_exception(error: Exception):
        """Handle all unexpected exceptions.

        Catches any exception not handled by specific handlers,
        logs full traceback, and returns generic 500 error.

        IMPORTANT: This prevents sensitive error details from
        leaking to clients.
        """
        # Log full traceback for debugging
        logger.error(
            f"Unexpected exception: {str(error)}",
            extra={
                "path": request.path,
                "method": request.method,
                "user_id": getattr(request, "user_id", None),
                "traceback": traceback.format_exc()
            }
        )

        # Return generic error to client
        response = jsonify({
            "error": "Internal server error",
            "code": 500
        })
        response.status_code = 500
        return response
