"""Tests for OutcomeValidator.

Tests outcome-activity alignment validation, coverage scoring, and gap detection.
"""

import pytest
from src.validators.outcome_validator import OutcomeValidator
from src.core.models import Course, Module, Lesson, Activity, LearningOutcome, ContentType, ActivityType, BloomLevel


@pytest.fixture
def validator():
    """Create OutcomeValidator instance."""
    return OutcomeValidator()


@pytest.fixture
def sample_course():
    """Create a sample course with modules, lessons, and activities."""
    course = Course(
        id="course_test123",
        title="Test Course",
        description="A test course"
    )

    # Create module with lesson and activities
    module = Module(id="mod_1", title="Module 1", order=0)
    lesson = Lesson(id="les_1", title="Lesson 1", order=0)

    # Add three activities
    activity1 = Activity(id="act_1", title="Activity 1", content_type=ContentType.VIDEO, activity_type=ActivityType.VIDEO_LECTURE)
    activity2 = Activity(id="act_2", title="Activity 2", content_type=ContentType.READING, activity_type=ActivityType.READING_MATERIAL)
    activity3 = Activity(id="act_3", title="Activity 3", content_type=ContentType.QUIZ, activity_type=ActivityType.GRADED_QUIZ)

    lesson.activities = [activity1, activity2, activity3]
    module.lessons = [lesson]
    course.modules = [module]

    return course


def test_course_with_no_outcomes(validator, sample_course):
    """Course with no learning outcomes should be valid with warning."""
    result = validator.validate(sample_course)

    assert result.is_valid is True
    assert "No learning outcomes defined" in result.warnings
    assert result.metrics["coverage_score"] == 0.0
    assert result.metrics["unmapped_outcomes"] == 0
    assert result.metrics["total_outcomes"] == 0
    assert result.metrics["total_activities"] == 3
    assert result.metrics["unmapped_activities"] == 3


def test_outcome_with_no_mapped_activities(validator, sample_course):
    """Outcome with 0 mapped activities should produce error."""
    outcome = LearningOutcome(
        id="lo_1",
        audience="Students",
        behavior="Explain the basics of Python programming",
        condition="Given code examples",
        degree="With 80% accuracy",
        bloom_level=BloomLevel.UNDERSTAND,
        mapped_activity_ids=[]
    )
    sample_course.learning_outcomes = [outcome]

    result = validator.validate(sample_course)

    assert result.is_valid is False
    assert len(result.errors) == 1
    assert "Unmapped outcome: Explain the basics of Python programming" in result.errors[0]
    assert result.metrics["coverage_score"] == 0.0
    assert result.metrics["unmapped_outcomes"] == 1


def test_outcome_with_one_activity(validator, sample_course):
    """Outcome with 1 mapped activity should produce warning (low coverage)."""
    outcome = LearningOutcome(
        id="lo_1",
        audience="Students",
        behavior="Apply Python data structures in programs",
        condition="Given programming tasks",
        degree="Correctly",
        bloom_level=BloomLevel.APPLY,
        mapped_activity_ids=["act_1"]
    )
    sample_course.learning_outcomes = [outcome]

    result = validator.validate(sample_course)

    assert result.is_valid is True
    # Should have low coverage warning (and may have unmapped activity warnings)
    assert any("Low coverage" in w for w in result.warnings)
    low_coverage_warning = [w for w in result.warnings if "Low coverage" in w][0]
    assert "Apply Python data structures in programs" in low_coverage_warning
    assert "only 1 activity" in low_coverage_warning
    assert result.metrics["coverage_score"] == 1.0  # Covered (has 1+ activities)
    assert result.metrics["low_coverage_outcomes"] == 1


def test_outcome_with_two_or_more_activities(validator, sample_course):
    """Outcome with 2+ activities should have no issues."""
    outcome = LearningOutcome(
        id="lo_1",
        audience="Students",
        behavior="Design and implement object-oriented solutions",
        condition="For real-world problems",
        degree="Effectively",
        bloom_level=BloomLevel.CREATE,
        mapped_activity_ids=["act_1", "act_2"]
    )
    sample_course.learning_outcomes = [outcome]

    result = validator.validate(sample_course)

    assert result.is_valid is True
    assert len(result.errors) == 0
    assert not any("Low coverage" in w for w in result.warnings)
    assert result.metrics["coverage_score"] == 1.0
    assert result.metrics["low_coverage_outcomes"] == 0
    assert result.metrics["avg_activities_per_outcome"] == 2.0


def test_unmapped_activities(validator, sample_course):
    """Activities not in any outcome should produce warning."""
    outcome1 = LearningOutcome(
        id="lo_1",
        audience="Students",
        behavior="Test Python code",
        condition="Using pytest",
        degree="Thoroughly",
        bloom_level=BloomLevel.APPLY,
        mapped_activity_ids=["act_1"]
    )
    sample_course.learning_outcomes = [outcome1]

    result = validator.validate(sample_course)

    # act_2 and act_3 are not mapped to any outcome
    assert "2 activity(ies) not mapped to any learning outcome" in result.warnings
    assert result.metrics["unmapped_activities"] == 2


