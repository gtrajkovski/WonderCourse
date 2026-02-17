"""Tests for textbook API endpoints.

Tests async textbook generation with mocked TextbookGenerator and CoherenceValidator.
Covers generate endpoint, job status polling, error handling, and model updates.
"""

import pytest
import time
from unittest.mock import MagicMock, patch

from src.core.models import Course, Module, Lesson, Activity, LearningOutcome, TextbookChapter
from src.api.job_tracker import JobTracker


@pytest.fixture(autouse=True)
def clear_jobs():
    """Clear JobTracker state before each test."""
    JobTracker.clear_jobs()
    yield
    JobTracker.clear_jobs()


@pytest.fixture
def course_with_outcome(client, tmp_path, monkeypatch):
    """Create a course with a learning outcome for textbook generation."""
    # Create course with learning outcome
    from src.config import Config
    from src.collab.decorators import ensure_owner_collaborator
    import app as app_module

    course = Course(
        title="Test Course",
        description="A test course for textbook generation"
    )

    outcome = LearningOutcome(
        audience="Students",
        behavior="understand machine learning fundamentals",
        condition="after completing this chapter",
        degree="with 80% accuracy"
    )
    course.learning_outcomes.append(outcome)

    # Add a module with lesson and activity
    module = Module(title="Module 1")
    lesson = Lesson(title="Lesson 1")
    activity = Activity(title="Activity 1")
    lesson.activities.append(activity)
    module.lessons.append(lesson)
    course.modules.append(module)

    # User ID 1 is the authenticated test user from conftest.py
    app_module.project_store.save(1, course)

    # Create owner collaborator record in database
    with app_module.app.app_context():
        ensure_owner_collaborator(course.id, 1)

    return course, outcome


