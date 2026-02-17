"""Standards profile storage and management.

Handles persistence of content standards profiles to the standards/ directory.
Seeds system presets on first run.
"""

import json
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from src.core.models import ContentStandardsProfile


class StandardsStore:
    """Manages content standards profiles on disk.

    Profiles are stored as JSON files in the standards/ directory.
    System presets are seeded on first initialization.
    """

    def __init__(self, standards_dir: Path = Path("standards")):
        self.standards_dir = standards_dir
        self.standards_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_system_presets()

    def _ensure_system_presets(self) -> None:
        """Seed system presets if they don't exist."""
        presets = self._get_system_presets()
        for preset in presets:
            path = self.standards_dir / f"{preset.id}.json"
            if not path.exists():
                self.save(preset)

    def _get_system_presets(self) -> List[ContentStandardsProfile]:
        """Return all system preset profiles."""
        return [
            self._coursera_preset(),
            self._flexible_preset(),
            self._corporate_preset(),
        ]

    def _coursera_preset(self) -> ContentStandardsProfile:
        """Coursera Short Course preset - the default standard."""
        return ContentStandardsProfile(
            id="std_coursera",
            name="Coursera Short Course",
            description="Standard Coursera short course format with WWHAA structure, 3-10 minute videos, and rigorous assessment requirements.",
            is_system_preset=True,
            # All defaults match Coursera specs (already set in dataclass)
            # Humanization enabled to ensure natural-sounding content
            enable_auto_humanize=True,
            humanization_score_threshold=70,
        )

    def _flexible_preset(self) -> ContentStandardsProfile:
        """Flexible preset with minimal constraints."""
        return ContentStandardsProfile(
            id="std_flexible",
            name="Flexible / No Constraints",
            description="Minimal constraints for maximum flexibility. Use when client has no specific format requirements.",
            is_system_preset=True,
            # Humanization disabled for maximum flexibility
            enable_auto_humanize=False,
            # Video
            video_max_duration_min=60,
            video_ideal_min_duration=1,
            video_ideal_max_duration=30,
            video_structure=[],
            video_structure_required=False,
            # Reading
            reading_max_words=10000,
            reading_min_references=0,
            reading_max_references=20,
            reading_reference_format="none",
            reading_require_free_links=False,
            # HOL
            hol_rubric_criteria_count=1,
            hol_rubric_total_points=100,
            hol_rubric_levels=[
                {"name": "Excellent", "points": 100},
                {"name": "Good", "points": 80},
                {"name": "Satisfactory", "points": 60},
                {"name": "Needs Improvement", "points": 40},
            ],
            hol_submission_format="any",
            hol_max_word_count=5000,
            # Quiz
            quiz_options_per_question=4,
            quiz_require_per_option_feedback=False,
            quiz_require_balanced_distribution=False,
            # Coach
            coach_require_example_responses=False,
            coach_require_scenario=False,
            # Course structure
            course_min_modules=1,
            course_max_modules=20,
            course_min_duration_min=5,
            course_max_duration_min=1200,
            course_min_learning_objectives=1,
            course_max_learning_objectives=20,
            course_min_items=1,
            course_max_items=200,
            forbid_sequential_references=False,
            # Attribution
            require_attribution=False,
        )

    def _corporate_preset(self) -> ContentStandardsProfile:
        """Corporate training preset with shorter content and simpler rubrics."""
        return ContentStandardsProfile(
            id="std_corporate",
            name="Corporate Training",
            description="Optimized for internal corporate training: shorter videos, simpler rubrics, no academic references required.",
            is_system_preset=True,
            # Humanization enabled for professional tone
            enable_auto_humanize=True,
            humanization_score_threshold=75,
            # Video - shorter
            video_max_duration_min=5,
            video_ideal_min_duration=2,
            video_ideal_max_duration=4,
            video_structure=["Hook", "Content", "Summary", "CTA"],
            video_structure_required=False,
            # Reading - no references required
            reading_max_words=800,
            reading_min_references=0,
            reading_max_references=2,
            reading_reference_format="none",
            reading_require_free_links=False,
            # HOL - 4-level rubric
            hol_rubric_criteria_count=4,
            hol_rubric_total_points=20,
            hol_rubric_levels=[
                {"name": "Exceeds Expectations", "points": 5},
                {"name": "Meets Expectations", "points": 4},
                {"name": "Approaching Expectations", "points": 3},
                {"name": "Below Expectations", "points": 1},
            ],
            hol_submission_format="any",
            # Quiz
            quiz_options_per_question=4,
            quiz_require_per_option_feedback=True,
            quiz_require_balanced_distribution=False,
            # Coach - optional
            coach_require_example_responses=False,
            coach_require_scenario=False,
            # Course structure - more flexible
            course_min_modules=1,
            course_max_modules=10,
            course_min_duration_min=15,
            course_max_duration_min=480,
            course_min_learning_objectives=1,
            course_max_learning_objectives=10,
            forbid_sequential_references=False,
            # Tone - more direct
            tone_description="Direct and practical. Focus on actionable takeaways and real workplace applications.",
            # Attribution
            require_attribution=False,
        )

    def _get_profile_path(self, profile_id: str) -> Path:
        """Get the file path for a profile."""
        return self.standards_dir / f"{profile_id}.json"

    def load(self, profile_id: str) -> Optional[ContentStandardsProfile]:
        """Load a profile by ID.

        Args:
            profile_id: The profile ID to load

        Returns:
            The profile if found, None otherwise
        """
        path = self._get_profile_path(profile_id)
        if not path.exists():
            return None

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return ContentStandardsProfile.from_dict(data)

    def save(self, profile: ContentStandardsProfile) -> None:
        """Save a profile to disk.

        Args:
            profile: The profile to save
        """
        profile.updated_at = datetime.now().isoformat()
        path = self._get_profile_path(profile.id)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(profile.to_dict(), f, indent=2)

    def delete(self, profile_id: str) -> bool:
        """Delete a profile by ID.

        System presets cannot be deleted.

        Args:
            profile_id: The profile ID to delete

        Returns:
            True if deleted, False if not found or is system preset
        """
        profile = self.load(profile_id)
        if profile is None:
            return False
        if profile.is_system_preset:
            return False

        path = self._get_profile_path(profile_id)
        path.unlink()
        return True

    def list_all(self) -> List[ContentStandardsProfile]:
        """List all profiles.

        Returns:
            List of all profiles, system presets first
        """
        profiles = []
        for path in self.standards_dir.glob("*.json"):
            profile = self.load(path.stem)
            if profile:
                profiles.append(profile)

        # Sort: system presets first, then by name
        profiles.sort(key=lambda p: (not p.is_system_preset, p.name))
        return profiles

    def duplicate(self, profile_id: str, new_name: str) -> Optional[ContentStandardsProfile]:
        """Duplicate a profile with a new name.

        Args:
            profile_id: The profile ID to duplicate
            new_name: Name for the new profile

        Returns:
            The new profile if successful, None if source not found
        """
        source = self.load(profile_id)
        if source is None:
            return None

        # Create new profile with new ID and name
        new_data = source.to_dict()
        new_data["id"] = f"std_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        new_data["name"] = new_name
        new_data["description"] = f"Copy of {source.name}"
        new_data["is_system_preset"] = False
        new_data["created_at"] = datetime.now().isoformat()
        new_data["updated_at"] = datetime.now().isoformat()

        new_profile = ContentStandardsProfile.from_dict(new_data)
        self.save(new_profile)
        return new_profile

    def get_default(self) -> ContentStandardsProfile:
        """Get the default profile (Coursera Short Course).

        Returns:
            The Coursera preset profile
        """
        profile = self.load("std_coursera")
        if profile is None:
            # Re-seed if missing
            self._ensure_system_presets()
            profile = self.load("std_coursera")
        return profile

    def get_for_course(self, course) -> ContentStandardsProfile:
        """Get the active standards profile for a course.

        Args:
            course: The course object (must have standards_profile_id attribute)

        Returns:
            The course's profile if set, otherwise the default
        """
        if course.standards_profile_id:
            profile = self.load(course.standards_profile_id)
            if profile:
                return profile
        return self.get_default()
