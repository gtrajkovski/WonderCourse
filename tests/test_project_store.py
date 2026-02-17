"""Tests for ProjectStore disk persistence with file locking."""

import json
import threading
import time
from pathlib import Path
from datetime import datetime

import pytest

from src.core.project_store import ProjectStore
from src.core.models import (
    Course,
    Module,
    Lesson,
    Activity,
    ContentType,
    ActivityType,
    BuildState,
    BloomLevel,
    WWHAAPhase,
)


# Test user ID for ProjectStore tests
TEST_USER_ID = "test_user_1"


@pytest.fixture
def temp_store(tmp_path):
    """Create a temporary ProjectStore."""
    return ProjectStore(base_dir=tmp_path / "projects")


@pytest.fixture
def sample_course():
    """Create a sample course with nested structure."""
    course = Course(
        id="test_course_123",
        title="Python Fundamentals",
        description="Learn Python basics",
        audience_level="beginner",
        target_duration_minutes=120,
        modality="online",
    )

    module = Module(
        id="mod_1",
        title="Module 1",
        description="Introduction to Python",
        order=0,
    )

    lesson = Lesson(
        id="les_1",
        title="Lesson 1",
        description="Variables and Data Types",
        order=0,
    )

    activity = Activity(
        id="act_1",
        title="Video: Introduction",
        content_type=ContentType.VIDEO,
        activity_type=ActivityType.VIDEO_LECTURE,
        wwhaa_phase=WWHAAPhase.HOOK,
        content="Welcome to Python!",
        build_state=BuildState.DRAFT,
        word_count=10,
        estimated_duration_minutes=5.0,
        bloom_level=BloomLevel.REMEMBER,
        order=0,
    )

    lesson.activities.append(activity)
    module.lessons.append(lesson)
    course.modules.append(module)

    return course


def test_save_and_load(temp_store, sample_course):
    """Test save/load round-trip preserves all Course data."""
    # Save course
    path = temp_store.save(TEST_USER_ID, sample_course)
    assert path.exists()
    assert path.name == "course_data.json"

    # Load course
    loaded = temp_store.load(TEST_USER_ID, sample_course.id)
    assert loaded is not None
    assert loaded.id == sample_course.id
    assert loaded.title == sample_course.title
    assert loaded.description == sample_course.description
    assert loaded.audience_level == sample_course.audience_level
    assert loaded.target_duration_minutes == sample_course.target_duration_minutes
    assert loaded.modality == sample_course.modality

    # Verify nested structure
    assert len(loaded.modules) == 1
    module = loaded.modules[0]
    assert module.id == "mod_1"
    assert module.title == "Module 1"

    assert len(module.lessons) == 1
    lesson = module.lessons[0]
    assert lesson.id == "les_1"
    assert lesson.title == "Lesson 1"

    assert len(lesson.activities) == 1
    activity = lesson.activities[0]
    assert activity.id == "act_1"
    assert activity.title == "Video: Introduction"
    assert activity.content_type == ContentType.VIDEO
    assert activity.activity_type == ActivityType.VIDEO_LECTURE
    assert activity.wwhaa_phase == WWHAAPhase.HOOK
    assert activity.bloom_level == BloomLevel.REMEMBER


def test_save_creates_subdirectories(temp_store, sample_course):
    """Test that save() creates exports/ and textbook/ subdirectories."""
    temp_store.save(TEST_USER_ID, sample_course)

    course_dir = temp_store._course_dir(TEST_USER_ID, sample_course.id)
    assert (course_dir / "exports").exists()
    assert (course_dir / "exports").is_dir()
    assert (course_dir / "textbook").exists()
    assert (course_dir / "textbook").is_dir()


def test_save_updates_timestamp(temp_store, sample_course):
    """Test that save() updates the updated_at timestamp."""
    original_updated_at = sample_course.updated_at

    # Small delay to ensure timestamp changes
    time.sleep(0.01)

    temp_store.save(TEST_USER_ID, sample_course)
    loaded = temp_store.load(TEST_USER_ID, sample_course.id)

    assert loaded.updated_at != original_updated_at
    # Verify it's a valid ISO timestamp
    datetime.fromisoformat(loaded.updated_at)


def test_load_nonexistent_returns_none(temp_store):
    """Test that load() returns None for non-existent course."""
    result = temp_store.load(TEST_USER_ID, "fake_id_does_not_exist")
    assert result is None


def test_list_courses_empty(temp_store):
    """Test that list_courses() returns empty list for empty store."""
    courses = temp_store.list_courses(TEST_USER_ID)
    assert courses == []


def test_list_courses_multiple(temp_store, sample_course):
    """Test that list_courses() returns metadata for all saved courses."""
    # Create and save three courses
    course1 = sample_course
    course1.id = "course_1"
    course1.title = "Course 1"
    course1.description = "First course"

    course2 = Course(
        id="course_2",
        title="Course 2",
        description="Second course",
    )
    course2.modules.append(Module(title="Module A"))
    course2.modules.append(Module(title="Module B"))

    course3 = Course(
        id="course_3",
        title="Course 3",
        description="Third course",
    )
    course3.modules.append(Module(title="Module X"))
    course3.modules.append(Module(title="Module Y"))
    course3.modules.append(Module(title="Module Z"))

    temp_store.save(TEST_USER_ID, course1)
    temp_store.save(TEST_USER_ID, course2)
    temp_store.save(TEST_USER_ID, course3)

    # List courses
    courses = temp_store.list_courses(TEST_USER_ID)
    assert len(courses) == 3

    # Verify metadata is present
    ids = {c["id"] for c in courses}
    assert ids == {"course_1", "course_2", "course_3"}

    # Check required fields
    for course in courses:
        assert "id" in course
        assert "title" in course
        assert "description" in course
        assert "module_count" in course
        assert "updated_at" in course

    # Verify module counts
    course_map = {c["id"]: c for c in courses}
    assert course_map["course_1"]["module_count"] == 1
    assert course_map["course_2"]["module_count"] == 2
    assert course_map["course_3"]["module_count"] == 3


