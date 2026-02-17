"""Transcript storage and retrieval for coaching sessions.

Persists coaching session transcripts to course data for instructor review
and analysis.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid

from src.core.project_store import ProjectStore
from src.coach.conversation import Message
from src.coach.evaluator import SessionEvaluation


@dataclass
class Transcript:
    """Complete coaching session transcript.

    Attributes:
        id: Unique transcript identifier
        session_id: Session identifier from ConversationManager
        activity_id: Activity this coaching session was for
        course_id: Course containing the activity
        user_id: User who participated in the session
        messages: List of conversation messages
        started_at: ISO timestamp when session started
        ended_at: ISO timestamp when session ended (None if ongoing)
        evaluation: Overall session evaluation (None if not evaluated)
        summary: Natural language session summary (None if not generated)
    """

    id: str = field(default_factory=lambda: f"transcript_{uuid.uuid4().hex[:8]}")
    session_id: str = ""
    activity_id: str = ""
    course_id: str = ""
    user_id: str = ""
    messages: List[Message] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ended_at: Optional[str] = None
    evaluation: Optional[SessionEvaluation] = None
    summary: Optional[str] = None

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "activity_id": self.activity_id,
            "course_id": self.course_id,
            "user_id": self.user_id,
            "messages": [msg.to_dict() for msg in self.messages],
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "evaluation": self.evaluation.to_dict() if self.evaluation else None,
            "summary": self.summary
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Transcript":
        """Deserialize from dictionary."""
        messages = [Message.from_dict(msg) for msg in data.get("messages", [])]
        evaluation = None
        if data.get("evaluation"):
            evaluation = SessionEvaluation.from_dict(data["evaluation"])

        return cls(
            id=data["id"],
            session_id=data["session_id"],
            activity_id=data["activity_id"],
            course_id=data["course_id"],
            user_id=data["user_id"],
            messages=messages,
            started_at=data["started_at"],
            ended_at=data.get("ended_at"),
            evaluation=evaluation,
            summary=data.get("summary")
        )


class TranscriptStore:
    """Manages storage and retrieval of coaching transcripts.

    Transcripts are stored in the course data JSON file under a
    'transcripts' array field.
    """

    def __init__(self, project_store: ProjectStore):
        """Initialize transcript store.

        Args:
            project_store: ProjectStore instance for persistence
        """
        self.project_store = project_store

    def _load_course(self, course_id: str):
        """Load course by finding the owner ID.

        Args:
            course_id: Course ID to load

        Returns:
            Course object or raises FileNotFoundError
        """
        from src.collab.models import Collaborator
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            raise FileNotFoundError(f"Course {course_id} not found (no owner)")
        return self.project_store.load(owner_id, course_id)

    def save_transcript(self, transcript: Transcript) -> str:
        """Save a coaching transcript.

        Args:
            transcript: Transcript to save

        Returns:
            Transcript ID

        Raises:
            FileNotFoundError: If course doesn't exist
        """
        from src.collab.models import Collaborator
        course = self._load_course(transcript.course_id)

        # Check if transcript exists (update) or new (append)
        existing_index = None
        for i, t in enumerate(course.transcripts):
            if t.get("id") == transcript.id:
                existing_index = i
                break

        transcript_dict = transcript.to_dict()

        if existing_index is not None:
            # Update existing
            course.transcripts[existing_index] = transcript_dict
        else:
            # Append new
            course.transcripts.append(transcript_dict)

        # Save course with updated transcripts
        owner_id = Collaborator.get_course_owner_id(transcript.course_id)
        self.project_store.save(owner_id, course)

        return transcript.id

    def get_transcript(self, course_id: str, transcript_id: str) -> Transcript:
        """Retrieve a specific transcript.

        Args:
            course_id: Course ID
            transcript_id: Transcript ID

        Returns:
            Transcript object

        Raises:
            FileNotFoundError: If course or transcript doesn't exist
        """
        course = self._load_course(course_id)

        for t_data in course.transcripts:
            if t_data.get("id") == transcript_id:
                return Transcript.from_dict(t_data)

        raise FileNotFoundError(f"Transcript {transcript_id} not found in course {course_id}")

    def list_transcripts(
        self,
        course_id: str,
        activity_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[Transcript]:
        """List transcripts with optional filtering.

        Args:
            course_id: Course ID
            activity_id: Optional activity filter
            user_id: Optional user filter

        Returns:
            List of Transcript objects matching filters

        Raises:
            FileNotFoundError: If course doesn't exist
        """
        course = self._load_course(course_id)

        transcripts = [Transcript.from_dict(t) for t in course.transcripts]

        # Apply filters
        if activity_id:
            transcripts = [t for t in transcripts if t.activity_id == activity_id]
        if user_id:
            transcripts = [t for t in transcripts if t.user_id == user_id]

        # Sort by started_at descending (most recent first)
        transcripts.sort(key=lambda t: t.started_at, reverse=True)

        return transcripts

    def delete_transcript(self, course_id: str, transcript_id: str) -> bool:
        """Delete a transcript.

        Args:
            course_id: Course ID
            transcript_id: Transcript ID

        Returns:
            True if deleted, False if not found

        Raises:
            FileNotFoundError: If course doesn't exist
        """
        from src.collab.models import Collaborator
        course = self._load_course(course_id)

        # Find and remove transcript
        original_len = len(course.transcripts)
        course.transcripts = [t for t in course.transcripts if t.get("id") != transcript_id]

        if len(course.transcripts) == original_len:
            return False  # Not found

        # Save course with updated transcripts
        owner_id = Collaborator.get_course_owner_id(course_id)
        self.project_store.save(owner_id, course)

        return True

    def get_session_stats(self, course_id: str, activity_id: str) -> dict:
        """Get statistics for coaching sessions on an activity.

        Args:
            course_id: Course ID
            activity_id: Activity ID

        Returns:
            Dict with stats:
                - total_sessions: Total number of sessions
                - completed_sessions: Sessions with ended_at
                - avg_duration: Average session duration in seconds
                - avg_turns: Average number of conversation turns
                - level_distribution: Count by performance level

        Raises:
            FileNotFoundError: If course doesn't exist
        """
        transcripts = self.list_transcripts(course_id, activity_id=activity_id)

        total_sessions = len(transcripts)
        completed_sessions = [t for t in transcripts if t.ended_at]
        completed_count = len(completed_sessions)

        # Calculate averages from completed sessions
        avg_duration = 0
        avg_turns = 0
        level_distribution = {
            "developing": 0,
            "proficient": 0,
            "exemplary": 0
        }

        if completed_count > 0:
            total_duration = 0
            total_turns = 0

            for transcript in completed_sessions:
                if transcript.evaluation:
                    total_duration += transcript.evaluation.time_spent
                    total_turns += transcript.evaluation.turns_count

                    # Count level distribution
                    level = transcript.evaluation.overall_level
                    if level in level_distribution:
                        level_distribution[level] += 1

            avg_duration = total_duration / completed_count if completed_count > 0 else 0
            avg_turns = total_turns / completed_count if completed_count > 0 else 0

        return {
            "total_sessions": total_sessions,
            "completed_sessions": completed_count,
            "avg_duration": int(avg_duration),
            "avg_turns": int(avg_turns),
            "level_distribution": level_distribution
        }
