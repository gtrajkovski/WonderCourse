"""Tests for CourseraValidator and CourseValidator."""
import pytest
from src.validators.course_validator import CourseraValidator, CourseValidator, BlueprintValidation
from src.validators.validation_result import ValidationResult
from src.generators.blueprint_generator import (
    CourseBlueprint,
    ModuleBlueprint,
    LessonBlueprint,
    ActivityBlueprint
)
from src.core.models import Course, Module, Lesson, Activity, ContentType, BloomLevel


def make_blueprint(**overrides):
    """Create a valid CourseBlueprint for testing with optional overrides.

    Default blueprint:
    - 2 modules
    - 3 lessons per module
    - 3 activities per lesson (mixed types)
    - ~90 minutes total duration
    - Good Bloom diversity
    """
    # Default activities with variety
    default_activities = [
        ActivityBlueprint(
            title="Introduction Video",
            content_type="video",
            activity_type="video_lecture",
            wwhaa_phase="hook",
            bloom_level="remember",
            estimated_duration_minutes=5.0,
            description="Intro video"
        ),
        ActivityBlueprint(
            title="Core Concepts Reading",
            content_type="reading",
            activity_type="reading_material",
            wwhaa_phase=None,
            bloom_level="understand",
            estimated_duration_minutes=10.0,
            description="Reading material"
        ),
        ActivityBlueprint(
            title="Practice Quiz",
            content_type="quiz",
            activity_type="practice_quiz",
            wwhaa_phase=None,
            bloom_level="apply",
            estimated_duration_minutes=5.0,
            description="Practice quiz"
        ),
    ]

    # Create default lessons
    default_lessons = [
        LessonBlueprint(
            title=f"Lesson {i+1}",
            description=f"Description for lesson {i+1}",
            activities=default_activities
        )
        for i in range(3)
    ]

    # Create default modules
    default_modules = [
        ModuleBlueprint(
            title=f"Module {i+1}",
            description=f"Description for module {i+1}",
            lessons=default_lessons
        )
        for i in range(2)
    ]

    # Calculate total duration (2 modules * 3 lessons * 3 activities * avg 6.67 min = 120 min)
    # Adjust to 90 min
    default_total_duration = 90.0

    # Create blueprint with defaults
    blueprint_data = {
        "modules": default_modules,
        "total_duration_minutes": default_total_duration,
        "rationale": "Well-balanced course with good content distribution"
    }

    # Apply overrides
    blueprint_data.update(overrides)

    return CourseBlueprint(**blueprint_data)


def test_valid_blueprint_passes():
    """Valid blueprint should pass validation with no errors."""
    validator = CourseraValidator()
    blueprint = make_blueprint()

    result = validator.validate(blueprint)

    assert result.is_valid is True
    assert len(result.errors) == 0
    assert isinstance(result.warnings, list)
    assert isinstance(result.suggestions, list)
    assert isinstance(result.metrics, dict)


def test_too_few_modules_error():
    """Blueprint with 1 module should produce error."""
    validator = CourseraValidator()

    # Create blueprint with only 1 module
    single_module = ModuleBlueprint(
        title="Solo Module",
        description="Only module",
        lessons=[
            LessonBlueprint(
                title="Lesson 1",
                description="Lesson desc",
                activities=[
                    ActivityBlueprint(
                        title="Activity",
                        content_type="video",
                        activity_type="video_lecture",
                        bloom_level="remember",
                        estimated_duration_minutes=45.0,
                        description="Activity desc"
                    ),
                    ActivityBlueprint(
                        title="Activity 2",
                        content_type="reading",
                        activity_type="reading_material",
                        bloom_level="understand",
                        estimated_duration_minutes=45.0,
                        description="Activity desc"
                    )
                ]
            )
        ] * 3
    )

    blueprint = make_blueprint(modules=[single_module])

    result = validator.validate(blueprint)

    assert result.is_valid is False
    assert any("Must have 2-3 modules" in error for error in result.errors)


def test_too_many_modules_error():
    """Blueprint with 4 modules should produce error."""
    validator = CourseraValidator()

    # Create 4 modules
    modules = [
        ModuleBlueprint(
            title=f"Module {i+1}",
            description=f"Module {i+1} desc",
            lessons=[
                LessonBlueprint(
                    title=f"Lesson {j+1}",
                    description=f"Lesson {j+1} desc",
                    activities=[
                        ActivityBlueprint(
                            title=f"Activity {k+1}",
                            content_type="video",
                            activity_type="video_lecture",
                            bloom_level="apply",
                            estimated_duration_minutes=5.0,
                            description="Activity desc"
                        )
                        for k in range(2)
                    ]
                )
                for j in range(3)
            ]
        )
        for i in range(4)
    ]

    blueprint = make_blueprint(modules=modules)

    result = validator.validate(blueprint)

    assert result.is_valid is False
    assert any("Must have 2-3 modules" in error for error in result.errors)


