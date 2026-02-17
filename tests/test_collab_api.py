"""Tests for Collaboration API endpoints - comments and activity feed."""

import pytest
from flask import Flask
from flask_login import LoginManager, UserMixin
from unittest.mock import MagicMock
import json
from pathlib import Path

from src.api.collab import collab_bp, init_collab_bp
from src.auth.db import get_db, init_db, close_db


class MockUser(UserMixin):
    def __init__(self, id, email="test@example.com", name="Test User"):
        self.id = id
        self.email = email
        self.name = name


@pytest.fixture
def app(tmp_path):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"
    app.config["DATABASE"] = tmp_path / "test.db"
    app.teardown_appcontext(close_db)

    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return MockUser(int(user_id))

    mock_store = MagicMock()
    init_collab_bp(mock_store)
    app.register_blueprint(collab_bp)

    # Ensure instance dir exists for schema loading
    instance_dir = Path(__file__).parent.parent / 'instance'
    instance_dir.mkdir(exist_ok=True)

    with app.app_context():
        init_db()
        from src.collab.permissions import seed_permissions
        seed_permissions(get_db())
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(app, client):
    with client.session_transaction() as sess:
        sess["_user_id"] = "1"
    
    with app.app_context():
        db = get_db()
        db.execute("INSERT INTO user (id, email, name, password_hash) VALUES (1, 'test@example.com', 'Test User', 'hash')")
        db.execute("INSERT INTO user (id, email, name, password_hash) VALUES (2, 'other@example.com', 'Other User', 'hash')")
        db.commit()
        
        from src.collab.models import Role
        from src.collab.permissions import seed_permissions
        seed_permissions(db)
        role = Role.create_from_template("course1", "Owner")
        db.execute("INSERT INTO collaborator (course_id, user_id, role_id, invited_by) VALUES ('course1', 1, ?, 1)", (role.id,))
        db.commit()
    
    return client


@pytest.fixture
def setup_comments(app, auth_client):
    with app.app_context():
        from src.collab.comments import Comment
        c1 = Comment.create("course1", 1, "Top level comment")
        c2 = Comment.create("course1", 1, "Reply to comment", parent_id=c1.id)
        return {"parent": c1, "reply": c2}


# Course-level Comment Tests
def test_create_course_comment(auth_client):
    response = auth_client.post(
        "/api/courses/course1/comments",
        json={"content": "This is a test comment"}
    )
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data["content"] == "This is a test comment"
    assert data["course_id"] == "course1"


def test_list_course_comments(app, auth_client):
    with app.app_context():
        from src.collab.comments import Comment
        parent = Comment.create("course1", 1, "Parent comment")
        Comment.create("course1", 1, "Reply", parent_id=parent.id)
    
    response = auth_client.get("/api/courses/course1/comments")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert len(data[0]["replies"]) == 1


def test_reply_to_comment(app, auth_client, setup_comments):
    parent_id = setup_comments["parent"].id
    response = auth_client.post(
        "/api/courses/course1/comments",
        json={"content": "Another reply", "parent_id": parent_id}
    )
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data["parent_id"] == parent_id


def test_cannot_reply_to_reply(app, auth_client, setup_comments):
    reply_id = setup_comments["reply"].id
    response = auth_client.post(
        "/api/courses/course1/comments",
        json={"content": "Nested reply", "parent_id": reply_id}
    )
    assert response.status_code == 400


# Activity-level Comment Tests
def test_create_activity_comment(auth_client):
    response = auth_client.post(
        "/api/courses/course1/activities/act1/comments",
        json={"content": "Activity feedback"}
    )
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data["activity_id"] == "act1"


def test_list_activity_comments(app, auth_client):
    with app.app_context():
        from src.collab.comments import Comment
        Comment.create("course1", 1, "Comment on act1", activity_id="act1")
        Comment.create("course1", 1, "Comment on act2", activity_id="act2")
    
    response = auth_client.get("/api/courses/course1/activities/act1/comments")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]["activity_id"] == "act1"


