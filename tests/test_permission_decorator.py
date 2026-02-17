"""Tests for permission enforcement decorators.

Tests verify that decorators correctly enforce permission checks on routes,
handle missing permissions, and integrate with the permission system.
"""

import pytest
from flask import Flask, jsonify
from flask_login import login_user, logout_user
from src.auth.models import User
from src.auth.db import init_db, get_db
from src.auth.login_manager import login_manager, init_login_manager
from src.collab.models import Role, Collaborator
from src.collab.permissions import seed_permissions
from src.collab.decorators import (
    require_permission,
    require_any_permission,
    require_collaborator,
    ensure_owner_collaborator,
)


@pytest.fixture
def test_app(tmp_path):
    """Create Flask app with test configuration."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    # Use temp file instead of :memory: so all connections share same database
    db_file = tmp_path / "test.db"
    app.config['DATABASE'] = str(db_file)
    app.config['LOGIN_DISABLED'] = False

    # Initialize database
    with app.app_context():
        init_db()
        db = get_db()
        seed_permissions(db)

    # Initialize login manager
    init_login_manager(app)

    # Override unauthorized handler to treat /test/ routes as API routes
    @login_manager.unauthorized_handler
    def unauthorized():
        return jsonify({"error": "Unauthorized"}), 401

    # Create test routes
    from flask_login import login_required

    @app.route('/test/courses/<course_id>/protected')
    @login_required
    @require_permission('edit_content')
    def protected_route(course_id):
        return jsonify({"status": "ok"})

    @app.route('/test/courses/<course_id>/multi-perm')
    @login_required
    @require_any_permission('edit_content', 'approve_content')
    def multi_perm_route(course_id):
        return jsonify({"status": "ok"})

    @app.route('/test/courses/<course_id>/collab-only')
    @login_required
    @require_collaborator()
    def collab_only_route(course_id):
        return jsonify({"status": "ok"})

    @app.route('/test/no-course-id')
    @login_required
    @require_permission('edit_content')
    def no_course_id_route():
        return jsonify({"status": "ok"})

    return app


@pytest.fixture
def test_db(test_app):
    """Provide fresh database for each test."""
    with test_app.app_context():
        db = get_db()
        # Clear all tables - use DELETE OR IGNORE in case tables don't exist yet
        try:
            db.execute("DELETE FROM collaborator")
            db.execute("DELETE FROM role_permission")
            db.execute("DELETE FROM course_role")
            db.execute("DELETE FROM user")
            db.commit()
        except Exception:
            # Tables might not exist yet, that's OK
            db.rollback()
        yield db


@pytest.fixture
def test_user(test_app, test_db):
    """Create test user."""
    with test_app.app_context():
        user = User.create(
            email="test@example.com",
            password="password123",
            name="Test User"
        )
        yield user


@pytest.fixture
def test_course():
    """Provide test course ID."""
    return "course_123"


@pytest.fixture
def test_owner_role(test_app, test_db, test_course):
    """Create Owner role for test course."""
    with test_app.app_context():
        role = Role.create_from_template(test_course, "Owner")
        yield role


@pytest.fixture
def test_collaborator(test_app, test_db, test_user, test_course, test_owner_role):
    """Create collaborator relationship."""
    with test_app.app_context():
        collaborator = Collaborator.create(
            test_course,
            test_user.id,
            test_owner_role.id,
            invited_by=test_user.id
        )
        yield collaborator


def test_require_permission_allows_with_permission(test_app, test_user, test_course, test_collaborator):
    """Test that decorator allows access when user has required permission."""
    with test_app.test_client() as client:
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)

        response = client.get(f'/test/courses/{test_course}/protected')
        assert response.status_code == 200
        assert response.json == {"status": "ok"}


def test_require_permission_denies_without_permission(test_app, test_user, test_course, test_db):
    """Test that decorator denies access when user lacks permission."""
    with test_app.app_context():
        # Create an admin user who is the Owner (so course is "found")
        admin_user = User.create(
            email="admin@example.com",
            password="adminpass",
            name="Admin User"
        )
        owner_role = Role.create_from_template(test_course, "Owner")
        Collaborator.create(test_course, admin_user.id, owner_role.id, invited_by=admin_user.id)

        # Create role without edit_content permission (Reviewer only has view/approve/export)
        reviewer_role = Role.create_from_template(test_course, "Reviewer")
        Collaborator.create(test_course, test_user.id, reviewer_role.id, invited_by=admin_user.id)

    with test_app.test_client() as client:
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)

        response = client.get(f'/test/courses/{test_course}/protected')
        assert response.status_code == 403
        assert response.json == {"error": "Permission denied"}


def test_require_permission_returns_400_no_course_id(test_app, test_user):
    """Test that decorator returns 400 when course_id missing from route."""
    with test_app.test_client() as client:
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)

        response = client.get('/test/no-course-id')
        assert response.status_code == 400
        assert response.json == {"error": "course_id not found in route"}


def test_require_permission_requires_login(test_app, test_course):
    """Test that decorator requires authentication."""
    with test_app.test_client() as client:
        response = client.get(f'/test/courses/{test_course}/protected')
        # Flask-Login returns 401 for API routes (our test routes are under /test/...)
        assert response.status_code == 401
        assert response.json == {"error": "Unauthorized"}


def test_require_any_permission_one_of_many(test_app, test_user, test_course, test_db):
    """Test that require_any_permission passes with any matching permission."""
    # Create Reviewer role (has approve_content but not edit_content)
    with test_app.app_context():
        reviewer_role = Role.create_from_template(test_course, "Reviewer")
        Collaborator.create(test_course, test_user.id, reviewer_role.id, invited_by=test_user.id)

    with test_app.test_client() as client:
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)

        response = client.get(f'/test/courses/{test_course}/multi-perm')
        assert response.status_code == 200
        assert response.json == {"status": "ok"}


def test_require_any_permission_none_match(test_app, test_user, test_course, test_db):
    """Test that require_any_permission fails when none match."""
    # Create SME role (only has view_content and export_course)
    with test_app.app_context():
        sme_role = Role.create_from_template(test_course, "SME")
        Collaborator.create(test_course, test_user.id, sme_role.id, invited_by=test_user.id)

    with test_app.test_client() as client:
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)

        response = client.get(f'/test/courses/{test_course}/multi-perm')
        assert response.status_code == 403
        assert response.json == {"error": "Permission denied"}


def test_require_collaborator_allows_any_role(test_app, test_user, test_course, test_db):
    """Test that require_collaborator allows any collaborator regardless of permissions."""
    # Create SME role (minimal permissions)
    with test_app.app_context():
        sme_role = Role.create_from_template(test_course, "SME")
        Collaborator.create(test_course, test_user.id, sme_role.id, invited_by=test_user.id)

    with test_app.test_client() as client:
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)

        response = client.get(f'/test/courses/{test_course}/collab-only')
        assert response.status_code == 200
        assert response.json == {"status": "ok"}


def test_require_collaborator_denies_non_collaborator(test_app, test_user, test_course):
    """Test that require_collaborator denies non-collaborators."""
    with test_app.test_client() as client:
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)

        response = client.get(f'/test/courses/{test_course}/collab-only')
        assert response.status_code == 403
        assert response.json == {"error": "Permission denied"}


def test_ensure_owner_creates_role_and_collaborator(test_app, test_db, test_user):
    """Test that ensure_owner_collaborator creates Owner role and collaborator for new course."""
    course_id = "new_course_123"

    with test_app.app_context():
        # Verify no role or collaborator exists
        roles = Role.get_for_course(course_id)
        assert len(roles) == 0

        collaborator = Collaborator.get_by_user_and_course(test_user.id, course_id)
        assert collaborator is None

        # Call ensure_owner_collaborator
        result = ensure_owner_collaborator(course_id, test_user.id)

        # Verify Owner role created
        roles = Role.get_for_course(course_id)
        assert len(roles) == 1
        assert roles[0].name == "Owner"

        # Verify collaborator created
        collaborator = Collaborator.get_by_user_and_course(test_user.id, course_id)
        assert collaborator is not None
        assert collaborator.role_name == "Owner"
        assert collaborator.user_id == test_user.id
        assert collaborator.invited_by == test_user.id  # Self-invited

        # Verify result matches created collaborator
        assert result.id == collaborator.id


def test_ensure_owner_idempotent(test_app, test_db, test_user, test_course, test_owner_role):
    """Test that ensure_owner_collaborator is idempotent (safe to call multiple times)."""
    with test_app.app_context():
        # Create initial collaborator
        first = Collaborator.create(test_course, test_user.id, test_owner_role.id, invited_by=test_user.id)

        # Call ensure_owner_collaborator again
        second = ensure_owner_collaborator(test_course, test_user.id)

        # Should return existing collaborator, not create new one
        assert first.id == second.id

        # Verify only one collaborator exists
        all_collabs = Collaborator.get_for_course(test_course)
        assert len(all_collabs) == 1


def test_permission_change_takes_effect_immediately(test_app, test_user, test_course, test_db):
    """Test that permission changes take effect on next request (no stale cache)."""
    with test_app.app_context():
        # Create an admin user who remains the Owner (so course stays "found")
        admin_user = User.create(
            email="admin@example.com",
            password="adminpass",
            name="Admin User"
        )
        owner_role = Role.create_from_template(test_course, "Owner")
        Collaborator.create(test_course, admin_user.id, owner_role.id, invited_by=admin_user.id)

        # Start test user with Designer role (has edit_content permission)
        designer_role = Role.create_from_template(test_course, "Designer")
        collaborator = Collaborator.create(test_course, test_user.id, designer_role.id, invited_by=admin_user.id)

    with test_app.test_client() as client:
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)

        # First request should succeed
        response = client.get(f'/test/courses/{test_course}/protected')
        assert response.status_code == 200

        # Change role to Reviewer (no edit_content permission)
        with test_app.app_context():
            reviewer_role = Role.create_from_template(test_course, "Reviewer")
            Collaborator.update_role(collaborator.id, reviewer_role.id)

        # Next request should fail immediately
        response = client.get(f'/test/courses/{test_course}/protected')
        assert response.status_code == 403


def test_revoked_collaborator_loses_access(test_app, test_user, test_course, test_db):
    """Test that removing collaborator revokes access on next request."""
    with test_app.app_context():
        # Create an admin user who remains the Owner (so course stays "found")
        admin_user = User.create(
            email="admin@example.com",
            password="adminpass",
            name="Admin User"
        )
        owner_role = Role.create_from_template(test_course, "Owner")
        Collaborator.create(test_course, admin_user.id, owner_role.id, invited_by=admin_user.id)

        # Create test user as Designer (has edit_content permission)
        designer_role = Role.create_from_template(test_course, "Designer")
        collaborator = Collaborator.create(test_course, test_user.id, designer_role.id, invited_by=admin_user.id)
        collaborator_id = collaborator.id

    with test_app.test_client() as client:
        with client.session_transaction() as sess:
            sess['_user_id'] = str(test_user.id)

        # First request should succeed
        response = client.get(f'/test/courses/{test_course}/protected')
        assert response.status_code == 200

        # Remove collaborator
        with test_app.app_context():
            Collaborator.delete(collaborator_id)

        # Next request should fail immediately
        response = client.get(f'/test/courses/{test_course}/protected')
        assert response.status_code == 403
