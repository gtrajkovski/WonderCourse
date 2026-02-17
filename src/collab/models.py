"""Data models for collaboration and role management.

Provides Role and Collaborator classes for managing course access control.
Uses direct database operations without ORM for consistency with existing codebase.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from src.auth.db import get_db
from src.collab.permissions import ROLE_TEMPLATES


class Role:
    """Custom role per course with assigned permissions.

    A role defines a set of permissions that can be assigned to collaborators.
    Roles are course-specific, allowing different permission sets across courses.
    """

    def __init__(
        self,
        id: Optional[int] = None,
        course_id: Optional[str] = None,
        name: Optional[str] = None,
        created_at: Optional[datetime] = None,
        permissions: Optional[List[str]] = None,
    ):
        self.id = id
        self.course_id = course_id
        self.name = name
        self.created_at = created_at
        self.permissions = permissions or []

    @classmethod
    def get_by_id(cls, role_id: int) -> Optional["Role"]:
        """Load role with its permissions.

        Args:
            role_id: Role ID to load

        Returns:
            Role instance if found, None otherwise
        """
        db = get_db()

        # Get role basic info
        row = db.execute(
            "SELECT id, course_id, name, created_at FROM course_role WHERE id = ?",
            (role_id,)
        ).fetchone()

        if not row:
            return None

        # Get permissions for this role
        perm_rows = db.execute(
            """
            SELECT p.code
            FROM role_permission rp
            JOIN permission p ON rp.permission_id = p.id
            WHERE rp.role_id = ?
            ORDER BY p.code
            """,
            (role_id,)
        ).fetchall()

        permissions = [r["code"] for r in perm_rows]

        return cls(
            id=row["id"],
            course_id=row["course_id"],
            name=row["name"],
            created_at=row["created_at"],
            permissions=permissions,
        )

    @classmethod
    def create(cls, course_id: str, name: str, permission_codes: List[str]) -> "Role":
        """Create role with specified permissions.

        Args:
            course_id: Course ID this role belongs to
            name: Role name (e.g., "Designer")
            permission_codes: List of permission codes to assign

        Returns:
            Created Role instance
        """
        db = get_db()

        # Insert role
        cursor = db.execute(
            "INSERT INTO course_role (course_id, name) VALUES (?, ?)",
            (course_id, name)
        )
        role_id = cursor.lastrowid

        # Insert role_permission entries
        for code in permission_codes:
            # Get permission id from code
            perm_row = db.execute(
                "SELECT id FROM permission WHERE code = ?", (code,)
            ).fetchone()

            if perm_row:
                db.execute(
                    "INSERT INTO role_permission (role_id, permission_id) VALUES (?, ?)",
                    (role_id, perm_row["id"])
                )

        db.commit()

        return cls.get_by_id(role_id)

    @classmethod
    def create_from_template(cls, course_id: str, template_name: str) -> "Role":
        """Create role from predefined template.

        Args:
            course_id: Course ID this role belongs to
            template_name: Template name (Owner, Designer, Reviewer, SME)

        Returns:
            Created Role instance

        Raises:
            ValueError: If template_name not in ROLE_TEMPLATES
        """
        if template_name not in ROLE_TEMPLATES:
            raise ValueError(f"Unknown template: {template_name}")

        permission_codes = ROLE_TEMPLATES[template_name]
        return cls.create(course_id, template_name, permission_codes)

    @classmethod
    def get_for_course(cls, course_id: str) -> List["Role"]:
        """List all roles for a course.

        Args:
            course_id: Course ID to list roles for

        Returns:
            List of Role instances for this course
        """
        db = get_db()

        rows = db.execute(
            "SELECT id FROM course_role WHERE course_id = ? ORDER BY name",
            (course_id,)
        ).fetchall()

        return [cls.get_by_id(row["id"]) for row in rows]

    @classmethod
    def delete(cls, role_id: int) -> None:
        """Delete role (CASCADE removes role_permissions).

        Args:
            role_id: Role ID to delete
        """
        db = get_db()
        db.execute("DELETE FROM course_role WHERE id = ?", (role_id,))
        db.commit()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize role for API responses.

        Returns:
            Dictionary with role data
        """
        return {
            "id": self.id,
            "course_id": self.course_id,
            "name": self.name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "permissions": self.permissions,
        }


