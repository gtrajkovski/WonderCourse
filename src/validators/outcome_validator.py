"""OutcomeValidator for learning outcome coverage and gap detection.

Validates alignment between learning outcomes and activities, detecting:
- Unmapped outcomes (0 activities linked)
- Low coverage outcomes (< 2 activities linked)
- Unmapped activities (not linked to any outcome)
- Stale activity references (deleted activities in mapped_activity_ids)
"""

from typing import List
from src.validators.validation_result import ValidationResult
from src.core.models import Course, Activity


class OutcomeValidator:
    """Validates learning outcome coverage and gap detection.

    Implements QA-03 (outcome-activity alignment with coverage scoring) and
    QA-04 (gap detection) from validation requirements.
    """

    MIN_ACTIVITIES_PER_OUTCOME = 2  # Recommended minimum for robust coverage

    def validate(self, course: Course) -> ValidationResult:
        """Run outcome coverage validation.

        Args:
            course: Course object with learning outcomes and activities

        Returns:
            ValidationResult with errors, warnings, and coverage metrics
        """
        errors = []
        warnings = []
        suggestions = []

        # Get all activity IDs from course structure
        all_activities = self._flatten_activities(course)
        activity_ids = {a.id for a in all_activities}

        # Handle case of no outcomes
        if not course.learning_outcomes:
            return ValidationResult(
                is_valid=True,
                errors=[],
                warnings=["No learning outcomes defined"],
                suggestions=["Add learning outcomes to track alignment"],
                metrics={
                    "coverage_score": 0.0,
                    "unmapped_outcomes": 0,
                    "low_coverage_outcomes": 0,
                    "unmapped_activities": len(all_activities),
                    "avg_activities_per_outcome": 0.0,
                    "total_outcomes": 0,
                    "total_activities": len(all_activities)
                }
            )

        # Check each outcome for coverage
        unmapped_outcomes = []
        low_coverage_outcomes = []

        for outcome in course.learning_outcomes:
            # Filter out stale activity IDs (deleted activities)
            valid_mappings = [aid for aid in outcome.mapped_activity_ids if aid in activity_ids]

            if len(valid_mappings) == 0:
                unmapped_outcomes.append(outcome)
            elif len(valid_mappings) < self.MIN_ACTIVITIES_PER_OUTCOME:
                low_coverage_outcomes.append((outcome, len(valid_mappings)))

        # ERROR: Unmapped outcomes (blockers)
        if unmapped_outcomes:
            for outcome in unmapped_outcomes:
                behavior_preview = self._truncate_text(outcome.behavior, 50)
                errors.append(f"Unmapped outcome: {behavior_preview}")

        # WARNING: Low coverage outcomes (concerns)
        for outcome, count in low_coverage_outcomes:
            behavior_preview = self._truncate_text(outcome.behavior, 50)
            warnings.append(
                f"Low coverage: '{behavior_preview}' has only {count} activity(ies) "
                f"(recommended {self.MIN_ACTIVITIES_PER_OUTCOME}+)"
            )

        # Check for unmapped activities
        mapped_activity_ids = set()
        for outcome in course.learning_outcomes:
            mapped_activity_ids.update(outcome.mapped_activity_ids)

        unmapped_activities = [a for a in all_activities if a.id not in mapped_activity_ids]
        if unmapped_activities:
            warnings.append(
                f"{len(unmapped_activities)} activity(ies) not mapped to any learning outcome"
            )

        # Calculate metrics
        covered_outcomes = len(course.learning_outcomes) - len(unmapped_outcomes)
        coverage_score = covered_outcomes / len(course.learning_outcomes)

        total_valid_mappings = sum(
            len([aid for aid in o.mapped_activity_ids if aid in activity_ids])
            for o in course.learning_outcomes
        )
        avg_activities = total_valid_mappings / len(course.learning_outcomes)

        metrics = {
            "coverage_score": round(coverage_score, 2),
            "unmapped_outcomes": len(unmapped_outcomes),
            "low_coverage_outcomes": len(low_coverage_outcomes),
            "unmapped_activities": len(unmapped_activities),
            "avg_activities_per_outcome": round(avg_activities, 1),
            "total_outcomes": len(course.learning_outcomes),
            "total_activities": len(all_activities)
        }

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            metrics=metrics
        )

    def _flatten_activities(self, course: Course) -> List[Activity]:
        """Extract all activities from course structure.

        Args:
            course: Course object with nested module/lesson/activity structure

        Returns:
            Flat list of all activities in the course
        """
        activities = []
        for module in course.modules:
            for lesson in module.lessons:
                activities.extend(lesson.activities)
        return activities

    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to max_length with ellipsis if needed.

        Args:
            text: Text to truncate
            max_length: Maximum length before truncation

        Returns:
            Truncated text with "..." appended if over max_length
        """
        if len(text) > max_length:
            return text[:max_length] + "..."
        return text
