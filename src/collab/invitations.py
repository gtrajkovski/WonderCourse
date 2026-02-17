"""Invitation management for course collaboration.

Supports both email invitations and shareable links with configurable expiry.
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple, List
from flask import g

from src.auth.db import get_db


# Constants
DEFAULT_EXPIRY_SECONDS = 604800  # 7 days
INVITATION_TOKEN_LENGTH = 32


def generate_invitation_token() -> str:
    """Generate a unique URL-safe invitation token.
    
    Returns:
        32-character URL-safe token
    """
    return secrets.token_urlsafe(INVITATION_TOKEN_LENGTH)


class Invitation:
    """Invitation to collaborate on a course.

    Can be either an email invitation (with email address) or a shareable
    link (email=None). Supports optional expiry and revocation.
    """

    def __init__(self, id: int, token: str, course_id: str, role_id: int,
                 invited_by: int, email: Optional[str], expires_at: Optional[datetime],
                 created_at: datetime, revoked: int):
        self.id = id
        self.token = token
        self.course_id = course_id
        self.role_id = role_id
        self.invited_by = invited_by
        self.email = email
        self.expires_at = expires_at
        self.created_at = created_at
        self.revoked = bool(revoked)

    @classmethod
    def create(cls, course_id: str, role_id: int, invited_by: int,
               email: Optional[str] = None, expires_in: Optional[int] = DEFAULT_EXPIRY_SECONDS) -> 'Invitation':
        """Create a new invitation.

        Args:
            course_id: Course ID to invite to
            role_id: Role ID to assign
            invited_by: User ID who created invitation
            email: Email address for email invitations, None for shareable links
            expires_in: Seconds until expiry, None for no expiry

        Returns:
            Created Invitation instance
        """
        db = get_db()
        token = generate_invitation_token()

        # Calculate expiry
        expires_at = None
        if expires_in is not None:
            expires_at = datetime.now() + timedelta(seconds=expires_in)

        cursor = db.execute(
            """INSERT INTO invitation (token, course_id, role_id, invited_by, email, expires_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (token, course_id, role_id, invited_by, email, expires_at)
        )
        db.commit()

        return cls.get_by_id(cursor.lastrowid)

    @classmethod
    def create_shareable_link(cls, course_id: str, role_id: int, invited_by: int,
                              expires_in: Optional[int] = None) -> 'Invitation':
        """Create a shareable link invitation (no email required).

        Args:
            course_id: Course ID to invite to
            role_id: Role ID to assign
            invited_by: User ID who created invitation
            expires_in: Seconds until expiry, None for no expiry

        Returns:
            Created Invitation instance
        """
        return cls.create(course_id, role_id, invited_by, email=None, expires_in=expires_in)

    @classmethod
    def get_by_id(cls, invitation_id: int) -> Optional['Invitation']:
        """Load invitation by ID.

        Args:
            invitation_id: Invitation ID

        Returns:
            Invitation instance or None if not found
        """
        db = get_db()
        row = db.execute(
            "SELECT * FROM invitation WHERE id = ?",
            (invitation_id,)
        ).fetchone()

        if not row:
            return None

        # Handle datetime fields (SQLite returns datetime objects when detect_types is enabled)
        expires_at = row['expires_at']
        if expires_at and isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)

        created_at = row['created_at']
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        return cls(
            id=row['id'],
            token=row['token'],
            course_id=row['course_id'],
            role_id=row['role_id'],
            invited_by=row['invited_by'],
            email=row['email'],
            expires_at=expires_at,
            created_at=created_at,
            revoked=row['revoked']
        )

    @classmethod
    def get_by_token(cls, token: str) -> Optional['Invitation']:
        """Load invitation by token.

        Args:
            token: Invitation token

        Returns:
            Invitation instance or None if not found
        """
        db = get_db()
        row = db.execute(
            "SELECT * FROM invitation WHERE token = ?",
            (token,)
        ).fetchone()

        if not row:
            return None

        # Handle datetime fields (SQLite returns datetime objects when detect_types is enabled)
        expires_at = row['expires_at']
        if expires_at and isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)

        created_at = row['created_at']
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        return cls(
            id=row['id'],
            token=row['token'],
            course_id=row['course_id'],
            role_id=row['role_id'],
            invited_by=row['invited_by'],
            email=row['email'],
            expires_at=expires_at,
            created_at=created_at,
            revoked=row['revoked']
        )

    @classmethod
    def get_for_course(cls, course_id: str, include_revoked: bool = False) -> List['Invitation']:
        """Get all invitations for a course.

        Args:
            course_id: Course ID
            include_revoked: Whether to include revoked invitations

        Returns:
            List of Invitation instances
        """
        db = get_db()

        if include_revoked:
            query = "SELECT * FROM invitation WHERE course_id = ? ORDER BY created_at DESC"
            rows = db.execute(query, (course_id,)).fetchall()
        else:
            query = "SELECT * FROM invitation WHERE course_id = ? AND revoked = 0 ORDER BY created_at DESC"
            rows = db.execute(query, (course_id,)).fetchall()

        invitations = []
        for row in rows:
            expires_at = row['expires_at']
            if expires_at and isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at)

            created_at = row['created_at']
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)

            invitations.append(cls(
                id=row['id'],
                token=row['token'],
                course_id=row['course_id'],
                role_id=row['role_id'],
                invited_by=row['invited_by'],
                email=row['email'],
                expires_at=expires_at,
                created_at=created_at,
                revoked=row['revoked']
            ))

        return invitations

    @classmethod
    def revoke(cls, invitation_id: int) -> None:
        """Revoke an invitation.

        Args:
            invitation_id: Invitation ID to revoke
        """
        db = get_db()
        db.execute(
            "UPDATE invitation SET revoked = 1 WHERE id = ?",
            (invitation_id,)
        )
        db.commit()

    @classmethod
    def delete(cls, invitation_id: int) -> None:
        """Hard delete an invitation.

        Args:
            invitation_id: Invitation ID to delete
        """
        db = get_db()
        db.execute("DELETE FROM invitation WHERE id = ?", (invitation_id,))
        db.commit()

    def to_dict(self) -> dict:
        """Serialize invitation for API responses.

        Returns:
            Dictionary representation
        """
        return {
            'token': self.token,
            'course_id': self.course_id,
            'role_id': self.role_id,
            'invited_by': self.invited_by,
            'email': self.email,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat(),
            'revoked': self.revoked
        }

    def is_valid(self) -> bool:
        """Check if invitation is valid (not revoked and not expired).

        Returns:
            True if valid, False otherwise
        """
        if self.revoked:
            return False

        if self.expires_at and datetime.now() > self.expires_at:
            return False

        return True


