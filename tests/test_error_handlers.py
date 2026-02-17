"""Tests for Flask error handlers."""

import pytest
import logging
from flask import Flask, jsonify
from src.utils.error_handlers import register_error_handlers
from src.api.errors import (
    ValidationError,
    NotFoundError,
    AIServiceError,
    RateLimitError,
    AuthorizationError
)


@pytest.fixture
def test_app():
    """Create test Flask app with error handlers registered."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    register_error_handlers(app)

    # Add test routes that raise exceptions
    @app.route('/validation-error')
    def raise_validation_error():
        raise ValidationError("Invalid input", field="email")

    @app.route('/not-found-error')
    def raise_not_found_error():
        raise NotFoundError("Course", "crs_123")

    @app.route('/ai-service-error')
    def raise_ai_service_error():
        raise AIServiceError("Claude API unavailable")

    @app.route('/rate-limit-error')
    def raise_rate_limit_error():
        raise RateLimitError("Too many requests", retry_after=120)

    @app.route('/authorization-error')
    def raise_authorization_error():
        raise AuthorizationError("Insufficient permissions")

    @app.route('/werkzeug-exception')
    def raise_werkzeug_exception():
        from werkzeug.exceptions import NotFound
        raise NotFound("Page not found")

    @app.route('/unexpected-exception')
    def raise_unexpected_exception():
        raise RuntimeError("Something went wrong")

    return app


@pytest.fixture
def client(test_app):
    """Create test client."""
    return test_app.test_client()


def test_validation_error_returns_400(client):
    """Test ValidationError returns 400 with field information."""
    response = client.get('/validation-error')

    assert response.status_code == 400
    data = response.get_json()
    assert data['error'] == "Invalid input"
    assert data['code'] == 400
    assert data['field'] == "email"


def test_not_found_error_returns_404(client):
    """Test NotFoundError returns 404 with resource info."""
    response = client.get('/not-found-error')

    assert response.status_code == 404
    data = response.get_json()
    assert data['error'] == "Course crs_123 not found"
    assert data['code'] == 404
    assert data['resource_type'] == "Course"
    assert data['resource_id'] == "crs_123"


def test_ai_service_error_returns_502(client):
    """Test AIServiceError returns 502."""
    response = client.get('/ai-service-error')

    assert response.status_code == 502
    data = response.get_json()
    assert data['error'] == "Claude API unavailable"
    assert data['code'] == 502


def test_authorization_error_returns_403(client):
    """Test AuthorizationError returns 403."""
    response = client.get('/authorization-error')

    assert response.status_code == 403
    data = response.get_json()
    assert data['error'] == "Insufficient permissions"
    assert data['code'] == 403


def test_rate_limit_error_includes_retry_after(client):
    """Test RateLimitError includes Retry-After header."""
    response = client.get('/rate-limit-error')

    assert response.status_code == 429
    data = response.get_json()
    assert data['error'] == "Too many requests"
    assert data['code'] == 429
    assert data['retry_after'] == 120
    assert response.headers.get('Retry-After') == '120'


def test_werkzeug_exception_converted_to_json(client):
    """Test Werkzeug exception (abort) returns JSON."""
    response = client.get('/werkzeug-exception')

    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data
    assert data['code'] == 404


def test_unexpected_exception_returns_500(client):
    """Test unexpected exception returns generic 500."""
    response = client.get('/unexpected-exception')

    assert response.status_code == 500
    data = response.get_json()
    assert data['error'] == "Internal server error"
    assert data['code'] == 500


def test_exception_logging_includes_context(test_app, caplog):
    """Test that exceptions log appropriate context."""
    client = test_app.test_client()

    with caplog.at_level(logging.ERROR):
        # Test 5xx error logging
        response = client.get('/ai-service-error')

    assert response.status_code == 502

    # Check that error was logged
    assert len(caplog.records) > 0
    log_record = caplog.records[0]
    assert "Claude API unavailable" in log_record.message
    assert log_record.levelname == "ERROR"


def test_validation_error_not_logged_as_error(test_app, caplog):
    """Test that 4xx errors are not logged at ERROR level."""
    client = test_app.test_client()

    with caplog.at_level(logging.ERROR):
        response = client.get('/validation-error')

    assert response.status_code == 400

    # 4xx errors should not be logged at ERROR level
    error_logs = [r for r in caplog.records if r.levelname == "ERROR"]
    assert len(error_logs) == 0


def test_api_error_to_dict():
    """Test APIError.to_dict() serialization."""
    from src.api.errors import APIError

    error = APIError("Test error", status_code=418, payload={"custom": "data"})
    result = error.to_dict()

    assert result == {
        "error": "Test error",
        "code": 418,
        "custom": "data"
    }


def test_api_error_str_representation():
    """Test APIError.__str__() for logging."""
    from src.api.errors import APIError

    error = APIError("Test error", status_code=500, payload={"detail": "info"})
    error_str = str(error)

    assert "Test error" in error_str
    assert "status=500" in error_str
    assert "payload=" in error_str
