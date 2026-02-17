"""Audit trail for tracking all course changes.

Provides AuditEntry model and utilities for logging changes with efficient diff storage.
All changes are tracked with user attribution for accountability.
"""

import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from jsondiff import diff
from src.auth.db import get_db


# Content actions
ACTION_CONTENT_CREATED = "content_created"
ACTION_CONTENT_UPDATED = "content_updated"
ACTION_CONTENT_DELETED = "content_deleted"
ACTION_CONTENT_GENERATED = "content_generated"
ACTION_CONTENT_APPROVED = "content_approved"

# Structure actions
ACTION_STRUCTURE_ADDED = "structure_added"
ACTION_STRUCTURE_UPDATED = "structure_updated"
ACTION_STRUCTURE_DELETED = "structure_deleted"
ACTION_STRUCTURE_REORDERED = "structure_reordered"

# Collaborator actions
ACTION_COLLABORATOR_INVITED = "collaborator_invited"
ACTION_COLLABORATOR_JOINED = "collaborator_joined"
ACTION_COLLABORATOR_REMOVED = "collaborator_removed"
ACTION_COLLABORATOR_ROLE_CHANGED = "collaborator_role_changed"

# Course actions
ACTION_COURSE_CREATED = "course_created"
ACTION_COURSE_UPDATED = "course_updated"
ACTION_COURSE_EXPORTED = "course_exported"
ACTION_COURSE_PUBLISHED = "course_published"


class AuditEntry:
    """Represents a single audit log entry."""

    def __init__(
        self,
        id: int,
        course_id: str,
        user_id: int,
        action: str,
        entity_type: str,
        entity_id: Optional[str],
        changes: Optional[str],
        created_at: datetime,
        user_name: Optional[str] = None,
        user_email: Optional[str] = None,
    ):
        self.id = id
        self.course_id = course_id
        self.user_id = user_id
        self.action = action
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.changes = changes
        self.created_at = created_at
        self.user_name = user_name
        self.user_email = user_email

    @classmethod
    def get_for_course(
        cls, course_id: str, limit: int = 50, offset: int = 0
    ) -> List["AuditEntry"]:
        """Get paginated audit entries for a course with user info."""
        db = get_db()
        rows = db.execute(
            """
            SELECT
                a.id, a.course_id, a.user_id, a.action, a.entity_type,
                a.entity_id, a.changes, a.created_at,
                u.name as user_name, u.email as user_email
            FROM audit_entry a
            LEFT JOIN user u ON a.user_id = u.id
            WHERE a.course_id = ?
            ORDER BY a.created_at DESC, a.id DESC
            LIMIT ? OFFSET ?
            """,
            (course_id, limit, offset),
        ).fetchall()

        return [cls._from_row(row) for row in rows]

    @classmethod
    def get_for_entity(
        cls, course_id: str, entity_type: str, entity_id: str
    ) -> List["AuditEntry"]:
        """Get audit history for a specific entity."""
        db = get_db()
        rows = db.execute(
            """
            SELECT
                a.id, a.course_id, a.user_id, a.action, a.entity_type,
                a.entity_id, a.changes, a.created_at,
                u.name as user_name, u.email as user_email
            FROM audit_entry a
            LEFT JOIN user u ON a.user_id = u.id
            WHERE a.course_id = ? AND a.entity_type = ? AND a.entity_id = ?
            ORDER BY a.created_at DESC, a.id DESC
            """,
            (course_id, entity_type, entity_id),
        ).fetchall()

        return [cls._from_row(row) for row in rows]

    @classmethod
    def get_by_user(cls, course_id: str, user_id: int) -> List["AuditEntry"]:
        """Get all audit entries for a specific user in a course."""
        db = get_db()
        rows = db.execute(
            """
            SELECT
                a.id, a.course_id, a.user_id, a.action, a.entity_type,
                a.entity_id, a.changes, a.created_at,
                u.name as user_name, u.email as user_email
            FROM audit_entry a
            LEFT JOIN user u ON a.user_id = u.id
            WHERE a.course_id = ? AND a.user_id = ?
            ORDER BY a.created_at DESC, a.id DESC
            """,
            (course_id, user_id),
        ).fetchall()

        return [cls._from_row(row) for row in rows]

    @staticmethod
    def _from_row(row) -> "AuditEntry":
        """Create AuditEntry from database row."""
        return AuditEntry(
            id=row["id"],
            course_id=row["course_id"],
            user_id=row["user_id"],
            action=row["action"],
            entity_type=row["entity_type"],
            entity_id=row["entity_id"],
            changes=row["changes"],
            created_at=row["created_at"],
            user_name=row["user_name"],
            user_email=row["user_email"],
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize audit entry for API responses."""
        return {
            "id": self.id,
            "course_id": self.course_id,
            "user_id": self.user_id,
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "changes": json.loads(self.changes) if self.changes else None,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "user_name": self.user_name or "[Deleted User]",
            "user_email": self.user_email,
        }


def log_audit_entry(
    course_id: str,
    user_id: int,
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    before: Optional[Dict[str, Any]] = None,
    after: Optional[Dict[str, Any]] = None,
) -> AuditEntry:
    """Log an audit entry with optional diff calculation.

    Args:
        course_id: Course identifier
        user_id: User who performed the action
        action: Action constant (e.g., ACTION_CONTENT_UPDATED)
        entity_type: Type of entity affected
        entity_id: ID of the affected entity
        before: Entity state before change (for diff calculation)
        after: Entity state after change (for diff calculation)

    Returns:
        Created AuditEntry instance
    """
    db = get_db()

    # Calculate diff if before and after provided
    changes_json = None
    if before is not None and after is not None:
        changes_dict = diff(before, after, marshal=True)
        changes_json = json.dumps(changes_dict)

    cursor = db.execute(
        """
        INSERT INTO audit_entry
        (course_id, user_id, action, entity_type, entity_id, changes)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (course_id, user_id, action, entity_type, entity_id, changes_json),
    )
    db.commit()

    # Fetch the created entry with user info
    row = db.execute(
        """
        SELECT
            a.id, a.course_id, a.user_id, a.action, a.entity_type,
            a.entity_id, a.changes, a.created_at,
            u.name as user_name, u.email as user_email
        FROM audit_entry a
        LEFT JOIN user u ON a.user_id = u.id
        WHERE a.id = ?
        """,
        (cursor.lastrowid,),
    ).fetchone()

    return AuditEntry._from_row(row)


