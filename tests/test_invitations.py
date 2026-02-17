"""Tests for invitation management."""

import pytest
from datetime import datetime, timedelta
from flask import Flask
from pathlib import Path

from src.auth.db import get_db, init_db, close_db
from src.auth.models import User
from src.collab.invitations import (
    Invitation,
    generate_invitation_token,
    validate_invitation_token,
    accept_invitation,
    DEFAULT_EXPIRY_SECONDS
)


@pytest.fixture
def test_app(tmp_path):
    """Create Flask app with test config."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['DATABASE'] = tmp_path / 'test_users.db'
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.teardown_appcontext(close_db)
    return app


@pytest.fixture
def test_db(test_app, tmp_path):
    """Initialize database schema before each test."""
    instance_dir = Path(__file__).parent.parent / 'instance'
    instance_dir.mkdir(exist_ok=True)

    with test_app.app_context():
        init_db()
        yield get_db()


@pytest.fixture
def test_user(test_app, test_db):
    """Create a test user who creates invitations."""
    with test_app.app_context():
        user = User.create(
            email='owner@example.com',
            password='password123',
            name='Test Owner'
        )
        yield user


@pytest.fixture
def test_course_role(test_app, test_db):
    """Create a test course role."""
    with test_app.app_context():
        db = get_db()
        cursor = db.execute(
            """INSERT INTO course_role (course_id, name)
               VALUES (?, ?)""",
            ('test-course-123', 'Reviewer')
        )
        db.commit()
        yield cursor.lastrowid


class TestTokenGeneration:
    """Tests for token generation."""

    def test_generate_invitation_token_is_unique(self, test_app, test_db):
        """Generated tokens should be unique."""
        with test_app.app_context():
            tokens = [generate_invitation_token() for _ in range(100)]
            assert len(tokens) == len(set(tokens))

    def test_generate_invitation_token_is_url_safe(self, test_app, test_db):
        """Tokens should be URL-safe (no special chars)."""
        with test_app.app_context():
            token = generate_invitation_token()
            # URL-safe characters are alphanumeric, dash, and underscore
            assert all(c.isalnum() or c in '-_' for c in token)


class TestEmailInvitations:
    """Tests for email invitations."""

    def test_create_email_invitation(self, test_app, test_db, test_user, test_course_role):
        """Create email invitation returns Invitation instance."""
        with test_app.app_context():
            invitation = Invitation.create(
                course_id='test-course-123',
                role_id=test_course_role,
                invited_by=test_user.id,
                email='invitee@example.com'
            )

            assert invitation is not None
            assert invitation.email == 'invitee@example.com'
            assert invitation.course_id == 'test-course-123'
            assert invitation.token is not None

    def test_email_invitation_has_expiry(self, test_app, test_db, test_user, test_course_role):
        """Email invitation has default 7-day expiry."""
        with test_app.app_context():
            invitation = Invitation.create(
                course_id='test-course-123',
                role_id=test_course_role,
                invited_by=test_user.id,
                email='invitee@example.com'
            )

            assert invitation.expires_at is not None
            # Should expire approximately 7 days from now
            expected_expiry = datetime.now() + timedelta(seconds=DEFAULT_EXPIRY_SECONDS)
            time_diff = abs((invitation.expires_at - expected_expiry).total_seconds())
            assert time_diff < 2  # Within 2 seconds

    def test_email_invitation_custom_expiry(self, test_app, test_db, test_user, test_course_role):
        """Email invitation respects custom expiry."""
        with test_app.app_context():
            custom_expiry = 3600  # 1 hour
            invitation = Invitation.create(
                course_id='test-course-123',
                role_id=test_course_role,
                invited_by=test_user.id,
                email='invitee@example.com',
                expires_in=custom_expiry
            )

            expected_expiry = datetime.now() + timedelta(seconds=custom_expiry)
            time_diff = abs((invitation.expires_at - expected_expiry).total_seconds())
            assert time_diff < 2  # Within 2 seconds


class TestShareableLinks:
    """Tests for shareable link invitations."""

    def test_create_shareable_link_no_email(self, test_app, test_db, test_user, test_course_role):
        """Shareable link has no email."""
        with test_app.app_context():
            invitation = Invitation.create_shareable_link(
                course_id='test-course-123',
                role_id=test_course_role,
                invited_by=test_user.id
            )

            assert invitation.email is None

    def test_shareable_link_no_expiry(self, test_app, test_db, test_user, test_course_role):
        """Shareable link with no expiry never expires."""
        with test_app.app_context():
            invitation = Invitation.create_shareable_link(
                course_id='test-course-123',
                role_id=test_course_role,
                invited_by=test_user.id,
                expires_in=None
            )

            assert invitation.expires_at is None

    def test_shareable_link_with_expiry(self, test_app, test_db, test_user, test_course_role):
        """Shareable link can have custom expiry."""
        with test_app.app_context():
            custom_expiry = 7200  # 2 hours
            invitation = Invitation.create_shareable_link(
                course_id='test-course-123',
                role_id=test_course_role,
                invited_by=test_user.id,
                expires_in=custom_expiry
            )

            assert invitation.expires_at is not None
            expected_expiry = datetime.now() + timedelta(seconds=custom_expiry)
            time_diff = abs((invitation.expires_at - expected_expiry).total_seconds())
            assert time_diff < 2


class TestValidation:
    """Tests for invitation validation."""

    def test_validate_valid_token(self, test_app, test_db, test_user, test_course_role):
        """Valid token returns (course_id, role_id)."""
        with test_app.app_context():
            invitation = Invitation.create(
                course_id='test-course-123',
                role_id=test_course_role,
                invited_by=test_user.id,
                email='invitee@example.com'
            )

            result = validate_invitation_token(invitation.token)
            assert result is not None
            assert result == ('test-course-123', test_course_role)

    def test_validate_revoked_token(self, test_app, test_db, test_user, test_course_role):
        """Revoked token returns None."""
        with test_app.app_context():
            invitation = Invitation.create(
                course_id='test-course-123',
                role_id=test_course_role,
                invited_by=test_user.id,
                email='invitee@example.com'
            )

            Invitation.revoke(invitation.id)
            result = validate_invitation_token(invitation.token)
            assert result is None

    def test_validate_expired_token(self, test_app, test_db, test_user, test_course_role):
        """Expired token returns None."""
        with test_app.app_context():
            # Create invitation with 1-second expiry
            invitation = Invitation.create(
                course_id='test-course-123',
                role_id=test_course_role,
                invited_by=test_user.id,
                email='invitee@example.com',
                expires_in=1
            )

            # Wait for expiry
            import time
            time.sleep(2)

            result = validate_invitation_token(invitation.token)
            assert result is None

    def test_validate_nonexistent_token(self, test_app, test_db):
        """Nonexistent token returns None."""
        with test_app.app_context():
            result = validate_invitation_token('nonexistent-token-12345')
            assert result is None

    def test_validate_no_expiry_always_valid(self, test_app, test_db, test_user, test_course_role):
        """Token with no expiry never expires."""
        with test_app.app_context():
            invitation = Invitation.create_shareable_link(
                course_id='test-course-123',
                role_id=test_course_role,
                invited_by=test_user.id,
                expires_in=None
            )

            # Should be valid even after waiting
            import time
            time.sleep(1)

            result = validate_invitation_token(invitation.token)
            assert result is not None
            assert result == ('test-course-123', test_course_role)


class TestRevocation:
    """Tests for invitation revocation."""

    def test_revoke_invitation(self, test_app, test_db, test_user, test_course_role):
        """Revoking sets revoked=1."""
        with test_app.app_context():
            invitation = Invitation.create(
                course_id='test-course-123',
                role_id=test_course_role,
                invited_by=test_user.id,
                email='invitee@example.com'
            )

            Invitation.revoke(invitation.id)

            # Reload from database
            reloaded = Invitation.get_by_id(invitation.id)
            assert reloaded.revoked is True

    def test_revoked_invitation_invalid(self, test_app, test_db, test_user, test_course_role):
        """is_valid() returns False for revoked invitation."""
        with test_app.app_context():
            invitation = Invitation.create(
                course_id='test-course-123',
                role_id=test_course_role,
                invited_by=test_user.id,
                email='invitee@example.com'
            )

            assert invitation.is_valid() is True

            Invitation.revoke(invitation.id)

            # Reload from database
            reloaded = Invitation.get_by_id(invitation.id)
            assert reloaded.is_valid() is False


class TestAcceptance:
    """Tests for accepting invitations."""

    def test_accept_invitation_creates_collaborator(self, test_app, test_db, test_user, test_course_role):
        """Accepting invitation creates collaborator entry."""
        with test_app.app_context():
            invitation = Invitation.create(
                course_id='test-course-123',
                role_id=test_course_role,
                invited_by=test_user.id,
                email='invitee@example.com'
            )

            # Create another user to accept
            accepting_user = User.create(
                email='invitee@example.com',
                password='password123',
                name='Accepting User'
            )

            result = accept_invitation(invitation.token, accepting_user.id)

            assert result is not None
            assert result['user_id'] == accepting_user.id
            assert result['course_id'] == 'test-course-123'
            assert result['role_id'] == test_course_role

    def test_accept_invitation_already_collaborator(self, test_app, test_db, test_user, test_course_role):
        """Accepting when already collaborator returns None."""
        with test_app.app_context():
            invitation = Invitation.create(
                course_id='test-course-123',
                role_id=test_course_role,
                invited_by=test_user.id,
                email='invitee@example.com'
            )

            # Create another user to accept
            accepting_user = User.create(
                email='invitee@example.com',
                password='password123',
                name='Accepting User'
            )

            # Accept once
            accept_invitation(invitation.token, accepting_user.id)

            # Try to accept again
            result = accept_invitation(invitation.token, accepting_user.id)
            assert result is None

    def test_accept_revoked_invitation_fails(self, test_app, test_db, test_user, test_course_role):
        """Cannot accept revoked invitation."""
        with test_app.app_context():
            invitation = Invitation.create(
                course_id='test-course-123',
                role_id=test_course_role,
                invited_by=test_user.id,
                email='invitee@example.com'
            )

            # Revoke it
            Invitation.revoke(invitation.id)

            # Create another user to accept
            accepting_user = User.create(
                email='invitee@example.com',
                password='password123',
                name='Accepting User'
            )

            # Try to accept revoked invitation
            result = accept_invitation(invitation.token, accepting_user.id)
            assert result is None
