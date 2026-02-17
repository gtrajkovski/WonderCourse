"""Bloom's taxonomy distribution validator.

Validates that course activities have sufficient cognitive diversity
across Bloom's taxonomy levels.
"""

from collections import Counter
from typing import List
from src.validators.validation_result import ValidationResult
from src.core.models import Course, Activity, BloomLevel


class BloomsValidator:
    """Validates Bloom's taxonomy level distribution across activities.

    Checks for:
    - Minimum diversity (at least 2 different levels)
    - Balanced distribution (no single level dominates >80%)
    - Higher-order thinking activities (Analyze/Evaluate/Create)
    """

    MIN_DIVERSITY = 2  # At least 2 different levels
    IMBALANCE_THRESHOLD = 0.80  # Warn if >80% single level

    HIGHER_ORDER_LEVELS = [BloomLevel.ANALYZE, BloomLevel.EVALUATE, BloomLevel.CREATE]

    def validate(self, course: Course) -> ValidationResult:
        """Run Bloom's distribution validation.

        Args:
            course: Course to validate

        Returns:
            ValidationResult with errors, warnings, suggestions, and metrics
        """
        errors = []
        warnings = []
        suggestions = []

        # Get all activities with bloom_level set
        all_activities = self._flatten_activities(course)
        bloom_activities = [a for a in all_activities if a.bloom_level is not None]

        if not bloom_activities:
            return ValidationResult(
                is_valid=True,
                errors=[],
                warnings=[],
                suggestions=["Add activities with Bloom's levels to analyze distribution"],
                metrics={
                    "unique_levels": 0,
                    "total_activities": 0,
                    "distribution": {},
                    "dominant_level": None
                }
            )

        # Count levels
        level_counts = Counter(a.bloom_level for a in bloom_activities)
        unique_levels = len(level_counts)
        total = len(bloom_activities)
        dominant_level = max(level_counts, key=level_counts.get)
        max_count = level_counts[dominant_level]

        # ERROR: Must have at least 2 different levels
        if unique_levels < self.MIN_DIVERSITY:
            errors.append(
                f"Only {unique_levels} Bloom's level(s) used (minimum {self.MIN_DIVERSITY} for diverse learning)"
            )

        # WARNING: Imbalanced distribution (>80% single level)
        if max_count / total > self.IMBALANCE_THRESHOLD:
            percentage = int(max_count / total * 100)
            warnings.append(
                f"Bloom's distribution imbalanced: {percentage}% {dominant_level.value} (consider more variety)"
            )

        # SUGGESTION: No higher-order thinking
        has_higher_order = any(level in self.HIGHER_ORDER_LEVELS for level in level_counts.keys())
        if not has_higher_order:
            suggestions.append(
                "Consider adding higher-order thinking activities (Analyze, Evaluate, Create)"
            )

        # Build metrics
        distribution = {level.value: round(count / total, 2) for level, count in level_counts.items()}

        metrics = {
            "unique_levels": unique_levels,
            "total_activities": total,
            "distribution": distribution,
            "dominant_level": dominant_level.value
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
            course: Course to extract activities from

        Returns:
            List of all activities across all modules and lessons
        """
        activities = []
        for module in course.modules:
            for lesson in module.lessons:
                activities.extend(lesson.activities)
        return activities
