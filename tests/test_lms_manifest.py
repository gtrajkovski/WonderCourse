"""Tests for LMSManifestExporter JSON manifest generation."""

import json
import pytest
from pathlib import Path
from datetime import datetime
from src.exporters.lms_manifest import LMSManifestExporter
from src.exporters.base_exporter import BaseExporter
from src.core.models import (
    Course, Module, Lesson, Activity, LearningOutcome,
    ContentType, BuildState, BloomLevel
)


@pytest.fixture
def exporter(tmp_path):
    """Create LMSManifestExporter with temp output directory."""
    return LMSManifestExporter(output_dir=tmp_path)


@pytest.fixture
def sample_course():
    """Create a sample course with full hierarchy and learning outcomes."""
    course = Course(
        id="course_test123",
        title="Introduction to Python",
        description="Learn Python programming fundamentals",
        audience_level="beginner",
        target_duration_minutes=120,
    )

    # Create learning outcomes
    lo1 = LearningOutcome(
        id="lo_1",
        audience="Students",
        behavior="write Python functions",
        condition="using a code editor",
        degree="with correct syntax",
        bloom_level=BloomLevel.APPLY,
        mapped_activity_ids=["act_1", "act_2"],
    )
    lo2 = LearningOutcome(
        id="lo_2",
        audience="Students",
        behavior="debug simple programs",
        condition="given error messages",
        degree="identifying the root cause",
        bloom_level=BloomLevel.ANALYZE,
        mapped_activity_ids=["act_3"],
    )
    course.learning_outcomes = [lo1, lo2]

    # Create module 1 with 2 lessons
    module1 = Module(id="mod_1", title="Getting Started", description="Intro module", order=0)

    lesson1 = Lesson(id="les_1", title="Setup", description="Environment setup", order=0)
    lesson1.activities = [
        Activity(
            id="act_1",
            title="Install Python",
            content_type=ContentType.VIDEO,
            content='{"hook": "Welcome"}',
            build_state=BuildState.APPROVED,
            order=0,
        ),
        Activity(
            id="act_2",
            title="First Script",
            content_type=ContentType.READING,
            content="Read about scripts",
            build_state=BuildState.APPROVED,
            order=1,
        ),
    ]

    lesson2 = Lesson(id="les_2", title="Variables", description="Learn about variables", order=1)
    lesson2.activities = [
        Activity(
            id="act_3",
            title="Variable Quiz",
            content_type=ContentType.QUIZ,
            content='{"questions": []}',
            build_state=BuildState.APPROVED,
            order=0,
        ),
    ]

    module1.lessons = [lesson1, lesson2]
    course.modules.append(module1)

    return course


class TestLMSManifestExporterInheritance:
    """Tests for LMSManifestExporter inheritance from BaseExporter."""

    def test_inherits_from_base_exporter(self, exporter):
        """LMSManifestExporter should inherit from BaseExporter."""
        assert isinstance(exporter, BaseExporter)

    def test_format_name(self, exporter):
        """Should return 'LMS JSON Manifest' as format name."""
        assert exporter.format_name == "LMS JSON Manifest"

    def test_file_extension(self, exporter):
        """Should return '.json' as file extension."""
        assert exporter.file_extension == ".json"


class TestLMSManifestExport:
    """Tests for manifest export functionality."""

    def test_export_creates_json_file(self, exporter, sample_course, tmp_path):
        """Export should create a .json file."""
        output_path = exporter.export(sample_course)

        assert output_path.exists()
        assert output_path.suffix == ".json"
        assert output_path.parent == tmp_path

    def test_export_with_custom_filename(self, exporter, sample_course, tmp_path):
        """Export should use custom filename when provided."""
        output_path = exporter.export(sample_course, filename="custom_manifest")

        assert output_path.name == "custom_manifest.json"

    def test_export_creates_valid_json(self, exporter, sample_course):
        """Exported file should contain valid JSON."""
        output_path = exporter.export(sample_course)

        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert isinstance(data, dict)


