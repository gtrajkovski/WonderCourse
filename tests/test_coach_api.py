"""Integration tests for coach API endpoints."""

import pytest
from unittest.mock import MagicMock, patch, Mock
import json

from src.core.models import ContentType, ActivityType
from src.coach import Message, SessionEvaluation


# Uses client fixture from conftest.py which includes authentication


@pytest.fixture
def setup_coach_activity(client):
    """Create a course with a coach activity for testing.

    Returns:
        dict: IDs for course, module, lesson, and activity
    """
    # Create course
    resp = client.post('/api/courses', json={
        "title": "Coach Test Course",
        "description": "Test course for coaching",
        "audience_level": "intermediate",
        "target_duration_minutes": 120
    })
    course_id = resp.get_json()["id"]

    # Create module
    resp = client.post(f'/api/courses/{course_id}/modules', json={
        "title": "Module 1",
        "description": "Test module"
    })
    module_id = resp.get_json()["id"]

    # Create lesson
    resp = client.post(f'/api/courses/{course_id}/modules/{module_id}/lessons', json={
        "title": "Lesson 1",
        "description": "Test lesson"
    })
    lesson_id = resp.get_json()["id"]

    # Create coach activity with content
    resp = client.post(f'/api/courses/{course_id}/lessons/{lesson_id}/activities', json={
        "title": "Coach Dialogue",
        "content_type": "coach",
        "activity_type": "coach_dialogue"
    })
    activity_id = resp.get_json()["id"]

    # Add coach content to activity
    coach_content = {
        "title": "Problem-Solving Coach",
        "learning_objectives": [
            "Apply problem-solving strategies",
            "Analyze edge cases"
        ],
        "scenario": "You're debugging a production issue",
        "tasks": [
            "Identify the root cause",
            "Propose a solution",
            "Consider edge cases"
        ],
        "conversation_starters": [
            {
                "starter_text": "What's your first step?",
                "purpose": "Assess diagnostic approach"
            }
        ],
        "sample_responses": [
            {
                "response_text": "I would check the logs",
                "evaluation_level": "meets",
                "feedback": "Good start"
            }
        ],
        "evaluation_criteria": [
            "Systematic approach",
            "Considers multiple perspectives",
            "Proposes testable solutions"
        ],
        "wrap_up": "Great work!",
        "reflection_prompts": [
            "What did you learn?",
            "What would you do differently?"
        ]
    }

    resp = client.put(
        f'/api/courses/{course_id}/activities/{activity_id}/content',
        json={"content": coach_content}
    )

    # Debug: Check if content was set
    if resp.status_code != 200:
        print(f"Failed to set content: {resp.status_code} - {resp.get_json()}")

    return {
        "course_id": course_id,
        "module_id": module_id,
        "lesson_id": lesson_id,
        "activity_id": activity_id
    }


def test_start_session(client, setup_coach_activity):
    """Test starting a new coaching session."""
    ids = setup_coach_activity

    resp = client.post(
        f'/api/courses/{ids["course_id"]}/activities/{ids["activity_id"]}/coach/start',
        json={"persona_type": "supportive"}
    )

    # Debug output
    if resp.status_code != 200:
        print(f"Error status: {resp.status_code}")
        print(f"Error response: {resp.get_json()}")

    assert resp.status_code == 200
    data = resp.get_json()

    assert "session_id" in data
    assert "persona" in data
    assert "dialogue_structure" in data
    assert "welcome_message" in data

    assert data["persona"]["type"] == "supportive"
    assert "scenario" in data["dialogue_structure"]
    assert "tasks" in data["dialogue_structure"]


def test_start_session_default_persona(client, setup_coach_activity):
    """Test starting session with default persona."""
    ids = setup_coach_activity

    resp = client.post(
        f'/api/courses/{ids["course_id"]}/activities/{ids["activity_id"]}/coach/start',
        json={}
    )

    assert resp.status_code == 200
    data = resp.get_json()

    assert data["persona"]["type"] == "supportive"  # Default


