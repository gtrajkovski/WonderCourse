"""End-to-end collaboration integration tests.

Tests the full collaboration workflow including:
- Permission hierarchy enforcement (Owner > Designer > Reviewer > SME)
- Structure permission checks (modules, lessons, activities)
- Content workflow permission checks (generate, edit, approve)
- Audit trail logging for all changes
- Full collaboration flow scenarios
"""

import pytest
from flask import Flask
from flask_login import LoginManager, UserMixin
from unittest.mock import MagicMock, patch
import json
from pathlib import Path

from src.api.modules import modules_bp, init_modules_bp
from src.api.lessons import lessons_bp, init_lessons_bp
from src.api.activities import activities_bp, init_activities_bp
from src.api.learning_outcomes import learning_outcomes_bp, init_learning_outcomes_bp
from src.api.content import content_bp, init_content_bp
from src.api.build_state import build_state_bp, init_build_state_bp
from src.api.blueprint import blueprint_bp, init_blueprint_bp
from src.api.export import export_bp, init_export_bp
from src.api.collab import collab_bp, init_collab_bp
from src.auth.db import get_db, init_db, close_db
from src.collab.permissions import seed_permissions
from src.collab.models import Role, Collaborator
from src.collab.audit import AuditEntry
from src.core.models import Course, Module, Lesson, Activity, ContentType, BuildState


class MockUser(UserMixin):
    """Mock user for authentication tests."""
    def __init__(self, id, email="test@example.com", name="Test User"):
        self.id = id
        self.email = email
        self.name = name


# Mock course for project_store
def create_mock_course(course_id="course1"):
    """Create a mock course with structure for testing."""
    course = Course(
        id=course_id,
        title="Test Course",
        description="A test course"
    )
    module = Module(id="mod1", title="Module 1", order=0)
    lesson = Lesson(id="les1", title="Lesson 1", order=0)
    activity = Activity(
        id="act1",
        title="Activity 1",
        content_type=ContentType.VIDEO,
        order=0,
        build_state=BuildState.DRAFT
    )
    lesson.activities.append(activity)
    module.lessons.append(lesson)
    course.modules.append(module)
    return course


