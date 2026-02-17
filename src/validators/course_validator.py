"""Coursera requirements validator for course blueprints and Course objects.

All validation is deterministic Python logic - never uses AI.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from collections import Counter

from src.generators.blueprint_generator import CourseBlueprint, ActivityBlueprint
from src.validators.validation_result import ValidationResult
from src.core.models import Course, Activity


@dataclass
class BlueprintValidation:
    """Validation result for a course blueprint."""

    is_valid: bool
    errors: List[str]       # Blockers that prevent acceptance
    warnings: List[str]     # Non-blocking suggestions
    suggestions: List[str]  # Optional improvements
    metrics: Dict[str, Any] # Computed metrics for display


class CourseraValidator:
    """Validates course blueprints against Coursera short course requirements.

    All validation is deterministic Python logic - never uses AI.
    """

    # Constants (from Coursera requirements)
    MIN_DURATION = 30
    MAX_DURATION = 180
    MIN_MODULES = 2
    MAX_MODULES = 3
    MIN_LESSONS_PER_MODULE = 3
    MAX_LESSONS_PER_MODULE = 5
    MIN_ACTIVITIES_PER_LESSON = 2
    MAX_ACTIVITIES_PER_LESSON = 4
    TARGET_VIDEO_PCT = 0.30
    TARGET_READING_PCT = 0.20
    TARGET_PRACTICE_PCT = 0.30
    TARGET_ASSESSMENT_PCT = 0.20
    DISTRIBUTION_TOLERANCE = 0.15  # Allow 15% deviation from targets

    def validate(self, blueprint: CourseBlueprint, target_duration: Optional[int] = None) -> BlueprintValidation:
        """Run all validation checks. Returns BlueprintValidation."""
        errors = []
        warnings = []
        suggestions = []

        # Extract all activities for analysis
        all_activities = self._flatten_activities(blueprint)

        # ERROR checks (blockers):

        # 1. Module count: must be 2-3
        module_count = len(blueprint.modules)
        if not (self.MIN_MODULES <= module_count <= self.MAX_MODULES):
            errors.append(
                f"Must have {self.MIN_MODULES}-{self.MAX_MODULES} modules, got {module_count}"
            )

        # 2. Total duration: must be 30-180 min
        total_duration = blueprint.total_duration_minutes
        if total_duration < self.MIN_DURATION:
            errors.append(
                f"Duration {total_duration:.0f}min below minimum {self.MIN_DURATION}min"
            )
        elif total_duration > self.MAX_DURATION:
            errors.append(
                f"Duration {total_duration:.0f}min exceeds maximum {self.MAX_DURATION}min"
            )

        # 3. If target_duration provided: actual must be within 20% of target
        if target_duration is not None:
            deviation = abs(total_duration - target_duration) / target_duration
            if deviation > 0.20:
                errors.append(
                    f"Duration {total_duration:.0f}min deviates {deviation:.0%} from target "
                    f"{target_duration}min (max 20% allowed)"
                )

        # WARNING checks (non-blocking):

        # 4. Lessons per module: should be 3-5
        for i, module in enumerate(blueprint.modules, 1):
            lesson_count = len(module.lessons)
            if not (self.MIN_LESSONS_PER_MODULE <= lesson_count <= self.MAX_LESSONS_PER_MODULE):
                warnings.append(
                    f"Module {i} has {lesson_count} lessons "
                    f"(recommended {self.MIN_LESSONS_PER_MODULE}-{self.MAX_LESSONS_PER_MODULE})"
                )

        # 5. Activities per lesson: should be 2-4
        for module in blueprint.modules:
            for lesson in module.lessons:
                activity_count = len(lesson.activities)
                if not (self.MIN_ACTIVITIES_PER_LESSON <= activity_count <= self.MAX_ACTIVITIES_PER_LESSON):
                    warnings.append(
                        f"Lesson '{lesson.title}' has {activity_count} activities "
                        f"(recommended {self.MIN_ACTIVITIES_PER_LESSON}-{self.MAX_ACTIVITIES_PER_LESSON})"
                    )

        # 6. Video content percentage vs target (~30%)
        content_types = [a.content_type for a in all_activities]
        type_counts = Counter(content_types)
        total_activities = len(all_activities)

        if total_activities > 0:
            video_pct = type_counts.get('video', 0) / total_activities
            if abs(video_pct - self.TARGET_VIDEO_PCT) > self.DISTRIBUTION_TOLERANCE:
                warnings.append(
                    f"Video content {video_pct:.0%} (target ~{self.TARGET_VIDEO_PCT:.0%})"
                )

        # 7. Bloom's taxonomy diversity: should have 3+ levels
        bloom_levels = [a.bloom_level for a in all_activities]
        unique_blooms = len(set(bloom_levels))
        if unique_blooms < 3:
            warnings.append(
                f"Only {unique_blooms} Bloom's taxonomy level(s) used (recommended 3+)"
            )

        # 8. WWHAA phase present on video activities
        video_activities = [a for a in all_activities if a.content_type == 'video']
        videos_without_wwhaa = [a for a in video_activities if a.wwhaa_phase is None]
        if videos_without_wwhaa:
            warnings.append(
                f"{len(videos_without_wwhaa)} video activity(ies) missing WWHAA phase"
            )

        # SUGGESTION checks (optional):

        # 9. If no assessment activities, suggest adding quiz
        assessment_types = ['quiz']
        has_assessments = any(a.content_type in assessment_types for a in all_activities)
        if not has_assessments:
            suggestions.append(
                "Consider adding quiz activities for knowledge assessment"
            )

        # 10. If all same Bloom level, suggest variety
        if unique_blooms == 1:
            suggestions.append(
                "Consider varying Bloom's taxonomy levels across activities for better learning progression"
            )

        # METRICS:
        content_distribution = {}
        if total_activities > 0:
            content_distribution = {
                content_type: count / total_activities
                for content_type, count in type_counts.items()
            }

        # Calculate average activities per lesson
        total_lessons = sum(len(module.lessons) for module in blueprint.modules)
        activities_per_lesson_avg = total_activities / total_lessons if total_lessons > 0 else 0

        metrics = {
            "total_duration": total_duration,
            "module_count": module_count,
            "total_lessons": total_lessons,
            "total_activities": total_activities,
            "content_distribution": content_distribution,
            "bloom_diversity": unique_blooms,
            "activities_per_lesson_avg": round(activities_per_lesson_avg, 2)
        }

        return BlueprintValidation(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            metrics=metrics
        )

    def _flatten_activities(self, blueprint: CourseBlueprint) -> List[ActivityBlueprint]:
        """Extract all activities from nested structure."""
        activities = []
        for module in blueprint.modules:
            for lesson in module.lessons:
                activities.extend(lesson.activities)
        return activities


class CourseValidator:
    """Validates Course objects against Coursera short course requirements.

    All validation is deterministic Python logic - never uses AI.
    """

    # Constants (same as CourseraValidator)
    MIN_DURATION = 30
    MAX_DURATION = 180
    MIN_MODULES = 2
    MAX_MODULES = 3
    MIN_LESSONS_PER_MODULE = 3
    MAX_LESSONS_PER_MODULE = 5
    MIN_ACTIVITIES_PER_LESSON = 2
    MAX_ACTIVITIES_PER_LESSON = 4
    TARGET_VIDEO_PCT = 0.30
    TARGET_READING_PCT = 0.20
    TARGET_PRACTICE_PCT = 0.30
    TARGET_ASSESSMENT_PCT = 0.20
    DISTRIBUTION_TOLERANCE = 0.15

    def validate(self, course: Course) -> ValidationResult:
        """Run all validation checks on a Course object."""
        errors = []
        warnings = []
        suggestions = []

        # Get all activities
        all_activities = self._flatten_activities(course)

        # ERROR: Module count (2-3)
        module_count = len(course.modules)
        if not (self.MIN_MODULES <= module_count <= self.MAX_MODULES):
            errors.append(
                f"Must have {self.MIN_MODULES}-{self.MAX_MODULES} modules, got {module_count}"
            )

        # ERROR: Total duration (30-180 min)
        total_duration = sum(a.estimated_duration_minutes for a in all_activities)
        if total_duration < self.MIN_DURATION:
            errors.append(f"Duration {total_duration:.0f}min below minimum {self.MIN_DURATION}min")
        elif total_duration > self.MAX_DURATION:
            errors.append(f"Duration {total_duration:.0f}min exceeds maximum {self.MAX_DURATION}min")

        # ERROR: Duration deviation from target (if specified)
        target = course.target_duration_minutes
        if target and total_duration > 0:
            deviation = abs(total_duration - target) / target
            if deviation > 0.20:
                errors.append(
                    f"Duration {total_duration:.0f}min deviates {deviation:.0%} from target {target}min (max 20%)"
                )

        # WARNING: Lessons per module (3-5)
        for i, module in enumerate(course.modules, 1):
            lesson_count = len(module.lessons)
            if lesson_count > 0 and not (self.MIN_LESSONS_PER_MODULE <= lesson_count <= self.MAX_LESSONS_PER_MODULE):
                warnings.append(
                    f"Module {i} has {lesson_count} lessons (recommended {self.MIN_LESSONS_PER_MODULE}-{self.MAX_LESSONS_PER_MODULE})"
                )

        # WARNING: Activities per lesson (2-4)
        for module in course.modules:
            for lesson in module.lessons:
                activity_count = len(lesson.activities)
                if activity_count > 0 and not (self.MIN_ACTIVITIES_PER_LESSON <= activity_count <= self.MAX_ACTIVITIES_PER_LESSON):
                    warnings.append(
                        f"Lesson '{lesson.title}' has {activity_count} activities (recommended {self.MIN_ACTIVITIES_PER_LESSON}-{self.MAX_ACTIVITIES_PER_LESSON})"
                    )

        # WARNING: Video content percentage
        total_activities = len(all_activities)
        if total_activities > 0:
            from collections import Counter
            type_counts = Counter(a.content_type.value for a in all_activities)
            video_pct = type_counts.get('video', 0) / total_activities
            if abs(video_pct - self.TARGET_VIDEO_PCT) > self.DISTRIBUTION_TOLERANCE:
                warnings.append(f"Video content {video_pct:.0%} (target ~{self.TARGET_VIDEO_PCT:.0%})")

        # WARNING: Bloom's diversity (3+ levels)
        bloom_levels = [a.bloom_level for a in all_activities if a.bloom_level]
        unique_blooms = len(set(bloom_levels))
        if bloom_levels and unique_blooms < 3:
            warnings.append(f"Only {unique_blooms} Bloom's taxonomy level(s) used (recommended 3+)")

        # SUGGESTION: No assessments
        has_quiz = any(a.content_type.value == 'quiz' for a in all_activities)
        if not has_quiz:
            suggestions.append("Consider adding quiz activities for knowledge assessment")

        # Build metrics
        content_distribution = {}
        if total_activities > 0:
            from collections import Counter
            type_counts = Counter(a.content_type.value for a in all_activities)
            content_distribution = {ct: count / total_activities for ct, count in type_counts.items()}

        total_lessons = sum(len(m.lessons) for m in course.modules)

        metrics = {
            "total_duration": total_duration,
            "module_count": module_count,
            "total_lessons": total_lessons,
            "total_activities": total_activities,
            "content_distribution": content_distribution,
            "bloom_diversity": unique_blooms if bloom_levels else 0,
            "activities_per_lesson_avg": round(total_activities / total_lessons, 2) if total_lessons > 0 else 0
        }

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            metrics=metrics
        )

    def _flatten_activities(self, course: Course) -> List[Activity]:
        """Extract all activities from course structure."""
        activities = []
        for module in course.modules:
            for lesson in module.lessons:
                activities.extend(lesson.activities)
        return activities
