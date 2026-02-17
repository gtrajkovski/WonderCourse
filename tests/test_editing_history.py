"""Tests for edit history and version management."""

import pytest
import json
from datetime import datetime
import secrets

from src.editing.history import EditHistory, EditCommand, SessionHistoryManager, get_session_manager
from src.editing.version_store import VersionStore, Version
from src.core.models import Course, Module, Lesson, Activity, ContentType


class TestEditHistory:
    """Tests for EditHistory class."""

    def test_push_command(self):
        """Test pushing command to undo stack."""
        history = EditHistory()

        command = EditCommand(
            id="cmd_1",
            action="improve",
            before="old text",
            after="new text",
            timestamp=datetime.utcnow().isoformat() + "Z",
            metadata={"action_type": "ai_suggest"}
        )

        history.push(command)

        assert history.can_undo()
        assert not history.can_redo()
        assert len(history.get_undo_stack()) == 1

    def test_undo_redo_cycle(self):
        """Test undo/redo cycle."""
        history = EditHistory()

        # Push two commands
        cmd1 = EditCommand(
            id="cmd_1",
            action="improve",
            before="text1",
            after="text2",
            timestamp=datetime.utcnow().isoformat() + "Z",
            metadata={}
        )
        cmd2 = EditCommand(
            id="cmd_2",
            action="expand",
            before="text2",
            after="text3",
            timestamp=datetime.utcnow().isoformat() + "Z",
            metadata={}
        )

        history.push(cmd1)
        history.push(cmd2)

        # Undo once
        undone = history.undo()
        assert undone.id == "cmd_2"
        assert history.can_undo()
        assert history.can_redo()

        # Undo again
        undone = history.undo()
        assert undone.id == "cmd_1"
        assert not history.can_undo()
        assert history.can_redo()

        # Redo once
        redone = history.redo()
        assert redone.id == "cmd_1"
        assert history.can_undo()
        assert history.can_redo()

        # Redo again
        redone = history.redo()
        assert redone.id == "cmd_2"
        assert history.can_undo()
        assert not history.can_redo()

    def test_undo_stack_limit(self):
        """Test undo stack size limit enforcement."""
        history = EditHistory(max_size=3)

        # Push 5 commands (exceeds limit)
        for i in range(5):
            cmd = EditCommand(
                id=f"cmd_{i}",
                action="improve",
                before=f"text{i}",
                after=f"text{i+1}",
                timestamp=datetime.utcnow().isoformat() + "Z",
                metadata={}
            )
            history.push(cmd)

        # Only last 3 should remain
        undo_stack = history.get_undo_stack()
        assert len(undo_stack) == 3
        assert undo_stack[0].id == "cmd_4"  # Most recent first
        assert undo_stack[1].id == "cmd_3"
        assert undo_stack[2].id == "cmd_2"

    def test_redo_cleared_on_new_push(self):
        """Test that redo stack is cleared on new push."""
        history = EditHistory()

        # Push two commands
        cmd1 = EditCommand(
            id="cmd_1",
            action="improve",
            before="text1",
            after="text2",
            timestamp=datetime.utcnow().isoformat() + "Z",
            metadata={}
        )
        cmd2 = EditCommand(
            id="cmd_2",
            action="expand",
            before="text2",
            after="text3",
            timestamp=datetime.utcnow().isoformat() + "Z",
            metadata={}
        )

        history.push(cmd1)
        history.push(cmd2)

        # Undo both
        history.undo()
        history.undo()

        # Verify redo stack has commands
        assert history.can_redo()
        assert len(history.get_redo_stack()) == 2

        # Push new command (creates new edit path)
        cmd3 = EditCommand(
            id="cmd_3",
            action="simplify",
            before="text1",
            after="text4",
            timestamp=datetime.utcnow().isoformat() + "Z",
            metadata={}
        )
        history.push(cmd3)

        # Redo stack should be cleared
        assert not history.can_redo()
        assert len(history.get_redo_stack()) == 0

    def test_undo_when_empty(self):
        """Test undo when stack is empty."""
        history = EditHistory()

        result = history.undo()
        assert result is None
        assert not history.can_undo()

    def test_redo_when_empty(self):
        """Test redo when stack is empty."""
        history = EditHistory()

        result = history.redo()
        assert result is None
        assert not history.can_redo()

    def test_clear_history(self):
        """Test clearing both stacks."""
        history = EditHistory()

        # Push command
        cmd = EditCommand(
            id="cmd_1",
            action="improve",
            before="text1",
            after="text2",
            timestamp=datetime.utcnow().isoformat() + "Z",
            metadata={}
        )
        history.push(cmd)
        history.undo()

        # Clear
        history.clear()

        assert not history.can_undo()
        assert not history.can_redo()
        assert len(history.get_undo_stack()) == 0
        assert len(history.get_redo_stack()) == 0


