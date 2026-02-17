"""Tests for JobTracker in-memory job tracking system."""

import time
import pytest

from src.api.job_tracker import JobTracker, JobStatus


@pytest.fixture(autouse=True)
def clean_jobs():
    """Clear jobs before and after each test for isolation."""
    JobTracker.clear_jobs()
    yield
    JobTracker.clear_jobs()


class TestJobTrackerCreate:
    """Tests for JobTracker.create_job()."""

    def test_create_job_returns_task_id(self):
        """create_job returns string starting with task_type prefix."""
        task_id = JobTracker.create_job("textbook")
        assert isinstance(task_id, str)
        assert task_id.startswith("textbook_")
        assert len(task_id) == len("textbook_") + 8  # prefix + 8 hex chars

    def test_create_job_initializes_status(self):
        """New job has status='pending', progress=0.0, current_step='Initializing'."""
        task_id = JobTracker.create_job("chapter")
        job = JobTracker.get_job(task_id)

        assert job is not None
        assert job.status == "pending"
        assert job.progress == 0.0
        assert job.current_step == "Initializing"
        assert job.result is None
        assert job.error is None


class TestJobTrackerGet:
    """Tests for JobTracker.get_job()."""

    def test_get_job_returns_job(self):
        """get_job returns the created job with correct task_id."""
        task_id = JobTracker.create_job("test")
        job = JobTracker.get_job(task_id)

        assert job is not None
        assert job.task_id == task_id
        assert isinstance(job, JobStatus)

    def test_get_job_returns_none_for_unknown(self):
        """get_job('nonexistent') returns None."""
        result = JobTracker.get_job("nonexistent_12345678")
        assert result is None


class TestJobTrackerUpdate:
    """Tests for JobTracker.update_job()."""

    def test_update_job_changes_status(self):
        """update_job(tid, status='running') changes status."""
        task_id = JobTracker.create_job("test")
        JobTracker.update_job(task_id, status="running")

        job = JobTracker.get_job(task_id)
        assert job.status == "running"

    def test_update_job_changes_progress(self):
        """update_job(tid, progress=0.5, current_step='Halfway') updates both fields."""
        task_id = JobTracker.create_job("test")
        JobTracker.update_job(task_id, progress=0.5, current_step="Halfway")

        job = JobTracker.get_job(task_id)
        assert job.progress == 0.5
        assert job.current_step == "Halfway"

    def test_update_job_sets_result(self):
        """update_job with result stores result dict."""
        task_id = JobTracker.create_job("test")
        result_data = {"data": "test", "chapters": 5}
        JobTracker.update_job(task_id, status="completed", result=result_data)

        job = JobTracker.get_job(task_id)
        assert job.status == "completed"
        assert job.result == result_data

    def test_update_job_sets_error(self):
        """update_job with error stores error message."""
        task_id = JobTracker.create_job("test")
        JobTracker.update_job(task_id, status="failed", error="Something broke")

        job = JobTracker.get_job(task_id)
        assert job.status == "failed"
        assert job.error == "Something broke"

    def test_update_job_updates_timestamp(self):
        """updated_at changes after update_job call."""
        task_id = JobTracker.create_job("test")
        job_before = JobTracker.get_job(task_id)
        original_updated_at = job_before.updated_at

        # Small delay to ensure timestamp changes
        time.sleep(0.01)

        JobTracker.update_job(task_id, progress=0.1)
        job_after = JobTracker.get_job(task_id)

        assert job_after.updated_at != original_updated_at
        assert job_after.updated_at > original_updated_at


class TestJobTrackerClear:
    """Tests for JobTracker.clear_jobs()."""

    def test_clear_jobs(self):
        """clear_jobs() removes all jobs, get_job returns None."""
        task_id1 = JobTracker.create_job("test1")
        task_id2 = JobTracker.create_job("test2")

        # Verify jobs exist
        assert JobTracker.get_job(task_id1) is not None
        assert JobTracker.get_job(task_id2) is not None

        JobTracker.clear_jobs()

        # Verify jobs are gone
        assert JobTracker.get_job(task_id1) is None
        assert JobTracker.get_job(task_id2) is None


class TestJobStatus:
    """Tests for JobStatus dataclass."""

    def test_job_status_to_dict(self):
        """to_dict() returns dict with all expected keys."""
        task_id = JobTracker.create_job("test")
        job = JobTracker.get_job(task_id)
        result = job.to_dict()

        expected_keys = {
            "task_id",
            "status",
            "progress",
            "current_step",
            "result",
            "error",
            "created_at",
            "updated_at",
        }
        assert set(result.keys()) == expected_keys
        assert result["task_id"] == task_id
        assert result["status"] == "pending"
        assert result["progress"] == 0.0
        assert result["current_step"] == "Initializing"
        assert result["result"] is None
        assert result["error"] is None
        assert isinstance(result["created_at"], str)
        assert isinstance(result["updated_at"], str)
