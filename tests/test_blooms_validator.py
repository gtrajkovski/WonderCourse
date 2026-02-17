"""Tests for BloomsValidator."""
import pytest
from src.validators.blooms_validator import BloomsValidator
from src.validators.validation_result import ValidationResult
from src.core.models import Course, Module, Lesson, Activity, BloomLevel, ContentType


def make_course_with_blooms(bloom_levels):
    """Create a course with activities at specified Bloom's levels.

    Args:
        bloom_levels: List of BloomLevel enums (or None for activities without bloom_level)

    Returns:
        Course with one module, one lesson, activities with specified levels
    """
    activities = []
    for i, level in enumerate(bloom_levels):
        activity = Activity(
            id=f"act_{i}",
            title=f"Activity {i+1}",
            content_type=ContentType.VIDEO,
            bloom_level=level
        )
        activities.append(activity)

    lesson = Lesson(
        id="les_1",
        title="Test Lesson",
        activities=activities
    )

    module = Module(
        id="mod_1",
        title="Test Module",
        lessons=[lesson]
    )

    course = Course(
        id="course_1",
        title="Test Course",
        modules=[module]
    )

    return course


def test_no_activities():
    """Course with no activities should be valid with suggestion."""
    course = Course(id="c1", title="Empty Course", modules=[])
    validator = BloomsValidator()

    result = validator.validate(course)

    assert result.is_valid is True
    assert len(result.errors) == 0
    assert len(result.warnings) == 0
    assert len(result.suggestions) == 1
    assert "Add activities" in result.suggestions[0]
    assert result.metrics["unique_levels"] == 0
    assert result.metrics["total_activities"] == 0
    assert result.metrics["distribution"] == {}
    assert result.metrics["dominant_level"] is None


def test_activities_without_bloom_level():
    """Activities with bloom_level=None should be excluded from analysis."""
    course = make_course_with_blooms([None, None, None])
    validator = BloomsValidator()

    result = validator.validate(course)

    assert result.is_valid is True
    assert len(result.errors) == 0
    assert result.metrics["total_activities"] == 0
    assert "Add activities" in result.suggestions[0]


def test_only_one_unique_level_error():
    """Only 1 unique Bloom's level should produce an error."""
    # All activities at REMEMBER level
    course = make_course_with_blooms([
        BloomLevel.REMEMBER,
        BloomLevel.REMEMBER,
        BloomLevel.REMEMBER
    ])
    validator = BloomsValidator()

    result = validator.validate(course)

    assert result.is_valid is False
    assert len(result.errors) == 1
    assert "Only 1 Bloom's level" in result.errors[0]
    assert "minimum 2" in result.errors[0]
    assert result.metrics["unique_levels"] == 1
    assert result.metrics["total_activities"] == 3


def test_imbalanced_distribution_warning():
    """More than 80% single level should produce a warning."""
    # 5 APPLY, 1 REMEMBER = 83% APPLY
    course = make_course_with_blooms([
        BloomLevel.APPLY,
        BloomLevel.APPLY,
        BloomLevel.APPLY,
        BloomLevel.APPLY,
        BloomLevel.APPLY,
        BloomLevel.REMEMBER
    ])
    validator = BloomsValidator()

    result = validator.validate(course)

    assert result.is_valid is True  # Warning, not error
    assert len(result.errors) == 0
    assert len(result.warnings) == 1
    assert "imbalanced" in result.warnings[0]
    assert "83%" in result.warnings[0] or "5/6" in result.warnings[0]
    assert result.metrics["unique_levels"] == 2
    assert result.metrics["dominant_level"] == "apply"


def test_no_higher_order_thinking_suggestion():
    """No higher-order levels (ANALYZE, EVALUATE, CREATE) should produce suggestion."""
    # Only lower-order levels
    course = make_course_with_blooms([
        BloomLevel.REMEMBER,
        BloomLevel.UNDERSTAND,
        BloomLevel.APPLY
    ])
    validator = BloomsValidator()

    result = validator.validate(course)

    assert result.is_valid is True
    assert len(result.errors) == 0
    assert len(result.suggestions) >= 1
    # Find the higher-order suggestion
    higher_order_suggestions = [s for s in result.suggestions if "higher-order" in s.lower()]
    assert len(higher_order_suggestions) == 1
    assert "Analyze" in higher_order_suggestions[0] or "ANALYZE" in higher_order_suggestions[0]


def test_good_distribution_no_issues():
    """3+ unique levels with balance should have no errors or warnings."""
    # Good mix: REMEMBER, APPLY, ANALYZE, EVALUATE
    course = make_course_with_blooms([
        BloomLevel.REMEMBER,
        BloomLevel.APPLY,
        BloomLevel.APPLY,
        BloomLevel.ANALYZE,
        BloomLevel.EVALUATE
    ])
    validator = BloomsValidator()

    result = validator.validate(course)

    assert result.is_valid is True
    assert len(result.errors) == 0
    assert len(result.warnings) == 0
    # Might have suggestions, but not required
    assert result.metrics["unique_levels"] == 4
    assert result.metrics["total_activities"] == 5


def test_distribution_percentages():
    """Distribution should show percentages for each level."""
    # 3 APPLY, 2 REMEMBER, 1 ANALYZE
    course = make_course_with_blooms([
        BloomLevel.APPLY,
        BloomLevel.APPLY,
        BloomLevel.APPLY,
        BloomLevel.REMEMBER,
        BloomLevel.REMEMBER,
        BloomLevel.ANALYZE
    ])
    validator = BloomsValidator()

    result = validator.validate(course)

    distribution = result.metrics["distribution"]
    assert distribution["apply"] == 0.5  # 3/6
    assert distribution["remember"] == pytest.approx(0.33, abs=0.01)  # 2/6
    assert distribution["analyze"] == pytest.approx(0.17, abs=0.01)  # 1/6


def test_multiple_modules_and_lessons():
    """Should flatten activities from all modules and lessons."""
    # Create 2 modules with 2 lessons each
    activities_m1_l1 = [
        Activity(id="a1", title="A1", bloom_level=BloomLevel.REMEMBER),
        Activity(id="a2", title="A2", bloom_level=BloomLevel.APPLY)
    ]
    activities_m1_l2 = [
        Activity(id="a3", title="A3", bloom_level=BloomLevel.ANALYZE)
    ]
    activities_m2_l1 = [
        Activity(id="a4", title="A4", bloom_level=BloomLevel.EVALUATE)
    ]
    activities_m2_l2 = [
        Activity(id="a5", title="A5", bloom_level=BloomLevel.CREATE)
    ]

    lesson_m1_l1 = Lesson(id="l1", title="L1", activities=activities_m1_l1)
    lesson_m1_l2 = Lesson(id="l2", title="L2", activities=activities_m1_l2)
    lesson_m2_l1 = Lesson(id="l3", title="L3", activities=activities_m2_l1)
    lesson_m2_l2 = Lesson(id="l4", title="L4", activities=activities_m2_l2)

    module1 = Module(id="m1", title="M1", lessons=[lesson_m1_l1, lesson_m1_l2])
    module2 = Module(id="m2", title="M2", lessons=[lesson_m2_l1, lesson_m2_l2])

    course = Course(id="c1", title="Course", modules=[module1, module2])

    validator = BloomsValidator()
    result = validator.validate(course)

    assert result.metrics["total_activities"] == 5
    assert result.metrics["unique_levels"] == 5
