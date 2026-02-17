"""Tests for core data models with round-trip serialization."""

import pytest
from datetime import datetime
from src.core.models import (
    ContentType,
    ActivityType,
    BuildState,
    BloomLevel,
    WWHAAPhase,
    Activity,
    Lesson,
    Module,
    LearningOutcome,
    TextbookChapter,
    Course,
)


class TestEnums:
    """Test enum definitions and values."""

    def test_content_type_enum_values(self):
        """All 10 ContentType values exist."""
        assert ContentType.VIDEO.value == "video"
        assert ContentType.READING.value == "reading"
        assert ContentType.QUIZ.value == "quiz"
        assert ContentType.HOL.value == "hol"
        assert ContentType.COACH.value == "coach"
        assert ContentType.LAB.value == "lab"
        assert ContentType.DISCUSSION.value == "discussion"
        assert ContentType.ASSIGNMENT.value == "assignment"
        assert ContentType.PROJECT.value == "project"
        assert ContentType.RUBRIC.value == "rubric"

    def test_activity_type_enum_values(self):
        """All 11 ActivityType values exist."""
        assert ActivityType.GRADED_QUIZ.value == "graded_quiz"
        assert ActivityType.PRACTICE_QUIZ.value == "practice_quiz"
        assert ActivityType.UNGRADED_LAB.value == "ungraded_lab"
        assert ActivityType.PEER_REVIEW.value == "peer_review"
        assert ActivityType.DISCUSSION_PROMPT.value == "discussion_prompt"
        assert ActivityType.HANDS_ON_LAB.value == "hands_on_lab"
        assert ActivityType.COACH_DIALOGUE.value == "coach_dialogue"
        assert ActivityType.VIDEO_LECTURE.value == "video_lecture"
        assert ActivityType.READING_MATERIAL.value == "reading_material"
        assert ActivityType.ASSIGNMENT_SUBMISSION.value == "assignment_submission"
        assert ActivityType.PROJECT_MILESTONE.value == "project_milestone"

    def test_build_state_enum_values(self):
        """All 6 BuildState values exist."""
        assert BuildState.DRAFT.value == "draft"
        assert BuildState.GENERATING.value == "generating"
        assert BuildState.GENERATED.value == "generated"
        assert BuildState.REVIEWED.value == "reviewed"
        assert BuildState.APPROVED.value == "approved"
        assert BuildState.PUBLISHED.value == "published"

    def test_bloom_level_enum_values(self):
        """All 6 BloomLevel values exist."""
        assert BloomLevel.REMEMBER.value == "remember"
        assert BloomLevel.UNDERSTAND.value == "understand"
        assert BloomLevel.APPLY.value == "apply"
        assert BloomLevel.ANALYZE.value == "analyze"
        assert BloomLevel.EVALUATE.value == "evaluate"
        assert BloomLevel.CREATE.value == "create"

    def test_wwhaa_phase_enum_values(self):
        """All 6 WWHAAPhase values exist."""
        assert WWHAAPhase.HOOK.value == "hook"
        assert WWHAAPhase.OBJECTIVE.value == "objective"
        assert WWHAAPhase.CONTENT.value == "content"
        assert WWHAAPhase.IVQ.value == "ivq"
        assert WWHAAPhase.SUMMARY.value == "summary"
        assert WWHAAPhase.CTA.value == "cta"