def test_start_session_activity_not_found(client, setup_coach_activity):
    """Test starting session for non-existent activity."""
    ids = setup_coach_activity

    resp = client.post(
        f'/api/courses/{ids["course_id"]}/activities/invalid_activity/coach/start',
        json={}
    )

    assert resp.status_code == 404


@patch('src.api.coach_bp.Anthropic')
def test_chat_non_streaming(mock_anthropic, client, setup_coach_activity):
    """Test non-streaming chat endpoint."""
    ids = setup_coach_activity

    # Start session (send empty JSON to set content-type properly)
    resp = client.post(
        f'/api/courses/{ids["course_id"]}/activities/{ids["activity_id"]}/coach/start',
        json={}
    )
    response_data = resp.get_json()
    assert resp.status_code == 200, f"Start session failed: {response_data}"
    session_id = response_data["session_id"]

    # Mock Claude response
    mock_client = Mock()
    mock_response = Mock()
    mock_response.content = [Mock(text="Great question! Let me help you think through this.")]
    mock_client.messages.create.return_value = mock_response
    mock_anthropic.return_value = mock_client

    # Send message
    resp = client.post(
        f'/api/courses/{ids["course_id"]}/activities/{ids["activity_id"]}/coach/chat',
        json={
            "session_id": session_id,
            "message": "I think I should check the logs first"
        }
    )

    assert resp.status_code == 200
    data = resp.get_json()

    assert "response" in data
    assert "Great question" in data["response"]


@patch('src.coach.evaluator.Anthropic')
@patch('src.api.coach_bp.Anthropic')
def test_chat_with_evaluation(mock_anthropic, mock_eval_anthropic, client, setup_coach_activity):
    """Test chat with evaluation enabled."""
    ids = setup_coach_activity

    # Start session
    resp = client.post(
        f'/api/courses/{ids["course_id"]}/activities/{ids["activity_id"]}/coach/start',
        json={}
    )
    session_id = resp.get_json()["session_id"]

    # Mock Claude response for chat
    mock_client = Mock()
    mock_chat_response = Mock()
    mock_chat_response.content = [Mock(text="Good thinking!")]
    mock_client.messages.create.return_value = mock_chat_response
    mock_anthropic.return_value = mock_client

    # Mock Claude response for evaluation (separate client for evaluator)
    mock_eval_client = Mock()
    mock_eval_response = Mock()
    mock_eval_response.content = [Mock(text="""
LEVEL: proficient
SCORE: 2

CRITERIA MET:
- Systematic approach

CRITERIA MISSING:
- Considers multiple perspectives

STRENGTHS:
- Clear starting point

AREAS FOR IMPROVEMENT:
- Think about edge cases

FEEDBACK:
Good start, but consider other perspectives.
""")]
    mock_eval_client.messages.create.return_value = mock_eval_response
    mock_eval_anthropic.return_value = mock_eval_client

    # Send message with evaluation
    resp = client.post(
        f'/api/courses/{ids["course_id"]}/activities/{ids["activity_id"]}/coach/chat',
        json={
            "session_id": session_id,
            "message": "Check the logs",
            "evaluate": True
        }
    )

    assert resp.status_code == 200
    data = resp.get_json()

    assert "response" in data
    assert "evaluation" in data
    assert data["evaluation"]["level"] == "proficient"
    assert data["evaluation"]["score"] == 2


def test_chat_session_not_found(client, setup_coach_activity):
    """Test chat with invalid session ID."""
    ids = setup_coach_activity

    resp = client.post(
        f'/api/courses/{ids["course_id"]}/activities/{ids["activity_id"]}/coach/chat',
        json={
            "session_id": "invalid_session",
            "message": "Hello"
        }
    )

    assert resp.status_code == 404


def test_chat_missing_fields(client, setup_coach_activity):
    """Test chat with missing required fields."""
    ids = setup_coach_activity

    resp = client.post(
        f'/api/courses/{ids["course_id"]}/activities/{ids["activity_id"]}/coach/chat',
        json={"session_id": "test"}  # Missing message
    )

    assert resp.status_code == 400


