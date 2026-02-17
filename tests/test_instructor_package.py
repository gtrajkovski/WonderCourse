"""TDD Tests for InstructorPackageExporter ZIP bundle generation."""

import json
import pytest
import zipfile
from io import BytesIO

from src.exporters.instructor_package import InstructorPackageExporter
from src.core.models import (
    Course, Module, Lesson, Activity,
    ContentType, ActivityType, BuildState, BloomLevel,
    LearningOutcome, TextbookChapter,
)


@pytest.fixture
def exporter():
    """Create InstructorPackageExporter instance."""
    return InstructorPackageExporter()


@pytest.fixture
def simple_course():
    """Create a simple course for basic tests."""
    course = Course(
        id="course_simple",
        title="Introduction to Python",
        description="Learn Python programming basics",
        audience_level="beginner",
        target_duration_minutes=120,
    )
    module = Module(id="mod_1", title="Getting Started", description="Module intro")
    lesson = Lesson(id="les_1", title="Hello World", description="Your first program")
    activity = Activity(
        id="act_1",
        title="Writing Your First Script",
        content_type=ContentType.VIDEO,
        activity_type=ActivityType.VIDEO_LECTURE,
        content='{"hook": "Welcome to Python!", "objective": "Write hello world"}',
        build_state=BuildState.APPROVED,
        estimated_duration_minutes=15,
    )
    lesson.activities.append(activity)
    module.lessons.append(lesson)
    course.modules.append(module)
    return course


@pytest.fixture
def course_with_quiz():
    """Create a course with quiz activities for answer key testing."""
    course = Course(
        id="course_quiz",
        title="Python Quiz Course",
        description="Course with quizzes",
    )
    module = Module(id="mod_1", title="Module 1")
    lesson = Lesson(id="les_1", title="Lesson 1")

    quiz_content = {
        "title": "Python Basics Quiz",
        "questions": [
            {
                "question_text": "What keyword is used to define a function in Python?",
                "options": [
                    {"label": "A", "text": "function"},
                    {"label": "B", "text": "def"},
                    {"label": "C", "text": "func"},
                    {"label": "D", "text": "define"},
                ],
                "correct_answer": "B",
                "feedback_correct": "Correct! 'def' is the keyword used to define functions.",
                "feedback_incorrect": "The correct answer is 'def'.",
            },
            {
                "question_text": "Which of these is a valid variable name?",
                "options": [
                    {"label": "A", "text": "2var"},
                    {"label": "B", "text": "my-var"},
                    {"label": "C", "text": "my_var"},
                    {"label": "D", "text": "class"},
                ],
                "correct_answer": "C",
                "feedback_correct": "Correct! my_var follows Python naming conventions.",
                "feedback_incorrect": "Variable names cannot start with numbers or contain hyphens.",
            },
        ],
    }

    quiz_activity = Activity(
        id="act_quiz",
        title="Python Basics Quiz",
        content_type=ContentType.QUIZ,
        activity_type=ActivityType.GRADED_QUIZ,
        content=json.dumps(quiz_content),
        build_state=BuildState.APPROVED,
    )
    lesson.activities.append(quiz_activity)
    module.lessons.append(lesson)
    course.modules.append(module)
    return course


@pytest.fixture
def course_with_rubric():
    """Create a course with rubric activities."""
    course = Course(
        id="course_rubric",
        title="Python Project Course",
        description="Course with rubric",
    )
    module = Module(id="mod_1", title="Module 1")
    lesson = Lesson(id="les_1", title="Lesson 1")

    rubric_content = {
        "title": "Project Rubric",
        "criteria": [
            {
                "name": "Code Quality",
                "description": "Code is clean and well-organized",
                "levels": [
                    {"score": 4, "description": "Excellent: Clean, well-documented code"},
                    {"score": 3, "description": "Good: Mostly clean code"},
                    {"score": 2, "description": "Fair: Some organization issues"},
                    {"score": 1, "description": "Poor: Disorganized code"},
                ],
            },
        ],
    }

    rubric_activity = Activity(
        id="act_rubric",
        title="Final Project Rubric",
        content_type=ContentType.RUBRIC,
        content=json.dumps(rubric_content),
        build_state=BuildState.APPROVED,
    )
    lesson.activities.append(rubric_activity)
    module.lessons.append(lesson)
    course.modules.append(module)
    return course


