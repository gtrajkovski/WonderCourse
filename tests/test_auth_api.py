"""Tests for auth API endpoints (register, login, logout, me)."""

import json
from pathlib import Path

import pytest
from flask import Flask

from src.auth.models import User
from src.auth.db import get_db, init_db, close_db
from src.auth.routes import auth_bp, init_auth_bp
from src.auth.login_manager import init_login_manager


@pytest.fixture
def auth_app(tmp_path):
    """Create Flask app with auth blueprint for testing.

    Args:
        tmp_path: pytest's built-in temporary directory fixture

    Returns:
        Flask application configured for testing
    """
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['DATABASE'] = tmp_path / 'test_auth.db'
    app.config['SECRET_KEY'] = 'test-secret-key'
    # Disable CSRF for testing
    app.config['WTF_CSRF_ENABLED'] = False

    # Register teardown
    app.teardown_appcontext(close_db)

    # Initialize auth components
    init_login_manager(app)
    init_auth_bp(app)

    # Register auth blueprint
    app.register_blueprint(auth_bp)

    return app


@pytest.fixture
def auth_db(auth_app, tmp_path):
    """Initialize database schema before tests.

    Args:
        auth_app: Flask test application fixture
        tmp_path: pytest's built-in temporary directory fixture

    Yields:
        Database connection
    """
    # Ensure schema.sql exists
    instance_dir = Path(__file__).parent.parent / 'instance'
    instance_dir.mkdir(exist_ok=True)

    with auth_app.app_context():
        init_db()
        yield get_db()


@pytest.fixture
def client(auth_app, auth_db):
    """Create Flask test client with initialized database.

    Args:
        auth_app: Flask test application
        auth_db: Initialized database

    Returns:
        Flask test client
    """
    return auth_app.test_client()


# ===========================
# Registration Tests
# ===========================

