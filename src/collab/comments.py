"""Comment and mention models for threaded discussions.

Provides Comment and Mention classes for activity-level and course-level discussions
with single-level threading, resolution tracking, and @mention notifications.
"""

import re
from typing import List, Optional, Dict, Any
from datetime import datetime
from src.auth.db import get_db
from src.collab.models import Collaborator


def parse_mentions(text: str) -> List[str]:
    """Extract @mentions from text.

    Handles both @username and @"User Name" formats.

    Args:
        text: Text content to parse

    Returns:
        List of mentioned strings (names or emails)
    """
    # Pattern matches @username or @"Quoted Name"
    pattern = r'@(?:"([^"]+)|(\S+))'
    matches = re.findall(pattern, text)

    # Each match is a tuple (quoted, unquoted) - one will be empty
    return [quoted or unquoted for quoted, unquoted in matches]


class Comment:
    """Threaded comment on activity or course.

    Supports single-level threading: comments can have replies,
    but replies cannot have their own replies.
    """

    def __init__(
        self,
        id: Optional[int] = None,
        course_id: Optional[str] = None,
        activity_id: Optional[str] = None,
        user_id: Optional[int] = None,
        parent_id: Optional[int] = None,
        content: Optional[str] = None,
        resolved: int = 0,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        author_name: Optional[str] = None,
        author_email: Optional[str] = None,
        replies: Optional[List["Comment"]] = None,
    ):
        self.id = id
        self.course_id = course_id
        self.activity_id = activity_id
        self.user_id = user_id
        self.parent_id = parent_id
        self.content = content
        self.resolved = resolved
        self.created_at = created_at
        self.updated_at = updated_at
        self.author_name = author_name
        self.author_email = author_email
        self.replies = replies or []

    @classmethod
    def create(
        cls,
        course_id: str,
        user_id: int,
        content: str,
        activity_id: Optional[str] = None,
        parent_id: Optional[int] = None,
    ) -> "Comment":
        """Create new comment with mention notification.

        Args:
            course_id: Course ID this comment belongs to
            user_id: User ID of comment author
            content: Comment text content
            activity_id: Activity ID (None for course-level comments)
            parent_id: Parent comment ID for replies (None for top-level)

        Returns:
            Created Comment instance

        Raises:
            ValueError: If trying to reply to a reply (enforces single-level threading)
        """
        db = get_db()

        # Enforce single-level threading
        if parent_id:
            parent_row = db.execute(
                "SELECT parent_id FROM comment WHERE id = ?",
                (parent_id,)
            ).fetchone()

            if parent_row and parent_row["parent_id"] is not None:
                raise ValueError("Cannot reply to a reply. Reply to the parent comment instead.")

        # Insert comment
        cursor = db.execute(
            """
            INSERT INTO comment (course_id, activity_id, user_id, parent_id, content)
            VALUES (?, ?, ?, ?, ?)
            """,
            (course_id, activity_id, user_id, parent_id, content)
        )
        comment_id = cursor.lastrowid

        # Create mention notifications
        _create_mentions(comment_id, course_id, user_id, content)

        db.commit()

        return cls.get_by_id(comment_id)

    @classmethod
    def get_by_id(cls, comment_id: int) -> Optional["Comment"]:
        """Load single comment with author info.

        Args:
            comment_id: Comment ID to load

        Returns:
            Comment instance if found, None otherwise
        """
        db = get_db()

        row = db.execute(
            """
            SELECT c.id, c.course_id, c.activity_id, c.user_id, c.parent_id,
                   c.content, c.resolved, c.created_at, c.updated_at,
                   u.name as author_name, u.email as author_email
            FROM comment c
            JOIN user u ON c.user_id = u.id
            WHERE c.id = ?
            """,
            (comment_id,)
        ).fetchone()

        if not row:
            return None

        return cls(
            id=row["id"],
            course_id=row["course_id"],
            activity_id=row["activity_id"],
            user_id=row["user_id"],
            parent_id=row["parent_id"],
            content=row["content"],
            resolved=row["resolved"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            author_name=row["author_name"],
            author_email=row["author_email"],
        )

    @classmethod
    def get_for_course(cls, course_id: str, include_resolved: bool = False) -> List["Comment"]:
        """Get course-level comments only.

        Args:
            course_id: Course ID to get comments for
            include_resolved: Whether to include resolved comments

        Returns:
            List of course-level Comment instances
        """
        db = get_db()

        query = """
            SELECT c.id, c.course_id, c.activity_id, c.user_id, c.parent_id,
                   c.content, c.resolved, c.created_at, c.updated_at,
                   u.name as author_name, u.email as author_email
            FROM comment c
            JOIN user u ON c.user_id = u.id
            WHERE c.course_id = ? AND c.activity_id IS NULL
        """

        if not include_resolved:
            query += " AND c.resolved = 0"

        query += " ORDER BY c.created_at ASC"

        rows = db.execute(query, (course_id,)).fetchall()

        return [
            cls(
                id=row["id"],
                course_id=row["course_id"],
                activity_id=row["activity_id"],
                user_id=row["user_id"],
                parent_id=row["parent_id"],
                content=row["content"],
                resolved=row["resolved"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                author_name=row["author_name"],
                author_email=row["author_email"],
            )
            for row in rows
        ]

    @classmethod
    def get_for_activity(cls, course_id: str, activity_id: str, include_resolved: bool = False) -> List["Comment"]:
        """Get activity-specific comments.

        Args:
            course_id: Course ID
            activity_id: Activity ID to get comments for
            include_resolved: Whether to include resolved comments

        Returns:
            List of activity-level Comment instances
        """
        db = get_db()

        query = """
            SELECT c.id, c.course_id, c.activity_id, c.user_id, c.parent_id,
                   c.content, c.resolved, c.created_at, c.updated_at,
                   u.name as author_name, u.email as author_email
            FROM comment c
            JOIN user u ON c.user_id = u.id
            WHERE c.course_id = ? AND c.activity_id = ?
        """

        if not include_resolved:
            query += " AND c.resolved = 0"

        query += " ORDER BY c.created_at ASC"

        rows = db.execute(query, (course_id, activity_id)).fetchall()

        return [
            cls(
                id=row["id"],
                course_id=row["course_id"],
                activity_id=row["activity_id"],
                user_id=row["user_id"],
                parent_id=row["parent_id"],
                content=row["content"],
                resolved=row["resolved"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                author_name=row["author_name"],
                author_email=row["author_email"],
            )
            for row in rows
        ]

    @classmethod
    def get_with_replies(
        cls,
        course_id: str,
        activity_id: Optional[str] = None,
        include_resolved: bool = False,
    ) -> List["Comment"]:
        """Get comments with single-level reply hierarchy.

        Args:
            course_id: Course ID
            activity_id: Activity ID (None for course-level comments)
            include_resolved: Whether to include resolved comments

        Returns:
            List of top-level Comment instances with replies populated
        """
        if activity_id:
            all_comments = cls.get_for_activity(course_id, activity_id, include_resolved)
        else:
            all_comments = cls.get_for_course(course_id, include_resolved)

        # Build hierarchy: separate top-level from replies
        top_level = []
        replies_by_parent = {}

        for comment in all_comments:
            if comment.parent_id is None:
                top_level.append(comment)
            else:
                if comment.parent_id not in replies_by_parent:
                    replies_by_parent[comment.parent_id] = []
                replies_by_parent[comment.parent_id].append(comment)

        # Attach replies to their parents
        for comment in top_level:
            comment.replies = replies_by_parent.get(comment.id, [])

        return top_level

    @classmethod
    def resolve(cls, comment_id: int) -> None:
        """Mark comment as resolved.

        Args:
            comment_id: Comment ID to resolve
        """
        db = get_db()
        db.execute(
            "UPDATE comment SET resolved = 1 WHERE id = ?",
            (comment_id,)
        )
        db.commit()

    @classmethod
    def unresolve(cls, comment_id: int) -> None:
        """Mark comment as unresolved.

        Args:
            comment_id: Comment ID to unresolve
        """
        db = get_db()
        db.execute(
            "UPDATE comment SET resolved = 0 WHERE id = ?",
            (comment_id,)
        )
        db.commit()

    @classmethod
    def update(cls, comment_id: int, content: str) -> Optional["Comment"]:
        """Update comment content and re-parse mentions.

        Args:
            comment_id: Comment ID to update
            content: New comment content

        Returns:
            Updated Comment instance if found, None otherwise
        """
        db = get_db()

        # Get existing comment to get course_id and user_id
        comment = cls.get_by_id(comment_id)
        if not comment:
            return None

        # Update content and timestamp
        db.execute(
            "UPDATE comment SET content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (content, comment_id)
        )

        # Delete old mentions
        db.execute("DELETE FROM mention WHERE comment_id = ?", (comment_id,))

        # Create new mentions
        _create_mentions(comment_id, comment.course_id, comment.user_id, content)

        db.commit()

        return cls.get_by_id(comment_id)

    @classmethod
    def delete(cls, comment_id: int) -> None:
        """Delete comment (CASCADE removes replies).

        Args:
            comment_id: Comment ID to delete
        """
        db = get_db()
        db.execute("DELETE FROM comment WHERE id = ?", (comment_id,))
        db.commit()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize comment for API responses.

        Returns:
            Dictionary with comment data
        """
        return {
            "id": self.id,
            "course_id": self.course_id,
            "activity_id": self.activity_id,
            "user_id": self.user_id,
            "parent_id": self.parent_id,
            "content": self.content,
            "resolved": self.resolved,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "author_name": self.author_name,
            "author_email": self.author_email,
            "replies": [reply.to_dict() for reply in self.replies] if self.replies else [],
        }


class Mention:
    """Notification for @mentioned user in comment."""

    def __init__(
        self,
        id: Optional[int] = None,
        comment_id: Optional[int] = None,
        user_id: Optional[int] = None,
        read: int = 0,
        created_at: Optional[datetime] = None,
    ):
        self.id = id
        self.comment_id = comment_id
        self.user_id = user_id
        self.read = read
        self.created_at = created_at

    @classmethod
    def get_unread_for_user(cls, user_id: int) -> List["Mention"]:
        """Get all unread mentions for user.

        Args:
            user_id: User ID to get mentions for

        Returns:
            List of unread Mention instances
        """
        db = get_db()

        rows = db.execute(
            """
            SELECT id, comment_id, user_id, read, created_at
            FROM mention
            WHERE user_id = ? AND read = 0
            ORDER BY created_at DESC
            """,
            (user_id,)
        ).fetchall()

        return [
            cls(
                id=row["id"],
                comment_id=row["comment_id"],
                user_id=row["user_id"],
                read=row["read"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    @classmethod
    def mark_read(cls, mention_id: int) -> None:
        """Mark single mention as read.

        Args:
            mention_id: Mention ID to mark read
        """
        db = get_db()
        db.execute(
            "UPDATE mention SET read = 1 WHERE id = ?",
            (mention_id,)
        )
        db.commit()

    @classmethod
    def mark_all_read(cls, user_id: int) -> None:
        """Mark all mentions read for user.

        Args:
            user_id: User ID to mark all mentions read
        """
        db = get_db()
        db.execute(
            "UPDATE mention SET read = 1 WHERE user_id = ?",
            (user_id,)
        )
        db.commit()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize mention for API responses.

        Returns:
            Dictionary with mention data
        """
        return {
            "id": self.id,
            "comment_id": self.comment_id,
            "user_id": self.user_id,
            "read": self.read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


def _create_mentions(comment_id: int, course_id: str, author_id: int, content: str) -> None:
    """Create mention notifications for @mentions in comment.

    Args:
        comment_id: Comment ID that contains mentions
        course_id: Course ID to find collaborators in
        author_id: Comment author user ID (excluded from mentions)
        content: Comment text to parse for mentions
    """
    db = get_db()

    # Parse mentions from content
    mentioned_strings = parse_mentions(content)

    if not mentioned_strings:
        return

    # Get all collaborators on this course
    collaborators = Collaborator.get_for_course(course_id)

    # Match mentions to collaborators (by name or email)
    mentioned_user_ids = set()

    for mention_str in mentioned_strings:
        for collab in collaborators:
            # Match by name or email (case-insensitive)
            if (
                (collab.user_name and collab.user_name.lower() == mention_str.lower()) or
                (collab.user_email and collab.user_email.lower() == mention_str.lower())
            ):
                # Don't notify the author
                if collab.user_id != author_id:
                    mentioned_user_ids.add(collab.user_id)

    # Create mention entries
    for user_id in mentioned_user_ids:
        db.execute(
            "INSERT INTO mention (comment_id, user_id) VALUES (?, ?)",
            (comment_id, user_id)
        )