def validate_invitation_token(token: str) -> Optional[Tuple[str, int]]:
    """Validate an invitation token.

    Checks if token exists, is not revoked, and is not expired.

    Args:
        token: Invitation token to validate

    Returns:
        Tuple of (course_id, role_id) if valid, None if invalid
    """
    invitation = Invitation.get_by_token(token)

    if not invitation:
        return None

    if not invitation.is_valid():
        return None

    return (invitation.course_id, invitation.role_id)


def accept_invitation(token: str, user_id: int) -> Optional[dict]:
    """Accept an invitation and create a collaborator.

    Args:
        token: Invitation token
        user_id: User ID accepting the invitation

    Returns:
        Collaborator dict if successful, None with error if failed
    """
    # Validate token
    result = validate_invitation_token(token)
    if not result:
        return None

    course_id, role_id = result

    # Check if user is already a collaborator
    db = get_db()
    existing = db.execute(
        "SELECT id FROM collaborator WHERE course_id = ? AND user_id = ?",
        (course_id, user_id)
    ).fetchone()

    if existing:
        return None

    # Get invitation for invited_by
    invitation = Invitation.get_by_token(token)

    # Create collaborator
    cursor = db.execute(
        """INSERT INTO collaborator (course_id, user_id, role_id, invited_by)
           VALUES (?, ?, ?, ?)""",
        (course_id, user_id, role_id, invitation.invited_by)
    )
    db.commit()

    # Return collaborator data
    collab_row = db.execute(
        "SELECT * FROM collaborator WHERE id = ?",
        (cursor.lastrowid,)
    ).fetchone()

    return {
        'id': collab_row['id'],
        'course_id': collab_row['course_id'],
        'user_id': collab_row['user_id'],
        'role_id': collab_row['role_id'],
        'invited_by': collab_row['invited_by'],
        'invited_at': collab_row['invited_at']
    }
