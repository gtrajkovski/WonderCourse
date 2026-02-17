"""Tests for User model and database operations."""

import sqlite3
from pathlib import Path

import pytest
from flask import Flask

from src.auth.models import User
from src.auth.db import get_db, init_db, close_db


@pytest.fixture
def test_app(tmp_path):
    """Create Flask app with test config using temporary database.

    Args:
        tmp_path: pytest's built-in temporary directory fixture

    Returns:
        Flask application configured for testing
    """
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['DATABASE'] = tmp_path / 'test_users.db'
    app.config['SECRET_KEY'] = 'test-secret-key'

    # Register teardown
    app.teardown_appcontext(close_db)

    return app


@pytest.fixture
def test_db(test_app, tmp_path):
    """Initialize database schema before each test.

    Args:
        test_app: Flask test application fixture
        tmp_path: pytest's built-in temporary directory fixture

    Yields:
        Database connection
    """
    # Create schema.sql in expected location for init_db
    instance_dir = Path(__file__).parent.parent / 'instance'
    instance_dir.mkdir(exist_ok=True)

    with test_app.app_context():
        init_db()
        yield get_db()


class TestUserCreate:
    """Tests for User creation."""

    def test_user_create(self, test_app, test_db):
        """Create user with email, password, name; verify stored with hashed password."""
        with test_app.app_context():
            user = User.create(
                email='test@example.com',
                password='secret123',
                name='Test User'
            )

            assert user is not None
            assert user.email == 'test@example.com'
            assert user.name == 'Test User'
            assert user.id is not None
            # Password should be hashed, not plain text
            assert user.password_hash != 'secret123'
            assert user.password_hash.startswith('scrypt:')

    def test_user_create_without_name(self, test_app, test_db):
        """Create user without name (optional field)."""
        with test_app.app_context():
            user = User.create(
                email='noname@example.com',
                password='secret123'
            )

            assert user is not None
            assert user.email == 'noname@example.com'
            assert user.name is None


class TestPasswordHashing:
    """Tests for password hashing functionality."""

    def test_password_hashing(self, test_app, test_db):
        """Password is not stored as plain text; verify with check_password."""
        with test_app.app_context():
            user = User.create(
                email='hash@example.com',
                password='mypassword123'
            )

            # Password hash should not equal plain password
            assert user.password_hash != 'mypassword123'
            # Should be a werkzeug scrypt hash
            assert 'scrypt' in user.password_hash

    def test_check_password_correct(self, test_app, test_db):
        """Correct password returns True."""
        with test_app.app_context():
            user = User.create(
                email='correct@example.com',
                password='correctpass'
            )

            assert user.check_password('correctpass') is True

    def test_check_password_wrong(self, test_app, test_db):
        """Wrong password returns False."""
        with test_app.app_context():
            user = User.create(
                email='wrong@example.com',
                password='rightpassword'
            )

            assert user.check_password('wrongpassword') is False

    def test_set_password(self, test_app, test_db):
        """set_password updates the password hash."""
        with test_app.app_context():
            user = User.create(
                email='setpass@example.com',
                password='oldpassword'
            )

            old_hash = user.password_hash
            user.set_password('newpassword')

            # Hash should change
            assert user.password_hash != old_hash
            # New password should work
            assert user.check_password('newpassword') is True
            # Old password should not work
            assert user.check_password('oldpassword') is False


class TestUserRetrieval:
    """Tests for user retrieval methods."""

    def test_get_by_id(self, test_app, test_db):
        """Retrieve user by ID."""
        with test_app.app_context():
            created = User.create(
                email='getbyid@example.com',
                password='pass123',
                name='Get By ID'
            )

            retrieved = User.get_by_id(created.id)

            assert retrieved is not None
            assert retrieved.id == created.id
            assert retrieved.email == 'getbyid@example.com'
            assert retrieved.name == 'Get By ID'

    def test_get_by_id_not_found(self, test_app, test_db):
        """Return None for non-existent ID."""
        with test_app.app_context():
            result = User.get_by_id(99999)

            assert result is None

    def test_get_by_email(self, test_app, test_db):
        """Retrieve user by email."""
        with test_app.app_context():
            created = User.create(
                email='getbyemail@example.com',
                password='pass123',
                name='Get By Email'
            )

            retrieved = User.get_by_email('getbyemail@example.com')

            assert retrieved is not None
            assert retrieved.id == created.id
            assert retrieved.email == 'getbyemail@example.com'

    def test_get_by_email_not_found(self, test_app, test_db):
        """Return None for non-existent email."""
        with test_app.app_context():
            result = User.get_by_email('nonexistent@example.com')

            assert result is None


class TestUserSerialization:
    """Tests for user serialization."""

    def test_user_to_dict(self, test_app, test_db):
        """to_dict excludes password_hash."""
        with test_app.app_context():
            user = User.create(
                email='todict@example.com',
                password='secret',
                name='To Dict User'
            )

            user_dict = user.to_dict()

            assert 'id' in user_dict
            assert 'email' in user_dict
            assert 'name' in user_dict
            assert 'created_at' in user_dict
            # Security: password_hash should NOT be in dict
            assert 'password_hash' not in user_dict
            assert 'password' not in user_dict

    def test_to_dict_values(self, test_app, test_db):
        """to_dict returns correct values."""
        with test_app.app_context():
            user = User.create(
                email='values@example.com',
                password='secret',
                name='Values User'
            )

            user_dict = user.to_dict()

            assert user_dict['email'] == 'values@example.com'
            assert user_dict['name'] == 'Values User'
            assert user_dict['id'] == user.id


class TestUserConstraints:
    """Tests for database constraints."""

    def test_duplicate_email(self, test_app, test_db):
        """Creating user with duplicate email raises error."""
        with test_app.app_context():
            User.create(
                email='duplicate@example.com',
                password='pass1'
            )

            with pytest.raises(sqlite3.IntegrityError):
                User.create(
                    email='duplicate@example.com',
                    password='pass2'
                )


class TestFlaskLoginCompatibility:
    """Tests for Flask-Login integration."""

    def test_get_id_returns_string(self, test_app, test_db):
        """Flask-Login requires string ID."""
        with test_app.app_context():
            user = User.create(
                email='stringid@example.com',
                password='pass123'
            )

            user_id = user.get_id()

            assert isinstance(user_id, str)
            assert user_id == str(user.id)

    def test_get_by_id_accepts_string(self, test_app, test_db):
        """get_by_id should work with string IDs from Flask-Login."""
        with test_app.app_context():
            user = User.create(
                email='stringlookup@example.com',
                password='pass123'
            )

            # Flask-Login passes string IDs
            retrieved = User.get_by_id(str(user.id))

            assert retrieved is not None
            assert retrieved.id == user.id

    def test_is_authenticated(self, test_app, test_db):
        """UserMixin provides is_authenticated property."""
        with test_app.app_context():
            user = User.create(
                email='auth@example.com',
                password='pass123'
            )

            # UserMixin provides this
            assert user.is_authenticated is True

    def test_is_active(self, test_app, test_db):
        """UserMixin provides is_active property."""
        with test_app.app_context():
            user = User.create(
                email='active@example.com',
                password='pass123'
            )

            # UserMixin provides this
            assert user.is_active is True
