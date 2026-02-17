"""Tests for audit trail system."""

import pytest
import json
from flask import Flask
from pathlib import Path

from src.auth.db import get_db, init_db, close_db
from src.auth.models import User
from src.collab.models import Role, Collaborator
from src.collab.audit import (
    AuditEntry,
    log_audit_entry,
    get_activity_feed,
    summarize_changes,
    ACTION_CONTENT_CREATED,
    ACTION_CONTENT_UPDATED,
    ACTION_CONTENT_DELETED,
    ACTION_STRUCTURE_ADDED,
    ACTION_STRUCTURE_UPDATED,
    ACTION_COLLABORATOR_INVITED,
    ACTION_COLLABORATOR_ROLE_CHANGED,
    ACTION_COURSE_CREATED,
)
from src.collab.permissions import seed_permissions


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
        db = get_db()
        seed_permissions(db)
        yield db


@pytest.fixture
def test_user(test_app, test_db):
    """Create a test user who performs actions."""
    with test_app.app_context():
        user = User.create(
            email='alice@example.com',
            password='password123',
            name='Alice'
        )
        yield user


@pytest.fixture
def test_course(test_app, test_db, test_user):
    """Create a test course with collaborator."""
    with test_app.app_context():
        # Create Owner role
        role = Role.create_from_template('test-course-123', 'Owner')
        # Add test_user as collaborator
        collaborator = Collaborator.create(
            course_id='test-course-123',
            user_id=test_user.id,
            role_id=role.id,
            invited_by=test_user.id
        )
        yield 'test-course-123'


@pytest.fixture
def second_user(test_app, test_db):
    """Create a second user for multi-user tests."""
    with test_app.app_context():
        user = User.create(
            email='bob@example.com',
            password='password123',
            name='Bob Smith'
        )
        yield user


class TestAuditLogging:
    """Tests for audit entry logging."""

    def test_log_audit_entry_basic(self, test_app, test_db, test_user, test_course):
        """Create basic audit entry with action and entity."""
        with test_app.app_context():
            entry = log_audit_entry(
                course_id=test_course,
                user_id=test_user.id,
                action=ACTION_CONTENT_CREATED,
                entity_type='activity',
                entity_id='activity-123'
            )

            assert entry is not None
            assert entry.course_id == test_course
            assert entry.user_id == test_user.id
            assert entry.action == ACTION_CONTENT_CREATED
            assert entry.entity_type == 'activity'
            assert entry.entity_id == 'activity-123'
            assert entry.changes is None  # No diff provided

    def test_log_audit_entry_with_diff(self, test_app, test_db, test_user, test_course):
        """Log entry with before/after creates changes JSON."""
        with test_app.app_context():
            before = {'title': 'Old Title', 'status': 'draft'}
            after = {'title': 'New Title', 'status': 'published'}

            entry = log_audit_entry(
                course_id=test_course,
                user_id=test_user.id,
                action=ACTION_CONTENT_UPDATED,
                entity_type='activity',
                entity_id='activity-123',
                before=before,
                after=after
            )

            assert entry.changes is not None
            changes = json.loads(entry.changes)
            # jsondiff creates a diff object
            assert 'title' in changes or changes != {}

    def test_log_audit_entry_no_diff(self, test_app, test_db, test_user, test_course):
        """Entry without before/after has NULL changes."""
        with test_app.app_context():
            entry = log_audit_entry(
                course_id=test_course,
                user_id=test_user.id,
                action=ACTION_CONTENT_DELETED,
                entity_type='activity',
                entity_id='activity-123'
            )

            assert entry.changes is None


class TestDiffEfficiency:
    """Tests for efficient diff storage."""

    def test_diff_stores_only_changes(self, test_app, test_db, test_user, test_course):
        """Full documents in, only diff stored."""
        with test_app.app_context():
            before = {
                'id': 'activity-123',
                'title': 'Original Title',
                'description': 'Long description text...',
                'status': 'draft',
                'metadata': {'author': 'Alice', 'version': 1}
            }
            after = {
                'id': 'activity-123',
                'title': 'Updated Title',  # Changed
                'description': 'Long description text...',
                'status': 'published',  # Changed
                'metadata': {'author': 'Alice', 'version': 2}  # Changed
            }

            entry = log_audit_entry(
                course_id=test_course,
                user_id=test_user.id,
                action=ACTION_CONTENT_UPDATED,
                entity_type='activity',
                entity_id='activity-123',
                before=before,
                after=after
            )

            # Changes JSON should be smaller than full document
            changes = json.loads(entry.changes)
            assert changes is not None
            # Should contain only changed fields
            assert len(json.dumps(changes)) < len(json.dumps(after))

    def test_diff_handles_nested_objects(self, test_app, test_db, test_user, test_course):
        """Nested changes captured in diff."""
        with test_app.app_context():
            before = {'metadata': {'author': 'Alice', 'version': 1}}
            after = {'metadata': {'author': 'Alice', 'version': 2}}

            entry = log_audit_entry(
                course_id=test_course,
                user_id=test_user.id,
                action=ACTION_CONTENT_UPDATED,
                entity_type='activity',
                before=before,
                after=after
            )

            changes = json.loads(entry.changes)
            assert changes is not None

    def test_diff_handles_arrays(self, test_app, test_db, test_user, test_course):
        """Array additions/removals captured."""
        with test_app.app_context():
            before = {'tags': ['python', 'beginner']}
            after = {'tags': ['python', 'beginner', 'tutorial']}

            entry = log_audit_entry(
                course_id=test_course,
                user_id=test_user.id,
                action=ACTION_CONTENT_UPDATED,
                entity_type='activity',
                before=before,
                after=after
            )

            changes = json.loads(entry.changes)
            assert changes is not None


