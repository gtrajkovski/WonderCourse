"""Tests for per-user course isolation (AUTH-05).

Verifies that users can only see and access their own courses.
"""

import pytest
import tempfile
import os
from pathlib import Path

from app import app, project_store
from src.auth.db import get_db, init_db
from src.auth.models import User
from src.core.project_store import ProjectStore


@pytest.fixture
def test_app(tmp_path, monkeypatch):
    """Create a Flask app configured for testing with isolated database and projects."""
    from src.auth.routes import init_auth_bp
    from flask import g
    import app as app_module

    db_fd, db_path = tempfile.mkstemp()

    # Create a completely fresh ProjectStore with isolated directory
    fresh_store = ProjectStore(base_dir=tmp_path / "projects")
    (tmp_path / "projects").mkdir(parents=True, exist_ok=True)

    # Replace the module-level project_store in app.py
    original_store = app_module.project_store
    monkeypatch.setattr(app_module, 'project_store', fresh_store)

    # Also patch the local import in this test file
    monkeypatch.setattr('tests.test_user_isolation.project_store', fresh_store)

    app.config.update({
        'TESTING': True,
        'DATABASE': db_path,
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False,
    })

    # Re-init auth blueprint AFTER setting TESTING=True to disable rate limiter
    init_auth_bp(app)

    with app.app_context():
        # Close any existing db connection to ensure fresh connection
        if hasattr(g, 'db'):
            g.db.close()
            delattr(g, 'db')
        init_db()

    yield app

    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(test_app):
    """Create a test client."""
    return test_app.test_client()


@pytest.fixture
def user_b_client(test_app):
    """Create a separate client for user B."""
    return test_app.test_client()


def login_user_a(client, test_app):
    """Helper to register and login user A."""
    # Register user A
    response = client.post('/api/auth/register', json={
        'email': 'user_a@test.com',
        'password': 'password123',
        'name': 'User A'
    })
    assert response.status_code == 201

    # Log in user A
    response = client.post('/api/auth/login', json={
        'email': 'user_a@test.com',
        'password': 'password123'
    })
    assert response.status_code == 200
    return response.get_json()['user']


def login_user_b(user_b_client, test_app):
    """Helper to register and login user B."""
    # Register user B
    response = user_b_client.post('/api/auth/register', json={
        'email': 'user_b@test.com',
        'password': 'password456',
        'name': 'User B'
    })
    assert response.status_code == 201

    # Log in user B
    response = user_b_client.post('/api/auth/login', json={
        'email': 'user_b@test.com',
        'password': 'password456'
    })
    assert response.status_code == 200
    return response.get_json()['user']


