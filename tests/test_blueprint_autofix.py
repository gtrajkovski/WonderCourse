"""Tests for blueprint auto-fix functionality."""

import pytest
from copy import deepcopy

from src.generators.blueprint_generator import (
    CourseBlueprint, ModuleBlueprint, LessonBlueprint, ActivityBlueprint,
    ContentDistribution
)
from src.validators.blueprint_autofix import (
    BlueprintAutoFixer, AutoFixResult, auto_fix_blueprint
)
from src.validators.course_validator import CourseraValidator, BlueprintValidation


def make_test_blueprint(
    module_count: int = 2,
    lessons_per_module: int = 3,
    activities_per_lesson: int = 2,
    duration_per_activity: float = 10.0,
    include_wwhaa: bool = True
) -> CourseBlueprint:
    """Create a test blueprint with configurable structure."""
    modules = []

    # Map content types to activity types
    activity_type_map = {
        'video': 'video_lecture',
        'reading': 'reading_material',
        'quiz': 'graded_quiz',
        'hol': 'hands_on_lab'
    }

    for m_idx in range(module_count):
        lessons = []
        for l_idx in range(lessons_per_module):
            activities = []
            for a_idx in range(activities_per_lesson):
                # Alternate content types
                content_types = ['video', 'reading', 'quiz', 'hol']
                content_type = content_types[(m_idx + l_idx + a_idx) % len(content_types)]
                activity_type = activity_type_map[content_type]

                activities.append(ActivityBlueprint(
                    title=f"Activity {m_idx+1}.{l_idx+1}.{a_idx+1}",
                    description=f"Description for activity {a_idx+1}",
                    content_type=content_type,
                    activity_type=activity_type,
                    estimated_duration_minutes=duration_per_activity,
                    bloom_level="apply",
                    wwhaa_phase="content" if include_wwhaa else None
                ))
            lessons.append(LessonBlueprint(
                title=f"Lesson {m_idx+1}.{l_idx+1}",
                description=f"Description for lesson {l_idx+1}",
                activities=activities
            ))
        modules.append(ModuleBlueprint(
            title=f"Module {m_idx+1}",
            description=f"Description for module {m_idx+1}",
            lessons=lessons
        ))

    # Calculate total duration from all activities
    total_duration = sum(
        activity.estimated_duration_minutes
        for module in modules
        for lesson in module.lessons
        for activity in lesson.activities
    )

    return CourseBlueprint(
        modules=modules,
        total_duration_minutes=total_duration,
        content_distribution=ContentDistribution(
            video=0.30, reading=0.20, quiz=0.20, hands_on=0.30
        ),
        rationale="Test blueprint rationale"
    )