def get_activity_feed(
    course_id: str, limit: int = 50, offset: int = 0
) -> List[Dict[str, Any]]:
    """Get activity feed with human-readable summaries.

    Returns list of dicts with:
    - action, entity_type, entity_id, created_at
    - user_name (or "[Deleted User]" if user deleted)
    - summary (human-readable description)
    """
    entries = AuditEntry.get_for_course(course_id, limit, offset)

    feed = []
    for entry in entries:
        changes_dict = json.loads(entry.changes) if entry.changes else {}

        feed.append({
            "action": entry.action,
            "entity_type": entry.entity_type,
            "entity_id": entry.entity_id,
            "created_at": entry.created_at.isoformat() if isinstance(entry.created_at, datetime) else entry.created_at,
            "user_name": entry.user_name or "[Deleted User]",
            "summary": summarize_changes(entry.action, entry.entity_type, changes_dict),
        })

    return feed


def summarize_changes(
    action: str, entity_type: str, changes_dict: Dict[str, Any]
) -> str:
    """Generate human-readable summary of changes.

    Args:
        action: Action constant
        entity_type: Type of entity
        changes_dict: Parsed changes JSON (from jsondiff)

    Returns:
        Human-readable summary string
    """
    # Content actions
    if action == ACTION_CONTENT_CREATED:
        return f"Created {entity_type} content"
    elif action == ACTION_CONTENT_UPDATED:
        if changes_dict:
            fields = list(changes_dict.keys())
            if len(fields) == 1:
                return f"Updated {entity_type} {fields[0]}"
            elif len(fields) == 2:
                return f"Updated {entity_type} {fields[0]} and {fields[1]}"
            else:
                return f"Updated {entity_type} content and state"
        return f"Updated {entity_type}"
    elif action == ACTION_CONTENT_DELETED:
        return f"Deleted {entity_type} content"
    elif action == ACTION_CONTENT_GENERATED:
        return f"Generated {entity_type} content"
    elif action == ACTION_CONTENT_APPROVED:
        return f"Approved {entity_type} content"

    # Structure actions
    elif action == ACTION_STRUCTURE_ADDED:
        name = changes_dict.get("name", "")
        if name:
            return f"Added {entity_type} '{name}'"
        return f"Added {entity_type}"
    elif action == ACTION_STRUCTURE_UPDATED:
        if changes_dict:
            fields = list(changes_dict.keys())
            return f"Updated {entity_type} {', '.join(fields[:2])}"
        return f"Updated {entity_type}"
    elif action == ACTION_STRUCTURE_DELETED:
        return f"Deleted {entity_type}"
    elif action == ACTION_STRUCTURE_REORDERED:
        return f"Reordered {entity_type} items"

    # Collaborator actions
    elif action == ACTION_COLLABORATOR_INVITED:
        email = changes_dict.get("email", "")
        role = changes_dict.get("role", "")
        if email and role:
            return f"Invited {email} as {role}"
        return "Invited collaborator"
    elif action == ACTION_COLLABORATOR_JOINED:
        return "Joined course"
    elif action == ACTION_COLLABORATOR_REMOVED:
        email = changes_dict.get("email", "user")
        return f"Removed collaborator {email}"
    elif action == ACTION_COLLABORATOR_ROLE_CHANGED:
        email = changes_dict.get("email", "user")
        old_role = changes_dict.get("old_role", "")
        new_role = changes_dict.get("new_role", "")
        if old_role and new_role:
            return f"Changed role for {email} from {old_role} to {new_role}"
        return f"Changed role for {email}"

    # Course actions
    elif action == ACTION_COURSE_CREATED:
        return "Created course"
    elif action == ACTION_COURSE_UPDATED:
        if changes_dict:
            fields = list(changes_dict.keys())
            return f"Updated course {', '.join(fields[:2])}"
        return "Updated course"
    elif action == ACTION_COURSE_EXPORTED:
        return "Exported course"
    elif action == ACTION_COURSE_PUBLISHED:
        return "Published course"

    # Fallback
    return f"{action.replace('_', ' ').title()}"
