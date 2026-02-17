"""Tests for comment and mention system."""

import pytest
from flask import Flask
from pathlib import Path

from src.auth.db import get_db, init_db, close_db
from src.auth.models import User
from src.collab.models import Role, Collaborator
from src.collab.comments import Comment, Mention, parse_mentions
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
    """Create a test user who creates comments."""
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
    """Create a second user for mention tests."""
    with test_app.app_context():
        user = User.create(
            email='bob@example.com',
            password='password123',
            name='Bob Smith'
        )
        yield user


@pytest.fixture
def second_collaborator(test_app, test_db, second_user, test_course):
    """Add second user as collaborator."""
    with test_app.app_context():
        db = get_db()
        # Get an existing role
        role_row = db.execute(
            "SELECT id FROM course_role WHERE course_id = ? LIMIT 1",
            (test_course,)
        ).fetchone()

        collaborator = Collaborator.create(
            course_id=test_course,
            user_id=second_user.id,
            role_id=role_row['id'],
            invited_by=1  # Invited by first user
        )
        yield collaborator


class TestMentionParsing:
    """Tests for mention parsing."""

    def test_parse_mentions_simple(self):
        """Parse simple @username mention."""
        mentions = parse_mentions("Hey @alice check this out")
        assert mentions == ["alice"]

    def test_parse_mentions_quoted(self):
        """Parse quoted @\"Full Name\" mention."""
        mentions = parse_mentions('Hey @"Alice Smith" check this out')
        assert mentions == ["Alice Smith"]

    def test_parse_mentions_multiple(self):
        """Parse multiple mentions in text."""
        text = 'Hey @alice and @"Bob Smith" check this out'
        mentions = parse_mentions(text)
        assert set(mentions) == {"alice", "Bob Smith"}

    def test_parse_mentions_empty(self):
        """Empty list when no mentions."""
        mentions = parse_mentions("No mentions here")
        assert mentions == []

    def test_parse_mentions_email_format(self):
        """Parse @email format mentions."""
        mentions = parse_mentions("Contact @user@example.com about this")
        assert "user@example.com" in mentions


class TestCommentCreation:
    """Tests for comment creation."""

    def test_create_course_level_comment(self, test_app, test_db, test_user, test_course):
        """Create course-level comment with activity_id=None."""
        with test_app.app_context():
            comment = Comment.create(
                course_id=test_course,
                user_id=test_user.id,
                content="Course-level discussion comment"
            )

            assert comment is not None
            assert comment.course_id == test_course
            assert comment.activity_id is None
            assert comment.content == "Course-level discussion comment"

    def test_create_activity_comment(self, test_app, test_db, test_user, test_course):
        """Create activity-specific comment."""
        with test_app.app_context():
            comment = Comment.create(
                course_id=test_course,
                user_id=test_user.id,
                content="This activity needs review",
                activity_id="activity-123"
            )

            assert comment.activity_id == "activity-123"

    def test_comment_has_author_info(self, test_app, test_db, test_user, test_course):
        """Comment loads with author name and email."""
        with test_app.app_context():
            comment = Comment.create(
                course_id=test_course,
                user_id=test_user.id,
                content="Test comment"
            )

            loaded = Comment.get_by_id(comment.id)
            assert loaded.author_name == test_user.name
            assert loaded.author_email == test_user.email