@pytest.fixture
def app(tmp_path):
    """Create Flask app with all blueprints registered."""
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

    # Create mock project store
    mock_store = MagicMock()
    mock_course = create_mock_course()
    mock_store.load.return_value = mock_course
    mock_store.save.return_value = None

    # Initialize all blueprints
    init_modules_bp(mock_store)
    init_lessons_bp(mock_store)
    init_activities_bp(mock_store)
    init_learning_outcomes_bp(mock_store)
    init_content_bp(mock_store)
    init_build_state_bp(mock_store)
    init_blueprint_bp(mock_store)
    init_export_bp(mock_store)
    init_collab_bp(mock_store)

    # Register blueprints
    app.register_blueprint(modules_bp)
    app.register_blueprint(lessons_bp)
    app.register_blueprint(activities_bp)
    app.register_blueprint(learning_outcomes_bp)
    app.register_blueprint(content_bp)
    app.register_blueprint(build_state_bp)
    app.register_blueprint(blueprint_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(collab_bp)

    # Ensure instance dir exists for schema loading
    instance_dir = Path(__file__).parent.parent / 'instance'
    instance_dir.mkdir(exist_ok=True)

    with app.app_context():
        init_db()
        seed_permissions(get_db())
        yield app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


def setup_user_with_role(app, user_id, email, name, course_id, role_name, invited_by=1):
    """Helper to create user with specific role on course."""
    with app.app_context():
        db = get_db()
        # Create user
        db.execute(
            "INSERT OR IGNORE INTO user (id, email, name, password_hash) VALUES (?, ?, ?, 'hash')",
            (user_id, email, name)
        )
        # Also ensure invited_by user exists if different
        if invited_by != user_id:
            db.execute(
                "INSERT OR IGNORE INTO user (id, email, name, password_hash) VALUES (?, ?, ?, 'hash')",
                (invited_by, f"inviter{invited_by}@example.com", f"Inviter {invited_by}")
            )
        db.commit()

        # Check if role already exists for this course
        existing_role = db.execute(
            "SELECT id FROM course_role WHERE course_id = ? AND name = ?",
            (course_id, role_name)
        ).fetchone()

        if existing_role:
            role_id = existing_role["id"]
        else:
            # Create role from template
            role = Role.create_from_template(course_id, role_name)
            role_id = role.id

        # Check if collaborator already exists
        existing_collab = db.execute(
            "SELECT id FROM collaborator WHERE course_id = ? AND user_id = ?",
            (course_id, user_id)
        ).fetchone()

        if not existing_collab:
            # Create collaborator
            db.execute(
                "INSERT INTO collaborator (course_id, user_id, role_id, invited_by) VALUES (?, ?, ?, ?)",
                (course_id, user_id, role_id, invited_by)
            )
            db.commit()


@pytest.fixture
def owner_client(app, client):
    """Client authenticated as Owner."""
    with client.session_transaction() as sess:
        sess["_user_id"] = "1"
    setup_user_with_role(app, 1, "owner@example.com", "Owner User", "course1", "Owner", 1)
    return client


@pytest.fixture
def designer_client(app, client):
    """Client authenticated as Designer."""
    # First ensure owner exists
    setup_user_with_role(app, 1, "owner@example.com", "Owner User", "course1", "Owner", 1)
    # Then create designer
    with client.session_transaction() as sess:
        sess["_user_id"] = "2"
    setup_user_with_role(app, 2, "designer@example.com", "Designer User", "course1", "Designer", 1)
    return client


@pytest.fixture
def reviewer_client(app, client):
    """Client authenticated as Reviewer."""
    # First ensure owner exists
    setup_user_with_role(app, 1, "owner@example.com", "Owner User", "course1", "Owner", 1)
    # Then create reviewer
    with client.session_transaction() as sess:
        sess["_user_id"] = "3"
    setup_user_with_role(app, 3, "reviewer@example.com", "Reviewer User", "course1", "Reviewer", 1)
    return client


@pytest.fixture
def sme_client(app, client):
    """Client authenticated as SME (Subject Matter Expert)."""
    # First ensure owner exists
    setup_user_with_role(app, 1, "owner@example.com", "Owner User", "course1", "Owner", 1)
    # Then create SME
    with client.session_transaction() as sess:
        sess["_user_id"] = "4"
    setup_user_with_role(app, 4, "sme@example.com", "SME User", "course1", "SME", 1)
    return client


# ===========================================================================
# Permission Hierarchy Tests
# ===========================================================================

class TestPermissionHierarchy:
    """Test that role permissions are correctly enforced."""

    def test_owner_has_all_permissions(self, owner_client):
        """Owner should be able to access all endpoints."""
        # View content
        response = owner_client.get("/api/courses/course1/modules")
        assert response.status_code == 200

        # Add structure
        response = owner_client.post(
            "/api/courses/course1/modules",
            json={"title": "New Module"}
        )
        assert response.status_code == 201

    def test_designer_can_edit_not_approve(self, app, designer_client):
        """Designer can edit content but cannot approve."""
        # Designer can view
        response = designer_client.get("/api/courses/course1/modules")
        assert response.status_code == 200

        # Designer can add structure
        response = designer_client.post(
            "/api/courses/course1/modules",
            json={"title": "New Module"}
        )
        assert response.status_code == 201

        # Designer cannot approve (requires approve_content permission)
        # First need to set up activity in REVIEWED state
        with app.app_context():
            from src.api.build_state import _project_store
            course = _project_store.load.return_value
            course.modules[0].lessons[0].activities[0].build_state = BuildState.REVIEWED

        response = designer_client.post("/api/courses/course1/activities/act1/approve")
        assert response.status_code == 403

    def test_reviewer_can_approve_not_edit_structure(self, app, reviewer_client):
        """Reviewer can approve content but cannot edit structure."""
        # Reviewer cannot add structure
        response = reviewer_client.post(
            "/api/courses/course1/modules",
            json={"title": "New Module"}
        )
        assert response.status_code == 403

        # Reviewer can approve (has approve_content permission)
        with app.app_context():
            from src.api.build_state import _project_store
            course = _project_store.load.return_value
            course.modules[0].lessons[0].activities[0].build_state = BuildState.REVIEWED

        response = reviewer_client.post("/api/courses/course1/activities/act1/approve")
        assert response.status_code == 200

    def test_sme_can_view_only(self, sme_client):
        """SME can only view content, all mutations fail."""
        # SME can view
        response = sme_client.get("/api/courses/course1/modules")
        assert response.status_code == 200

        # SME cannot add structure
        response = sme_client.post(
            "/api/courses/course1/modules",
            json={"title": "New Module"}
        )
        assert response.status_code == 403

        # SME cannot delete
        response = sme_client.delete("/api/courses/course1/modules/mod1")
        assert response.status_code == 403


# ===========================================================================
# Structure Permission Tests
# ===========================================================================

class TestStructurePermissions:
    """Test structure management permissions."""

    def test_designer_can_add_module(self, designer_client):
        """Designer with add_structure can add modules."""
        response = designer_client.post(
            "/api/courses/course1/modules",
            json={"title": "New Module"}
        )
        assert response.status_code == 201

    def test_sme_cannot_add_module(self, sme_client):
        """SME without add_structure cannot add modules."""
        response = sme_client.post(
            "/api/courses/course1/modules",
            json={"title": "New Module"}
        )
        assert response.status_code == 403

    def test_owner_can_delete_module(self, owner_client):
        """Owner with delete_structure can delete modules."""
        response = owner_client.delete("/api/courses/course1/modules/mod1")
        assert response.status_code == 200

    def test_designer_cannot_delete_module(self, designer_client):
        """Designer without delete_structure cannot delete modules."""
        response = designer_client.delete("/api/courses/course1/modules/mod1")
        assert response.status_code == 403

    def test_designer_can_reorder_modules(self, app, designer_client):
        """Designer with reorder_structure can reorder modules."""
        # Add second module for reordering
        with app.app_context():
            from src.api.modules import _project_store
            course = _project_store.load.return_value
            module2 = Module(id="mod2", title="Module 2", order=1)
            course.modules.append(module2)

        response = designer_client.put(
            "/api/courses/course1/modules/reorder",
            json={"old_index": 0, "new_index": 1}
        )
        assert response.status_code == 200

    def test_sme_cannot_reorder_modules(self, sme_client):
        """SME without reorder_structure cannot reorder."""
        response = sme_client.put(
            "/api/courses/course1/modules/reorder",
            json={"old_index": 0, "new_index": 1}
        )
        assert response.status_code == 403


# ===========================================================================
# Content Workflow Tests
# ===========================================================================

class TestContentWorkflow:
    """Test content generation and approval workflow permissions."""

    @patch('src.generators.video_script_generator.VideoScriptGenerator.generate')
    def test_designer_can_generate_content(self, mock_generate, designer_client):
        """Designer with generate_content can generate."""
        mock_content = MagicMock()
        mock_content.model_dump.return_value = {"title": "Test"}
        mock_content.model_dump_json.return_value = '{"title": "Test"}'
        mock_generate.return_value = (mock_content, {"word_count": 100})

        response = designer_client.post(
            "/api/courses/course1/activities/act1/generate",
            json={}
        )
        # Should pass permission check (may fail on actual generation due to mocking)
        assert response.status_code != 403

    def test_designer_can_edit_content(self, designer_client):
        """Designer with edit_content can edit content."""
        response = designer_client.put(
            "/api/courses/course1/activities/act1/content",
            json={"content": "Updated content"}
        )
        assert response.status_code == 200

    def test_designer_cannot_approve_via_state_transition(self, app, designer_client):
        """Designer cannot transition to APPROVED state."""
        with app.app_context():
            from src.api.build_state import _project_store
            course = _project_store.load.return_value
            course.modules[0].lessons[0].activities[0].build_state = BuildState.REVIEWED

        response = designer_client.put(
            "/api/courses/course1/activities/act1/state",
            json={"build_state": "approved"}
        )
        assert response.status_code == 403

    def test_reviewer_can_approve(self, app, reviewer_client):
        """Reviewer with approve_content can approve."""
        with app.app_context():
            from src.api.build_state import _project_store
            course = _project_store.load.return_value
            course.modules[0].lessons[0].activities[0].build_state = BuildState.REVIEWED

        response = reviewer_client.post("/api/courses/course1/activities/act1/approve")
        assert response.status_code == 200

    def test_sme_cannot_generate(self, sme_client):
        """SME without generate_content cannot generate."""
        response = sme_client.post(
            "/api/courses/course1/activities/act1/generate",
            json={}
        )
        assert response.status_code == 403


# ===========================================================================
# Audit Trail Tests
# ===========================================================================

class TestAuditTrail:
    """Test that changes are logged to audit trail."""

    def test_module_creation_logged(self, app, owner_client):
        """Creating a module should log an audit entry."""
        response = owner_client.post(
            "/api/courses/course1/modules",
            json={"title": "Audit Test Module"}
        )
        assert response.status_code == 201

        # Check audit log
        with app.app_context():
            entries = AuditEntry.get_for_course("course1")
            actions = [e.action for e in entries]
            assert "structure_added" in actions

    def test_content_update_logged_with_diff(self, app, owner_client):
        """Content updates should log with before/after state."""
        response = owner_client.put(
            "/api/courses/course1/activities/act1/content",
            json={"content": "Updated content for audit test"}
        )
        assert response.status_code == 200

        with app.app_context():
            entries = AuditEntry.get_for_course("course1")
            content_updates = [e for e in entries if e.action == "content_updated"]
            assert len(content_updates) >= 1
            # Check that changes are recorded
            if content_updates:
                entry = content_updates[0]
                assert entry.changes is not None

    def test_approval_logged_with_user(self, app, reviewer_client):
        """Approval should log with user attribution."""
        with app.app_context():
            from src.api.build_state import _project_store
            course = _project_store.load.return_value
            course.modules[0].lessons[0].activities[0].build_state = BuildState.REVIEWED

        response = reviewer_client.post("/api/courses/course1/activities/act1/approve")
        assert response.status_code == 200

        with app.app_context():
            entries = AuditEntry.get_for_course("course1")
            approvals = [e for e in entries if e.action == "content_approved"]
            assert len(approvals) >= 1
            if approvals:
                assert approvals[0].user_id == 3  # Reviewer user ID

    def test_activity_feed_shows_all_actions(self, app, owner_client):
        """Activity feed should include all logged actions."""
        # Perform several actions
        owner_client.post("/api/courses/course1/modules", json={"title": "Feed Test 1"})
        owner_client.post("/api/courses/course1/modules", json={"title": "Feed Test 2"})

        # Get activity feed
        response = owner_client.get("/api/courses/course1/activity")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "feed" in data
        assert len(data["feed"]) >= 2


# ===========================================================================
# Full Collaboration Flow Tests
# ===========================================================================

class TestCollaborationFlow:
    """Test complete collaboration workflows."""

    def test_full_collaboration_workflow(self, app, client):
        """Test complete flow: create -> invite -> design -> review -> approve."""
        # 1. Owner creates course (auto-owner)
        setup_user_with_role(app, 10, "flowowner@example.com", "Flow Owner", "course1", "Owner", 10)

        # Login as owner
        with client.session_transaction() as sess:
            sess["_user_id"] = "10"

        # Verify owner can access
        response = client.get("/api/courses/course1/modules")
        assert response.status_code == 200

        # 2. Owner invites Designer
        setup_user_with_role(app, 11, "flowdesigner@example.com", "Flow Designer", "course1", "Designer", 10)

        # 3. Designer creates module (login as designer)
        with client.session_transaction() as sess:
            sess["_user_id"] = "11"

        response = client.post(
            "/api/courses/course1/modules",
            json={"title": "Designed Module"}
        )
        assert response.status_code == 201

        # 4. Invite Reviewer
        setup_user_with_role(app, 12, "flowreviewer@example.com", "Flow Reviewer", "course1", "Reviewer", 10)

        # 5. Reviewer approves content (login as reviewer, need REVIEWED state)
        with app.app_context():
            from src.api.build_state import _project_store
            course = _project_store.load.return_value
            course.modules[0].lessons[0].activities[0].build_state = BuildState.REVIEWED

        with client.session_transaction() as sess:
            sess["_user_id"] = "12"

        # Verify reviewer role has correct permissions
        with app.app_context():
            from src.collab.permissions import get_user_permissions
            perms = get_user_permissions(12, "course1")
            assert "approve_content" in perms, f"Reviewer permissions: {perms}"

        response = client.post("/api/courses/course1/activities/act1/approve")
        assert response.status_code == 200, f"Approve failed: {response.data.decode()}"

        # 6. All actions should be in audit trail
        with app.app_context():
            entries = AuditEntry.get_for_course("course1")
            actions = [e.action for e in entries]
            assert "structure_added" in actions
            assert "content_approved" in actions

    def test_revoked_collaborator_loses_access(self, app, client):
        """After removal, collaborator should get 403."""
        # First create an owner for the course
        setup_user_with_role(app, 20, "revokeowner@example.com", "Revoke Owner", "course1", "Owner", 20)

        # Setup user with role
        setup_user_with_role(app, 21, "removed@example.com", "Removed User", "course1", "Designer", 20)

        # User can access
        with client.session_transaction() as sess:
            sess["_user_id"] = "21"

        response = client.get("/api/courses/course1/modules")
        assert response.status_code == 200

        # Remove collaborator
        with app.app_context():
            db = get_db()
            db.execute("DELETE FROM collaborator WHERE user_id = 21 AND course_id = 'course1'")
            db.commit()

        # User should now get 403
        response = client.get("/api/courses/course1/modules")
        assert response.status_code == 403


# ===========================================================================
# Edge Case Tests
# ===========================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_role_change_takes_effect_immediately(self, app, client):
        """Permission changes should take effect without caching issues."""
        # First create an owner for the course
        setup_user_with_role(app, 30, "changeowner@example.com", "Change Owner", "course1", "Owner", 30)

        # Create user as Designer
        setup_user_with_role(app, 31, "rolechange@example.com", "Role Change User", "course1", "Designer", 30)

        with client.session_transaction() as sess:
            sess["_user_id"] = "31"

        # Can add modules as Designer
        response = client.post(
            "/api/courses/course1/modules",
            json={"title": "Designer Module"}
        )
        assert response.status_code == 201

        # Change role to SME (removes add_structure)
        with app.app_context():
            db = get_db()
            # Get or create SME role for this course
            existing_sme = db.execute(
                "SELECT id FROM course_role WHERE course_id = ? AND name = ?",
                ("course1", "SME")
            ).fetchone()
            if existing_sme:
                sme_role_id = existing_sme["id"]
            else:
                sme_role = Role.create_from_template("course1", "SME")
                sme_role_id = sme_role.id
            db.execute(
                "UPDATE collaborator SET role_id = ? WHERE user_id = 31 AND course_id = 'course1'",
                (sme_role_id,)
            )
            db.commit()

        # Should now fail
        response = client.post(
            "/api/courses/course1/modules",
            json={"title": "SME Module"}
        )
        assert response.status_code == 403

    def test_deleted_user_shows_in_audit(self, app, owner_client):
        """Deleted users should show as [Deleted User] in audit."""
        # Create an audit entry from a user that will be deleted
        with app.app_context():
            from src.collab.audit import log_audit_entry, ACTION_STRUCTURE_ADDED
            log_audit_entry(
                course_id="course1",
                user_id=999,  # Non-existent user
                action=ACTION_STRUCTURE_ADDED,
                entity_type="module",
                entity_id="test_mod"
            )

        # Get activity feed
        response = owner_client.get("/api/courses/course1/activity")
        assert response.status_code == 200
        data = json.loads(response.data)

        # Find entry from deleted user
        deleted_entries = [
            e for e in data["feed"]
            if e.get("user_name") == "[Deleted User]"
        ]
        assert len(deleted_entries) >= 1

    def test_non_collaborator_denied_access(self, app, client):
        """Users who are not collaborators should be denied access."""
        # First create an owner for the course (so the course exists)
        setup_user_with_role(app, 50, "noncollabowner@example.com", "NonCollab Owner", "course1", "Owner", 50)

        # Create a user who is not a collaborator
        with app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO user (id, email, name, password_hash) VALUES (?, ?, ?, 'hash')",
                (99, "stranger@example.com", "Stranger User")
            )
            db.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = "99"

        response = client.get("/api/courses/course1/modules")
        assert response.status_code == 403

    def test_export_requires_permission(self, app, client):
        """Export should require export_course permission."""
        # Create owner for the course
        setup_user_with_role(app, 40, "exportowner@example.com", "Export Owner", "course1", "Owner", 40)

        # Create SME (has export_course permission)
        setup_user_with_role(app, 41, "exportsme@example.com", "Export SME", "course1", "SME", 40)

        # SME has export_course permission
        with client.session_transaction() as sess:
            sess["_user_id"] = "41"

        response = client.get("/api/courses/course1/export/preview?format=instructor")
        assert response.status_code != 403

        # Owner also has it
        with client.session_transaction() as sess:
            sess["_user_id"] = "40"

        response = client.get("/api/courses/course1/export/preview?format=instructor")
        assert response.status_code != 403