@patch('src.api.coach_bp.Anthropic')
def test_chat_streaming(mock_anthropic, client, setup_coach_activity):
    """Test streaming chat endpoint (SSE)."""
    ids = setup_coach_activity

    # Start session
    resp = client.post(
        f'/api/courses/{ids["course_id"]}/activities/{ids["activity_id"]}/coach/start',
        json={}
    )
    session_id = resp.get_json()["session_id"]

    # Mock Claude streaming response
    mock_client = Mock()
    mock_stream = Mock()
    mock_stream.__enter__ = Mock(return_value=mock_stream)
    mock_stream.__exit__ = Mock(return_value=False)
    mock_stream.text_stream = iter(["Hello ", "there! ", "Great ", "question."])

    mock_client.messages.stream.return_value = mock_stream
    mock_anthropic.return_value = mock_client

    # Send streaming request
    resp = client.post(
        f'/api/courses/{ids["course_id"]}/activities/{ids["activity_id"]}/coach/chat/stream',
        json={
            "session_id": session_id,
            "message": "What should I do first?"
        }
    )

    assert resp.status_code == 200
    assert resp.mimetype == 'text/event-stream'

    # Parse SSE response
    data = resp.data.decode('utf-8')
    assert 'event: chunk' in data
    assert 'event: done' in data
    assert '"type": "chunk"' in data


@patch('src.coach.evaluator.Anthropic')
@patch('src.api.coach_bp.Anthropic')
def test_end_session(mock_anthropic, mock_eval_anthropic, client, setup_coach_activity):
    """Test ending a session and saving transcript."""
    ids = setup_coach_activity

    # Start session
    resp = client.post(
        f'/api/courses/{ids["course_id"]}/activities/{ids["activity_id"]}/coach/start',
        json={}
    )
    session_id = resp.get_json()["session_id"]

    # Mock Claude for chat
    mock_client = Mock()
    mock_response = Mock()
    mock_response.content = [Mock(text="Good thinking!")]
    mock_client.messages.create.return_value = mock_response
    mock_anthropic.return_value = mock_client

    # Have a conversation
    client.post(
        f'/api/courses/{ids["course_id"]}/activities/{ids["activity_id"]}/coach/chat',
        json={
            "session_id": session_id,
            "message": "I'll check the logs"
        }
    )

    # Mock evaluation responses (for CoachEvaluator which uses its own Anthropic client)
    mock_eval_client = Mock()
    mock_eval_response = Mock()
    mock_eval_response.content = [Mock(text="""
OVERALL LEVEL: proficient

PROGRESS TRAJECTORY: improving

KEY INSIGHTS:
- Showed systematic thinking
- Considered multiple approaches

RECOMMENDATIONS:
- Practice edge case analysis
- Review debugging strategies
""")]

    mock_summary_response = Mock()
    mock_summary_response.content = [Mock(text="Student showed good progress in systematic problem-solving.")]

    mock_eval_client.messages.create.side_effect = [mock_eval_response, mock_summary_response]
    mock_eval_anthropic.return_value = mock_eval_client

    # End session
    resp = client.post(
        f'/api/courses/{ids["course_id"]}/activities/{ids["activity_id"]}/coach/end',
        json={"session_id": session_id}
    )

    assert resp.status_code == 200
    data = resp.get_json()

    assert "transcript_id" in data
    assert "evaluation" in data
    assert "summary" in data

    assert data["evaluation"]["overall_level"] == "proficient"
    assert data["evaluation"]["progress_trajectory"] == "improving"
    assert len(data["evaluation"]["key_insights"]) >= 2


def test_end_session_not_found(client, setup_coach_activity):
    """Test ending non-existent session."""
    ids = setup_coach_activity

    resp = client.post(
        f'/api/courses/{ids["course_id"]}/activities/{ids["activity_id"]}/coach/end',
        json={"session_id": "invalid_session"}
    )

    assert resp.status_code == 404