def test_duration_below_minimum_error():
    """Blueprint with total_duration=20 should produce error."""
    validator = CourseraValidator()
    blueprint = make_blueprint(total_duration_minutes=20.0)

    result = validator.validate(blueprint)

    assert result.is_valid is False
    assert any("below minimum 30min" in error for error in result.errors)


def test_duration_above_maximum_error():
    """Blueprint with total_duration=200 should produce error."""
    validator = CourseraValidator()
    blueprint = make_blueprint(total_duration_minutes=200.0)

    result = validator.validate(blueprint)

    assert result.is_valid is False
    assert any("exceeds maximum 180min" in error for error in result.errors)


def test_few_lessons_warning():
    """Module with 2 lessons should produce warning (not error)."""
    validator = CourseraValidator()

    # Create module with only 2 lessons
    module_with_few_lessons = ModuleBlueprint(
        title="Short Module",
        description="Module with few lessons",
        lessons=[
            LessonBlueprint(
                title=f"Lesson {i+1}",
                description=f"Lesson {i+1} desc",
                activities=[
                    ActivityBlueprint(
                        title="Activity",
                        content_type="video",
                        activity_type="video_lecture",
                        bloom_level="remember",
                        estimated_duration_minutes=10.0,
                        description="Activity desc"
                    ),
                    ActivityBlueprint(
                        title="Activity 2",
                        content_type="reading",
                        activity_type="reading_material",
                        bloom_level="understand",
                        estimated_duration_minutes=10.0,
                        description="Activity desc"
                    )
                ]
            )
            for i in range(2)
        ]
    )

    normal_module = ModuleBlueprint(
        title="Normal Module",
        description="Module with normal lessons",
        lessons=[
            LessonBlueprint(
                title=f"Lesson {i+1}",
                description=f"Lesson {i+1} desc",
                activities=[
                    ActivityBlueprint(
                        title="Activity",
                        content_type="video",
                        activity_type="video_lecture",
                        bloom_level="apply",
                        estimated_duration_minutes=15.0,
                        description="Activity desc"
                    ),
                    ActivityBlueprint(
                        title="Activity 2",
                        content_type="quiz",
                        activity_type="practice_quiz",
                        bloom_level="analyze",
                        estimated_duration_minutes=15.0,
                        description="Activity desc"
                    )
                ]
            )
            for i in range(3)
        ]
    )

    blueprint = make_blueprint(modules=[module_with_few_lessons, normal_module])

    result = validator.validate(blueprint)

    # Should be valid but have warning
    assert result.is_valid is True
    assert any("Module 1 has 2 lessons" in warning for warning in result.warnings)


def test_bloom_diversity_warning():
    """All activities with same Bloom level should produce warning."""
    validator = CourseraValidator()

    # Create activities all with same Bloom level
    same_bloom_activities = [
        ActivityBlueprint(
            title=f"Activity {i+1}",
            content_type="video",
            activity_type="video_lecture",
            bloom_level="remember",  # All same
            estimated_duration_minutes=10.0,
            description="Activity desc"
        )
        for i in range(3)
    ]

    lessons = [
        LessonBlueprint(
            title=f"Lesson {i+1}",
            description=f"Lesson {i+1} desc",
            activities=same_bloom_activities
        )
        for i in range(3)
    ]

    modules = [
        ModuleBlueprint(
            title=f"Module {i+1}",
            description=f"Module {i+1} desc",
            lessons=lessons
        )
        for i in range(2)
    ]

    blueprint = make_blueprint(modules=modules)

    result = validator.validate(blueprint)

    assert result.is_valid is True
    assert any("Bloom's taxonomy level(s)" in warning for warning in result.warnings)


def test_metrics_computed():
    """Validate that metrics dict includes all expected keys."""
    validator = CourseraValidator()
    blueprint = make_blueprint()

    result = validator.validate(blueprint)

    assert "total_duration" in result.metrics
    assert "module_count" in result.metrics
    assert "total_activities" in result.metrics
    assert "content_distribution" in result.metrics
    assert "bloom_diversity" in result.metrics
    assert "activities_per_lesson_avg" in result.metrics

    # Check values
    assert result.metrics["module_count"] == 2
    assert result.metrics["total_duration"] == 90.0
    assert result.metrics["total_activities"] == 18  # 2 modules * 3 lessons * 3 activities


def test_video_distribution_warning():
    """Blueprint with 80% video activities should produce warning."""
    validator = CourseraValidator()

    # Create mostly video activities
    video_heavy_activities = [
        ActivityBlueprint(
            title=f"Video {i+1}",
            content_type="video",
            activity_type="video_lecture",
            wwhaa_phase="content",
            bloom_level="remember",
            estimated_duration_minutes=10.0,
            description="Video activity"
        )
        for i in range(3)
    ]

    lessons = [
        LessonBlueprint(
            title=f"Lesson {i+1}",
            description=f"Lesson {i+1} desc",
            activities=video_heavy_activities
        )
        for i in range(3)
    ]

    modules = [
        ModuleBlueprint(
            title=f"Module {i+1}",
            description=f"Module {i+1} desc",
            lessons=lessons
        )
        for i in range(2)
    ]

    blueprint = make_blueprint(modules=modules)

    result = validator.validate(blueprint)

    assert result.is_valid is True
    assert any("Video content" in warning for warning in result.warnings)