# ===========================================================================
# Learning Outcomes Permission Tests
# ===========================================================================

class TestLearningOutcomesPermissions:
    """Test learning outcomes require manage_outcomes permission."""

    def test_owner_can_manage_outcomes(self, owner_client):
        """Owner with manage_outcomes can manage learning outcomes."""
        response = owner_client.post(
            "/api/courses/course1/outcomes",
            json={"behavior": "Test outcome", "bloom_level": "apply"}
        )
        assert response.status_code == 201

    def test_designer_can_manage_outcomes(self, designer_client):
        """Designer with manage_outcomes can manage learning outcomes."""
        response = designer_client.post(
            "/api/courses/course1/outcomes",
            json={"behavior": "Designer outcome", "bloom_level": "analyze"}
        )
        assert response.status_code == 201

    def test_sme_cannot_manage_outcomes(self, sme_client):
        """SME without manage_outcomes cannot manage learning outcomes."""
        response = sme_client.post(
            "/api/courses/course1/outcomes",
            json={"behavior": "SME outcome", "bloom_level": "apply"}
        )
        assert response.status_code == 403

    def test_reviewer_cannot_manage_outcomes(self, reviewer_client):
        """Reviewer without manage_outcomes cannot manage learning outcomes."""
        response = reviewer_client.post(
            "/api/courses/course1/outcomes",
            json={"behavior": "Reviewer outcome", "bloom_level": "apply"}
        )
        assert response.status_code == 403