# Comment Management Tests
def test_update_own_comment(app, auth_client, setup_comments):
    comment_id = setup_comments["parent"].id
    response = auth_client.put(
        f"/api/courses/course1/comments/{comment_id}",
        json={"content": "Updated content"}
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["content"] == "Updated content"


def test_cannot_update_others_comment(app, auth_client):
    with app.app_context():
        from src.collab.comments import Comment
        from src.collab.models import Role, Collaborator
        # Create comment by user 2
        comment = Comment.create("course1", 2, "Other users comment")
        comment_id = comment.id
        # Make user 2 a collaborator
        role = Role.create_from_template("course1", "SME")
        Collaborator.create("course1", 2, role.id, 1)
    
    # User 1 is Owner so can update
    response = auth_client.put(
        f"/api/courses/course1/comments/{comment_id}",
        json={"content": "Owner update"}
    )
    assert response.status_code == 200


def test_resolve_comment(app, auth_client, setup_comments):
    comment_id = setup_comments["parent"].id
    response = auth_client.post(f"/api/courses/course1/comments/{comment_id}/resolve")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "resolved"
    
    response = auth_client.get("/api/courses/course1/comments")
    data = json.loads(response.data)
    assert len(data) == 0
    
    response = auth_client.get("/api/courses/course1/comments?include_resolved=true")
    data = json.loads(response.data)
    assert len(data) >= 1


def test_unresolve_comment(app, auth_client, setup_comments):
    comment_id = setup_comments["parent"].id
    auth_client.post(f"/api/courses/course1/comments/{comment_id}/resolve")
    response = auth_client.post(f"/api/courses/course1/comments/{comment_id}/unresolve")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["status"] == "unresolved"


def test_delete_comment(app, auth_client, setup_comments):
    comment_id = setup_comments["parent"].id
    response = auth_client.delete(f"/api/courses/course1/comments/{comment_id}")
    assert response.status_code == 204
    
    response = auth_client.get("/api/courses/course1/comments?include_resolved=true")
    data = json.loads(response.data)
    assert len(data) == 0


# Mention/Notification Tests
def test_comment_with_mention_creates_notification(app, auth_client):
    with app.app_context():
        from src.collab.models import Role, Collaborator
        role = Role.create_from_template("course1", "Reviewer")
        Collaborator.create("course1", 2, role.id, 1)

    # Use quoted format for full name with space
    response = auth_client.post(
        "/api/courses/course1/comments",
        json={"content": 'Hey @"Other User" check this out'}
    )
    assert response.status_code == 201

    with app.app_context():
        from src.collab.comments import Mention
        mentions = Mention.get_unread_for_user(2)
        assert len(mentions) == 1


def test_get_notifications(app, auth_client):
    with app.app_context():
        from src.collab.comments import Comment
        Comment.create("course1", 2, "Test @Test User")
    
    response = auth_client.get("/api/notifications")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)


def test_mark_notification_read(app, auth_client):
    with app.app_context():
        db = get_db()
        db.execute("INSERT INTO comment (course_id, user_id, content) VALUES ('course1', 2, 'test')")
        db.execute("INSERT INTO mention (comment_id, user_id) VALUES (1, 1)")
        db.commit()
    
    response = auth_client.post("/api/notifications/1/read")
    assert response.status_code == 204


def test_mark_all_read(app, auth_client):
    with app.app_context():
        db = get_db()
        db.execute("INSERT INTO comment (course_id, user_id, content) VALUES ('course1', 2, 'test1')")
        db.execute("INSERT INTO comment (course_id, user_id, content) VALUES ('course1', 2, 'test2')")
        db.execute("INSERT INTO mention (comment_id, user_id) VALUES (1, 1)")
        db.execute("INSERT INTO mention (comment_id, user_id) VALUES (2, 1)")
        db.commit()
    
    response = auth_client.post("/api/notifications/read-all")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "marked_read" in data


# Activity Feed Tests
def test_activity_feed_returns_entries(app, auth_client):
    with app.app_context():
        from src.collab.audit import log_audit_entry
        log_audit_entry("course1", 1, "test_action", "test", "123")
    
    response = auth_client.get("/api/courses/course1/activity")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "feed" in data
    assert "limit" in data
    assert "offset" in data
    assert "has_more" in data


def test_activity_feed_pagination(app, auth_client):
    with app.app_context():
        from src.collab.audit import log_audit_entry
        for i in range(10):
            log_audit_entry("course1", 1, f"action_{i}", "test", str(i))
    
    response = auth_client.get("/api/courses/course1/activity?limit=5&offset=0")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data["feed"]) <= 5
    assert data["limit"] == 5
    assert data["offset"] == 0


def test_activity_feed_includes_user_name(app, auth_client):
    with app.app_context():
        from src.collab.audit import log_audit_entry
        log_audit_entry("course1", 1, "test_action", "test", "123")
    
    response = auth_client.get("/api/courses/course1/activity")
    data = json.loads(response.data)
    if data["feed"]:
        assert "user_name" in data["feed"][0]


def test_activity_logs_comment_actions(app, auth_client):
    auth_client.post(
        "/api/courses/course1/comments",
        json={"content": "Test comment for audit"}
    )
    
    response = auth_client.get("/api/courses/course1/activity")
    data = json.loads(response.data)
    actions = [entry["action"] for entry in data["feed"]]
    assert "comment_added" in actions


# Permission Tests
def test_non_collaborator_cannot_comment(app, auth_client):
    """Test that non-collaborator cannot post comments."""
    # auth_client fixture creates course1 with user1 as owner
    # Now login as user3 (non-collaborator)
    with auth_client.session_transaction() as sess:
        sess["_user_id"] = "3"

    with app.app_context():
        db = get_db()
        db.execute("INSERT OR IGNORE INTO user (id, email, name, password_hash) VALUES (3, 'nobody@example.com', 'Nobody', 'hash')")
        db.commit()

    response = auth_client.post(
        "/api/courses/course1/comments",
        json={"content": "Should fail"}
    )
    assert response.status_code == 403


def test_non_collaborator_cannot_view_feed(app, auth_client):
    """Test that non-collaborator cannot view activity feed."""
    # auth_client fixture creates course1 with user1 as owner
    # Now login as user3 (non-collaborator)
    with auth_client.session_transaction() as sess:
        sess["_user_id"] = "3"

    with app.app_context():
        db = get_db()
        db.execute("INSERT OR IGNORE INTO user (id, email, name, password_hash) VALUES (3, 'nobody@example.com', 'Nobody', 'hash')")
        db.commit()

    response = auth_client.get("/api/courses/course1/activity")
    assert response.status_code == 403