class TestActivity:
    """Test Activity dataclass serialization."""

    def test_activity_default_creation(self):
        """Activity can be created with defaults."""
        activity = Activity()
        assert activity.id.startswith("act_")
        assert len(activity.id) == 12  # "act_" + 8 hex chars
        assert activity.title == ""
        assert activity.content_type == ContentType.VIDEO
        assert activity.activity_type == ActivityType.VIDEO_LECTURE
        assert activity.wwhaa_phase == WWHAAPhase.CONTENT
        assert activity.build_state == BuildState.DRAFT
        assert activity.word_count == 0
        assert activity.estimated_duration_minutes == 0.0
        assert activity.bloom_level is None
        assert activity.order == 0
        assert isinstance(activity.metadata, dict)
        assert activity.created_at
        assert activity.updated_at

    def test_activity_round_trip(self):
        """Activity round-trips through to_dict/from_dict without data loss."""
        original = Activity(
            id="act_12345678",
            title="Test Activity",
            content_type=ContentType.QUIZ,
            activity_type=ActivityType.GRADED_QUIZ,
            wwhaa_phase=WWHAAPhase.IVQ,
            content="Test content",
            build_state=BuildState.APPROVED,
            word_count=100,
            estimated_duration_minutes=5.5,
            bloom_level=BloomLevel.APPLY,
            order=3,
            metadata={"key": "value"},
            created_at="2026-01-01T12:00:00",
            updated_at="2026-01-02T12:00:00",
        )

        data = original.to_dict()
        restored = Activity.from_dict(data)

        assert restored.id == original.id
        assert restored.title == original.title
        assert restored.content_type == original.content_type
        assert restored.activity_type == original.activity_type
        assert restored.wwhaa_phase == original.wwhaa_phase
        assert restored.content == original.content
        assert restored.build_state == original.build_state
        assert restored.word_count == original.word_count
        assert restored.estimated_duration_minutes == original.estimated_duration_minutes
        assert restored.bloom_level == original.bloom_level
        assert restored.order == original.order
        assert restored.metadata == original.metadata
        assert restored.created_at == original.created_at
        assert restored.updated_at == original.updated_at


class TestLesson:
    """Test Lesson dataclass serialization."""

    def test_lesson_default_creation(self):
        """Lesson can be created with defaults."""
        lesson = Lesson()
        assert lesson.id.startswith("les_")
        assert len(lesson.id) == 12  # "les_" + 8 hex chars
        assert lesson.title == ""
        assert lesson.description == ""
        assert isinstance(lesson.activities, list)
        assert len(lesson.activities) == 0
        assert lesson.order == 0

    def test_lesson_round_trip(self):
        """Lesson with nested activities round-trips correctly."""
        activity1 = Activity(id="act_11111111", title="Activity 1")
        activity2 = Activity(id="act_22222222", title="Activity 2")

        original = Lesson(
            id="les_12345678",
            title="Test Lesson",
            description="Test description",
            activities=[activity1, activity2],
            order=1,
            created_at="2026-01-01T12:00:00",
            updated_at="2026-01-02T12:00:00",
        )

        data = original.to_dict()
        restored = Lesson.from_dict(data)

        assert restored.id == original.id
        assert restored.title == original.title
        assert restored.description == original.description
        assert len(restored.activities) == 2
        assert restored.activities[0].id == "act_11111111"
        assert restored.activities[1].id == "act_22222222"
        assert restored.order == original.order


class TestModule:
    """Test Module dataclass serialization."""

    def test_module_default_creation(self):
        """Module can be created with defaults."""
        module = Module()
        assert module.id.startswith("mod_")
        assert len(module.id) == 12  # "mod_" + 8 hex chars
        assert module.title == ""
        assert module.description == ""
        assert isinstance(module.lessons, list)
        assert len(module.lessons) == 0
        assert module.order == 0

    def test_module_round_trip(self):
        """Module with nested lessons and activities round-trips correctly."""
        activity1 = Activity(id="act_11111111", title="Activity 1")
        activity2 = Activity(id="act_22222222", title="Activity 2")
        lesson1 = Lesson(id="les_11111111", title="Lesson 1", activities=[activity1])
        lesson2 = Lesson(id="les_22222222", title="Lesson 2", activities=[activity2])

        original = Module(
            id="mod_12345678",
            title="Test Module",
            description="Test description",
            lessons=[lesson1, lesson2],
            order=2,
            created_at="2026-01-01T12:00:00",
            updated_at="2026-01-02T12:00:00",
        )

        data = original.to_dict()
        restored = Module.from_dict(data)

        assert restored.id == original.id
        assert restored.title == original.title
        assert restored.description == original.description
        assert len(restored.lessons) == 2
        assert restored.lessons[0].id == "les_11111111"
        assert restored.lessons[1].id == "les_22222222"
        assert len(restored.lessons[0].activities) == 1
        assert len(restored.lessons[1].activities) == 1
        assert restored.order == original.order