def test_validation_with_target_duration():
    """When target_duration provided, validate actual is within 20%."""
    validator = CourseraValidator()

    # Create blueprint with 90 min duration
    blueprint = make_blueprint(total_duration_minutes=90.0)

    # Test within 20% (should pass)
    result = validator.validate(blueprint, target_duration=100)
    assert result.is_valid is True

    # Test outside 20% (should fail)
    result = validator.validate(blueprint, target_duration=150)
    assert result.is_valid is False
    assert any("deviates" in error for error in result.errors)


# ===========================
# Tests for CourseValidator
# ===========================

@pytest.fixture
def validator():
    return CourseValidator()


@pytest.fixture
def minimal_valid_course():
    """Create a minimal course that passes validation."""
    course = Course(title="Test Course", target_duration_minutes=60)
    # 2 modules, 3 lessons each, 2 activities each = 12 activities
    for m_idx in range(2):
        module = Module(title=f"Module {m_idx+1}")
        for l_idx in range(3):
            lesson = Lesson(title=f"Lesson {l_idx+1}")
            for a_idx in range(2):
                # Mix content types and bloom levels
                content_type = ContentType.VIDEO if a_idx == 0 else ContentType.READING
                bloom = [BloomLevel.REMEMBER, BloomLevel.UNDERSTAND, BloomLevel.APPLY][l_idx % 3]
                activity = Activity(
                    title=f"Activity {a_idx+1}",
                    content_type=content_type,
                    bloom_level=bloom,
                    estimated_duration_minutes=5.0
                )
                lesson.activities.append(activity)
            module.lessons.append(lesson)
        course.modules.append(module)
    return course


class TestValidationResult:
    def test_to_dict(self):
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=["warning1"],
            suggestions=["suggestion1"],
            metrics={"count": 5}
        )
        d = result.to_dict()
        assert d["is_valid"] is True
        assert d["warnings"] == ["warning1"]
        assert d["metrics"]["count"] == 5


class TestCourseValidatorModuleCount:
    def test_valid_module_count(self, validator, minimal_valid_course):
        result = validator.validate(minimal_valid_course)
        assert "modules" not in str(result.errors).lower() or result.is_valid

    def test_too_few_modules(self, validator):
        course = Course(title="Test")
        course.modules = [Module(title="Only One")]
        result = validator.validate(course)
        assert not result.is_valid
        assert any("modules" in e.lower() for e in result.errors)

    def test_too_many_modules(self, validator):
        course = Course(title="Test")
        course.modules = [Module(title=f"M{i}") for i in range(5)]
        result = validator.validate(course)
        assert not result.is_valid
        assert any("modules" in e.lower() for e in result.errors)


class TestCourseValidatorDuration:
    def test_duration_below_minimum(self, validator):
        course = Course(title="Test", target_duration_minutes=60)
        course.modules = [Module(title="M1"), Module(title="M2")]
        # No activities = 0 duration
        result = validator.validate(course)
        assert any("duration" in e.lower() and "below" in e.lower() for e in result.errors)

    def test_duration_above_maximum(self, validator):
        course = Course(title="Test", target_duration_minutes=60)
        course.modules = [Module(title="M1"), Module(title="M2")]
        # Add many long activities
        lesson = Lesson(title="L1")
        for i in range(20):
            lesson.activities.append(Activity(
                title=f"A{i}",
                estimated_duration_minutes=15.0  # 20 * 15 = 300 min
            ))
        course.modules[0].lessons.append(lesson)
        result = validator.validate(course)
        assert any("duration" in e.lower() and "exceeds" in e.lower() for e in result.errors)


class TestCourseValidatorWarnings:
    def test_lessons_per_module_warning(self, validator):
        course = Course(title="Test")
        module = Module(title="M1")
        module.lessons = [Lesson(title="L1")]  # Only 1 lesson
        course.modules = [module, Module(title="M2")]
        result = validator.validate(course)
        assert any("lessons" in w.lower() for w in result.warnings)

    def test_activities_per_lesson_warning(self, validator):
        course = Course(title="Test")
        lesson = Lesson(title="L1")
        lesson.activities = [Activity(title="A1", estimated_duration_minutes=30)]  # Only 1 activity
        module = Module(title="M1")
        module.lessons = [lesson]
        course.modules = [module, Module(title="M2")]
        result = validator.validate(course)
        assert any("activities" in w.lower() for w in result.warnings)


class TestCourseValidatorMetrics:
    def test_metrics_include_counts(self, validator, minimal_valid_course):
        result = validator.validate(minimal_valid_course)
        assert "module_count" in result.metrics
        assert "total_lessons" in result.metrics
        assert "total_activities" in result.metrics
        assert result.metrics["module_count"] == 2
        assert result.metrics["total_lessons"] == 6
        assert result.metrics["total_activities"] == 12