class TestAuditQueries:
    """Tests for audit entry queries."""

    def test_get_for_course_paginated(self, test_app, test_db, test_user, test_course):
        """get_for_course with limit and offset works."""
        with test_app.app_context():
            # Create multiple entries
            for i in range(5):
                log_audit_entry(
                    course_id=test_course,
                    user_id=test_user.id,
                    action=ACTION_CONTENT_CREATED,
                    entity_type='activity',
                    entity_id=f'activity-{i}'
                )

            # Get first page
            page1 = AuditEntry.get_for_course(test_course, limit=2, offset=0)
            assert len(page1) == 2

            # Get second page
            page2 = AuditEntry.get_for_course(test_course, limit=2, offset=2)
            assert len(page2) == 2

            # Entries should be different
            assert page1[0].id != page2[0].id

    def test_get_for_course_ordered_by_newest(self, test_app, test_db, test_user, test_course):
        """Entries ordered by created_at DESC (most recent first)."""
        with test_app.app_context():
            entry1 = log_audit_entry(
                course_id=test_course,
                user_id=test_user.id,
                action=ACTION_CONTENT_CREATED,
                entity_type='activity',
                entity_id='activity-1'
            )

            entry2 = log_audit_entry(
                course_id=test_course,
                user_id=test_user.id,
                action=ACTION_CONTENT_UPDATED,
                entity_type='activity',
                entity_id='activity-1'
            )

            entries = AuditEntry.get_for_course(test_course)

            # Most recent first
            assert entries[0].id == entry2.id
            assert entries[1].id == entry1.id

    def test_get_for_entity_filters(self, test_app, test_db, test_user, test_course):
        """get_for_entity returns only matching entity."""
        with test_app.app_context():
            log_audit_entry(
                course_id=test_course,
                user_id=test_user.id,
                action=ACTION_CONTENT_CREATED,
                entity_type='activity',
                entity_id='activity-1'
            )

            log_audit_entry(
                course_id=test_course,
                user_id=test_user.id,
                action=ACTION_CONTENT_CREATED,
                entity_type='activity',
                entity_id='activity-2'
            )

            entries = AuditEntry.get_for_entity(test_course, 'activity', 'activity-1')

            assert len(entries) == 1
            assert entries[0].entity_id == 'activity-1'

    def test_get_by_user_filters(self, test_app, test_db, test_user, second_user, test_course):
        """get_by_user returns only entries for that user."""
        with test_app.app_context():
            log_audit_entry(
                course_id=test_course,
                user_id=test_user.id,
                action=ACTION_CONTENT_CREATED,
                entity_type='activity',
                entity_id='activity-1'
            )

            log_audit_entry(
                course_id=test_course,
                user_id=second_user.id,
                action=ACTION_CONTENT_UPDATED,
                entity_type='activity',
                entity_id='activity-1'
            )

            entries = AuditEntry.get_by_user(test_course, test_user.id)

            assert len(entries) == 1
            assert entries[0].user_id == test_user.id


