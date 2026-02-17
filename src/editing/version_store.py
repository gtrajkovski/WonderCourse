"""Named version management for activity content.

Provides persistent storage of named snapshots with restore, comparison,
and automatic version limit enforcement.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict
import secrets

from src.core.project_store import ProjectStore
from src.editing.diff_generator import DiffGenerator, DiffResult


@dataclass
class Version:
    """Represents a named snapshot of activity content.

    Attributes:
        id: Unique version identifier
        name: User-provided descriptive name
        activity_id: Activity this version belongs to
        content: Full content snapshot
        created_at: ISO 8601 timestamp
        created_by: User ID who created version
    """
    id: str
    name: str
    activity_id: str
    content: Dict
    created_at: str
    created_by: str

    def to_dict(self) -> dict:
        """Convert version to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'Version':
        """Create Version from dictionary."""
        return cls(
            id=data['id'],
            name=data['name'],
            activity_id=data['activity_id'],
            content=data['content'],
            created_at=data['created_at'],
            created_by=data['created_by']
        )


class VersionStore:
    """Manages named versions of activity content.

    Stores versions in course_data.json under activity.versions array.
    Enforces 20-version limit per activity by deleting oldest when exceeded.
    """

    MAX_VERSIONS_PER_ACTIVITY = 20

    def __init__(self, project_store: ProjectStore):
        """Initialize version store with project store dependency.

        Args:
            project_store: ProjectStore for course persistence
        """
        self.project_store = project_store
        self.diff_generator = DiffGenerator()

    def save_version(
        self,
        course_id: str,
        activity_id: str,
        name: str,
        content: Dict,
        user_id: str
    ) -> Version:
        """Save a named version of activity content.

        Args:
            course_id: Course ID
            activity_id: Activity ID
            name: User-provided version name
            content: Full activity content snapshot
            user_id: User creating the version

        Returns:
            Created Version object

        Raises:
            ValueError: If course or activity not found
        """
        # Load course
        course = self.project_store.load(user_id, course_id)
        if not course:
            raise ValueError(f"Course not found: {course_id}")

        # Find activity
        activity = self._find_activity(course, activity_id)
        if not activity:
            raise ValueError(f"Activity not found: {activity_id}")

        # Create version
        version = Version(
            id=f"ver_{secrets.token_hex(8)}",
            name=name,
            activity_id=activity_id,
            content=content,
            created_at=datetime.utcnow().isoformat() + "Z",
            created_by=user_id
        )

        # Initialize versions array if not exists
        if not hasattr(activity, 'versions'):
            activity.versions = []

        # Add version
        activity.versions.append(version.to_dict())

        # Enforce version limit (delete oldest if exceeded)
        if len(activity.versions) > self.MAX_VERSIONS_PER_ACTIVITY:
            activity.versions.pop(0)  # Remove oldest

        # Save course
        self.project_store.save(user_id, course)

        return version

    def list_versions(
        self,
        course_id: str,
        activity_id: str,
        user_id: str
    ) -> List[Version]:
        """List all versions for an activity.

        Args:
            course_id: Course ID
            activity_id: Activity ID
            user_id: User ID for permission check

        Returns:
            List of Version objects, most recent first

        Raises:
            ValueError: If course or activity not found
        """
        # Load course
        course = self.project_store.load(user_id, course_id)
        if not course:
            raise ValueError(f"Course not found: {course_id}")

        # Find activity
        activity = self._find_activity(course, activity_id)
        if not activity:
            raise ValueError(f"Activity not found: {activity_id}")

        # Get versions (most recent first)
        versions = getattr(activity, 'versions', [])
        return [Version.from_dict(v) for v in reversed(versions)]

    def get_version(
        self,
        course_id: str,
        activity_id: str,
        version_id: str,
        user_id: str
    ) -> Version:
        """Get a specific version by ID.

        Args:
            course_id: Course ID
            activity_id: Activity ID
            version_id: Version ID
            user_id: User ID for permission check

        Returns:
            Version object

        Raises:
            ValueError: If course, activity, or version not found
        """
        # Load course
        course = self.project_store.load(user_id, course_id)
        if not course:
            raise ValueError(f"Course not found: {course_id}")

        # Find activity
        activity = self._find_activity(course, activity_id)
        if not activity:
            raise ValueError(f"Activity not found: {activity_id}")

        # Find version
        versions = getattr(activity, 'versions', [])
        for v_dict in versions:
            if v_dict['id'] == version_id:
                return Version.from_dict(v_dict)

        raise ValueError(f"Version not found: {version_id}")

    def restore_version(
        self,
        course_id: str,
        activity_id: str,
        version_id: str,
        user_id: str
    ) -> Dict:
        """Restore activity content from a version.

        Args:
            course_id: Course ID
            activity_id: Activity ID
            version_id: Version ID to restore
            user_id: User ID for permission check

        Returns:
            Restored content dict

        Raises:
            ValueError: If course, activity, or version not found
        """
        # Load course
        course = self.project_store.load(user_id, course_id)
        if not course:
            raise ValueError(f"Course not found: {course_id}")

        # Find activity
        activity = self._find_activity(course, activity_id)
        if not activity:
            raise ValueError(f"Activity not found: {activity_id}")

        # Find version
        versions = getattr(activity, 'versions', [])
        version_dict = None
        for v in versions:
            if v['id'] == version_id:
                version_dict = v
                break

        if not version_dict:
            raise ValueError(f"Version not found: {version_id}")

        # Restore content to activity
        activity.content = version_dict['content']

        # Save course
        self.project_store.save(user_id, course)

        return version_dict['content']

    def delete_version(
        self,
        course_id: str,
        activity_id: str,
        version_id: str,
        user_id: str
    ) -> bool:
        """Delete a version.

        Args:
            course_id: Course ID
            activity_id: Activity ID
            version_id: Version ID to delete
            user_id: User ID for permission check

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If course or activity not found
        """
        # Load course
        course = self.project_store.load(user_id, course_id)
        if not course:
            raise ValueError(f"Course not found: {course_id}")

        # Find activity
        activity = self._find_activity(course, activity_id)
        if not activity:
            raise ValueError(f"Activity not found: {activity_id}")

        # Find and remove version
        versions = getattr(activity, 'versions', [])
        for i, v in enumerate(versions):
            if v['id'] == version_id:
                versions.pop(i)
                self.project_store.save(user_id, course)
                return True

        return False

    def compare_versions(
        self,
        course_id: str,
        activity_id: str,
        v1_id: str,
        v2_id: str,
        user_id: str
    ) -> DiffResult:
        """Compare two versions and return diff.

        Args:
            course_id: Course ID
            activity_id: Activity ID
            v1_id: First version ID (original)
            v2_id: Second version ID (modified)
            user_id: User ID for permission check

        Returns:
            DiffResult showing changes between versions

        Raises:
            ValueError: If course, activity, or versions not found
        """
        # Get both versions
        v1 = self.get_version(course_id, activity_id, v1_id, user_id)
        v2 = self.get_version(course_id, activity_id, v2_id, user_id)

        # Convert content dicts to strings for comparison
        import json
        v1_text = json.dumps(v1.content, indent=2, sort_keys=True)
        v2_text = json.dumps(v2.content, indent=2, sort_keys=True)

        # Generate diff
        return self.diff_generator.generate_diff(v1_text, v2_text)

    def _find_activity(self, course, activity_id: str):
        """Find activity by ID in course structure.

        Args:
            course: Course object
            activity_id: Activity ID to find

        Returns:
            Activity object or None if not found
        """
        for module in course.modules:
            for lesson in module.lessons:
                for activity in lesson.activities:
                    if activity.id == activity_id:
                        return activity
        return None