@pytest.fixture
def course_with_learning_outcomes():
    """Create a course with learning outcomes."""
    course = Course(
        id="course_outcomes",
        title="Python Fundamentals",
        description="Course with outcomes",
    )
    course.learning_outcomes = [
        LearningOutcome(
            id="lo_1",
            behavior="Define and call functions in Python",
            bloom_level=BloomLevel.APPLY,
        ),
        LearningOutcome(
            id="lo_2",
            behavior="Implement loops and conditionals",
            bloom_level=BloomLevel.ANALYZE,
        ),
    ]
    module = Module(id="mod_1", title="Module 1")
    lesson = Lesson(id="les_1", title="Lesson 1")
    activity = Activity(id="act_1", title="Activity 1", content="content")
    lesson.activities.append(activity)
    module.lessons.append(lesson)
    course.modules.append(module)
    return course


@pytest.fixture
def course_with_textbook():
    """Create a course with textbook chapters."""
    course = Course(
        id="course_textbook",
        title="Python Textbook Course",
        description="Course with textbook chapters",
    )
    course.textbook_chapters = [
        TextbookChapter(
            id="ch_1",
            title="Introduction to Python",
            sections=[
                {"heading": "What is Python?", "content": "Python is a programming language."},
                {"heading": "Installing Python", "content": "Download from python.org."},
            ],
            glossary_terms=[
                {"term": "Python", "definition": "A programming language"},
            ],
        ),
    ]
    module = Module(id="mod_1", title="Module 1")
    lesson = Lesson(id="les_1", title="Lesson 1")
    activity = Activity(id="act_1", title="Activity 1", content="content")
    lesson.activities.append(activity)
    module.lessons.append(lesson)
    course.modules.append(module)
    return course


@pytest.fixture
def course_with_special_chars():
    """Create a course with special characters in names."""
    course = Course(
        id="course_special",
        title="Python: Advanced Topics!",
        description="Course with special chars",
    )
    module = Module(id="mod_1", title="Module #1 (Intro)")
    lesson = Lesson(id="les_1", title="Lesson 1: The Beginning?")
    activity = Activity(
        id="act_1",
        title="Activity @1 & More!",
        content="content",
        estimated_duration_minutes=10,
    )
    lesson.activities.append(activity)
    module.lessons.append(lesson)
    course.modules.append(module)
    return course


class TestInstructorPackageExporterBasics:
    """Test basic InstructorPackageExporter properties."""

    def test_exporter_has_correct_format_name(self, exporter):
        """Exporter should report correct format name."""
        assert exporter.format_name == "Instructor Package"

    def test_exporter_has_correct_file_extension(self, exporter):
        """Exporter should use .zip extension."""
        assert exporter.file_extension == ".zip"


