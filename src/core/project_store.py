"""Course persistence layer with file locking support.

Manages disk persistence for Course objects in projects/{user_id}/{course_id}/course_data.json
with platform-specific file locking to prevent concurrent write corruption.
"""

import json
import shutil
import time
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from .models import Course


class ProjectStore:
    """Manages course persistence on disk with file locking and user isolation."""

    def __init__(self, base_dir: Path = Path("projects")):
        """Initialize ProjectStore with base directory.

        Args:
            base_dir: Root directory for storing course projects.
        """
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _sanitize_id(id_value: str) -> str:
        """Sanitize an ID to prevent path traversal attacks.

        Args:
            id_value: Raw identifier (user_id or course_id).

        Returns:
            Sanitized ID safe for filesystem use.

        Raises:
            ValueError: If id_value is empty after sanitization.
        """
        # Strip any path separators or parent-directory references
        sanitized = str(id_value).replace("/", "").replace("\\", "").replace("..", "")
        if not sanitized:
            raise ValueError("Invalid course ID")
        return sanitized

    def _user_dir(self, user_id: str) -> Path:
        """Get user's project directory.

        Args:
            user_id: User identifier (sanitized).

        Returns:
            Path to user's project directory.
        """
        safe_user_id = self._sanitize_id(str(user_id))
        user_path = self.base_dir / safe_user_id
        user_path.mkdir(parents=True, exist_ok=True)
        return user_path

    def _course_dir(self, user_id: str, course_id: str) -> Path:
        """Get course directory path scoped to user.

        Args:
            user_id: User identifier.
            course_id: Course identifier.

        Returns:
            Path to course directory within user's folder.
        """
        safe_course_id = self._sanitize_id(course_id)
        return self._user_dir(user_id) / safe_course_id

    def _course_file(self, user_id: str, course_id: str) -> Path:
        """Get course data file path.

        Args:
            user_id: User identifier.
            course_id: Course identifier.

        Returns:
            Path to course_data.json file.
        """
        return self._course_dir(user_id, course_id) / "course_data.json"

    def _acquire_lock(self, lock_path: Path) -> None:
        """Acquire a lock file for synchronization.

        Args:
            lock_path: Path to lock file.
        """
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        max_attempts = 50
        attempt = 0

        while attempt < max_attempts:
            try:
                # Try to create lock file exclusively
                fd = lock_path.open("x")
                fd.close()
                return
            except FileExistsError:
                # Lock exists, wait briefly and retry
                time.sleep(0.01)
                attempt += 1

        # If we couldn't acquire lock after max attempts, forcibly take it
        # (handles case where lock file was orphaned)
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass
        fd = lock_path.open("x")
        fd.close()

    def _release_lock(self, lock_path: Path) -> None:
        """Release a lock file.

        Args:
            lock_path: Path to lock file.
        """
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass  # Lock already released

    def _write_json(self, path: Path, data: dict) -> None:
        """Write JSON data to file with file locking.

        Args:
            path: File path to write to.
            data: Dictionary data to serialize.
        """
        lock_path = path.with_suffix(path.suffix + ".lock")
        self._acquire_lock(lock_path)

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        finally:
            self._release_lock(lock_path)

    def _read_json(self, path: Path) -> dict:
        """Read JSON data from file with file locking.

        Args:
            path: File path to read from.

        Returns:
            Deserialized dictionary data.
        """
        lock_path = path.with_suffix(path.suffix + ".lock")
        self._acquire_lock(lock_path)

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        finally:
            self._release_lock(lock_path)

    def save(self, user_id: str, course: Course) -> Path:
        """Save course to disk with automatic subdirectory creation.

        Creates course directory and subdirectories (exports/, textbook/).
        Updates course.updated_at timestamp automatically.

        Args:
            user_id: User identifier for scoping.
            course: Course object to persist.

        Returns:
            Path to saved course_data.json file.
        """
        course_dir = self._course_dir(user_id, course.id)
        course_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories for exports and textbook
        (course_dir / "exports").mkdir(exist_ok=True)
        (course_dir / "textbook").mkdir(exist_ok=True)

        # Update timestamp
        course.updated_at = datetime.now().isoformat()

        # Serialize and write with file locking
        data = course.to_dict()
        path = self._course_file(user_id, course.id)
        self._write_json(path, data)

        return path

    def load(self, user_id: str, course_id: str) -> Optional[Course]:
        """Load course from disk.

        Args:
            user_id: User identifier for scoping.
            course_id: Course identifier.

        Returns:
            Course object if exists, None otherwise.
        """
        path = self._course_file(user_id, course_id)
        if not path.exists():
            return None

        data = self._read_json(path)
        return Course.from_dict(data)

    def list_courses(self, user_id: str) -> List[dict]:
        """List all courses for a specific user.

        Args:
            user_id: User identifier for scoping.

        Returns:
            List of course metadata dictionaries, sorted by updated_at (newest first).
            Each dict contains: id, title, description, module_count, updated_at.
        """
        courses = []
        user_dir = self._user_dir(user_id)
        if not user_dir.exists():
            return courses

        for course_dir in user_dir.iterdir():
            if course_dir.is_dir():
                course_file = course_dir / "course_data.json"
                if course_file.exists():
                    try:
                        data = self._read_json(course_file)
                        courses.append(
                            {
                                "id": data["id"],
                                "title": data.get("title", "Untitled Course"),
                                "description": data.get("description", ""),
                                "module_count": len(data.get("modules", [])),
                                "updated_at": data.get("updated_at", ""),
                            }
                        )
                    except (json.JSONDecodeError, KeyError):
                        # Skip corrupted or invalid course files
                        continue

        # Sort by updated_at descending (newest first)
        return sorted(courses, key=lambda x: x.get("updated_at", ""), reverse=True)

    def delete(self, user_id: str, course_id: str) -> bool:
        """Delete course and all associated files.

        Args:
            user_id: User identifier for scoping.
            course_id: Course identifier.

        Returns:
            True if course was deleted, False if it didn't exist.
        """
        course_dir = self._course_dir(user_id, course_id)
        if course_dir.exists():
            shutil.rmtree(course_dir)
            return True
        return False
