"""Abstract base class for all export formats.

Provides common interface for exporting course content to various formats
(DOCX, PDF, HTML, etc.).
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any

from src.core.models import Course


class BaseExporter(ABC):
    """Abstract base class for course content exporters.

    All concrete exporters must implement export() method to generate
    output in their specific format.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize exporter with optional output directory.

        Args:
            output_dir: Directory for export output. If None, uses current directory.
        """
        self.output_dir = output_dir or Path.cwd()

    @property
    @abstractmethod
    def format_name(self) -> str:
        """Human-readable name of the export format (e.g., 'Microsoft Word')."""
        pass

    @property
    @abstractmethod
    def file_extension(self) -> str:
        """File extension for exported files (e.g., '.docx')."""
        pass

    @abstractmethod
    def export(self, course: Course, filename: Optional[str] = None) -> Path:
        """Export course content to file.

        Args:
            course: Course object to export.
            filename: Optional filename (without extension). If None, uses course title.

        Returns:
            Path to the exported file.
        """
        pass

    def get_output_path(self, course: Course, filename: Optional[str] = None) -> Path:
        """Generate output file path for export.

        Args:
            course: Course object being exported.
            filename: Optional filename (without extension). If None, uses course title.

        Returns:
            Full path including directory and extension.
        """
        if filename is None:
            # Sanitize course title for use as filename
            safe_title = "".join(
                c if c.isalnum() or c in " -_" else "_"
                for c in course.title
            ).strip()
            filename = safe_title or "untitled_course"

        return self.output_dir / f"{filename}{self.file_extension}"

    def get_metadata(self, course: Course) -> Dict[str, Any]:
        """Extract export metadata from course.

        Args:
            course: Course object to extract metadata from.

        Returns:
            Dictionary of metadata for export.
        """
        total_activities = 0
        for module in course.modules:
            for lesson in module.lessons:
                total_activities += len(lesson.activities)

        return {
            "title": course.title,
            "description": course.description,
            "audience_level": course.audience_level,
            "target_duration_minutes": course.target_duration_minutes,
            "module_count": len(course.modules),
            "activity_count": total_activities,
            "outcome_count": len(course.learning_outcomes),
        }
