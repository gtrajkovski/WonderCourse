"""
In-memory job tracking system for long-running generation tasks.

Provides task_id creation, progress updates, and status polling for
async operations like textbook chapter generation.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional


@dataclass
class JobStatus:
    """Status information for a tracked job."""

    task_id: str
    status: str  # "pending", "running", "completed", "failed"
    progress: float  # 0.0 to 1.0
    current_step: str  # human-readable description
    created_at: str  # ISO timestamp
    updated_at: str  # ISO timestamp
    result: Optional[dict] = field(default=None)  # final result on completion
    error: Optional[str] = field(default=None)  # error message on failure

    def to_dict(self) -> dict:
        """Convert job status to JSON-serializable dict."""
        return {
            "task_id": self.task_id,
            "status": self.status,
            "progress": self.progress,
            "current_step": self.current_step,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class JobTracker:
    """
    In-memory job tracking for async generation tasks.

    Uses class-level storage for simplicity. Migration path to Redis/Celery
    is deferred to Phase 8+.
    """

    _jobs: Dict[str, JobStatus] = {}

    @classmethod
    def create_job(cls, task_type: str) -> str:
        """
        Create a new job and return its unique task_id.

        Args:
            task_type: Prefix for the task_id (e.g., "textbook", "chapter")

        Returns:
            Unique task_id in format "{task_type}_{hex}"
        """
        task_id = f"{task_type}_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        job = JobStatus(
            task_id=task_id,
            status="pending",
            progress=0.0,
            current_step="Initializing",
            created_at=now,
            updated_at=now,
        )

        cls._jobs[task_id] = job
        return task_id

    @classmethod
    def update_job(cls, task_id: str, **kwargs) -> None:
        """
        Update fields on an existing job.

        Automatically updates the updated_at timestamp.
        No-op if task_id not found.

        Args:
            task_id: The job's task_id
            **kwargs: Fields to update (status, progress, current_step, result, error)
        """
        job = cls._jobs.get(task_id)
        if job is None:
            return

        for key, value in kwargs.items():
            if hasattr(job, key):
                setattr(job, key, value)

        job.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    @classmethod
    def get_job(cls, task_id: str) -> Optional[JobStatus]:
        """
        Retrieve job status by task_id.

        Args:
            task_id: The job's task_id

        Returns:
            JobStatus if found, None otherwise
        """
        return cls._jobs.get(task_id)

    @classmethod
    def clear_jobs(cls) -> None:
        """Clear all jobs (for testing)."""
        cls._jobs.clear()