class TestLearningOutcome:
    """Test LearningOutcome dataclass serialization."""

    def test_learning_outcome_default_creation(self):
        """LearningOutcome can be created with defaults."""
        lo = LearningOutcome()
        assert lo.id.startswith("lo_")
        assert len(lo.id) == 11  # "lo_" + 8 hex chars
        assert lo.audience == ""
        assert lo.behavior == ""
        assert lo.condition == ""
        assert lo.degree == ""
        assert lo.bloom_level == BloomLevel.APPLY
        assert isinstance(lo.tags, list)
        assert isinstance(lo.mapped_activity_ids, list)

    def test_learning_outcome_round_trip(self):
        """LearningOutcome with bloom_level and tags round-trips correctly."""
        original = LearningOutcome(
            id="lo_12345678",
            audience="data analysts",
            behavior="implement a decision tree classifier",
            condition="given a labeled dataset",
            degree="with 80%+ accuracy",
            bloom_level=BloomLevel.CREATE,
            tags=["machine-learning", "classification"],
            mapped_activity_ids=["act_11111111", "act_22222222"],
        )

        data = original.to_dict()
        restored = LearningOutcome.from_dict(data)

        assert restored.id == original.id
        assert restored.audience == original.audience
        assert restored.behavior == original.behavior
        assert restored.condition == original.condition
        assert restored.degree == original.degree
        assert restored.bloom_level == original.bloom_level
        assert restored.tags == original.tags
        assert restored.mapped_activity_ids == original.mapped_activity_ids


class TestTextbookChapter:
    """Test TextbookChapter dataclass serialization."""

    def test_textbook_chapter_default_creation(self):
        """TextbookChapter can be created with defaults."""
        chapter = TextbookChapter()
        assert chapter.id.startswith("ch_")
        assert len(chapter.id) == 11  # "ch_" + 8 hex chars
        assert chapter.title == ""
        assert isinstance(chapter.sections, list)
        assert isinstance(chapter.glossary_terms, list)
        assert chapter.word_count == 0
        assert chapter.learning_outcome_id is None

    def test_textbook_chapter_round_trip(self):
        """TextbookChapter with sections and glossary round-trips correctly."""
        original = TextbookChapter(
            id="ch_12345678",
            title="Test Chapter",
            sections=[
                {"heading": "Introduction", "body": "This is the intro."},
                {"heading": "Conclusion", "body": "This is the conclusion."},
            ],
            glossary_terms=[
                {"term": "API", "definition": "Application Programming Interface"},
                {"term": "REST", "definition": "Representational State Transfer"},
            ],
            word_count=500,
            learning_outcome_id="lo_11111111",
            created_at="2026-01-01T12:00:00",
            updated_at="2026-01-02T12:00:00",
        )

        data = original.to_dict()
        restored = TextbookChapter.from_dict(data)

        assert restored.id == original.id
        assert restored.title == original.title
        assert len(restored.sections) == 2
        assert restored.sections[0]["heading"] == "Introduction"
        assert len(restored.glossary_terms) == 2
        assert restored.glossary_terms[0]["term"] == "API"
        assert restored.word_count == original.word_count
        assert restored.learning_outcome_id == original.learning_outcome_id


class TestCourse:
    """Test Course dataclass serialization."""

    def test_course_default_creation(self):
        """Course can be created with defaults."""
        course = Course()
        assert course.id.startswith("course_")
        assert len(course.id) == 19  # "course_" + 12 hex chars
        assert course.title == "Untitled Course"
        assert course.description == ""
        assert course.audience_level == "intermediate"
        assert course.target_duration_minutes == 60
        assert course.modality == "online"
        assert isinstance(course.modules, list)
        assert isinstance(course.learning_outcomes, list)
        assert isinstance(course.textbook_chapters, list)
        assert course.schema_version == 1

    def test_course_round_trip(self):
        """Full Course with all nested objects round-trips correctly."""
        # Build nested structure
        activity = Activity(id="act_11111111", title="Test Activity")
        lesson = Lesson(id="les_11111111", title="Test Lesson", activities=[activity])
        module = Module(id="mod_11111111", title="Test Module", lessons=[lesson])
        learning_outcome = LearningOutcome(
            id="lo_11111111",
            audience="developers",
            behavior="write unit tests",
            bloom_level=BloomLevel.APPLY,
        )
        textbook_chapter = TextbookChapter(
            id="ch_11111111",
            title="Chapter 1",
            sections=[{"heading": "Intro", "body": "Content"}],
        )

        original = Course(
            id="course_123456789012",
            title="Test Course",
            description="A test course",
            audience_level="beginner",
            target_duration_minutes=120,
            modality="blended",
            modules=[module],
            learning_outcomes=[learning_outcome],
            textbook_chapters=[textbook_chapter],
            schema_version=1,
            created_at="2026-01-01T12:00:00",
            updated_at="2026-01-02T12:00:00",
        )

        data = original.to_dict()
        restored = Course.from_dict(data)

        assert restored.id == original.id
        assert restored.title == original.title
        assert restored.description == original.description
        assert restored.audience_level == original.audience_level
        assert restored.target_duration_minutes == original.target_duration_minutes
        assert restored.modality == original.modality
        assert len(restored.modules) == 1
        assert len(restored.learning_outcomes) == 1
        assert len(restored.textbook_chapters) == 1
        assert restored.modules[0].id == "mod_11111111"
        assert len(restored.modules[0].lessons) == 1
        assert len(restored.modules[0].lessons[0].activities) == 1
        assert restored.learning_outcomes[0].bloom_level == BloomLevel.APPLY
        assert restored.schema_version == original.schema_version


