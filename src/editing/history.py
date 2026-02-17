"""Edit history management with undo/redo command pattern.

Provides in-memory undo/redo stacks for text editing operations with
session-scoped history management and size limits.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Tuple
import secrets


@dataclass
class EditCommand:
    """Represents a single edit operation for undo/redo.

    Attributes:
        id: Unique command identifier
        action: Description of what was done (e.g., "improve", "expand")
        before: Content before the edit
        after: Content after the edit
        timestamp: ISO 8601 timestamp when edit occurred
        metadata: Additional context (action type, selections, etc.)
    """
    id: str
    action: str
    before: str
    after: str
    timestamp: str
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert command to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'EditCommand':
        """Create EditCommand from dictionary."""
        return cls(
            id=data['id'],
            action=data['action'],
            before=data['before'],
            after=data['after'],
            timestamp=data['timestamp'],
            metadata=data.get('metadata', {})
        )


class EditHistory:
    """Manages undo/redo stacks for a single activity in a session.

    Implements command pattern with dual stacks:
    - undo_stack: commands that can be undone
    - redo_stack: commands that can be redone

    When a new command is pushed:
    - Added to undo_stack
    - redo_stack is cleared (new edit path)

    When undo() is called:
    - Command popped from undo_stack
    - Command pushed to redo_stack

    When redo() is called:
    - Command popped from redo_stack
    - Command pushed to undo_stack
    """

    def __init__(self, max_size: int = 100):
        """Initialize edit history with size limit.

        Args:
            max_size: Maximum number of commands in undo stack
        """
        self.max_size = max_size
        self.undo_stack: List[EditCommand] = []
        self.redo_stack: List[EditCommand] = []

    def push(self, command: EditCommand) -> None:
        """Add command to undo stack and clear redo stack.

        Args:
            command: Edit command to add
        """
        # Add to undo stack
        self.undo_stack.append(command)

        # Enforce size limit (remove oldest)
        if len(self.undo_stack) > self.max_size:
            self.undo_stack.pop(0)

        # Clear redo stack (new edit path)
        self.redo_stack.clear()

    def undo(self) -> Optional[EditCommand]:
        """Undo last command by moving from undo to redo stack.

        Returns:
            Command that was undone, or None if nothing to undo
        """
        if not self.undo_stack:
            return None

        # Pop from undo stack
        command = self.undo_stack.pop()

        # Push to redo stack
        self.redo_stack.append(command)

        return command

    def redo(self) -> Optional[EditCommand]:
        """Redo last undone command by moving from redo to undo stack.

        Returns:
            Command that was redone, or None if nothing to redo
        """
        if not self.redo_stack:
            return None

        # Pop from redo stack
        command = self.redo_stack.pop()

        # Push to undo stack
        self.undo_stack.append(command)

        return command

    def can_undo(self) -> bool:
        """Check if undo is available."""
        return len(self.undo_stack) > 0

    def can_redo(self) -> bool:
        """Check if redo is available."""
        return len(self.redo_stack) > 0

    def get_undo_stack(self) -> List[EditCommand]:
        """Get copy of undo stack for UI display.

        Returns most recent first (reverse chronological).
        """
        return list(reversed(self.undo_stack))

    def get_redo_stack(self) -> List[EditCommand]:
        """Get copy of redo stack for UI display.

        Returns most recent first (reverse chronological).
        """
        return list(reversed(self.redo_stack))

    def clear(self) -> None:
        """Clear both undo and redo stacks."""
        self.undo_stack.clear()
        self.redo_stack.clear()


class SessionHistoryManager:
    """Manages edit histories across sessions and activities.

    Uses in-memory storage keyed by (session_id, activity_id) tuples.
    Each combination gets its own EditHistory instance.

    Includes cleanup mechanism to remove old sessions.
    """

    def __init__(self):
        """Initialize session history manager."""
        # Storage: {(session_id, activity_id): (EditHistory, last_accessed)}
        self._histories: Dict[Tuple[str, str], Tuple[EditHistory, datetime]] = {}

    def get_history(self, session_id: str, activity_id: str) -> EditHistory:
        """Get or create edit history for session and activity.

        Args:
            session_id: Flask session ID
            activity_id: Activity being edited

        Returns:
            EditHistory instance for this combination
        """
        key = (session_id, activity_id)

        if key in self._histories:
            history, _ = self._histories[key]
            # Update last accessed time
            self._histories[key] = (history, datetime.now(timezone.utc))
            return history

        # Create new history
        history = EditHistory()
        self._histories[key] = (history, datetime.now(timezone.utc))
        return history

    def cleanup_old_sessions(self, max_age_hours: int = 24) -> int:
        """Remove histories for sessions not accessed recently.

        Args:
            max_age_hours: Hours of inactivity before cleanup

        Returns:
            Number of sessions cleaned up
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

        # Find old sessions
        old_keys = [
            key for key, (_, last_accessed) in self._histories.items()
            if last_accessed < cutoff
        ]

        # Remove them
        for key in old_keys:
            del self._histories[key]

        return len(old_keys)

    def clear_all(self) -> None:
        """Clear all histories (for testing)."""
        self._histories.clear()


# Global session manager instance
_session_manager = SessionHistoryManager()


def get_session_manager() -> SessionHistoryManager:
    """Get global session history manager instance."""
    return _session_manager