class TestGenerateTextbook:
    """Tests for POST /api/courses/<id>/textbook/generate endpoint."""

    def test_generate_textbook_returns_202_with_task_id(self, client, course_with_outcome, mocker):
        """Test that generate endpoint returns 202 with task_id."""
        course, outcome = course_with_outcome

        # Mock TextbookGenerator to return immediately
        mock_chapter = MagicMock()
        mock_chapter.title = "Test Chapter"
        mock_chapter.sections = []
        mock_chapter.glossary_terms = []
        mock_chapter.image_placeholders = []
        mock_chapter.references = []

        mock_generator = MagicMock()
        mock_generator.generate_chapter.return_value = (mock_chapter, {"word_count": 100})
        mocker.patch('src.api.textbook.TextbookGenerator', return_value=mock_generator)

        # Mock CoherenceValidator
        mock_validator = MagicMock()
        mock_validator.check_consistency.return_value = []
        mocker.patch('src.api.textbook.CoherenceValidator', return_value=mock_validator)

        response = client.post(
            f'/api/courses/{course.id}/textbook/generate',
            json={"learning_outcome_id": outcome.id, "topic": "Machine Learning"}
        )

        assert response.status_code == 202
        data = response.get_json()
        assert "task_id" in data
        assert data["task_id"].startswith("textbook_")

    def test_generate_textbook_requires_learning_outcome_id(self, client, course_with_outcome):
        """Test that generate endpoint returns 400 without learning_outcome_id."""
        course, _ = course_with_outcome

        response = client.post(
            f'/api/courses/{course.id}/textbook/generate',
            json={"topic": "Machine Learning"}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "learning_outcome_id" in data["error"]

    def test_generate_textbook_404_for_missing_course(self, client):
        """Test that generate endpoint returns 404 for nonexistent course."""
        response = client.post(
            '/api/courses/nonexistent_course/textbook/generate',
            json={"learning_outcome_id": "lo_123", "topic": "Test"}
        )

        assert response.status_code == 404
        data = response.get_json()
        assert "Course not found" in data["error"]

    def test_generate_textbook_404_for_missing_outcome(self, client, course_with_outcome):
        """Test that generate endpoint returns 404 for nonexistent learning outcome."""
        course, _ = course_with_outcome

        response = client.post(
            f'/api/courses/{course.id}/textbook/generate',
            json={"learning_outcome_id": "lo_nonexistent", "topic": "Test"}
        )

        assert response.status_code == 404
        data = response.get_json()
        assert "Learning outcome not found" in data["error"]


class TestGetJobStatus:
    """Tests for GET /api/jobs/<task_id> endpoint."""

    def test_get_job_status(self, client):
        """Test that job status endpoint returns job details."""
        # Create a job directly
        task_id = JobTracker.create_job("textbook")
        JobTracker.update_job(task_id, status="running", progress=0.5, current_step="Generating")

        response = client.get(f'/api/jobs/{task_id}')

        assert response.status_code == 200
        data = response.get_json()
        assert data["task_id"] == task_id
        assert data["status"] == "running"
        assert data["progress"] == 0.5
        assert data["current_step"] == "Generating"

    def test_get_job_status_404(self, client):
        """Test that job status endpoint returns 404 for nonexistent job."""
        response = client.get('/api/jobs/nonexistent_task')

        assert response.status_code == 404
        data = response.get_json()
        assert "Job not found" in data["error"]


class TestTextbookChapterSaved:
    """Tests for chapter persistence after generation."""

    def test_textbook_chapter_saved_to_course(self, client, course_with_outcome, mocker):
        """Test that generated chapter is saved to course.textbook_chapters."""
        course, outcome = course_with_outcome
        import app as app_module

        # Mock TextbookGenerator with synchronous execution
        mock_chapter = MagicMock()
        mock_chapter.title = "Generated Chapter"
        mock_chapter.sections = []
        mock_chapter.glossary_terms = []
        mock_chapter.image_placeholders = []
        mock_chapter.references = []

        mock_generator = MagicMock()
        mock_generator.generate_chapter.return_value = (mock_chapter, {"word_count": 1500})
        mocker.patch('src.api.textbook.TextbookGenerator', return_value=mock_generator)

        # Mock CoherenceValidator
        mock_validator = MagicMock()
        mock_validator.check_consistency.return_value = []
        mocker.patch('src.api.textbook.CoherenceValidator', return_value=mock_validator)

        # Mock threading to run synchronously
        def run_immediately(target, args, daemon):
            target(*args)
            return MagicMock()

        mocker.patch('src.api.textbook.threading.Thread', side_effect=lambda **kwargs: MagicMock(start=lambda: run_immediately(kwargs['target'], kwargs['args'], kwargs.get('daemon', False))))

        # Actually run the target function directly
        original_thread = mocker.patch('src.api.textbook.threading.Thread')

        def sync_thread(**kwargs):
            mock_thread = MagicMock()
            def start():
                kwargs['target'](*kwargs['args'])
            mock_thread.start = start
            return mock_thread

        original_thread.side_effect = sync_thread

        response = client.post(
            f'/api/courses/{course.id}/textbook/generate',
            json={"learning_outcome_id": outcome.id, "topic": "Machine Learning"}
        )

        assert response.status_code == 202
        task_id = response.get_json()["task_id"]

        # Check job completed
        job = JobTracker.get_job(task_id)
        assert job.status == "completed"

        # Verify chapter was saved (test user always has ID 1)
        updated_course = app_module.project_store.load(1, course.id)
        assert len(updated_course.textbook_chapters) == 1
        assert updated_course.textbook_chapters[0].title == "Generated Chapter"


class TestJobTransitions:
    """Tests for job status transitions."""

    def test_job_transitions_to_completed(self, client, course_with_outcome, mocker):
        """Test that job status transitions from pending to completed."""
        course, outcome = course_with_outcome

        # Track status changes
        statuses = []

        original_update = JobTracker.update_job

        def track_update(task_id, **kwargs):
            if "status" in kwargs:
                statuses.append(kwargs["status"])
            original_update(task_id, **kwargs)

        mocker.patch.object(JobTracker, 'update_job', side_effect=track_update)

        # Mock generator
        mock_chapter = MagicMock()
        mock_chapter.title = "Test"
        mock_chapter.sections = []
        mock_chapter.glossary_terms = []
        mock_chapter.image_placeholders = []
        mock_chapter.references = []

        mock_generator = MagicMock()
        mock_generator.generate_chapter.return_value = (mock_chapter, {"word_count": 100})
        mocker.patch('src.api.textbook.TextbookGenerator', return_value=mock_generator)

        mock_validator = MagicMock()
        mock_validator.check_consistency.return_value = []
        mocker.patch('src.api.textbook.CoherenceValidator', return_value=mock_validator)

        # Run synchronously
        def sync_thread(**kwargs):
            mock_thread = MagicMock()
            mock_thread.start = lambda: kwargs['target'](*kwargs['args'])
            return mock_thread

        mocker.patch('src.api.textbook.threading.Thread', side_effect=sync_thread)

        response = client.post(
            f'/api/courses/{course.id}/textbook/generate',
            json={"learning_outcome_id": outcome.id, "topic": "Test"}
        )

        assert response.status_code == 202

        # Verify transitions: running (multiple times during progress) -> completed
        assert "running" in statuses
        assert statuses[-1] == "completed"

    def test_job_transitions_to_failed_on_error(self, client, course_with_outcome, mocker):
        """Test that job status becomes failed on generator error."""
        course, outcome = course_with_outcome

        # Mock generator to raise exception
        mock_generator = MagicMock()
        mock_generator.generate_chapter.side_effect = Exception("API Error: Rate limited")
        mocker.patch('src.api.textbook.TextbookGenerator', return_value=mock_generator)

        # Run synchronously
        def sync_thread(**kwargs):
            mock_thread = MagicMock()
            mock_thread.start = lambda: kwargs['target'](*kwargs['args'])
            return mock_thread

        mocker.patch('src.api.textbook.threading.Thread', side_effect=sync_thread)

        response = client.post(
            f'/api/courses/{course.id}/textbook/generate',
            json={"learning_outcome_id": outcome.id, "topic": "Test"}
        )

        assert response.status_code == 202
        task_id = response.get_json()["task_id"]

        # Verify job failed
        job = JobTracker.get_job(task_id)
        assert job.status == "failed"
        assert "API Error" in job.error


class TestTextbookChapterModel:
    """Tests for updated TextbookChapter model."""

    def test_updated_textbook_chapter_model(self):
        """Test that TextbookChapter.to_dict() includes new fields."""
        chapter = TextbookChapter(
            title="Test Chapter",
            sections=[{"heading": "Section 1", "content": "Content"}],
            glossary_terms=[{"term": "AI", "definition": "Artificial Intelligence"}],
            word_count=500,
            image_placeholders=[{"figure_number": "1.1", "caption": "Test image"}],
            references=[{"citation": "Author (2024). Title."}],
            coherence_issues=["Minor redundancy detected"]
        )

        data = chapter.to_dict()

        assert "image_placeholders" in data
        assert len(data["image_placeholders"]) == 1
        assert data["image_placeholders"][0]["figure_number"] == "1.1"

        assert "references" in data
        assert len(data["references"]) == 1

        assert "coherence_issues" in data
        assert len(data["coherence_issues"]) == 1
        assert "redundancy" in data["coherence_issues"][0]