@patch('src.api.coach_bp.Anthropic')
def test_get_session_state(mock_anthropic, client, setup_coach_activity):
    """Test retrieving current session state."""
    ids = setup_coach_activity

    # Start session
    resp = client.post(
        f'/api/courses/{ids["course_id"]}/activities/{ids["activity_id"]}/coach/start',
        json={}
    )
    session_id = resp.get_json()["session_id"]

    # Mock Claude
    mock_client = Mock()
    mock_response = Mock()
    mock_response.content = [Mock(text="Good!")]
    mock_client.messages.create.return_value = mock_response
    mock_anthropic.return_value = mock_client

    # Have conversation
    client.post(
        f'/api/courses/{ids["course_id"]}/activities/{ids["activity_id"]}/coach/chat',
        json={
            "session_id": session_id,
            "message": "Check logs"
        }
    )

    # Get session state
    resp = client.get(
        f'/api/courses/{ids["course_id"]}/activities/{ids["activity_id"]}/coach/session/{session_id}'
    )

    assert resp.status_code == 200
    data = resp.get_json()

    assert data["session_id"] == session_id
    assert "messages" in data
    assert "coverage" in data
    assert len(data["messages"]) >= 2  # System + user + assistant


@patch('src.coach.evaluator.Anthropic')
@patch('src.api.coach_bp.Anthropic')
def test_continue_session(mock_anthropic, mock_eval_anthropic, client, setup_coach_activity):
    """Test continuing a previous session from transcript."""
    ids = setup_coach_activity

    # Start and end a session first
    resp = client.post(
        f'/api/courses/{ids["course_id"]}/activities/{ids["activity_id"]}/coach/start',
        json={}
    )
    original_session_id = resp.get_json()["session_id"]

    # Mock Claude for chat
    mock_client = Mock()
    mock_response = Mock()
    mock_response.content = [Mock(text="Good thinking!")]
    mock_client.messages.create.return_value = mock_response
    mock_anthropic.return_value = mock_client

    # Mock evaluation responses (for CoachEvaluator)
    mock_eval_client = Mock()
    mock_eval_response = Mock()
    mock_eval_response.content = [Mock(text="""
OVERALL LEVEL: developing
PROGRESS TRAJECTORY: consistent
KEY INSIGHTS:
- Basic understanding
RECOMMENDATIONS:
- Keep practicing
""")]

    mock_summary_response = Mock()
    mock_summary_response.content = [Mock(text="Good session.")]

    mock_eval_client.messages.create.side_effect = [
        mock_eval_response,  # Eval
        mock_summary_response  # Summary
    ]
    mock_eval_anthropic.return_value = mock_eval_client

    # Have conversation
    client.post(
        f'/api/courses/{ids["course_id"]}/activities/{ids["activity_id"]}/coach/chat',
        json={
            "session_id": original_session_id,
            "message": "Check logs"
        }
    )

    # End session
    resp = client.post(
        f'/api/courses/{ids["course_id"]}/activities/{ids["activity_id"]}/coach/end',
        json={"session_id": original_session_id}
    )
    transcript_id = resp.get_json()["transcript_id"]

    # Continue session
    resp = client.post(
        f'/api/courses/{ids["course_id"]}/activities/{ids["activity_id"]}/coach/continue',
        json={"transcript_id": transcript_id}
    )

    assert resp.status_code == 200
    data = resp.get_json()

    assert "session_id" in data
    assert data["session_id"] != original_session_id  # New session ID
    assert "messages" in data
    assert "coverage" in data
    assert len(data["messages"]) >= 2  # Restored messages