class TestManifestStructure:
    """Tests for manifest JSON structure."""

    def test_manifest_has_version(self, exporter, sample_course):
        """Manifest should include version field."""
        output_path = exporter.export(sample_course)
        with open(output_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        assert "version" in manifest
        assert manifest["version"] == "1.0"

    def test_manifest_has_exported_at_timestamp(self, exporter, sample_course):
        """Manifest should include exported_at ISO timestamp."""
        output_path = exporter.export(sample_course)
        with open(output_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        assert "exported_at" in manifest
        # Should be valid ISO format
        datetime.fromisoformat(manifest["exported_at"].replace("Z", "+00:00"))

    def test_manifest_has_course_section(self, exporter, sample_course):
        """Manifest should include course section with metadata."""
        output_path = exporter.export(sample_course)
        with open(output_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        assert "course" in manifest
        course = manifest["course"]
        assert course["id"] == "course_test123"
        assert course["title"] == "Introduction to Python"
        assert course["description"] == "Learn Python programming fundamentals"
        assert course["audience_level"] == "beginner"
        assert course["target_duration_minutes"] == 120


class TestCourseHierarchy:
    """Tests for complete course hierarchy in manifest."""

    def test_modules_included(self, exporter, sample_course):
        """Manifest should include all modules."""
        output_path = exporter.export(sample_course)
        with open(output_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        modules = manifest["course"]["modules"]
        assert len(modules) == 1
        assert modules[0]["id"] == "mod_1"
        assert modules[0]["title"] == "Getting Started"
        assert modules[0]["description"] == "Intro module"
        assert modules[0]["order"] == 0

    def test_lessons_included(self, exporter, sample_course):
        """Manifest should include all lessons within modules."""
        output_path = exporter.export(sample_course)
        with open(output_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        lessons = manifest["course"]["modules"][0]["lessons"]
        assert len(lessons) == 2
        assert lessons[0]["id"] == "les_1"
        assert lessons[0]["title"] == "Setup"
        assert lessons[1]["id"] == "les_2"
        assert lessons[1]["title"] == "Variables"

    def test_activities_included(self, exporter, sample_course):
        """Manifest should include all activities within lessons."""
        output_path = exporter.export(sample_course)
        with open(output_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        activities = manifest["course"]["modules"][0]["lessons"][0]["activities"]
        assert len(activities) == 2
        assert activities[0]["id"] == "act_1"
        assert activities[0]["title"] == "Install Python"
        assert activities[0]["content_type"] == "video"
        assert activities[1]["id"] == "act_2"
        assert activities[1]["title"] == "First Script"

    def test_activity_includes_all_fields(self, exporter, sample_course):
        """Activities should include all relevant fields."""
        output_path = exporter.export(sample_course)
        with open(output_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        activity = manifest["course"]["modules"][0]["lessons"][0]["activities"][0]
        assert activity["id"] == "act_1"
        assert activity["title"] == "Install Python"
        assert activity["content_type"] == "video"
        assert activity["content"] == '{"hook": "Welcome"}'
        assert activity["build_state"] == "approved"
        assert activity["order"] == 0


class TestLearningOutcomes:
    """Tests for learning outcomes with activity mappings."""

    def test_learning_outcomes_included(self, exporter, sample_course):
        """Manifest should include learning outcomes section."""
        output_path = exporter.export(sample_course)
        with open(output_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        assert "learning_outcomes" in manifest
        outcomes = manifest["learning_outcomes"]
        assert len(outcomes) == 2

    def test_learning_outcome_structure(self, exporter, sample_course):
        """Learning outcomes should include all ABCD fields."""
        output_path = exporter.export(sample_course)
        with open(output_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        outcome = manifest["learning_outcomes"][0]
        assert outcome["id"] == "lo_1"
        assert outcome["audience"] == "Students"
        assert outcome["behavior"] == "write Python functions"
        assert outcome["condition"] == "using a code editor"
        assert outcome["degree"] == "with correct syntax"
        assert outcome["bloom_level"] == "apply"

    def test_learning_outcome_activity_mappings(self, exporter, sample_course):
        """Learning outcomes should include mapped activity IDs."""
        output_path = exporter.export(sample_course)
        with open(output_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        outcome = manifest["learning_outcomes"][0]
        assert "mapped_activity_ids" in outcome
        assert outcome["mapped_activity_ids"] == ["act_1", "act_2"]

        outcome2 = manifest["learning_outcomes"][1]
        assert outcome2["mapped_activity_ids"] == ["act_3"]


class TestEmptyCourse:
    """Tests for edge cases with empty courses."""

    def test_empty_course_export(self, exporter):
        """Empty course should still produce valid manifest."""
        course = Course(id="empty_course", title="Empty Course")

        output_path = exporter.export(course)
        with open(output_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        assert manifest["course"]["id"] == "empty_course"
        assert manifest["course"]["modules"] == []
        assert manifest["learning_outcomes"] == []

    def test_module_without_lessons(self, exporter):
        """Module without lessons should have empty lessons array."""
        course = Course(id="test", title="Test")
        course.modules.append(Module(id="mod_1", title="Empty Module"))

        output_path = exporter.export(course)
        with open(output_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        assert manifest["course"]["modules"][0]["lessons"] == []