class TestSessionHistoryManager:
    """Tests for SessionHistoryManager class."""

    def test_get_history_creates_new(self):
        """Test that get_history creates new history if not exists."""
        manager = SessionHistoryManager()

        history = manager.get_history("session_1", "activity_1")

        assert history is not None
        assert isinstance(history, EditHistory)

    def test_get_history_returns_same_instance(self):
        """Test that get_history returns same instance for same session/activity."""
        manager = SessionHistoryManager()

        history1 = manager.get_history("session_1", "activity_1")
        history2 = manager.get_history("session_1", "activity_1")

        assert history1 is history2

    def test_session_isolation(self):
        """Test that different sessions get different histories."""
        manager = SessionHistoryManager()

        history1 = manager.get_history("session_1", "activity_1")
        history2 = manager.get_history("session_2", "activity_1")

        assert history1 is not history2

        # Modify one history
        cmd = EditCommand(
            id="cmd_1",
            action="improve",
            before="text1",
            after="text2",
            timestamp=datetime.utcnow().isoformat() + "Z",
            metadata={}
        )
        history1.push(cmd)

        # Other history should be unaffected
        assert history1.can_undo()
        assert not history2.can_undo()

    def test_activity_isolation(self):
        """Test that different activities get different histories."""
        manager = SessionHistoryManager()

        history1 = manager.get_history("session_1", "activity_1")
        history2 = manager.get_history("session_1", "activity_2")

        assert history1 is not history2

    def test_cleanup_old_sessions(self):
        """Test cleanup of old sessions."""
        manager = SessionHistoryManager()

        # Create some histories
        manager.get_history("session_1", "activity_1")
        manager.get_history("session_2", "activity_2")

        # Cleanup with 0 max age (clears all)
        cleaned = manager.cleanup_old_sessions(max_age_hours=0)

        assert cleaned == 2