class TestActivityFeed:
    """Tests for activity feed generation."""

    def test_activity_feed_includes_user_info(self, test_app, test_db, test_user, test_course):
        """Activity feed populates user_name."""
        with test_app.app_context():
            log_audit_entry(
                course_id=test_course,
                user_id=test_user.id,
                action=ACTION_CONTENT_CREATED,
                entity_type='activity',
                entity_id='activity-1'
            )

            feed = get_activity_feed(test_course)

            assert len(feed) == 1
            assert feed[0]['user_name'] == test_user.name

    def test_activity_feed_deleted_user(self, test_app, test_db, test_user, test_course):
        """Deleted user shows as '[Deleted User]'."""
        with test_app.app_context():
            # Create audit entry with non-existent user_id (simulates deleted user)
            db = get_db()
            db.execute(
                """
                INSERT INTO audit_entry
                (course_id, user_id, action, entity_type, entity_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (test_course, 99999, ACTION_CONTENT_CREATED, 'activity', 'activity-1')
            )
            db.commit()

            feed = get_activity_feed(test_course)

            assert len(feed) >= 1
            # Find the entry with non-existent user
            deleted_user_entry = [e for e in feed if e['user_name'] == '[Deleted User]']
            assert len(deleted_user_entry) == 1

    def test_activity_feed_has_summary(self, test_app, test_db, test_user, test_course):
        """Activity feed includes human-readable summary."""
        with test_app.app_context():
            log_audit_entry(
                course_id=test_course,
                user_id=test_user.id,
                action=ACTION_CONTENT_CREATED,
                entity_type='activity',
                entity_id='activity-1'
            )

            feed = get_activity_feed(test_course)

            assert 'summary' in feed[0]
            assert len(feed[0]['summary']) > 0


class TestSummarization:
    """Tests for change summary generation."""

    def test_summarize_content_update(self):
        """Content update lists changed fields."""
        changes = {'title': 'new', 'description': 'updated'}
        summary = summarize_changes(ACTION_CONTENT_UPDATED, 'activity', changes)

        assert 'title' in summary.lower() or 'description' in summary.lower()

    def test_summarize_structure_add(self):
        """Structure add shows entity name."""
        changes = {'name': 'Introduction'}
        summary = summarize_changes(ACTION_STRUCTURE_ADDED, 'module', changes)

        assert 'Introduction' in summary or 'module' in summary.lower()

    def test_summarize_collaborator_change(self):
        """Collaborator change shows user and role."""
        changes = {
            'email': 'alice@example.com',
            'old_role': 'Reviewer',
            'new_role': 'Designer'
        }
        summary = summarize_changes(ACTION_COLLABORATOR_ROLE_CHANGED, 'collaborator', changes)

        assert 'alice@example.com' in summary
        assert 'Reviewer' in summary or 'Designer' in summary


class TestActionConstants:
    """Tests for action constant definitions."""

    def test_all_action_constants_unique(self):
        """All action constants have unique values."""
        actions = [
            ACTION_CONTENT_CREATED,
            ACTION_CONTENT_UPDATED,
            ACTION_CONTENT_DELETED,
            ACTION_STRUCTURE_ADDED,
            ACTION_STRUCTURE_UPDATED,
            ACTION_COLLABORATOR_INVITED,
            ACTION_COLLABORATOR_ROLE_CHANGED,
            ACTION_COURSE_CREATED,
        ]

        assert len(actions) == len(set(actions)), "Duplicate action constants found"


class TestAuditToDict:
    """Tests for AuditEntry serialization."""

    def test_to_dict_includes_all_fields(self, test_app, test_db, test_user, test_course):
        """to_dict includes all audit entry fields."""
        with test_app.app_context():
            entry = log_audit_entry(
                course_id=test_course,
                user_id=test_user.id,
                action=ACTION_CONTENT_CREATED,
                entity_type='activity',
                entity_id='activity-1'
            )

            data = entry.to_dict()

            assert 'id' in data
            assert 'course_id' in data
            assert 'user_id' in data
            assert 'action' in data
            assert 'entity_type' in data
            assert 'entity_id' in data
            assert 'changes' in data
            assert 'created_at' in data
            assert 'user_name' in data

    def test_to_dict_parses_changes_json(self, test_app, test_db, test_user, test_course):
        """to_dict parses changes JSON string to dict."""
        with test_app.app_context():
            before = {'title': 'Old'}
            after = {'title': 'New'}

            entry = log_audit_entry(
                course_id=test_course,
                user_id=test_user.id,
                action=ACTION_CONTENT_UPDATED,
                entity_type='activity',
                entity_id='activity-1',
                before=before,
                after=after
            )

            data = entry.to_dict()

            # changes should be parsed dict, not string
            assert isinstance(data['changes'], dict)

    def test_to_dict_shows_deleted_user(self, test_app, test_db, test_user, test_course):
        """to_dict shows '[Deleted User]' when user is deleted."""
        with test_app.app_context():
            # Create audit entry with non-existent user_id (simulates deleted user)
            db = get_db()
            db.execute(
                """
                INSERT INTO audit_entry
                (course_id, user_id, action, entity_type, entity_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (test_course, 99999, ACTION_CONTENT_CREATED, 'activity', 'activity-1')
            )
            db.commit()

            # Get entries and find the one with deleted user
            entries = AuditEntry.get_for_course(test_course)
            deleted_user_entries = [e for e in entries if e.user_id == 99999]
            assert len(deleted_user_entries) == 1

            data = deleted_user_entries[0].to_dict()
            assert data['user_name'] == '[Deleted User]'
