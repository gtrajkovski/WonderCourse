"""User model with Flask-Login integration and password hashing."""

from typing import Optional
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


class User(UserMixin):
    """User model with password hashing and database operations.

    Uses raw SQLite queries instead of SQLAlchemy for simplicity.
    Passwords are always hashed using Werkzeug scrypt.
    """

    def __init__(
        self,
        id: int,
        email: str,
        password_hash: str,
        name: Optional[str] = None,
        created_at: Optional[str] = None
    ):
        self.id = id
        self.email = email
        self.password_hash = password_hash
        self.name = name
        self.created_at = created_at

    def get_id(self) -> str:
        """Return string ID for Flask-Login compatibility."""
        return str(self.id)

    def set_password(self, password: str) -> None:
        """Hash and store password using Werkzeug."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify password against stored hash."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        """Return dict representation (excludes password_hash for security)."""
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "created_at": self.created_at
        }

    @classmethod
    def get_by_id(cls, user_id: int) -> Optional["User"]:
        """Load user from database by ID."""
        from src.auth.db import get_db

        db = get_db()
        row = db.execute(
            "SELECT id, email, password_hash, name, created_at FROM user WHERE id = ?",
            (user_id,)
        ).fetchone()

        if row is None:
            return None

        return cls(
            id=row["id"],
            email=row["email"],
            password_hash=row["password_hash"],
            name=row["name"],
            created_at=row["created_at"]
        )

    @classmethod
    def get_by_email(cls, email: str) -> Optional["User"]:
        """Load user from database by email."""
        from src.auth.db import get_db

        db = get_db()
        row = db.execute(
            "SELECT id, email, password_hash, name, created_at FROM user WHERE email = ?",
            (email,)
        ).fetchone()

        if row is None:
            return None

        return cls(
            id=row["id"],
            email=row["email"],
            password_hash=row["password_hash"],
            name=row["name"],
            created_at=row["created_at"]
        )

    @classmethod
    def create(cls, email: str, password: str, name: Optional[str] = None) -> "User":
        """Create new user with hashed password."""
        from src.auth.db import get_db

        password_hash = generate_password_hash(password)
        db = get_db()
        cursor = db.execute(
            "INSERT INTO user (email, password_hash, name) VALUES (?, ?, ?)",
            (email, password_hash, name)
        )
        db.commit()

        return cls.get_by_id(cursor.lastrowid)

    def update_profile(self, name=None, email=None):
        """Update user profile fields.

        Args:
            name: New name (optional)
            email: New email (optional, checked for uniqueness)

        Returns:
            Updated User object

        Raises:
            ValueError: If email already in use by another user
        """
        from src.auth.db import get_db
        db = get_db()

        if email and email != self.email:
            # Check email uniqueness
            existing = db.execute(
                "SELECT id FROM user WHERE email = ? AND id != ?",
                (email, self.id)
            ).fetchone()
            if existing:
                raise ValueError("Email already in use")
            self.email = email

        if name is not None:
            self.name = name

        # Update in database
        db.execute(
            "UPDATE user SET email = ?, name = ? WHERE id = ?",
            (self.email, self.name, self.id)
        )
        db.commit()
        return self

    def update_password(self, current_password, new_password):
        """Change user password.

        Args:
            current_password: Current password for verification
            new_password: New password to set

        Returns:
            True if password changed

        Raises:
            ValueError: If current password is incorrect
        """
        if not self.check_password(current_password):
            raise ValueError("Current password is incorrect")

        self.set_password(new_password)

        from src.auth.db import get_db
        db = get_db()
        db.execute(
            "UPDATE user SET password_hash = ? WHERE id = ?",
            (self.password_hash, self.id)
        )
        db.commit()
        return True