def test_stale_activity_ids_filtered_out(validator, sample_course):
    """Stale activity IDs (deleted activities) should be filtered and not counted."""
    outcome = LearningOutcome(
        id="lo_1",
        audience="Students",
        behavior="Debug Python applications",
        condition="Using debugging tools",
        degree="Efficiently",
        bloom_level=BloomLevel.APPLY,
        mapped_activity_ids=["act_1", "act_deleted", "act_also_deleted"]
    )
    sample_course.learning_outcomes = [outcome]

    result = validator.validate(sample_course)

    # Only act_1 exists, so outcome has low coverage (1 activity)
    assert result.is_valid is True
    assert "Low coverage" in result.warnings[0]
    assert result.metrics["avg_activities_per_outcome"] == 1.0


def test_multiple_outcomes_with_mixed_coverage(validator, sample_course):
    """Multiple outcomes with different coverage levels."""
    outcome1 = LearningOutcome(
        id="lo_1",
        audience="Students",
        behavior="Understand Python syntax",
        condition="In basic programs",
        degree="Completely",
        bloom_level=BloomLevel.UNDERSTAND,
        mapped_activity_ids=[]  # Unmapped
    )
    outcome2 = LearningOutcome(
        id="lo_2",
        audience="Students",
        behavior="Apply Python functions",
        condition="In code",
        degree="Correctly",
        bloom_level=BloomLevel.APPLY,
        mapped_activity_ids=["act_1"]  # Low coverage
    )
    outcome3 = LearningOutcome(
        id="lo_3",
        audience="Students",
        behavior="Create Python applications",
        condition="From scratch",
        degree="Successfully",
        bloom_level=BloomLevel.CREATE,
        mapped_activity_ids=["act_2", "act_3"]  # Good coverage
    )
    sample_course.learning_outcomes = [outcome1, outcome2, outcome3]

    result = validator.validate(sample_course)

    assert result.is_valid is False
    assert len(result.errors) == 1  # outcome1 is unmapped
    assert "Unmapped outcome: Understand Python syntax" in result.errors[0]

    # outcome2 has low coverage
    assert any("Low coverage" in w and "Apply Python functions" in w for w in result.warnings)

    # Metrics
    assert result.metrics["unmapped_outcomes"] == 1
    assert result.metrics["low_coverage_outcomes"] == 1
    assert result.metrics["coverage_score"] == 0.67  # 2 out of 3 covered
    assert result.metrics["total_outcomes"] == 3
    assert result.metrics["avg_activities_per_outcome"] == 1.0  # (0 + 1 + 2) / 3


def test_all_activities_mapped(validator, sample_course):
    """All activities mapped to outcomes should have no unmapped activity warning."""
    outcome1 = LearningOutcome(
        id="lo_1",
        audience="Students",
        behavior="Master Python programming",
        condition="In various contexts",
        degree="Proficiently",
        bloom_level=BloomLevel.APPLY,
        mapped_activity_ids=["act_1", "act_2"]
    )
    outcome2 = LearningOutcome(
        id="lo_2",
        audience="Students",
        behavior="Evaluate code quality",
        condition="Using best practices",
        degree="Critically",
        bloom_level=BloomLevel.EVALUATE,
        mapped_activity_ids=["act_2", "act_3"]
    )
    sample_course.learning_outcomes = [outcome1, outcome2]

    result = validator.validate(sample_course)

    assert result.is_valid is True
    assert result.metrics["unmapped_activities"] == 0
    assert not any("not mapped to any learning outcome" in w for w in result.warnings)


def test_coverage_score_calculation(validator, sample_course):
    """Coverage score should be correctly calculated."""
    # Create 5 outcomes: 2 unmapped, 3 covered
    outcomes = [
        LearningOutcome(id=f"lo_{i}", behavior=f"Outcome {i}", mapped_activity_ids=[])
        for i in range(2)
    ]
    outcomes.extend([
        LearningOutcome(id=f"lo_{i}", behavior=f"Outcome {i}", mapped_activity_ids=["act_1"])
        for i in range(2, 5)
    ])
    sample_course.learning_outcomes = outcomes

    result = validator.validate(sample_course)

    # 3 out of 5 covered = 0.6
    assert result.metrics["coverage_score"] == 0.6
    assert result.metrics["unmapped_outcomes"] == 2


def test_long_behavior_text_truncated_in_messages(validator, sample_course):
    """Long behavior text should be truncated in error/warning messages."""
    long_behavior = "A" * 100  # 100 characters
    outcome = LearningOutcome(
        id="lo_1",
        audience="Students",
        behavior=long_behavior,
        condition="In all cases",
        degree="Perfectly",
        bloom_level=BloomLevel.APPLY,
        mapped_activity_ids=[]
    )
    sample_course.learning_outcomes = [outcome]

    result = validator.validate(sample_course)

    # Error message should contain truncated behavior (50 chars + "...")
    assert result.errors[0].startswith("Unmapped outcome: " + "A" * 50 + "...")


def test_metrics_completeness(validator, sample_course):
    """All required metrics should be present."""
    outcome = LearningOutcome(
        id="lo_1",
        behavior="Sample outcome",
        mapped_activity_ids=["act_1", "act_2"]
    )
    sample_course.learning_outcomes = [outcome]

    result = validator.validate(sample_course)

    # Check all required metrics are present
    assert "coverage_score" in result.metrics
    assert "unmapped_outcomes" in result.metrics
    assert "low_coverage_outcomes" in result.metrics
    assert "unmapped_activities" in result.metrics
    assert "avg_activities_per_outcome" in result.metrics
    assert "total_outcomes" in result.metrics
    assert "total_activities" in result.metrics
