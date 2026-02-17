"""Permission definitions and role templates for collaboration.

Defines all permission codes organized by category, predefined role
templates with permission sets, and helper functions for permission checks.
"""

from typing import List, Optional
from src.auth.db import get_db


# All permission codes organized by category
PERMISSIONS = {
    "content": {
        "view_content": "View course content and activities",
        "edit_content": "Edit existing course content",
        "delete_content": "Delete course content",
        "generate_content": "Use AI to generate new content",
        "approve_content": "Approve content for publishing",
    },
    "structure": {
        "add_structure": "Add new modules and lessons",
        "reorder_structure": "Reorder modules, lessons, and activities",
        "delete_structure": "Delete modules and lessons",
        "manage_outcomes": "Manage learning outcomes",
    },
    "course": {
        "invite_collaborators": "Invite new collaborators to course",
        "export_course": "Export course to Word/PDF",
        "publish_course": "Publish course to Coursera",
        "delete_course": "Delete entire course",
    },
}


# Predefined role templates with permission sets
ROLE_TEMPLATES = {
    "Owner": [
        # All permissions
        "view_content", "edit_content", "delete_content", "generate_content", "approve_content",
        "add_structure", "reorder_structure", "delete_structure", "manage_outcomes",
        "invite_collaborators", "export_course", "publish_course", "delete_course",
    ],
    "Designer": [
        # Content creation and structure
        "view_content", "edit_content", "generate_content",
        "add_structure", "reorder_structure", "manage_outcomes",
        "export_course",
    ],
    "Reviewer": [
        # Review and approval only
        "view_content", "approve_content", "export_course",
    ],
    "SME": [
        # View and export only (subject matter expert consultant)
        "view_content", "export_course",
    ],
}


def seed_permissions(db) -> None:
    """Insert all permission codes into database (idempotent).

    Args:
        db: Database connection from get_db()
    """
    for category, perms in PERMISSIONS.items():
        for code, description in perms.items():
            # Use INSERT OR IGNORE to make idempotent
            db.execute(
                "INSERT OR IGNORE INTO permission (code, category, description) VALUES (?, ?, ?)",
                (code, category, description)
            )
    db.commit()


def has_permission(user_id: int, course_id: str, permission_code: str) -> bool:
    """Check if user has specific permission on course.

    Args:
        user_id: User ID to check
        course_id: Course ID to check permission for
        permission_code: Permission code (e.g., "edit_content")

    Returns:
        True if user has permission, False otherwise
    """
    db = get_db()

    # Query joins collaborator -> role -> role_permission -> permission
    result = db.execute(
        """
        SELECT COUNT(*) as count
        FROM collaborator c
        JOIN role_permission rp ON c.role_id = rp.role_id
        JOIN permission p ON rp.permission_id = p.id
        WHERE c.user_id = ? AND c.course_id = ? AND p.code = ?
        """,
        (user_id, course_id, permission_code)
    ).fetchone()

    return result["count"] > 0 if result else False


def get_user_permissions(user_id: int, course_id: str) -> List[str]:
    """Get all permission codes for user on course.

    Args:
        user_id: User ID to get permissions for
        course_id: Course ID to check

    Returns:
        List of permission codes user has on this course
    """
    db = get_db()

    rows = db.execute(
        """
        SELECT p.code
        FROM collaborator c
        JOIN role_permission rp ON c.role_id = rp.role_id
        JOIN permission p ON rp.permission_id = p.id
        WHERE c.user_id = ? AND c.course_id = ?
        ORDER BY p.code
        """,
        (user_id, course_id)
    ).fetchall()

    return [row["code"] for row in rows]


def get_user_role(user_id: int, course_id: str) -> Optional[str]:
    """Get role name for user on course.

    Args:
        user_id: User ID to check
        course_id: Course ID to check

    Returns:
        Role name if user is collaborator, None otherwise
    """
    db = get_db()

    row = db.execute(
        """
        SELECT cr.name
        FROM collaborator c
        JOIN course_role cr ON c.role_id = cr.id
        WHERE c.user_id = ? AND c.course_id = ?
        """,
        (user_id, course_id)
    ).fetchone()

    return row["name"] if row else None