@patch('src.coach.evaluator.Anthropic')
@patch('src.api.coach_bp.Anthropic')
def test_list_transcripts(mock_anthropic, mock_eval_anthropic, client, setup_coach_activity):
    """Test listing transcripts for an activity."""
    ids = setup_coach_activity

    # Create and end a session
    resp = client.post(
        f'/api/courses/{ids["course_id"]}/activities/{ids["activity_id"]}/coach/start',
        json={}
    )
    session_id = resp.get_json()["session_id"]

    # Mock Claude for chat
    mock_client = Mock()
    mock_response = Mock()
    mock_response.content = [Mock(text="Good!")]
    mock_client.messages.create.return_value = mock_response
    mock_anthropic.return_value = mock_client

    # Mock evaluation responses (for CoachEvaluator)
    mock_eval_client = Mock()
    mock_eval_response = Mock()
    mock_eval_response.content = [Mock(text="""
OVERALL LEVEL: proficient
PROGRESS TRAJECTORY: improving
KEY INSIGHTS:
- Good progress
RECOMMENDATIONS:
- Keep going
""")]

    mock_summary_response = Mock()
    mock_summary_response.content = [Mock(text="Great session!")]

    mock_eval_client.messages.create.side_effect = [
        mock_eval_response,
        mock_summary_response
    ]
    mock_eval_anthropic.return_value = mock_eval_client

    # Chat
    client.post(
        f'/api/courses/{ids["course_id"]}/activities/{ids["activity_id"]}/coach/chat',
        json={
            "session_id": session_id,
            "message": "Test message"
        }
    )

    # End session
    client.post(
        f'/api/courses/{ids["course_id"]}/activities/{ids["activity_id"]}/coach/end',
        json={"session_id": session_id}
    )

    # List transcripts
    resp = client.get(
        f'/api/courses/{ids["course_id"]}/activities/{ids["activity_id"]}/transcripts'
    )

    assert resp.status_code == 200
    data = resp.get_json()

    assert "transcripts" in data
    assert len(data["transcripts"]) >= 1


@patch('src.coach.evaluator.Anthropic')
@patch('src.api.coach_bp.Anthropic')
def test_get_specific_transcript(mock_anthropic, mock_eval_anthropic, client, setup_coach_activity):
    """Test retrieving a specific transcript."""
    ids = setup_coach_activity

    # Create and end session
    resp = client.post(
        f'/api/courses/{ids["course_id"]}/activities/{ids["activity_id"]}/coach/start',
        json={}
    )
    session_id = resp.get_json()["session_id"]

    # Mock evaluation responses (for CoachEvaluator)
    mock_eval_client = Mock()
    mock_eval_response = Mock()
    mock_eval_response.content = [Mock(text="""
OVERALL LEVEL: developing
PROGRESS TRAJECTORY: consistent
KEY INSIGHTS:
- Progress made
RECOMMENDATIONS:
- Continue
""")]

    mock_summary_response = Mock()
    mock_summary_response.content = [Mock(text="Session complete.")]

    mock_eval_client.messages.create.side_effect = [
        mock_eval_response,
        mock_summary_response
    ]
    mock_eval_anthropic.return_value = mock_eval_client

    # End session
    resp = client.post(
        f'/api/courses/{ids["course_id"]}/activities/{ids["activity_id"]}/coach/end',
        json={"session_id": session_id}
    )
    transcript_id = resp.get_json()["transcript_id"]

    # Get specific transcript
    resp = client.get(
        f'/api/courses/{ids["course_id"]}/transcripts/{transcript_id}'
    )

    assert resp.status_code == 200
    data = resp.get_json()

    assert "transcript" in data
    assert data["transcript"]["id"] == transcript_id
    assert "evaluation" in data["transcript"]
    assert "summary" in data["transcript"]


def test_get_transcript_not_found(client, setup_coach_activity):
    """Test getting non-existent transcript."""
    ids = setup_coach_activity

    resp = client.get(
        f'/api/courses/{ids["course_id"]}/transcripts/invalid_transcript'
    )

    assert resp.status_code == 404


def test_authentication_required(client, setup_coach_activity):
    """Test that endpoints require authentication."""
    ids = setup_coach_activity

    # Logout
    client.post('/api/auth/logout')

    # Try to start session without auth
    resp = client.post(
        f'/api/courses/{ids["course_id"]}/activities/{ids["activity_id"]}/coach/start',
        json={}
    )

    assert resp.status_code == 401
