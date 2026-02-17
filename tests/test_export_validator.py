"""Tests for ExportValidator content completeness checking."""

import pytest
from src.exporters.export_validator import ExportValidator, ExportValidationResult
from src.core.models import Course, Module, Lesson, Activity, ContentType, BuildState


@pytest.fixture
def validator():
    """Create ExportValidator instance."""
    return ExportValidator()


@pytest.fixture
def complete_course():
    """Create a fully complete course ready for export."""
    course = Course(
        id="course_test",
        title="Complete Course",
        description="A course with all content approved",
    )
    module = Module(id="mod_1", title="Module 1")
    lesson = Lesson(id="les_1", title="Lesson 1")
    activity = Activity(
        id="act_1",
        title="Video 1",
        content_type=ContentType.VIDEO,
        content='{"hook": "Welcome!", "objective": "Learn X", "content": "Main content here", "ivq": "Question?", "summary": "We learned X", "cta": "Next up"}',
        build_state=BuildState.APPROVED,
    )
    lesson.activities.append(activity)
    module.lessons.append(lesson)
    course.modules.append(module)
    return course


@pytest.fixture
def incomplete_course():
    """Create a course with missing content."""
    course = Course(
        id="course_incomplete",
        title="Incomplete Course",
    )
    module = Module(id="mod_1", title="Module 1")
    lesson = Lesson(id="les_1", title="Lesson 1")

    # Activity with content
    activity1 = Activity(
        id="act_1",
        title="Video 1",
        content_type=ContentType.VIDEO,
        content='{"hook": "Hello"}',
        build_state=BuildState.APPROVED,
    )

    # Activity without content
    activity2 = Activity(
        id="act_2",
        title="Reading 1",
        content_type=ContentType.READING,
        content="",
        build_state=BuildState.DRAFT,
    )

    lesson.activities.extend([activity1, activity2])
    module.lessons.append(lesson)
    course.modules.append(module)
    return course


class TestExportValidator:
    """Tests for ExportValidator class."""

    def test_validate_complete_course_is_exportable(self, validator, complete_course):
        """Complete course with approved content should be exportable."""
        result = validator.validate_for_export(complete_course)

        assert result.is_exportable is True
        assert len(result.missing_content) == 0
        assert len(result.incomplete_activities) == 0
        assert result.metrics["total_activities"] == 1
        assert result.metrics["content_completion_rate"] == 1.0
        assert result.metrics["approval_rate"] == 1.0

    def test_validate_missing_content(self, validator, incomplete_course):
        """Course with missing content should not be exportable."""
        result = validator.validate_for_export(incomplete_course)

        assert result.is_exportable is False
        assert len(result.missing_content) == 1
        assert result.missing_content[0]["activity_id"] == "act_2"
        assert result.missing_content[0]["title"] == "Reading 1"

    def test_validate_unapproved_activities(self, validator, incomplete_course):
        """Course with unapproved activities should not be exportable."""
        result = validator.validate_for_export(incomplete_course)

        assert result.is_exportable is False
        # act_2 is in DRAFT state
        assert len(result.incomplete_activities) == 1
        assert result.incomplete_activities[0]["current_state"] == "draft"

    def test_validate_without_require_approved(self, validator):
        """When require_approved=False, generated content is accepted."""
        course = Course(id="course_test", title="Test")
        module = Module(id="mod_1", title="Module 1")
        lesson = Lesson(id="les_1", title="Lesson 1")
        activity = Activity(
            id="act_1",
            title="Video 1",
            content_type=ContentType.VIDEO,
            content='{"some": "content"}',
            build_state=BuildState.GENERATED,  # Not approved
        )
        lesson.activities.append(activity)
        module.lessons.append(lesson)
        course.modules.append(module)

        result = validator.validate_for_export(course, require_approved=False)

        assert result.is_exportable is True
        assert len(result.incomplete_activities) == 0

    def test_validate_empty_course(self, validator):
        """Empty course should not be exportable."""
        course = Course(id="course_empty", title="Empty Course")

        result = validator.validate_for_export(course)

        assert result.is_exportable is False
        assert result.metrics["total_activities"] == 0
        assert "Course has no modules" in result.warnings

    def test_validate_empty_module_warning(self, validator):
        """Module without lessons should produce warning."""
        course = Course(id="course_test", title="Test")
        module = Module(id="mod_1", title="Empty Module")
        course.modules.append(module)

        result = validator.validate_for_export(course)

        assert result.is_exportable is False
        assert any("Empty Module" in w and "no lessons" in w for w in result.warnings)

    def test_get_missing_content(self, validator, incomplete_course):
        """get_missing_content returns list of activities without content."""
        missing = validator.get_missing_content(incomplete_course)

        assert len(missing) == 1
        assert missing[0]["activity_id"] == "act_2"
        assert missing[0]["content_type"] == "reading"
        assert missing[0]["module"] == "Module 1"
        assert missing[0]["lesson"] == "Lesson 1"

    def test_get_export_readiness(self, validator, incomplete_course):
        """get_export_readiness returns summary dict."""
        readiness = validator.get_export_readiness(incomplete_course)

        assert readiness["is_exportable"] is False
        assert readiness["total_activities"] == 2
        assert readiness["content_complete"] is False
        assert readiness["all_approved"] is False
        assert readiness["missing_count"] == 1
        assert readiness["unapproved_count"] == 1

    def test_export_validation_result_to_dict(self, validator, complete_course):
        """ExportValidationResult should serialize to dict."""
        result = validator.validate_for_export(complete_course)
        d = result.to_dict()

        assert isinstance(d, dict)
        assert "is_exportable" in d
        assert "missing_content" in d
        assert "incomplete_activities" in d
        assert "warnings" in d
        assert "metrics" in d

    def test_whitespace_content_treated_as_missing(self, validator):
        """Content that is only whitespace should be treated as missing."""
        course = Course(id="course_test", title="Test")
        module = Module(id="mod_1", title="Module 1")
        lesson = Lesson(id="les_1", title="Lesson 1")
        activity = Activity(
            id="act_1",
            title="Video 1",
            content_type=ContentType.VIDEO,
            content="   \n\t  ",  # Only whitespace
            build_state=BuildState.APPROVED,
        )
        lesson.activities.append(activity)
        module.lessons.append(lesson)
        course.modules.append(module)

        result = validator.validate_for_export(course)

        assert result.is_exportable is False
        assert len(result.missing_content) == 1

    def test_published_state_is_exportable(self, validator):
        """PUBLISHED state should be exportable."""
        course = Course(id="course_test", title="Test")
        module = Module(id="mod_1", title="Module 1")
        lesson = Lesson(id="les_1", title="Lesson 1")
        activity = Activity(
            id="act_1",
            title="Video 1",
            content_type=ContentType.VIDEO,
            content='{"content": "data"}',
            build_state=BuildState.PUBLISHED,
        )
        lesson.activities.append(activity)
        module.lessons.append(lesson)
        course.modules.append(module)

        result = validator.validate_for_export(course)

        assert result.is_exportable is True
        assert result.metrics["approved_activities"] == 1