class Collaborator:
    """User linked to course with specific role.

    Represents a collaboration relationship between a user and course,
    defining what permissions the user has through their assigned role.
    """

    def __init__(
        self,
        id: Optional[int] = None,
        course_id: Optional[str] = None,
        user_id: Optional[int] = None,
        role_id: Optional[int] = None,
        invited_by: Optional[int] = None,
        invited_at: Optional[datetime] = None,
        role_name: Optional[str] = None,
        user_email: Optional[str] = None,
        user_name: Optional[str] = None,
    ):
        self.id = id
        self.course_id = course_id
        self.user_id = user_id
        self.role_id = role_id
        self.invited_by = invited_by
        self.invited_at = invited_at
        self.role_name = role_name
        self.user_email = user_email
        self.user_name = user_name

    @classmethod
    def get_by_id(cls, collaborator_id: int) -> Optional["Collaborator"]:
        """Load collaborator with joins for role/user info.

        Args:
            collaborator_id: Collaborator ID to load

        Returns:
            Collaborator instance if found, None otherwise
        """
        db = get_db()

        row = db.execute(
            """
            SELECT c.id, c.course_id, c.user_id, c.role_id, c.invited_by, c.invited_at,
                   cr.name as role_name, u.email as user_email, u.name as user_name
            FROM collaborator c
            JOIN course_role cr ON c.role_id = cr.id
            JOIN user u ON c.user_id = u.id
            WHERE c.id = ?
            """,
            (collaborator_id,)
        ).fetchone()

        if not row:
            return None

        return cls(
            id=row["id"],
            course_id=row["course_id"],
            user_id=row["user_id"],
            role_id=row["role_id"],
            invited_by=row["invited_by"],
            invited_at=row["invited_at"],
            role_name=row["role_name"],
            user_email=row["user_email"],
            user_name=row["user_name"],
        )

    @classmethod
    def get_by_user_and_course(cls, user_id: int, course_id: str) -> Optional["Collaborator"]:
        """Find collaborator entry for user on course.

        Args:
            user_id: User ID to find
            course_id: Course ID to check

        Returns:
            Collaborator instance if found, None otherwise
        """
        db = get_db()

        row = db.execute(
            """
            SELECT c.id, c.course_id, c.user_id, c.role_id, c.invited_by, c.invited_at,
                   cr.name as role_name, u.email as user_email, u.name as user_name
            FROM collaborator c
            JOIN course_role cr ON c.role_id = cr.id
            JOIN user u ON c.user_id = u.id
            WHERE c.user_id = ? AND c.course_id = ?
            """,
            (user_id, course_id)
        ).fetchone()

        if not row:
            return None

        return cls(
            id=row["id"],
            course_id=row["course_id"],
            user_id=row["user_id"],
            role_id=row["role_id"],
            invited_by=row["invited_by"],
            invited_at=row["invited_at"],
            role_name=row["role_name"],
            user_email=row["user_email"],
            user_name=row["user_name"],
        )

    @classmethod
    def create(cls, course_id: str, user_id: int, role_id: int, invited_by: int) -> "Collaborator":
        """Add collaborator to course.

        Args:
            course_id: Course ID to add collaborator to
            user_id: User ID to add
            role_id: Role ID to assign
            invited_by: User ID who invited this collaborator

        Returns:
            Created Collaborator instance
        """
        db = get_db()

        cursor = db.execute(
            "INSERT INTO collaborator (course_id, user_id, role_id, invited_by) VALUES (?, ?, ?, ?)",
            (course_id, user_id, role_id, invited_by)
        )
        collaborator_id = cursor.lastrowid
        db.commit()

        return cls.get_by_id(collaborator_id)

    @classmethod
    def get_for_course(cls, course_id: str) -> List["Collaborator"]:
        """List all collaborators on course.

        Args:
            course_id: Course ID to list collaborators for

        Returns:
            List of Collaborator instances for this course
        """
        db = get_db()

        rows = db.execute(
            """
            SELECT c.id, c.course_id, c.user_id, c.role_id, c.invited_by, c.invited_at,
                   cr.name as role_name, u.email as user_email, u.name as user_name
            FROM collaborator c
            JOIN course_role cr ON c.role_id = cr.id
            JOIN user u ON c.user_id = u.id
            WHERE c.course_id = ?
            ORDER BY c.invited_at DESC
            """,
            (course_id,)
        ).fetchall()

        return [
            cls(
                id=row["id"],
                course_id=row["course_id"],
                user_id=row["user_id"],
                role_id=row["role_id"],
                invited_by=row["invited_by"],
                invited_at=row["invited_at"],
                role_name=row["role_name"],
                user_email=row["user_email"],
                user_name=row["user_name"],
            )
            for row in rows
        ]

    @classmethod
    def delete(cls, collaborator_id: int) -> None:
        """Remove collaborator from course.

        Args:
            collaborator_id: Collaborator ID to delete
        """
        db = get_db()
        db.execute("DELETE FROM collaborator WHERE id = ?", (collaborator_id,))
        db.commit()

    @classmethod
    def update_role(cls, collaborator_id: int, new_role_id: int) -> Optional["Collaborator"]:
        """Change collaborator's role.

        Args:
            collaborator_id: Collaborator ID to update
            new_role_id: New role ID to assign

        Returns:
            Updated Collaborator instance if found, None otherwise
        """
        db = get_db()

        db.execute(
            "UPDATE collaborator SET role_id = ? WHERE id = ?",
            (new_role_id, collaborator_id)
        )
        db.commit()

        return cls.get_by_id(collaborator_id)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize collaborator for API responses.

        Returns:
            Dictionary with collaborator data
        """
        return {
            "id": self.id,
            "course_id": self.course_id,
            "user_id": self.user_id,
            "role_id": self.role_id,
            "role_name": self.role_name,
            "user_email": self.user_email,
            "user_name": self.user_name,
            "invited_by": self.invited_by,
            "invited_at": self.invited_at.isoformat() if self.invited_at else None,
        }

    @classmethod
    def get_course_owner_id(cls, course_id: str) -> Optional[int]:
        """Get the user_id of the course owner.

        The owner is the collaborator with the 'Owner' role on the course.

        Args:
            course_id: Course ID to find owner for

        Returns:
            User ID of owner if found, None otherwise
        """
        db = get_db()

        row = db.execute(
            """
            SELECT c.user_id
            FROM collaborator c
            JOIN course_role cr ON c.role_id = cr.id
            WHERE c.course_id = ? AND cr.name = 'Owner'
            LIMIT 1
            """,
            (course_id,)
        ).fetchone()

        if not row:
            return None

        return row["user_id"]
