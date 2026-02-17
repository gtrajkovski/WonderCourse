"""LMS JSON manifest exporter for Course Builder Studio.

Exports complete course structure as a structured JSON manifest
suitable for LMS import.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

from src.core.models import Course, Module, Lesson, Activity, LearningOutcome
from src.exporters.base_exporter import BaseExporter


class LMSManifestExporter(BaseExporter):
    """Exports course content as structured JSON manifest.

    Creates a JSON file containing:
    - Manifest metadata (version, exported_at)
    - Complete course hierarchy (modules -> lessons -> activities)
    - Learning outcomes with activity mappings
    """

    MANIFEST_VERSION = "1.0"

    @property
    def format_name(self) -> str:
        """Human-readable name of the export format."""
        return "LMS JSON Manifest"

    @property
    def file_extension(self) -> str:
        """File extension for exported files."""
        return ".json"

    def export(self, course: Course, filename: Optional[str] = None) -> Path:
        """Export course as JSON manifest.

        Args:
            course: Course object to export.
            filename: Optional filename (without extension). If None, uses course title.

        Returns:
            Path to the exported JSON file.
        """
        output_path = self.get_output_path(course, filename)

        manifest = self._build_manifest(course)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        return output_path

    def _build_manifest(self, course: Course) -> Dict[str, Any]:
        """Build the complete manifest structure.

        Args:
            course: Course object to serialize.

        Returns:
            Dictionary containing the full manifest.
        """
        return {
            "version": self.MANIFEST_VERSION,
            "exported_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "course": self._serialize_course(course),
            "learning_outcomes": self._serialize_learning_outcomes(course.learning_outcomes),
        }

    def _serialize_course(self, course: Course) -> Dict[str, Any]:
        """Serialize course with full hierarchy.

        Args:
            course: Course object to serialize.

        Returns:
            Dictionary containing course data with nested modules, lessons, activities.
        """
        return {
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "audience_level": course.audience_level,
            "target_duration_minutes": course.target_duration_minutes,
            "modules": [self._serialize_module(m) for m in course.modules],
        }

    def _serialize_module(self, module: Module) -> Dict[str, Any]:
        """Serialize module with lessons.

        Args:
            module: Module object to serialize.

        Returns:
            Dictionary containing module data with nested lessons.
        """
        return {
            "id": module.id,
            "title": module.title,
            "description": module.description,
            "order": module.order,
            "lessons": [self._serialize_lesson(lesson) for lesson in module.lessons],
        }

    def _serialize_lesson(self, lesson: Lesson) -> Dict[str, Any]:
        """Serialize lesson with activities.

        Args:
            lesson: Lesson object to serialize.

        Returns:
            Dictionary containing lesson data with nested activities.
        """
        return {
            "id": lesson.id,
            "title": lesson.title,
            "description": lesson.description,
            "order": lesson.order,
            "activities": [self._serialize_activity(a) for a in lesson.activities],
        }

    def _serialize_activity(self, activity: Activity) -> Dict[str, Any]:
        """Serialize activity with all relevant fields.

        Args:
            activity: Activity object to serialize.

        Returns:
            Dictionary containing activity data.
        """
        return {
            "id": activity.id,
            "title": activity.title,
            "content_type": activity.content_type.value,
            "content": activity.content,
            "build_state": activity.build_state.value,
            "order": activity.order,
        }

    def _serialize_learning_outcomes(
        self, outcomes: List[LearningOutcome]
    ) -> List[Dict[str, Any]]:
        """Serialize learning outcomes with activity mappings.

        Args:
            outcomes: List of LearningOutcome objects.

        Returns:
            List of dictionaries containing outcome data.
        """
        return [self._serialize_outcome(outcome) for outcome in outcomes]

    def _serialize_outcome(self, outcome: LearningOutcome) -> Dict[str, Any]:
        """Serialize a single learning outcome.

        Args:
            outcome: LearningOutcome object to serialize.

        Returns:
            Dictionary containing outcome data with ABCD components and mappings.
        """
        return {
            "id": outcome.id,
            "audience": outcome.audience,
            "behavior": outcome.behavior,
            "condition": outcome.condition,
            "degree": outcome.degree,
            "bloom_level": outcome.bloom_level.value,
            "mapped_activity_ids": outcome.mapped_activity_ids,
        }