class TestVersionStore:
    """Tests for VersionStore class."""

    def test_save_version(self, tmp_store, sample_course_with_content):
        """Test saving a named version."""
        # Save course
        tmp_store.save("user1", sample_course_with_content)

        # Get first activity
        activity = sample_course_with_content.modules[0].lessons[0].activities[0]

        # Create version store
        version_store = VersionStore(tmp_store)

        # Save version
        version = version_store.save_version(
            sample_course_with_content.id,
            activity.id,
            "First draft",
            {"title": "Test", "content": "Test content"},
            "user1"
        )

        assert version.id.startswith("ver_")
        assert version.name == "First draft"
        assert version.activity_id == activity.id
        assert version.content == {"title": "Test", "content": "Test content"}
        assert version.created_by == "user1"

    def test_list_versions(self, tmp_store, sample_course_with_content):
        """Test listing versions for activity."""
        # Save course
        tmp_store.save("user1", sample_course_with_content)

        # Get first activity
        activity = sample_course_with_content.modules[0].lessons[0].activities[0]

        # Create version store
        version_store = VersionStore(tmp_store)

        # Save two versions
        version_store.save_version(
            sample_course_with_content.id,
            activity.id,
            "Version 1",
            {"content": "v1"},
            "user1"
        )
        version_store.save_version(
            sample_course_with_content.id,
            activity.id,
            "Version 2",
            {"content": "v2"},
            "user1"
        )

        # List versions
        versions = version_store.list_versions(sample_course_with_content.id, activity.id, "user1")

        assert len(versions) == 2
        # Most recent first
        assert versions[0].name == "Version 2"
        assert versions[1].name == "Version 1"

    def test_get_version(self, tmp_store, sample_course_with_content):
        """Test getting specific version."""
        # Save course
        tmp_store.save("user1", sample_course_with_content)

        # Get first activity
        activity = sample_course_with_content.modules[0].lessons[0].activities[0]

        # Create version store
        version_store = VersionStore(tmp_store)

        # Save version
        saved_version = version_store.save_version(
            sample_course_with_content.id,
            activity.id,
            "Test version",
            {"content": "test"},
            "user1"
        )

        # Get version
        retrieved_version = version_store.get_version(
            sample_course_with_content.id,
            activity.id,
            saved_version.id,
            "user1"
        )

        assert retrieved_version.id == saved_version.id
        assert retrieved_version.name == "Test version"

    def test_restore_version(self, tmp_store, sample_course_with_content):
        """Test restoring version content to activity."""
        # Save course
        tmp_store.save("user1", sample_course_with_content)

        # Get first activity
        activity = sample_course_with_content.modules[0].lessons[0].activities[0]
        original_content = activity.content

        # Create version store
        version_store = VersionStore(tmp_store)

        # Save version with different content
        version = version_store.save_version(
            sample_course_with_content.id,
            activity.id,
            "Backup",
            {"title": "Restored", "content": "Restored content"},
            "user1"
        )

        # Modify activity content
        course = tmp_store.load("user1", sample_course_with_content.id)
        activity = course.modules[0].lessons[0].activities[0]
        activity.content = "Modified content"
        tmp_store.save("user1", course)

        # Restore version
        restored_content = version_store.restore_version(
            sample_course_with_content.id,
            activity.id,
            version.id,
            "user1"
        )

        assert restored_content == {"title": "Restored", "content": "Restored content"}

        # Verify activity content was restored
        course = tmp_store.load("user1", sample_course_with_content.id)
        activity = course.modules[0].lessons[0].activities[0]
        assert activity.content == {"title": "Restored", "content": "Restored content"}

    def test_delete_version(self, tmp_store, sample_course_with_content):
        """Test deleting a version."""
        # Save course
        tmp_store.save("user1", sample_course_with_content)

        # Get first activity
        activity = sample_course_with_content.modules[0].lessons[0].activities[0]

        # Create version store
        version_store = VersionStore(tmp_store)

        # Save version
        version = version_store.save_version(
            sample_course_with_content.id,
            activity.id,
            "To delete",
            {"content": "test"},
            "user1"
        )

        # Delete version
        deleted = version_store.delete_version(
            sample_course_with_content.id,
            activity.id,
            version.id,
            "user1"
        )

        assert deleted is True

        # Verify version no longer exists
        with pytest.raises(ValueError, match="Version not found"):
            version_store.get_version(
                sample_course_with_content.id,
                activity.id,
                version.id,
                "user1"
            )

    def test_version_limit(self, tmp_store, sample_course_with_content):
        """Test 20-version limit enforcement."""
        # Save course
        tmp_store.save("user1", sample_course_with_content)

        # Get first activity
        activity = sample_course_with_content.modules[0].lessons[0].activities[0]

        # Create version store
        version_store = VersionStore(tmp_store)

        # Save 25 versions (exceeds limit of 20)
        for i in range(25):
            version_store.save_version(
                sample_course_with_content.id,
                activity.id,
                f"Version {i}",
                {"content": f"v{i}"},
                "user1"
            )

        # List versions
        versions = version_store.list_versions(sample_course_with_content.id, activity.id, "user1")

        # Only 20 should remain (oldest deleted)
        assert len(versions) == 20
        # Most recent first
        assert versions[0].name == "Version 24"
        assert versions[19].name == "Version 5"

    def test_compare_versions(self, tmp_store, sample_course_with_content):
        """Test comparing two versions."""
        # Save course
        tmp_store.save("user1", sample_course_with_content)

        # Get first activity
        activity = sample_course_with_content.modules[0].lessons[0].activities[0]

        # Create version store
        version_store = VersionStore(tmp_store)

        # Save two versions
        v1 = version_store.save_version(
            sample_course_with_content.id,
            activity.id,
            "Version 1",
            {"content": "Line 1\nLine 2"},
            "user1"
        )
        v2 = version_store.save_version(
            sample_course_with_content.id,
            activity.id,
            "Version 2",
            {"content": "Line 1\nLine 3"},
            "user1"
        )

        # Compare versions
        diff_result = version_store.compare_versions(
            sample_course_with_content.id,
            activity.id,
            v1.id,
            v2.id,
            "user1"
        )

        assert diff_result is not None
        assert diff_result.unified_diff is not None
        # Should show change from Line 2 to Line 3
        assert "Line 2" in diff_result.unified_diff or "Line 3" in diff_result.unified_diff