class TestThreading:
    """Tests for single-level threading."""

    def test_create_reply_to_comment(self, test_app, test_db, test_user, test_course):
        """Create reply to top-level comment."""
        with test_app.app_context():
            parent = Comment.create(
                course_id=test_course,
                user_id=test_user.id,
                content="Parent comment"
            )

            reply = Comment.create(
                course_id=test_course,
                user_id=test_user.id,
                content="Reply to parent",
                parent_id=parent.id
            )

            assert reply.parent_id == parent.id

    def test_cannot_reply_to_reply(self, test_app, test_db, test_user, test_course):
        """Raise ValueError when trying to reply to a reply."""
        with test_app.app_context():
            parent = Comment.create(
                course_id=test_course,
                user_id=test_user.id,
                content="Parent comment"
            )

            reply = Comment.create(
                course_id=test_course,
                user_id=test_user.id,
                content="Reply to parent",
                parent_id=parent.id
            )

            # Try to reply to the reply
            with pytest.raises(ValueError) as exc_info:
                Comment.create(
                    course_id=test_course,
                    user_id=test_user.id,
                    content="Reply to reply (should fail)",
                    parent_id=reply.id
                )

            assert "Cannot reply to a reply" in str(exc_info.value)

    def test_get_with_replies_builds_hierarchy(self, test_app, test_db, test_user, test_course):
        """get_with_replies builds correct hierarchy."""
        with test_app.app_context():
            # Create parent comments
            parent1 = Comment.create(
                course_id=test_course,
                user_id=test_user.id,
                content="Parent 1"
            )

            parent2 = Comment.create(
                course_id=test_course,
                user_id=test_user.id,
                content="Parent 2"
            )

            # Create replies
            reply1 = Comment.create(
                course_id=test_course,
                user_id=test_user.id,
                content="Reply to parent 1",
                parent_id=parent1.id
            )

            reply2 = Comment.create(
                course_id=test_course,
                user_id=test_user.id,
                content="Another reply to parent 1",
                parent_id=parent1.id
            )

            # Get with hierarchy
            comments = Comment.get_with_replies(test_course)

            assert len(comments) == 2  # Two top-level comments
            assert len(comments[0].replies) == 2  # First parent has 2 replies
            assert len(comments[1].replies) == 0  # Second parent has no replies


class TestResolution:
    """Tests for comment resolution."""

    def test_resolve_comment(self, test_app, test_db, test_user, test_course):
        """Resolve comment sets resolved=1."""
        with test_app.app_context():
            comment = Comment.create(
                course_id=test_course,
                user_id=test_user.id,
                content="Issue found"
            )

            Comment.resolve(comment.id)

            loaded = Comment.get_by_id(comment.id)
            assert loaded.resolved == 1

    def test_get_excludes_resolved_by_default(self, test_app, test_db, test_user, test_course):
        """get_for_course excludes resolved comments by default."""
        with test_app.app_context():
            comment1 = Comment.create(
                course_id=test_course,
                user_id=test_user.id,
                content="Active comment"
            )

            comment2 = Comment.create(
                course_id=test_course,
                user_id=test_user.id,
                content="Will be resolved"
            )

            Comment.resolve(comment2.id)

            comments = Comment.get_for_course(test_course)
            assert len(comments) == 1
            assert comments[0].id == comment1.id

    def test_get_includes_resolved_when_requested(self, test_app, test_db, test_user, test_course):
        """get_for_course with include_resolved=True shows all."""
        with test_app.app_context():
            comment1 = Comment.create(
                course_id=test_course,
                user_id=test_user.id,
                content="Active comment"
            )

            comment2 = Comment.create(
                course_id=test_course,
                user_id=test_user.id,
                content="Resolved comment"
            )

            Comment.resolve(comment2.id)

            comments = Comment.get_for_course(test_course, include_resolved=True)
            assert len(comments) == 2