def test_list_courses_sorted_by_updated(temp_store):
    """Test that list_courses() returns courses sorted by updated_at (most recent first)."""
    course1 = Course(id="course_old", title="Old Course")
    course2 = Course(id="course_mid", title="Mid Course")
    course3 = Course(id="course_new", title="New Course")

    # Save in specific order with delays
    temp_store.save(TEST_USER_ID, course1)
    time.sleep(0.01)
    temp_store.save(TEST_USER_ID, course2)
    time.sleep(0.01)
    temp_store.save(TEST_USER_ID, course3)

    courses = temp_store.list_courses(TEST_USER_ID)
    assert len(courses) == 3

    # Should be sorted newest first
    assert courses[0]["id"] == "course_new"
    assert courses[1]["id"] == "course_mid"
    assert courses[2]["id"] == "course_old"


def test_delete_existing(temp_store, sample_course):
    """Test that delete() removes the project directory tree."""
    # Save course
    temp_store.save(TEST_USER_ID, sample_course)
    course_dir = temp_store._course_dir(TEST_USER_ID, sample_course.id)
    assert course_dir.exists()

    # Delete course
    result = temp_store.delete(TEST_USER_ID, sample_course.id)
    assert result is True
    assert not course_dir.exists()


def test_delete_nonexistent_returns_false(temp_store):
    """Test that delete() returns False for non-existent course."""
    result = temp_store.delete(TEST_USER_ID, "fake_id_does_not_exist")
    assert result is False


def test_sanitize_id_strips_path_traversal(temp_store):
    """Test that _sanitize_id strips path traversal attempts."""
    # Test "../" attack
    sanitized = temp_store._sanitize_id("../hack")
    assert sanitized == "hack"
    assert ".." not in sanitized
    assert "/" not in sanitized


def test_sanitize_id_strips_slashes(temp_store):
    """Test that _sanitize_id strips forward and backward slashes."""
    sanitized = temp_store._sanitize_id("a/b\\c")
    assert sanitized == "abc"
    assert "/" not in sanitized
    assert "\\" not in sanitized


def test_sanitize_id_empty_raises(temp_store):
    """Test that _sanitize_id raises ValueError for empty string after sanitization."""
    with pytest.raises(ValueError, match="Invalid course ID"):
        temp_store._sanitize_id("")


def test_sanitize_id_dots_only_raises(temp_store):
    """Test that _sanitize_id raises ValueError for only dots."""
    with pytest.raises(ValueError, match="Invalid course ID"):
        temp_store._sanitize_id("..")


def test_concurrent_writes_no_corruption(temp_store, sample_course):
    """Test that concurrent writes using file locking do not corrupt JSON."""
    errors = []

    def write_course(course_id, title):
        try:
            course = Course(
                id=course_id,
                title=title,
                description=f"Description for {title}",
            )
            course.modules.append(Module(title=f"Module for {title}"))
            temp_store.save(TEST_USER_ID, course)
        except Exception as e:
            errors.append(e)

    # Create two threads that write different courses simultaneously
    thread1 = threading.Thread(target=write_course, args=("course_thread1", "Thread 1 Course"))
    thread2 = threading.Thread(target=write_course, args=("course_thread2", "Thread 2 Course"))

    thread1.start()
    thread2.start()

    thread1.join()
    thread2.join()

    # No errors should occur
    assert len(errors) == 0

    # Both courses should be loadable and have valid JSON
    course1 = temp_store.load(TEST_USER_ID, "course_thread1")
    course2 = temp_store.load(TEST_USER_ID, "course_thread2")

    assert course1 is not None
    assert course2 is not None
    assert course1.title == "Thread 1 Course"
    assert course2.title == "Thread 2 Course"

    # Verify JSON files are valid
    file1 = temp_store._course_file(TEST_USER_ID, "course_thread1")
    file2 = temp_store._course_file(TEST_USER_ID, "course_thread2")

    with open(file1, encoding="utf-8") as f:
        data1 = json.load(f)  # Should not raise JSONDecodeError

    with open(file2, encoding="utf-8") as f:
        data2 = json.load(f)  # Should not raise JSONDecodeError

    assert data1["title"] == "Thread 1 Course"
    assert data2["title"] == "Thread 2 Course"


def test_course_file_path(temp_store):
    """Test that _course_file returns correct path structure."""
    course_id = "test_123"
    path = temp_store._course_file(TEST_USER_ID, course_id)

    # Should be projects/{user_id}/{course_id}/course_data.json
    assert path.name == "course_data.json"
    assert path.parent.name == "test_123"
    assert path.parent.parent.name == TEST_USER_ID
    assert path.parent.parent.parent == temp_store.base_dir