class TestZipCreation:
    """Tests for ZIP file creation and structure."""

    def test_export_creates_valid_zip(self, exporter, simple_course):
        """Export should create a valid, readable ZIP file."""
        buffer, filename = exporter.export(simple_course)

        assert isinstance(buffer, BytesIO)
        assert filename.endswith(".zip")
        assert "Introduction_to_Python" in filename

        # Verify ZIP is valid
        with zipfile.ZipFile(buffer, "r") as zf:
            assert zf.testzip() is None  # None means no bad files

    def test_export_contains_syllabus(self, exporter, simple_course):
        """ZIP should contain syllabus.txt with course info."""
        buffer, _ = exporter.export(simple_course)

        with zipfile.ZipFile(buffer, "r") as zf:
            assert "syllabus.txt" in zf.namelist()
            syllabus = zf.read("syllabus.txt").decode("utf-8")
            assert "Introduction to Python" in syllabus
            assert "Learn Python programming basics" in syllabus
            assert "beginner" in syllabus.lower()
            assert "120 minutes" in syllabus

    def test_syllabus_contains_modules_and_lessons(self, exporter, simple_course):
        """Syllabus should list modules and lessons."""
        buffer, _ = exporter.export(simple_course)

        with zipfile.ZipFile(buffer, "r") as zf:
            syllabus = zf.read("syllabus.txt").decode("utf-8")
            assert "Getting Started" in syllabus
            assert "Hello World" in syllabus

    def test_syllabus_contains_learning_outcomes(self, exporter, course_with_learning_outcomes):
        """Syllabus should include learning outcomes."""
        buffer, _ = exporter.export(course_with_learning_outcomes)

        with zipfile.ZipFile(buffer, "r") as zf:
            syllabus = zf.read("syllabus.txt").decode("utf-8")
            assert "Learning Outcomes" in syllabus
            assert "Define and call functions" in syllabus
            assert "APPLY" in syllabus or "apply" in syllabus.lower()


class TestLessonPlans:
    """Tests for lesson plan generation."""

    def test_export_contains_lesson_plans(self, exporter, simple_course):
        """ZIP should contain lesson plans folder with lesson files."""
        buffer, _ = exporter.export(simple_course)

        with zipfile.ZipFile(buffer, "r") as zf:
            # Check for lesson_plans folder
            lesson_plan_files = [n for n in zf.namelist() if n.startswith("lesson_plans/")]
            assert len(lesson_plan_files) > 0

            # Check specific lesson plan exists
            expected_path = "lesson_plans/Getting_Started/Hello_World.txt"
            assert expected_path in zf.namelist()

    def test_lesson_plan_format(self, exporter, simple_course):
        """Lesson plan should contain title, module, activities."""
        buffer, _ = exporter.export(simple_course)

        with zipfile.ZipFile(buffer, "r") as zf:
            lesson_plan = zf.read("lesson_plans/Getting_Started/Hello_World.txt").decode("utf-8")
            assert "Lesson: Hello World" in lesson_plan
            assert "Module: Getting Started" in lesson_plan
            assert "Writing Your First Script" in lesson_plan
            assert "15 min" in lesson_plan


class TestRubrics:
    """Tests for rubric extraction."""

    def test_export_contains_rubrics(self, exporter, course_with_rubric):
        """ZIP should contain rubrics folder for RUBRIC activities."""
        buffer, _ = exporter.export(course_with_rubric)

        with zipfile.ZipFile(buffer, "r") as zf:
            rubric_files = [n for n in zf.namelist() if n.startswith("rubrics/")]
            assert len(rubric_files) > 0

    def test_rubric_format(self, exporter, course_with_rubric):
        """Rubric file should contain criteria and levels."""
        buffer, _ = exporter.export(course_with_rubric)

        with zipfile.ZipFile(buffer, "r") as zf:
            rubric_files = [n for n in zf.namelist() if n.startswith("rubrics/")]
            rubric_content = zf.read(rubric_files[0]).decode("utf-8")
            assert "Code Quality" in rubric_content
            assert "Excellent" in rubric_content


