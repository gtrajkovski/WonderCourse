"""Aggregates all validation results into comprehensive report.

Runs structural, outcome, Bloom's, and distractor validators and combines results.
"""

from typing import Dict
from src.core.models import Course, ContentType
from src.validators.validation_result import ValidationResult
from src.validators.course_validator import CourseValidator
from src.validators.outcome_validator import OutcomeValidator
from src.validators.blooms_validator import BloomsValidator
from src.validators.distractor_validator import DistractorValidator


class ValidationReport:
    """Aggregates all validation results into single report.

    Runs structural, outcome, Bloom's, and distractor validators.
    """

    def __init__(self):
        self.course_validator = CourseValidator()
        self.outcome_validator = OutcomeValidator()
        self.blooms_validator = BloomsValidator()
        self.distractor_validator = DistractorValidator()

    def validate_course(self, course: Course) -> Dict[str, ValidationResult]:
        """Run all validators and return combined report.

        Args:
            course: Course object to validate.

        Returns:
            Dict mapping validator name to ValidationResult.
        """
        results = {}

        # Run structural validation
        results["CourseValidator"] = self.course_validator.validate(course)

        # Run outcome validation
        results["OutcomeValidator"] = self.outcome_validator.validate(course)

        # Run Bloom's validation
        results["BloomsValidator"] = self.blooms_validator.validate(course)

        # Run distractor validation on all quiz activities
        distractor_result = self._validate_all_quizzes(course)
        results["DistractorValidator"] = distractor_result

        return results

    def is_publishable(self, course: Course) -> bool:
        """Check if course passes all critical validation checks.

        Only errors block publishing. Warnings are informational.

        Args:
            course: Course object to check.

        Returns:
            True if no errors from any validator.
        """
        results = self.validate_course(course)
        return all(result.is_valid for result in results.values())

    def _validate_all_quizzes(self, course: Course) -> ValidationResult:
        """Validate all quiz activities in course.

        Args:
            course: Course object to validate.

        Returns:
            Combined ValidationResult for all quizzes.
        """
        all_errors = []
        all_warnings = []
        all_suggestions = []
        total_quizzes = 0
        total_flagged = 0

        # Find all quiz activities
        for module in course.modules:
            for lesson in module.lessons:
                for activity in lesson.activities:
                    if activity.content_type == ContentType.QUIZ and activity.content:
                        total_quizzes += 1
                        result = self.distractor_validator.validate_quiz(activity.content)

                        # Prefix errors with activity title
                        for error in result.errors:
                            all_errors.append(f"[{activity.title}] {error}")
                        for warning in result.warnings:
                            all_warnings.append(f"[{activity.title}] {warning}")

                        if not result.is_valid:
                            total_flagged += 1

        if total_quizzes == 0:
            return ValidationResult(
                is_valid=True,
                errors=[],
                warnings=[],
                suggestions=["No quiz activities to validate"],
                metrics={"total_quizzes": 0}
            )

        quality_score = 1.0 - (total_flagged / total_quizzes) if total_quizzes > 0 else 0.0

        return ValidationResult(
            is_valid=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings,
            suggestions=all_suggestions,
            metrics={
                "total_quizzes": total_quizzes,
                "flagged_quizzes": total_flagged,
                "overall_quality_score": round(quality_score, 2)
            }
        )
