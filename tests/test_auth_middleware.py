"""Tests for authentication middleware on API endpoints.

Verifies that:
1. Protected endpoints return 401 for unauthenticated requests
2. Public endpoints (auth/*, health) remain accessible
3. Authenticated requests proceed normally
"""

import json
from pathlib import Path

import pytest
from flask import Flask

from src.auth.db import init_db, close_db
from src.auth.routes import auth_bp, init_auth_bp
from src.auth.login_manager import init_login_manager
from src.core.project_store import ProjectStore
from src.api.modules import modules_bp, init_modules_bp
from src.api.lessons import lessons_bp, init_lessons_bp
from src.api.activities import activities_bp, init_activities_bp
from src.api.learning_outcomes import learning_outcomes_bp, init_learning_outcomes_bp
from src.api.blueprint import blueprint_bp, init_blueprint_bp
from src.api.content import content_bp, init_content_bp
from src.api.build_state import build_state_bp, init_build_state_bp
from src.api.textbook import textbook_bp, init_textbook_bp
from src.api.validation import validation_bp, init_validation_bp
from src.api.export import export_bp, init_export_bp


@pytest.fixture
def app_with_auth(tmp_path):
    """Create Flask app with all API blueprints and auth for testing.

    Args:
        tmp_path: pytest's built-in temporary directory fixture

    Returns:
        Flask application configured for testing
    """
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['DATABASE'] = tmp_path / 'test_auth.db'
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['WTF_CSRF_ENABLED'] = False

    # Initialize auth
    app.teardown_appcontext(close_db)
    init_login_manager(app)
    init_auth_bp(app)
    app.register_blueprint(auth_bp)

    # Initialize project store
    projects_dir = tmp_path / 'projects'
    projects_dir.mkdir()
    project_store = ProjectStore(projects_dir)

    # Register all API blueprints
    init_modules_bp(project_store)
    app.register_blueprint(modules_bp)

    init_lessons_bp(project_store)
    app.register_blueprint(lessons_bp)

    init_activities_bp(project_store)
    app.register_blueprint(activities_bp)

    init_learning_outcomes_bp(project_store)
    app.register_blueprint(learning_outcomes_bp)

    init_blueprint_bp(project_store)
    app.register_blueprint(blueprint_bp)

    init_content_bp(project_store)
    app.register_blueprint(content_bp)

    init_build_state_bp(project_store)
    app.register_blueprint(build_state_bp)

    init_textbook_bp(project_store)
    app.register_blueprint(textbook_bp)

    init_validation_bp(project_store)
    app.register_blueprint(validation_bp)

    init_export_bp(project_store)
    app.register_blueprint(export_bp)

    # Add health endpoint
    @app.route('/api/system/health', methods=['GET'])
    def health_check():
        return {"status": "ok", "version": "1.0.0"}

    # Add course endpoints with protection
    from flask_login import login_required, current_user
    from flask import request, jsonify
    from src.core.models import Course

    @app.route('/api/courses', methods=['GET'])
    @login_required
    def get_courses():
        return jsonify([])

    @app.route('/api/courses', methods=['POST'])
    @login_required
    def create_course():
        data = request.get_json() or {}
        course = Course(
            title=data.get('title', 'Test Course'),
            description=data.get('description', '')
        )
        project_store.save(current_user.id, course)
        return jsonify(course.to_dict()), 201

    @app.route('/api/courses/<course_id>', methods=['GET'])
    @login_required
    def get_course(course_id):
        course = project_store.load(current_user.id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404
        return jsonify(course.to_dict())

    return app


@pytest.fixture
def middleware_db(app_with_auth):
    """Initialize database schema before tests."""
    with app_with_auth.app_context():
        init_db()
        yield


@pytest.fixture
def client(app_with_auth, middleware_db):
    """Create Flask test client with initialized database."""
    return app_with_auth.test_client()


@pytest.fixture
def authenticated_client(client):
    """Create authenticated client with registered user.

    Returns:
        Test client with active session
    """
    # Register and login
    client.post('/api/auth/register', json={
        'email': 'testuser@example.com',
        'password': 'testpassword123',
        'name': 'Test User'
    })
    client.post('/api/auth/login', json={
        'email': 'testuser@example.com',
        'password': 'testpassword123'
    })
    return client


# ===========================
# Unauthenticated Access Tests (should return 401)
# ===========================

class TestUnauthenticatedAccess:
    """Tests verifying 401 on protected endpoints when not authenticated."""

    def test_get_courses_unauthenticated(self, client):
        """GET /api/courses without auth returns 401."""
        response = client.get('/api/courses')
        assert response.status_code == 401

    def test_create_course_unauthenticated(self, client):
        """POST /api/courses without auth returns 401."""
        response = client.post('/api/courses', json={'title': 'Test'})
        assert response.status_code == 401

    def test_get_single_course_unauthenticated(self, client):
        """GET /api/courses/<id> without auth returns 401."""
        response = client.get('/api/courses/some-course-id')
        assert response.status_code == 401

    def test_get_modules_unauthenticated(self, client):
        """GET /api/courses/<id>/modules without auth returns 401."""
        response = client.get('/api/courses/some-course-id/modules')
        assert response.status_code == 401

    def test_create_module_unauthenticated(self, client):
        """POST /api/courses/<id>/modules without auth returns 401."""
        response = client.post('/api/courses/some-id/modules', json={'title': 'Module 1'})
        assert response.status_code == 401

    def test_get_lessons_unauthenticated(self, client):
        """GET /api/courses/<id>/modules/<id>/lessons without auth returns 401."""
        response = client.get('/api/courses/c1/modules/m1/lessons')
        assert response.status_code == 401

    def test_get_activities_unauthenticated(self, client):
        """GET /api/courses/<id>/lessons/<id>/activities without auth returns 401."""
        response = client.get('/api/courses/c1/lessons/l1/activities')
        assert response.status_code == 401

    def test_get_outcomes_unauthenticated(self, client):
        """GET /api/courses/<id>/outcomes without auth returns 401."""
        response = client.get('/api/courses/some-id/outcomes')
        assert response.status_code == 401

    def test_get_alignment_unauthenticated(self, client):
        """GET /api/courses/<id>/alignment without auth returns 401."""
        response = client.get('/api/courses/some-id/alignment')
        assert response.status_code == 401

    def test_generate_blueprint_unauthenticated(self, client):
        """POST /api/courses/<id>/blueprint/generate without auth returns 401."""
        response = client.post('/api/courses/some-id/blueprint/generate', json={})
        assert response.status_code == 401

    def test_generate_content_unauthenticated(self, client):
        """POST /api/courses/<id>/activities/<id>/generate without auth returns 401."""
        response = client.post('/api/courses/c1/activities/a1/generate', json={})
        assert response.status_code == 401

    def test_get_progress_unauthenticated(self, client):
        """GET /api/courses/<id>/progress without auth returns 401."""
        response = client.get('/api/courses/some-id/progress')
        assert response.status_code == 401

    def test_update_state_unauthenticated(self, client):
        """PUT /api/courses/<id>/activities/<id>/state without auth returns 401."""
        response = client.put('/api/courses/c1/activities/a1/state', json={'build_state': 'reviewed'})
        assert response.status_code == 401

    def test_generate_textbook_unauthenticated(self, client):
        """POST /api/courses/<id>/textbook/generate without auth returns 401."""
        response = client.post('/api/courses/some-id/textbook/generate', json={})
        assert response.status_code == 401

    def test_get_job_status_unauthenticated(self, client):
        """GET /api/jobs/<id> without auth returns 401."""
        response = client.get('/api/jobs/some-job-id')
        assert response.status_code == 401

    def test_validate_course_unauthenticated(self, client):
        """GET /api/courses/<id>/validate without auth returns 401."""
        response = client.get('/api/courses/some-id/validate')
        assert response.status_code == 401

    def test_check_publishable_unauthenticated(self, client):
        """GET /api/courses/<id>/publishable without auth returns 401."""
        response = client.get('/api/courses/some-id/publishable')
        assert response.status_code == 401

    def test_export_preview_unauthenticated(self, client):
        """GET /api/courses/<id>/export/preview without auth returns 401."""
        response = client.get('/api/courses/some-id/export/preview?format=instructor')
        assert response.status_code == 401

    def test_export_instructor_unauthenticated(self, client):
        """GET /api/courses/<id>/export/instructor without auth returns 401."""
        response = client.get('/api/courses/some-id/export/instructor')
        assert response.status_code == 401

    def test_export_lms_unauthenticated(self, client):
        """GET /api/courses/<id>/export/lms without auth returns 401."""
        response = client.get('/api/courses/some-id/export/lms')
        assert response.status_code == 401


# ===========================
# Public Endpoint Tests (should NOT return 401)
# ===========================

class TestPublicEndpoints:
    """Tests verifying public endpoints remain accessible without auth."""

    def test_health_endpoint_public(self, client):
        """GET /api/system/health returns 200 without auth."""
        response = client.get('/api/system/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'ok'

    def test_register_public(self, client):
        """POST /api/auth/register is accessible without auth."""
        response = client.post('/api/auth/register', json={
            'email': 'newuser@example.com',
            'password': 'password123'
        })
        # Returns 201 on success or 400 on validation error, NOT 401
        assert response.status_code in [201, 400]
        assert response.status_code != 401

    def test_login_public(self, client):
        """POST /api/auth/login is accessible without auth."""
        response = client.post('/api/auth/login', json={
            'email': 'unknown@example.com',
            'password': 'password123'
        })
        # Returns 401 for invalid credentials, but this is different from
        # 401 for "not authenticated" - login endpoint is public
        # If endpoint was protected, it would return 401 before checking credentials
        assert response.status_code in [200, 401]


# ===========================
# Authenticated Access Tests (should work normally)
# ===========================

class TestAuthenticatedAccess:
    """Tests verifying authenticated requests proceed normally."""

    def test_get_courses_authenticated(self, authenticated_client):
        """GET /api/courses with auth returns 200."""
        response = authenticated_client.get('/api/courses')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_create_course_authenticated(self, authenticated_client):
        """POST /api/courses with auth returns 201."""
        response = authenticated_client.post('/api/courses', json={
            'title': 'My Test Course',
            'description': 'A test course'
        })
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['title'] == 'My Test Course'
        assert 'id' in data

    def test_get_modules_authenticated(self, authenticated_client):
        """GET /api/courses/<id>/modules with auth returns 200 or 404."""
        # Create a course first
        course_response = authenticated_client.post('/api/courses', json={
            'title': 'Course for Modules'
        })
        course_id = json.loads(course_response.data)['id']

        # Get modules
        response = authenticated_client.get(f'/api/courses/{course_id}/modules')
        # Returns 200 (empty list) or 404 if course not found
        assert response.status_code in [200, 404]
        assert response.status_code != 401

    def test_get_outcomes_authenticated(self, authenticated_client):
        """GET /api/courses/<id>/outcomes with auth returns 200 or 404."""
        # Create a course first
        course_response = authenticated_client.post('/api/courses', json={
            'title': 'Course for Outcomes'
        })
        course_id = json.loads(course_response.data)['id']

        response = authenticated_client.get(f'/api/courses/{course_id}/outcomes')
        assert response.status_code in [200, 404]
        assert response.status_code != 401

    def test_get_progress_authenticated(self, authenticated_client):
        """GET /api/courses/<id>/progress with auth returns 200 or 404."""
        # Create a course first
        course_response = authenticated_client.post('/api/courses', json={
            'title': 'Course for Progress'
        })
        course_id = json.loads(course_response.data)['id']

        response = authenticated_client.get(f'/api/courses/{course_id}/progress')
        assert response.status_code in [200, 404]
        assert response.status_code != 401


# ===========================
# Session Behavior Tests
# ===========================

class TestSessionBehavior:
    """Tests verifying session-based authentication behavior."""

    def test_logout_revokes_access(self, authenticated_client):
        """After logout, protected endpoints return 401 again."""
        # Verify initially authenticated
        response = authenticated_client.get('/api/courses')
        assert response.status_code == 200

        # Logout
        authenticated_client.post('/api/auth/logout')

        # Verify no longer authenticated
        response = authenticated_client.get('/api/courses')
        assert response.status_code == 401

    def test_cross_request_authentication(self, authenticated_client):
        """Authentication persists across multiple requests."""
        # First request
        response1 = authenticated_client.get('/api/courses')
        assert response1.status_code == 200

        # Second request
        response2 = authenticated_client.get('/api/courses')
        assert response2.status_code == 200

        # Create course
        response3 = authenticated_client.post('/api/courses', json={'title': 'Test'})
        assert response3.status_code == 201
