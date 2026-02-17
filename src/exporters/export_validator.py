"""Pre-export validation for content completeness.

Verifies that all required content is present and in appropriate state
before exporting course content.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from src.core.models import Course, BuildState, ContentType


@dataclass
class ExportValidationResult:
    """Result of export validation check.

    Attributes:
        is_exportable: True if course can be exported.
        missing_content: List of activities missing content.
        incomplete_activities: List of activities not in approved/published state.
        warnings: List of warning messages.
        metrics: Quantitative metrics about course completeness.
    """
    is_exportable: bool
    missing_content: List[Dict[str, str]] = field(default_factory=list)
    incomplete_activities: List[Dict[str, str]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for API responses."""
        return {
            "is_exportable": self.is_exportable,
            "missing_content": self.missing_content,
            "incomplete_activities": self.incomplete_activities,
            "warnings": self.warnings,
            "metrics": self.metrics,
        }


class ExportValidator:
    """Validates course content completeness before export.

    Checks that:
    - All activities have generated content
    - All activities are in approved or published state
    - Course structure is complete (modules, lessons, activities)
    """

    # States that indicate content is ready for export
    EXPORTABLE_STATES = {BuildState.APPROVED, BuildState.PUBLISHED}

    def validate_for_export(
        self,
        course: Course,
        require_approved: bool = True
    ) -> ExportValidationResult:
        """Validate course is ready for export.

        Args:
            course: Course object to validate.
            require_approved: If True, activities must be in APPROVED or PUBLISHED state.
                            If False, any generated content is accepted.

        Returns:
            ExportValidationResult with validation details.
        """
        missing_content = []
        incomplete_activities = []
        warnings = []

        total_activities = 0
        activities_with_content = 0
        approved_activities = 0

        # Traverse course structure
        for module in course.modules:
            for lesson in module.lessons:
                for activity in lesson.activities:
                    total_activities += 1

                    # Check for missing content
                    if not activity.content or activity.content.strip() == "":
                        missing_content.append({
                            "activity_id": activity.id,
                            "title": activity.title,
                            "content_type": activity.content_type.value,
                            "module": module.title,
                            "lesson": lesson.title,
                        })
                    else:
                        activities_with_content += 1

                    # Check build state
                    if activity.build_state in self.EXPORTABLE_STATES:
                        approved_activities += 1
                    elif require_approved:
                        incomplete_activities.append({
                            "activity_id": activity.id,
                            "title": activity.title,
                            "current_state": activity.build_state.value,
                            "module": module.title,
                            "lesson": lesson.title,
                        })

        # Add warnings for empty structure
        if len(course.modules) == 0:
            warnings.append("Course has no modules")
        else:
            for module in course.modules:
                if len(module.lessons) == 0:
                    warnings.append(f"Module '{module.title}' has no lessons")

        # Determine if exportable
        has_content = len(missing_content) == 0
        has_approved = len(incomplete_activities) == 0 if require_approved else True
        is_exportable = has_content and has_approved and total_activities > 0

        # Calculate metrics
        content_completion = (
            activities_with_content / total_activities
            if total_activities > 0 else 0.0
        )
        approval_rate = (
            approved_activities / total_activities
            if total_activities > 0 else 0.0
        )

        return ExportValidationResult(
            is_exportable=is_exportable,
            missing_content=missing_content,
            incomplete_activities=incomplete_activities,
            warnings=warnings,
            metrics={
                "total_activities": total_activities,
                "activities_with_content": activities_with_content,
                "approved_activities": approved_activities,
                "content_completion_rate": round(content_completion, 2),
                "approval_rate": round(approval_rate, 2),
            }
        )

    def get_missing_content(self, course: Course) -> List[Dict[str, str]]:
        """Get list of activities missing content.

        Convenience method for quick check of missing content.

        Args:
            course: Course object to check.

        Returns:
            List of dicts with activity details for activities without content.
        """
        result = self.validate_for_export(course, require_approved=False)
        return result.missing_content

    def get_export_readiness(self, course: Course) -> Dict[str, Any]:
        """Get summary of export readiness.

        Args:
            course: Course object to check.

        Returns:
            Dict with readiness summary.
        """
        result = self.validate_for_export(course, require_approved=True)

        return {
            "is_exportable": result.is_exportable,
            "total_activities": result.metrics.get("total_activities", 0),
            "content_complete": len(result.missing_content) == 0,
            "all_approved": len(result.incomplete_activities) == 0,
            "missing_count": len(result.missing_content),
            "unapproved_count": len(result.incomplete_activities),
        }
