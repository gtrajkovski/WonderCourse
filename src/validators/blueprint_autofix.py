"""Blueprint auto-fix module for resolving common validation issues.

Provides automatic fixes for:
- Duration imbalances (scaling activity durations)
- Missing WWHAA phases on video activities
- Module count issues (merging/splitting)
- Activity count per lesson
"""

from typing import List, Dict, Any, Optional, Tuple
from copy import deepcopy
from dataclasses import dataclass

from src.generators.blueprint_generator import (
    CourseBlueprint, ModuleBlueprint, LessonBlueprint, ActivityBlueprint
)
from src.validators.course_validator import CourseraValidator, BlueprintValidation


@dataclass
class AutoFixResult:
    """Result of auto-fix operation."""

    blueprint: CourseBlueprint
    fixes_applied: List[str]
    remaining_issues: List[str]
    was_modified: bool


class BlueprintAutoFixer:
    """Automatically fixes common blueprint validation issues.

    Applies deterministic fixes that don't require AI regeneration:
    - Duration scaling to meet targets
    - Adding missing WWHAA phases
    - Balancing activity counts
    """

    # Activity type to WWHAA phase defaults
    DEFAULT_WWHAA = {
        'video': 'content',
        'reading': 'content',
        'quiz': 'assess',
        'practice_quiz': 'apply',
        'hol': 'apply',
        'lab': 'apply',
        'discussion': 'apply',
        'assignment': 'apply',
        'project': 'apply',
        'coach': 'hook',
    }

    # Duration ranges by content type (min, typical, max)
    DURATION_RANGES = {
        'video': (3, 7, 12),
        'reading': (5, 10, 15),
        'quiz': (5, 8, 15),
        'practice_quiz': (3, 5, 8),
        'hol': (15, 25, 45),
        'lab': (10, 20, 30),
        'discussion': (5, 10, 20),
        'assignment': (15, 30, 60),
        'project': (20, 45, 90),
        'coach': (3, 5, 10),
    }

    def __init__(self):
        self.validator = CourseraValidator()

    def auto_fix(
        self,
        blueprint: CourseBlueprint,
        target_duration: Optional[int] = None
    ) -> AutoFixResult:
        """Apply automatic fixes to a blueprint.

        Args:
            blueprint: The blueprint to fix
            target_duration: Optional target duration to scale towards

        Returns:
            AutoFixResult with fixed blueprint and list of fixes applied
        """
        # Work on a deep copy
        fixed = deepcopy(blueprint)
        fixes_applied = []

        # Fix 1: Add missing WWHAA phases to video activities
        wwhaa_fixes = self._fix_missing_wwhaa(fixed)
        fixes_applied.extend(wwhaa_fixes)

        # Fix 2: Scale durations to meet target
        if target_duration:
            duration_fixes = self._fix_duration_scaling(fixed, target_duration)
            fixes_applied.extend(duration_fixes)

        # Fix 3: Balance activity counts per lesson
        balance_fixes = self._fix_activity_balance(fixed)
        fixes_applied.extend(balance_fixes)

        # Re-validate to check remaining issues
        validation = self.validator.validate(fixed, target_duration)
        remaining = validation.errors + validation.warnings

        return AutoFixResult(
            blueprint=fixed,
            fixes_applied=fixes_applied,
            remaining_issues=remaining,
            was_modified=len(fixes_applied) > 0
        )

    def _fix_missing_wwhaa(self, blueprint: CourseBlueprint) -> List[str]:
        """Add WWHAA phases to activities missing them."""
        fixes = []

        for module in blueprint.modules:
            for lesson in module.lessons:
                for activity in lesson.activities:
                    if activity.wwhaa_phase is None:
                        default_phase = self.DEFAULT_WWHAA.get(
                            activity.content_type, 'content'
                        )
                        activity.wwhaa_phase = default_phase
                        fixes.append(
                            f"Added WWHAA phase '{default_phase}' to "
                            f"'{activity.title}'"
                        )

        return fixes

    def _fix_duration_scaling(
        self,
        blueprint: CourseBlueprint,
        target_duration: int
    ) -> List[str]:
        """Scale activity durations to meet target total."""
        fixes = []

        current_total = blueprint.total_duration_minutes
        if current_total == 0:
            return fixes

        # Calculate deviation
        deviation = abs(current_total - target_duration) / target_duration

        # Only fix if deviation exceeds 15%
        if deviation <= 0.15:
            return fixes

        scale_factor = target_duration / current_total

        # Apply scaling with bounds
        scaled_count = 0
        for module in blueprint.modules:
            for lesson in module.lessons:
                for activity in lesson.activities:
                    old_duration = activity.estimated_duration_minutes

                    # Get bounds for this content type
                    min_dur, _, max_dur = self.DURATION_RANGES.get(
                        activity.content_type, (3, 10, 30)
                    )

                    # Scale and clamp
                    new_duration = old_duration * scale_factor
                    new_duration = max(min_dur, min(max_dur, new_duration))
                    new_duration = round(new_duration)

                    if new_duration != old_duration:
                        activity.estimated_duration_minutes = new_duration
                        scaled_count += 1

        if scaled_count > 0:
            new_total = sum(
                a.estimated_duration_minutes
                for m in blueprint.modules
                for l in m.lessons
                for a in l.activities
            )

            # Update the blueprint's total duration field
            # Use model_config mutation or direct assignment
            try:
                blueprint.total_duration_minutes = new_total
            except (AttributeError, TypeError):
                # Pydantic model may be frozen, can't update in place
                pass

            fixes.append(
                f"Scaled {scaled_count} activity durations from "
                f"{current_total:.0f}min to {new_total:.0f}min "
                f"(target: {target_duration}min)"
            )

        return fixes

    def _fix_activity_balance(self, blueprint: CourseBlueprint) -> List[str]:
        """Balance activity counts per lesson (2-4 activities)."""
        fixes = []

        MIN_ACTIVITIES = 2
        MAX_ACTIVITIES = 4

        for module in blueprint.modules:
            lessons_to_merge = []

            for i, lesson in enumerate(module.lessons):
                activity_count = len(lesson.activities)

                # Mark lessons with too few activities for potential merge
                if activity_count < MIN_ACTIVITIES:
                    lessons_to_merge.append(i)

            # If we have consecutive lessons with < 2 activities, suggest merge
            # (We don't actually merge as it changes structure significantly)
            if len(lessons_to_merge) >= 2:
                fixes.append(
                    f"Module '{module.title}' has {len(lessons_to_merge)} "
                    f"lessons with fewer than {MIN_ACTIVITIES} activities. "
                    f"Consider consolidating lessons."
                )

        return fixes

    def generate_refinement_feedback(
        self,
        validation: BlueprintValidation
    ) -> str:
        """Generate feedback prompt for AI refinement based on validation issues.

        Args:
            validation: The validation result to generate feedback from

        Returns:
            Formatted feedback string for refinement prompt
        """
        if validation.is_valid and not validation.warnings:
            return ""

        feedback_parts = []

        if validation.errors:
            feedback_parts.append("CRITICAL ISSUES (must fix):")
            for error in validation.errors:
                feedback_parts.append(f"- {error}")

        if validation.warnings:
            feedback_parts.append("\nWARNINGS (should fix):")
            for warning in validation.warnings:
                feedback_parts.append(f"- {warning}")

        feedback_parts.append("\nPlease regenerate the blueprint addressing these issues.")

        return "\n".join(feedback_parts)


def auto_fix_blueprint(
    blueprint: CourseBlueprint,
    target_duration: Optional[int] = None
) -> AutoFixResult:
    """Convenience function to auto-fix a blueprint.

    Args:
        blueprint: The blueprint to fix
        target_duration: Optional target duration

    Returns:
        AutoFixResult with fixed blueprint
    """
    fixer = BlueprintAutoFixer()
    return fixer.auto_fix(blueprint, target_duration)