class TestRegistration:
    """Tests for POST /api/auth/register endpoint."""

    def test_register_success(self, client):
        """Valid email and password returns 201 with user data."""
        response = client.post('/api/auth/register', json={
            'email': 'newuser@example.com',
            'password': 'securepassword123'
        })

        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'message' in data
        assert data['message'] == 'User registered successfully'
        assert 'user' in data
        assert data['user']['email'] == 'newuser@example.com'
        assert 'id' in data['user']
        # Password should not be in response
        assert 'password' not in data['user']
        assert 'password_hash' not in data['user']

    def test_register_with_name(self, client):
        """Registration with optional name includes name in response."""
        response = client.post('/api/auth/register', json={
            'email': 'named@example.com',
            'password': 'securepassword123',
            'name': 'John Doe'
        })

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['user']['name'] == 'John Doe'

    def test_register_missing_email(self, client):
        """Missing email returns 400."""
        response = client.post('/api/auth/register', json={
            'password': 'securepassword123'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'email' in data['error'].lower()

    def test_register_missing_password(self, client):
        """Missing password returns 400."""
        response = client.post('/api/auth/register', json={
            'email': 'nopass@example.com'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'password' in data['error'].lower()

    def test_register_duplicate_email(self, client):
        """Duplicate email returns 400."""
        # Register first user
        client.post('/api/auth/register', json={
            'email': 'duplicate@example.com',
            'password': 'password1'
        })

        # Attempt to register with same email
        response = client.post('/api/auth/register', json={
            'email': 'duplicate@example.com',
            'password': 'password2'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'already' in data['error'].lower() or 'email' in data['error'].lower()

    def test_register_invalid_email_format(self, client):
        """Invalid email format returns 400."""
        response = client.post('/api/auth/register', json={
            'email': 'not-an-email',
            'password': 'securepassword123'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_register_no_json_body(self, client):
        """Request without JSON body returns 400."""
        response = client.post('/api/auth/register')

        assert response.status_code in [400, 415]


# ===========================
# Login Tests
# ===========================

class TestLogin:
    """Tests for POST /api/auth/login endpoint."""

    def test_login_success(self, client):
        """Valid credentials return 200 with user data and set session cookie."""
        # Register user first
        client.post('/api/auth/register', json={
            'email': 'login@example.com',
            'password': 'correctpassword'
        })

        # Login
        response = client.post('/api/auth/login', json={
            'email': 'login@example.com',
            'password': 'correctpassword'
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data
        assert data['message'] == 'Logged in successfully'
        assert 'user' in data
        assert data['user']['email'] == 'login@example.com'

    def test_login_wrong_password(self, client):
        """Wrong password returns 401 with generic error."""
        # Register user
        client.post('/api/auth/register', json={
            'email': 'wrongpass@example.com',
            'password': 'correctpassword'
        })

        # Login with wrong password
        response = client.post('/api/auth/login', json={
            'email': 'wrongpass@example.com',
            'password': 'wrongpassword'
        })

        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['error'] == 'Invalid credentials'

    def test_login_unknown_email(self, client):
        """Unknown email returns 401 with same error as wrong password."""
        response = client.post('/api/auth/login', json={
            'email': 'nonexistent@example.com',
            'password': 'anypassword'
        })

        assert response.status_code == 401
        data = json.loads(response.data)
        # IMPORTANT: Same error as wrong password to prevent user enumeration
        assert data['error'] == 'Invalid credentials'

    def test_login_missing_email(self, client):
        """Missing email returns 400."""
        response = client.post('/api/auth/login', json={
            'password': 'somepassword'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_login_missing_password(self, client):
        """Missing password returns 400."""
        response = client.post('/api/auth/login', json={
            'email': 'user@example.com'
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_login_remember_me(self, client):
        """Login with remember=True sets longer session."""
        # Register user
        client.post('/api/auth/register', json={
            'email': 'remember@example.com',
            'password': 'password123'
        })

        # Login with remember
        response = client.post('/api/auth/login', json={
            'email': 'remember@example.com',
            'password': 'password123',
            'remember': True
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['user']['email'] == 'remember@example.com'

    def test_login_no_json_body(self, client):
        """Request without JSON body returns 400."""
        response = client.post('/api/auth/login')

        assert response.status_code in [400, 415]


# ===========================
# Logout Tests
# ===========================

class TestLogout:
    """Tests for POST /api/auth/logout endpoint."""

    def test_logout_success(self, client):
        """Logged-in user can logout successfully."""
        # Register and login
        client.post('/api/auth/register', json={
            'email': 'logout@example.com',
            'password': 'password123'
        })
        client.post('/api/auth/login', json={
            'email': 'logout@example.com',
            'password': 'password123'
        })

        # Logout
        response = client.post('/api/auth/logout')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data
        assert 'logged out' in data['message'].lower()

    def test_logout_unauthenticated(self, client):
        """Unauthenticated user cannot logout (returns 401)."""
        response = client.post('/api/auth/logout')

        assert response.status_code == 401


# ===========================
# Me Endpoint Tests
# ===========================

class TestMe:
    """Tests for GET /api/auth/me endpoint."""

    def test_me_authenticated(self, client):
        """Authenticated user gets their data."""
        # Register and login
        client.post('/api/auth/register', json={
            'email': 'me@example.com',
            'password': 'password123',
            'name': 'Me User'
        })
        client.post('/api/auth/login', json={
            'email': 'me@example.com',
            'password': 'password123'
        })

        # Get current user
        response = client.get('/api/auth/me')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['email'] == 'me@example.com'
        assert data['name'] == 'Me User'
        assert 'id' in data
        assert 'created_at' in data
        # Password should not be exposed
        assert 'password' not in data
        assert 'password_hash' not in data

    def test_me_unauthenticated(self, client):
        """Unauthenticated user gets 401."""
        response = client.get('/api/auth/me')

        assert response.status_code == 401


# ===========================
# Session Persistence Tests
# ===========================

class TestSessionPersistence:
    """Tests for session behavior across requests."""

    def test_session_persists(self, client):
        """After login, subsequent requests are authenticated."""
        # Register and login
        client.post('/api/auth/register', json={
            'email': 'session@example.com',
            'password': 'password123'
        })
        client.post('/api/auth/login', json={
            'email': 'session@example.com',
            'password': 'password123'
        })

        # Verify session persists across requests
        response = client.get('/api/auth/me')
        assert response.status_code == 200

        # Make another request
        response2 = client.get('/api/auth/me')
        assert response2.status_code == 200

    def test_session_cleared_after_logout(self, client):
        """After logout, me endpoint returns 401."""
        # Register, login, then logout
        client.post('/api/auth/register', json={
            'email': 'cleared@example.com',
            'password': 'password123'
        })
        client.post('/api/auth/login', json={
            'email': 'cleared@example.com',
            'password': 'password123'
        })

        # Verify logged in
        me_response = client.get('/api/auth/me')
        assert me_response.status_code == 200

        # Logout
        client.post('/api/auth/logout')

        # Verify logged out
        response = client.get('/api/auth/me')
        assert response.status_code == 401

    def test_multiple_logins(self, client):
        """User can login, logout, and login again."""
        # Register
        client.post('/api/auth/register', json={
            'email': 'multi@example.com',
            'password': 'password123'
        })

        # First login
        response1 = client.post('/api/auth/login', json={
            'email': 'multi@example.com',
            'password': 'password123'
        })
        assert response1.status_code == 200

        # Logout
        client.post('/api/auth/logout')

        # Second login
        response2 = client.post('/api/auth/login', json={
            'email': 'multi@example.com',
            'password': 'password123'
        })
        assert response2.status_code == 200

        # Verify authenticated
        me_response = client.get('/api/auth/me')
        assert me_response.status_code == 200