class TestSchemaEvolution:
    """Test schema evolution and deserialization edge cases."""

    def test_from_dict_ignores_unknown_fields(self):
        """from_dict ignores unknown fields for schema evolution."""
        data = {
            "id": "act_12345678",
            "title": "Test",
            "unknown_field": "should be ignored",
            "another_unknown": 123,
        }

        activity = Activity.from_dict(data)
        assert activity.id == "act_12345678"
        assert activity.title == "Test"
        # Unknown fields silently ignored - no error

    def test_from_dict_handles_missing_optional(self):
        """from_dict works with partial data for optional fields."""
        minimal_data = {
            "id": "act_12345678",
            "title": "Minimal Activity",
        }

        activity = Activity.from_dict(minimal_data)
        assert activity.id == "act_12345678"
        assert activity.title == "Minimal Activity"
        assert activity.content_type == ContentType.VIDEO  # default
        assert activity.bloom_level is None  # optional, not in data

    def test_enum_string_deserialization(self):
        """Enums deserialize from string values correctly."""
        data = {
            "id": "act_12345678",
            "title": "Test",
            "build_state": "approved",  # string, not enum
            "content_type": "quiz",
            "activity_type": "graded_quiz",
            "wwhaa_phase": "ivq",
        }

        activity = Activity.from_dict(data)
        assert activity.build_state == BuildState.APPROVED
        assert activity.content_type == ContentType.QUIZ
        assert activity.activity_type == ActivityType.GRADED_QUIZ
        assert activity.wwhaa_phase == WWHAAPhase.IVQ

    def test_enum_invalid_value_fallback(self):
        """Invalid enum values fall back to first enum value."""
        data = {
            "id": "act_12345678",
            "title": "Test",
            "build_state": "invalid_state",  # not a valid BuildState
        }

        activity = Activity.from_dict(data)
        assert activity.build_state == BuildState.DRAFT  # fallback to first value


class TestDefaultIDGeneration:
    """Test ID generation patterns."""

    def test_activity_id_pattern(self):
        """Activity IDs use act_ prefix with 8 hex chars."""
        activity = Activity()
        assert activity.id.startswith("act_")
        assert len(activity.id) == 12
        assert all(c in "0123456789abcdef" for c in activity.id[4:])

    def test_lesson_id_pattern(self):
        """Lesson IDs use les_ prefix with 8 hex chars."""
        lesson = Lesson()
        assert lesson.id.startswith("les_")
        assert len(lesson.id) == 12

    def test_module_id_pattern(self):
        """Module IDs use mod_ prefix with 8 hex chars."""
        module = Module()
        assert module.id.startswith("mod_")
        assert len(module.id) == 12

    def test_learning_outcome_id_pattern(self):
        """LearningOutcome IDs use lo_ prefix with 8 hex chars."""
        lo = LearningOutcome()
        assert lo.id.startswith("lo_")
        assert len(lo.id) == 11

    def test_textbook_chapter_id_pattern(self):
        """TextbookChapter IDs use ch_ prefix with 8 hex chars."""
        chapter = TextbookChapter()
        assert chapter.id.startswith("ch_")
        assert len(chapter.id) == 11

    def test_course_id_pattern(self):
        """Course IDs use course_ prefix with 12 hex chars."""
        course = Course()
        assert course.id.startswith("course_")
        assert len(course.id) == 19