class TestQuizzesAndAnswerKeys:
    """Tests for quiz and answer key generation."""

    def test_export_contains_quiz_questions(self, exporter, course_with_quiz):
        """ZIP should contain quizzes folder with question files (no answers)."""
        buffer, _ = exporter.export(course_with_quiz)

        with zipfile.ZipFile(buffer, "r") as zf:
            quiz_files = [n for n in zf.namelist() if n.startswith("quizzes/")]
            assert len(quiz_files) > 0

            quiz_content = zf.read(quiz_files[0]).decode("utf-8")
            assert "What keyword is used to define a function" in quiz_content
            # Should NOT contain correct answers
            assert "Correct:" not in quiz_content
            assert "feedback_correct" not in quiz_content

    def test_export_contains_answer_keys(self, exporter, course_with_quiz):
        """ZIP should contain answer_keys folder with answer files."""
        buffer, _ = exporter.export(course_with_quiz)

        with zipfile.ZipFile(buffer, "r") as zf:
            key_files = [n for n in zf.namelist() if n.startswith("answer_keys/")]
            assert len(key_files) > 0

            key_content = zf.read(key_files[0]).decode("utf-8")
            assert "Correct: B" in key_content
            assert "'def' is the keyword" in key_content


class TestTextbookIntegration:
    """Tests for textbook.docx inclusion."""

    def test_export_includes_textbook_when_chapters_exist(self, exporter, course_with_textbook):
        """ZIP should contain textbook.docx when course has textbook chapters."""
        buffer, _ = exporter.export(course_with_textbook)

        with zipfile.ZipFile(buffer, "r") as zf:
            assert "textbook.docx" in zf.namelist()

    def test_export_no_textbook_without_chapters(self, exporter, simple_course):
        """ZIP should NOT contain textbook.docx when no chapters exist."""
        buffer, _ = exporter.export(simple_course)

        with zipfile.ZipFile(buffer, "r") as zf:
            assert "textbook.docx" not in zf.namelist()


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_export_handles_empty_course(self, exporter):
        """Course with no modules should produce valid ZIP with syllabus only."""
        empty_course = Course(
            id="course_empty",
            title="Empty Course",
            description="No content yet",
        )

        buffer, filename = exporter.export(empty_course)

        with zipfile.ZipFile(buffer, "r") as zf:
            assert zf.testzip() is None
            assert "syllabus.txt" in zf.namelist()
            # No lesson_plans since no modules
            lesson_plans = [n for n in zf.namelist() if n.startswith("lesson_plans/")]
            assert len(lesson_plans) == 0

    def test_export_sanitizes_filenames(self, exporter, course_with_special_chars):
        """Special characters should be removed from folder/file names."""
        buffer, filename = exporter.export(course_with_special_chars)

        # Filename should be sanitized
        assert ":" not in filename
        assert "!" not in filename

        with zipfile.ZipFile(buffer, "r") as zf:
            # No special characters in paths
            for name in zf.namelist():
                assert ":" not in name
                assert "?" not in name
                assert "#" not in name
                assert "@" not in name
                assert "&" not in name
                assert "!" not in name

    def test_export_handles_course_without_quiz_content(self, exporter, simple_course):
        """Course without quizzes should have empty quizzes and answer_keys folders."""
        buffer, _ = exporter.export(simple_course)

        with zipfile.ZipFile(buffer, "r") as zf:
            # Folders might not exist if empty, or exist but be empty
            quiz_files = [n for n in zf.namelist() if n.startswith("quizzes/") and not n.endswith("/")]
            assert len(quiz_files) == 0

    def test_export_handles_invalid_json_content_gracefully(self, exporter):
        """Activity with invalid JSON content should not crash export."""
        course = Course(id="course_test", title="Test Course")
        module = Module(id="mod_1", title="Module 1")
        lesson = Lesson(id="les_1", title="Lesson 1")
        activity = Activity(
            id="act_1",
            title="Bad Quiz",
            content_type=ContentType.QUIZ,
            content="not valid json {{{",
            build_state=BuildState.APPROVED,
        )
        lesson.activities.append(activity)
        module.lessons.append(lesson)
        course.modules.append(module)

        # Should not raise, just skip the activity
        buffer, _ = exporter.export(course)

        with zipfile.ZipFile(buffer, "r") as zf:
            assert zf.testzip() is None