class TestBlueprintAutoFixer:
    """Tests for BlueprintAutoFixer class."""

    def test_auto_fix_returns_result(self):
        """Test that auto_fix returns an AutoFixResult."""
        blueprint = make_test_blueprint()
        fixer = BlueprintAutoFixer()

        result = fixer.auto_fix(blueprint)

        assert isinstance(result, AutoFixResult)
        assert result.blueprint is not None
        assert isinstance(result.fixes_applied, list)
        assert isinstance(result.remaining_issues, list)

    def test_auto_fix_adds_missing_wwhaa(self):
        """Test that missing WWHAA phases are added."""
        blueprint = make_test_blueprint(include_wwhaa=False)
        fixer = BlueprintAutoFixer()

        result = fixer.auto_fix(blueprint)

        # Check that WWHAA phases were added
        for module in result.blueprint.modules:
            for lesson in module.lessons:
                for activity in lesson.activities:
                    assert activity.wwhaa_phase is not None

        # Check that fixes were recorded
        wwhaa_fixes = [f for f in result.fixes_applied if "WWHAA" in f]
        assert len(wwhaa_fixes) > 0

    def test_auto_fix_scales_duration(self):
        """Test that durations are scaled to meet target."""
        # Create blueprint with 12 activities at 10min each = 120min
        blueprint = make_test_blueprint(
            module_count=2,
            lessons_per_module=3,
            activities_per_lesson=2,
            duration_per_activity=10
        )
        fixer = BlueprintAutoFixer()

        # Target is 60min, so should scale down
        result = fixer.auto_fix(blueprint, target_duration=60)

        # Check total duration moved toward target
        new_total = result.blueprint.total_duration_minutes
        assert new_total < 120  # Should have scaled down

        # Check that scaling fix was recorded
        scale_fixes = [f for f in result.fixes_applied if "Scaled" in f]
        assert len(scale_fixes) > 0

    def test_auto_fix_does_not_modify_valid_blueprint(self):
        """Test that valid blueprints aren't unnecessarily modified."""
        blueprint = make_test_blueprint()
        fixer = BlueprintAutoFixer()

        # Validate first
        validator = CourseraValidator()
        initial_validation = validator.validate(blueprint)

        # If already valid and target matches, minimal changes
        result = fixer.auto_fix(blueprint, target_duration=int(blueprint.total_duration_minutes))

        # Should not have scaled
        scale_fixes = [f for f in result.fixes_applied if "Scaled" in f]
        assert len(scale_fixes) == 0

    def test_auto_fix_preserves_blueprint_structure(self):
        """Test that auto-fix preserves module/lesson structure."""
        blueprint = make_test_blueprint(module_count=2, lessons_per_module=3)
        fixer = BlueprintAutoFixer()

        result = fixer.auto_fix(blueprint)

        # Structure should be preserved
        assert len(result.blueprint.modules) == 2
        assert all(len(m.lessons) == 3 for m in result.blueprint.modules)

    def test_auto_fix_respects_duration_bounds(self):
        """Test that scaled durations stay within content type bounds."""
        blueprint = make_test_blueprint(duration_per_activity=30)
        fixer = BlueprintAutoFixer()

        # Extreme scaling target
        result = fixer.auto_fix(blueprint, target_duration=30)

        # Check no activity has negative or zero duration
        for module in result.blueprint.modules:
            for lesson in module.lessons:
                for activity in lesson.activities:
                    assert activity.estimated_duration_minutes >= 3  # Minimum bound


class TestAutoFixConvenienceFunction:
    """Tests for auto_fix_blueprint convenience function."""

    def test_auto_fix_blueprint_function(self):
        """Test the convenience function."""
        blueprint = make_test_blueprint(include_wwhaa=False)

        result = auto_fix_blueprint(blueprint, target_duration=90)

        assert isinstance(result, AutoFixResult)
        assert result.blueprint is not None


class TestRefinementFeedback:
    """Tests for refinement feedback generation."""

    def test_generate_refinement_feedback_with_errors(self):
        """Test feedback generation when errors exist."""
        fixer = BlueprintAutoFixer()

        # Create a mock validation with errors
        from src.validators.course_validator import BlueprintValidation
        validation = BlueprintValidation(
            is_valid=False,
            errors=["Duration 200min exceeds maximum 180min"],
            warnings=["Only 2 Bloom levels used"],
            suggestions=[],
            metrics={}
        )

        feedback = fixer.generate_refinement_feedback(validation)

        assert "CRITICAL ISSUES" in feedback
        assert "Duration 200min" in feedback
        assert "WARNINGS" in feedback
        assert "Bloom levels" in feedback

    def test_generate_refinement_feedback_valid(self):
        """Test feedback generation for valid blueprint."""
        fixer = BlueprintAutoFixer()

        validation = BlueprintValidation(
            is_valid=True,
            errors=[],
            warnings=[],
            suggestions=[],
            metrics={}
        )

        feedback = fixer.generate_refinement_feedback(validation)

        assert feedback == ""


class TestAutoFixIntegration:
    """Integration tests for auto-fix with validation."""

    def test_auto_fix_reduces_validation_issues(self):
        """Test that auto-fix reduces the number of validation issues."""
        # Create a blueprint with issues
        blueprint = make_test_blueprint(
            include_wwhaa=False,  # Missing WWHAA
            duration_per_activity=25  # High duration = 300 total
        )

        validator = CourseraValidator()
        fixer = BlueprintAutoFixer()

        # Initial validation
        initial_validation = validator.validate(blueprint, target_duration=90)
        initial_issues = len(initial_validation.errors) + len(initial_validation.warnings)

        # Auto-fix
        result = fixer.auto_fix(blueprint, target_duration=90)

        # Final validation
        final_validation = validator.validate(result.blueprint, target_duration=90)
        final_issues = len(final_validation.errors) + len(final_validation.warnings)

        # Should have fewer or equal issues after fix
        assert final_issues <= initial_issues

        # Remaining issues should match what auto-fix reports
        assert len(result.remaining_issues) == len(final_validation.errors) + len(final_validation.warnings)