class TestUserIsolation:
    """Tests verifying cross-user access is blocked."""

    def test_user_sees_only_own_courses(self, test_app, client, user_b_client):
        """User A's course list doesn't include user B's courses."""
        login_user_a(client, test_app)
        login_user_b(user_b_client, test_app)

        # User A creates a course
        response_a = client.post('/api/courses', json={
            'title': 'User A Course',
            'description': 'Course by User A'
        })
        assert response_a.status_code == 201
        course_a_id = response_a.get_json()['id']

        # User B creates a course
        response_b = user_b_client.post('/api/courses', json={
            'title': 'User B Course',
            'description': 'Course by User B'
        })
        assert response_b.status_code == 201
        course_b_id = response_b.get_json()['id']

        # User A lists courses - should only see own course
        response = client.get('/api/courses')
        assert response.status_code == 200
        data = response.get_json()
        courses = data['courses']
        assert len(courses) == 1
        assert courses[0]['id'] == course_a_id
        assert courses[0]['title'] == 'User A Course'

        # User B lists courses - should only see own course
        response = user_b_client.get('/api/courses')
        assert response.status_code == 200
        data = response.get_json()
        courses = data['courses']
        assert len(courses) == 1
        assert courses[0]['id'] == course_b_id
        assert courses[0]['title'] == 'User B Course'

    def test_user_cannot_get_other_user_course(self, test_app, client, user_b_client):
        """User A cannot GET user B's course by ID."""
        login_user_a(client, test_app)
        login_user_b(user_b_client, test_app)

        # User B creates a course
        response_b = user_b_client.post('/api/courses', json={
            'title': 'User B Course',
            'description': 'Course by User B'
        })
        assert response_b.status_code == 201
        course_b_id = response_b.get_json()['id']

        # User A tries to get User B's course
        response = client.get(f'/api/courses/{course_b_id}')
        assert response.status_code == 404

    def test_user_cannot_update_other_user_course(self, test_app, client, user_b_client):
        """User A cannot PUT to user B's course."""
        login_user_a(client, test_app)
        login_user_b(user_b_client, test_app)

        # User B creates a course
        response_b = user_b_client.post('/api/courses', json={
            'title': 'User B Course',
            'description': 'Course by User B'
        })
        assert response_b.status_code == 201
        course_b_id = response_b.get_json()['id']

        # User A tries to update User B's course
        response = client.put(f'/api/courses/{course_b_id}', json={
            'title': 'Hacked Title'
        })
        assert response.status_code == 404

    def test_user_cannot_delete_other_user_course(self, test_app, client, user_b_client):
        """User A cannot DELETE user B's course."""
        login_user_a(client, test_app)
        login_user_b(user_b_client, test_app)

        # User B creates a course
        response_b = user_b_client.post('/api/courses', json={
            'title': 'User B Course',
            'description': 'Course by User B'
        })
        assert response_b.status_code == 201
        course_b_id = response_b.get_json()['id']

        # User A tries to delete User B's course
        response = client.delete(f'/api/courses/{course_b_id}')
        assert response.status_code == 404

        # Verify course still exists for User B
        response = user_b_client.get(f'/api/courses/{course_b_id}')
        assert response.status_code == 200

    def test_user_cannot_access_other_user_modules(self, test_app, client, user_b_client):
        """User A cannot access modules of user B's course."""
        login_user_a(client, test_app)
        login_user_b(user_b_client, test_app)

        # User B creates a course
        response_b = user_b_client.post('/api/courses', json={
            'title': 'User B Course',
            'description': 'Course by User B'
        })
        assert response_b.status_code == 201
        course_b_id = response_b.get_json()['id']

        # User A tries to list modules of User B's course
        # 403 (forbidden) is correct - user exists but lacks permission
        response = client.get(f'/api/courses/{course_b_id}/modules')
        assert response.status_code == 403


class TestProjectStoreUserScoping:
    """Tests for ProjectStore user-scoped storage."""

    def test_course_stored_in_user_directory(self, tmp_path):
        """Verify file path is projects/{user_id}/{course_id}/."""
        from src.core.models import Course

        tmp_store = ProjectStore(base_dir=tmp_path)
        user_id = "user_123"
        course = Course(title="Test Course", description="Test")

        # Save course
        saved_path = tmp_store.save(user_id, course)

        # Verify directory structure
        expected_path = tmp_store.base_dir / user_id / course.id / "course_data.json"
        assert saved_path == expected_path
        assert expected_path.exists()

    def test_list_courses_only_returns_user_courses(self, tmp_path):
        """list_courses only returns courses for the given user_id."""
        from src.core.models import Course

        tmp_store = ProjectStore(base_dir=tmp_path)

        # Create courses for two users
        course_a = Course(title="Course A", description="User A's course")
        course_b = Course(title="Course B", description="User B's course")

        tmp_store.save("user_a", course_a)
        tmp_store.save("user_b", course_b)

        # List courses for user_a
        courses_a = tmp_store.list_courses("user_a")
        assert len(courses_a) == 1
        assert courses_a[0]['title'] == "Course A"

        # List courses for user_b
        courses_b = tmp_store.list_courses("user_b")
        assert len(courses_b) == 1
        assert courses_b[0]['title'] == "Course B"

    def test_load_requires_correct_user_id(self, tmp_path):
        """load returns None if user_id doesn't match."""
        from src.core.models import Course

        tmp_store = ProjectStore(base_dir=tmp_path)
        course = Course(title="Test Course", description="Test")
        tmp_store.save("user_a", course)

        # User A can load
        loaded = tmp_store.load("user_a", course.id)
        assert loaded is not None
        assert loaded.title == "Test Course"

        # User B cannot load
        loaded = tmp_store.load("user_b", course.id)
        assert loaded is None

    def test_delete_requires_correct_user_id(self, tmp_path):
        """delete returns False if user_id doesn't match."""
        from src.core.models import Course

        tmp_store = ProjectStore(base_dir=tmp_path)
        course = Course(title="Test Course", description="Test")
        tmp_store.save("user_a", course)

        # User B cannot delete
        result = tmp_store.delete("user_b", course.id)
        assert result is False

        # Course still exists for user A
        loaded = tmp_store.load("user_a", course.id)
        assert loaded is not None

        # User A can delete
        result = tmp_store.delete("user_a", course.id)
        assert result is True