class TestTimestamps:
    """Test timestamp generation."""

    def test_default_timestamps_iso_format(self):
        """created_at and updated_at are ISO format timestamps."""
        activity = Activity()

        # Verify ISO format by parsing
        datetime.fromisoformat(activity.created_at)
        datetime.fromisoformat(activity.updated_at)

        # Both should be recent (within last minute)
        created = datetime.fromisoformat(activity.created_at)
        now = datetime.now()
        assert (now - created).total_seconds() < 60


class TestCourseExtendedFields:
    """Test Course extended metadata fields (prerequisites, tools, grading_policy)."""

    def test_course_with_new_fields_serializes(self):
        """Course with prerequisites, tools, grading_policy serializes correctly."""
        course = Course(
            title="Advanced Python",
            prerequisites="Basic Python knowledge and object-oriented programming",
            tools=["Python 3.9+", "VS Code", "Git"],
            grading_policy="70% assignments, 20% quizzes, 10% participation"
        )

        data = course.to_dict()
        assert data['prerequisites'] == "Basic Python knowledge and object-oriented programming"
        assert data['tools'] == ["Python 3.9+", "VS Code", "Git"]
        assert data['grading_policy'] == "70% assignments, 20% quizzes, 10% participation"

    def test_course_new_fields_round_trip(self):
        """Course with new fields round-trips through to_dict/from_dict."""
        original = Course(
            id="course_123456789012",
            title="Machine Learning Fundamentals",
            prerequisites="Linear algebra, Python programming, basic statistics",
            tools=["Python 3.9+", "Jupyter Notebook", "scikit-learn", "pandas"],
            grading_policy="50% projects, 30% quizzes, 20% final exam"
        )

        data = original.to_dict()
        restored = Course.from_dict(data)

        assert restored.prerequisites == original.prerequisites
        assert restored.tools == original.tools
        assert restored.grading_policy == original.grading_policy

    def test_course_from_dict_missing_new_fields(self):
        """Course from_dict with missing new fields defaults correctly (backward compat)."""
        # Old course JSON without new fields
        data = {
            "id": "course_123456789012",
            "title": "Old Course",
            "description": "Created before new fields",
            "audience_level": "intermediate",
            "target_duration_minutes": 60,
            "modality": "online"
        }

        course = Course.from_dict(data)
        assert course.id == "course_123456789012"
        assert course.title == "Old Course"
        # New fields should default correctly
        assert course.prerequisites is None
        assert course.tools == []
        assert course.grading_policy is None

    def test_course_tools_list_multiple_items(self):
        """Course with multiple tools in list serializes and deserializes correctly."""
        original = Course(
            title="Full Stack Development",
            tools=["Node.js", "React", "PostgreSQL", "Docker", "AWS", "Git"]
        )

        data = original.to_dict()
        restored = Course.from_dict(data)

        assert len(restored.tools) == 6
        assert "Node.js" in restored.tools
        assert "React" in restored.tools
        assert "PostgreSQL" in restored.tools
        assert "Docker" in restored.tools
        assert "AWS" in restored.tools
        assert "Git" in restored.tools


class TestCourseLanguageField:
    """Test Course language field for multi-language content generation."""

    def test_course_language_default(self):
        """Course defaults to English language."""
        course = Course()
        assert course.language == "English"

    def test_course_language_serializes(self):
        """Course language field is included in to_dict output."""
        course = Course(language="Spanish")
        data = course.to_dict()
        assert "language" in data
        assert data["language"] == "Spanish"

    def test_course_language_round_trip(self):
        """Course with language field round-trips correctly."""
        original = Course(
            title="Curso de Python",
            language="Spanish"
        )
        data = original.to_dict()
        restored = Course.from_dict(data)
        assert restored.language == "Spanish"

    def test_course_language_backward_compat(self):
        """Course from_dict without language field defaults to English."""
        # Simulate old course data without language field
        data = {
            "id": "course_123456789012",
            "title": "Old Course",
            "description": "Created before language field"
        }
        course = Course.from_dict(data)
        assert course.language == "English"

    def test_course_language_various_values(self):
        """Course supports various language values."""
        languages = ["English", "Spanish", "French", "German", "Chinese", "Japanese"]
        for lang in languages:
            course = Course(language=lang)
            data = course.to_dict()
            restored = Course.from_dict(data)
            assert restored.language == lang