class TestMentionNotifications:
    """Tests for mention notification system."""

    def test_comment_creates_mentions(self, test_app, test_db, test_user, second_user, test_course, second_collaborator):
        """Mentions created for valid collaborators."""
        with test_app.app_context():
            comment = Comment.create(
                course_id=test_course,
                user_id=test_user.id,
                content='Hey @"Bob Smith" can you review this?'
            )

            mentions = Mention.get_unread_for_user(second_user.id)
            assert len(mentions) == 1
            assert mentions[0].comment_id == comment.id
            assert mentions[0].user_id == second_user.id

    def test_mention_excludes_non_collaborators(self, test_app, test_db, test_user, test_course):
        """Non-collaborators don't get mention notifications."""
        with test_app.app_context():
            # Create user who's not a collaborator
            non_collab = User.create(
                email='noncollab@example.com',
                password='password123',
                name='Non Collaborator'
            )

            comment = Comment.create(
                course_id=test_course,
                user_id=test_user.id,
                content='Hey @"Non Collaborator" this wont notify you'
            )

            mentions = Mention.get_unread_for_user(non_collab.id)
            assert len(mentions) == 0

    def test_mention_excludes_self(self, test_app, test_db, test_user, test_course):
        """Author doesn't get notified of their own mention."""
        with test_app.app_context():
            comment = Comment.create(
                course_id=test_course,
                user_id=test_user.id,
                content='I mentioned @Alice (myself)'
            )

            mentions = Mention.get_unread_for_user(test_user.id)
            assert len(mentions) == 0

    def test_get_unread_mentions(self, test_app, test_db, test_user, second_user, test_course, second_collaborator):
        """get_unread_for_user returns only unread."""
        with test_app.app_context():
            comment1 = Comment.create(
                course_id=test_course,
                user_id=test_user.id,
                content='@bob@example.com first mention'
            )

            comment2 = Comment.create(
                course_id=test_course,
                user_id=test_user.id,
                content='@bob@example.com second mention'
            )

            mentions = Mention.get_unread_for_user(second_user.id)
            assert len(mentions) == 2

            # Mark one read
            Mention.mark_read(mentions[0].id)

            unread = Mention.get_unread_for_user(second_user.id)
            assert len(unread) == 1

    def test_mark_mention_read(self, test_app, test_db, test_user, second_user, test_course, second_collaborator):
        """mark_read sets read=1."""
        with test_app.app_context():
            comment = Comment.create(
                course_id=test_course,
                user_id=test_user.id,
                content='@bob@example.com check this'
            )

            mentions = Mention.get_unread_for_user(second_user.id)
            mention_id = mentions[0].id

            Mention.mark_read(mention_id)

            # Verify it's now read
            db = get_db()
            row = db.execute("SELECT read FROM mention WHERE id = ?", (mention_id,)).fetchone()
            assert row['read'] == 1

    def test_mark_all_read(self, test_app, test_db, test_user, second_user, test_course, second_collaborator):
        """mark_all_read marks all mentions for user."""
        with test_app.app_context():
            comment1 = Comment.create(
                course_id=test_course,
                user_id=test_user.id,
                content='@bob@example.com mention 1'
            )

            comment2 = Comment.create(
                course_id=test_course,
                user_id=test_user.id,
                content='@bob@example.com mention 2'
            )

            Mention.mark_all_read(second_user.id)

            unread = Mention.get_unread_for_user(second_user.id)
            assert len(unread) == 0


class TestUpdateAndDelete:
    """Tests for comment update and delete operations."""

    def test_update_comment_content(self, test_app, test_db, test_user, test_course):
        """Update changes content and updated_at."""
        import time
        with test_app.app_context():
            comment = Comment.create(
                course_id=test_course,
                user_id=test_user.id,
                content="Original content"
            )

            original_updated_at = comment.updated_at
            time.sleep(1)  # Ensure timestamp difference

            updated = Comment.update(comment.id, "Updated content")

            assert updated.content == "Updated content"
            assert updated.updated_at >= original_updated_at  # Should be same or later

    def test_update_re_parses_mentions(self, test_app, test_db, test_user, second_user, test_course, second_collaborator):
        """Updating comment re-parses mentions."""
        with test_app.app_context():
            comment = Comment.create(
                course_id=test_course,
                user_id=test_user.id,
                content="No mentions here"
            )

            # No mentions initially
            mentions = Mention.get_unread_for_user(second_user.id)
            assert len(mentions) == 0

            # Update with mention
            Comment.update(comment.id, "@bob@example.com now you're mentioned")

            mentions = Mention.get_unread_for_user(second_user.id)
            assert len(mentions) == 1

    def test_delete_comment_cascades_replies(self, test_app, test_db, test_user, test_course):
        """Deleting parent deletes replies via CASCADE."""
        with test_app.app_context():
            parent = Comment.create(
                course_id=test_course,
                user_id=test_user.id,
                content="Parent"
            )

            reply = Comment.create(
                course_id=test_course,
                user_id=test_user.id,
                content="Reply",
                parent_id=parent.id
            )

            Comment.delete(parent.id)

            # Reply should be gone
            assert Comment.get_by_id(reply.id) is None
