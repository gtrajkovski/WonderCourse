"""Coach API endpoints for interactive coaching sessions.

Provides endpoints for starting coaching sessions, chatting with the coach,
streaming responses, evaluating sessions, and managing transcripts.
"""

from flask import Blueprint, request, jsonify, Response, stream_with_context
from flask_login import login_required, current_user
from datetime import datetime, timezone
import json
import uuid

from src.core.project_store import ProjectStore
from src.coach import (
    ConversationManager,
    CoachEvaluator,
    TranscriptStore,
    Transcript,
    GuardrailEngine,
    PersonaBuilder
)
from anthropic import Anthropic
from src.config import Config


# Create Blueprint
coach_bp = Blueprint('coach', __name__)

# Module-level instances
_project_store = None
_transcript_store = None
_active_sessions = {}  # session_id -> ConversationManager


def init_coach_bp(project_store: ProjectStore):
    """Initialize the coach blueprint with dependencies.

    Args:
        project_store: ProjectStore instance for persistence

    Returns:
        Blueprint: Configured coach blueprint
    """
    global _project_store, _transcript_store
    _project_store = project_store
    _transcript_store = TranscriptStore(project_store)
    return coach_bp


@coach_bp.route('/api/courses/<course_id>/activities/<activity_id>/coach/start', methods=['POST'])
@login_required
def start_session(course_id: str, activity_id: str):
    """Start a new coaching session.

    Request JSON (optional):
        {
            "persona_type": str,  # Optional: supportive, challenging, formal, friendly
            "use_socratic": bool  # Optional: Enable Socratic method
        }

    Returns:
        {
            "session_id": str,
            "persona": dict,
            "dialogue_structure": dict,
            "welcome_message": str
        }

    Status Codes:
        200: Session started
        404: Course or activity not found
        500: Error starting session
    """
    try:
        # Load course and find activity
        course = _load_course(course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404
        activity = _find_activity(course, activity_id)

        if not activity:
            return jsonify({"error": "Activity not found"}), 404

        # Get coach content from activity
        if not activity.content or not isinstance(activity.content, dict):
            return jsonify({"error": "Activity has no coach content"}), 400

        coach_content = activity.content

        # Get persona preferences from request
        data = request.json or {}
        persona_type = data.get("persona_type", "supportive")
        use_socratic = data.get("use_socratic", True)

        # Build persona from CoachPersona dataclass
        from src.coach.persona import CoachPersona

        persona = CoachPersona(
            name=coach_content.get("title", "Coach"),
            personality=persona_type,
            style=_get_personality_style(persona_type),
            socratic=use_socratic,
            off_topic_handling="moderate"
        )

        # Create conversation manager
        session_id = f"session_{uuid.uuid4().hex[:12]}"
        manager = ConversationManager(session_id=session_id)

        # Add system message with persona
        system_message = _build_system_message(persona, coach_content)
        manager.add_message("system", system_message)

        # Store session
        _active_sessions[session_id] = manager

        # Generate welcome message
        welcome_message = _generate_welcome_message(
            persona,
            coach_content.get("scenario", ""),
            coach_content.get("tasks", [])
        )

        return jsonify({
            "session_id": session_id,
            "persona": {
                "type": persona_type,
                "name": persona.name,
                "style": persona.style
            },
            "dialogue_structure": {
                "scenario": coach_content.get("scenario", ""),
                "tasks": coach_content.get("tasks", []),
                "conversation_starters": coach_content.get("conversation_starters", [])
            },
            "welcome_message": welcome_message
        }), 200

    except FileNotFoundError:
        return jsonify({"error": "Course not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@coach_bp.route('/api/courses/<course_id>/activities/<activity_id>/coach/chat', methods=['POST'])
@login_required
def chat(course_id: str, activity_id: str):
    """Send a message and get coach response (non-streaming).

    Request JSON:
        {
            "session_id": str,
            "message": str
        }

    Returns:
        {
            "response": str,
            "evaluation": dict  # Optional evaluation result
        }

    Status Codes:
        200: Response generated
        400: Invalid request
        404: Session not found
        500: Error generating response
    """
    data = request.json

    if not data or 'session_id' not in data or 'message' not in data:
        return jsonify({"error": "Missing required fields: session_id, message"}), 400

    session_id = data['session_id']
    user_message = data['message']

    if session_id not in _active_sessions:
        return jsonify({"error": "Session not found"}), 404

    try:
        # Get conversation manager
        manager = _active_sessions[session_id]

        # Add user message
        manager.add_message("user", user_message)

        # Get context for Claude
        context = manager.get_context()

        # Generate response
        client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=Config.MODEL,
            max_tokens=1024,
            messages=context
        )

        assistant_response = response.content[0].text

        # Add assistant response to conversation
        manager.add_message("assistant", assistant_response)

        # Optional: Evaluate response
        evaluation = None
        if data.get("evaluate", False):
            evaluation = _evaluate_response(course_id, activity_id, user_message, context)

        result = {
            "response": assistant_response
        }

        if evaluation:
            result["evaluation"] = evaluation.to_dict()

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@coach_bp.route('/api/courses/<course_id>/activities/<activity_id>/coach/chat/stream', methods=['POST'])
@login_required
def chat_stream(course_id: str, activity_id: str):
    """Send a message and stream coach response (SSE).

    Request JSON:
        {
            "session_id": str,
            "message": str,
            "evaluate": bool  # Optional: evaluate after response
        }

    Returns:
        Server-Sent Events stream with:
        - event: chunk, data: {"type": "chunk", "text": str}
        - event: evaluation, data: {"type": "evaluation", "data": dict}
        - event: done, data: {"type": "done"}

    Status Codes:
        200: Stream started
        400: Invalid request
        404: Session not found
        500: Error generating response
    """
    data = request.json

    if not data or 'session_id' not in data or 'message' not in data:
        return jsonify({"error": "Missing required fields: session_id, message"}), 400

    session_id = data['session_id']
    user_message = data['message']
    should_evaluate = data.get("evaluate", False)

    if session_id not in _active_sessions:
        return jsonify({"error": "Session not found"}), 404

    def generate():
        """Generator function for SSE stream."""
        try:
            # Get conversation manager
            manager = _active_sessions[session_id]

            # Add user message
            manager.add_message("user", user_message)

            # Get context for Claude
            context = manager.get_context()

            # Stream response
            client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)
            full_response = ""

            with client.messages.stream(
                model=Config.MODEL,
                max_tokens=1024,
                messages=context
            ) as stream:
                for text in stream.text_stream:
                    full_response += text
                    event_data = json.dumps({'type': 'chunk', 'text': text})
                    yield f"event: chunk\ndata: {event_data}\n\n"

            # Add full response to conversation
            manager.add_message("assistant", full_response)

            # Evaluate if requested
            if should_evaluate:
                evaluation = _evaluate_response(
                    course_id,
                    activity_id,
                    user_message,
                    context
                )
                eval_data = json.dumps({
                    'type': 'evaluation',
                    'data': evaluation.to_dict()
                })
                yield f"event: evaluation\ndata: {eval_data}\n\n"

            # Send done event
            yield f"event: done\ndata: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            error_data = json.dumps({'type': 'error', 'error': str(e)})
            yield f"event: error\ndata: {error_data}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


@coach_bp.route('/api/courses/<course_id>/activities/<activity_id>/coach/end', methods=['POST'])
@login_required
def end_session(course_id: str, activity_id: str):
    """End a coaching session and save transcript.

    Request JSON:
        {
            "session_id": str
        }

    Returns:
        {
            "transcript_id": str,
            "evaluation": dict,
            "summary": str
        }

    Status Codes:
        200: Session ended and saved
        400: Invalid request
        404: Session not found
        500: Error ending session
    """
    data = request.json

    if not data or 'session_id' not in data:
        return jsonify({"error": "Missing required field: session_id"}), 400

    session_id = data['session_id']

    if session_id not in _active_sessions:
        return jsonify({"error": "Session not found"}), 404

    try:
        # Get conversation manager
        manager = _active_sessions[session_id]

        # Get course and activity
        course = _load_course(course_id)
        activity = _find_activity(course, activity_id)

        if not activity or not activity.content:
            return jsonify({"error": "Activity or content not found"}), 404

        # Create evaluator
        evaluation_criteria = activity.content.get("evaluation_criteria", [])
        evaluator = CoachEvaluator(evaluation_criteria)

        # Get transcript
        messages = manager.get_full_transcript()

        # Get session timing
        started_at = messages[0].timestamp if messages else datetime.now(timezone.utc).isoformat()
        ended_at = datetime.now(timezone.utc).isoformat()

        # Evaluate session
        session_evaluation = evaluator.evaluate_session(messages, started_at, ended_at)

        # Generate summary
        summary = evaluator.generate_summary(messages, session_evaluation)

        # Create transcript
        transcript = Transcript(
            session_id=session_id,
            activity_id=activity_id,
            course_id=course_id,
            user_id=str(current_user.id),
            messages=messages,
            started_at=started_at,
            ended_at=ended_at,
            evaluation=session_evaluation,
            summary=summary
        )

        # Save transcript
        transcript_id = _transcript_store.save_transcript(transcript)

        # Clean up session
        del _active_sessions[session_id]

        return jsonify({
            "transcript_id": transcript_id,
            "evaluation": session_evaluation.to_dict(),
            "summary": summary
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@coach_bp.route('/api/courses/<course_id>/activities/<activity_id>/coach/session/<session_id>', methods=['GET'])
@login_required
def get_session(course_id: str, activity_id: str, session_id: str):
    """Get current session state.

    Returns:
        {
            "session_id": str,
            "messages": list,
            "coverage": dict  # Topic coverage from guardrails
        }

    Status Codes:
        200: Session found
        404: Session not found
    """
    if session_id not in _active_sessions:
        return jsonify({"error": "Session not found"}), 404

    try:
        manager = _active_sessions[session_id]
        messages = manager.get_full_transcript()

        # Get course and activity for guardrails
        course = _load_course(course_id)
        activity = _find_activity(course, activity_id)

        coverage = {}
        if activity and activity.content:
            guardrails = GuardrailEngine(
                tasks=activity.content.get("tasks", []),
                evaluation_criteria=activity.content.get("evaluation_criteria", [])
            )
            coverage_result = guardrails.check_coverage(messages)
            coverage = coverage_result.to_dict()

        return jsonify({
            "session_id": session_id,
            "messages": [msg.to_dict() for msg in messages],
            "coverage": coverage
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@coach_bp.route('/api/courses/<course_id>/activities/<activity_id>/coach/continue', methods=['POST'])
@login_required
def continue_session(course_id: str, activity_id: str):
    """Continue a previous session from transcript.

    Request JSON:
        {
            "transcript_id": str
        }

    Returns:
        {
            "session_id": str,
            "messages": list,
            "coverage": dict
        }

    Status Codes:
        200: Session restored
        400: Invalid request
        404: Transcript not found
        500: Error restoring session
    """
    data = request.json

    if not data or 'transcript_id' not in data:
        return jsonify({"error": "Missing required field: transcript_id"}), 400

    transcript_id = data['transcript_id']

    try:
        # Load transcript
        transcript = _transcript_store.get_transcript(course_id, transcript_id)

        # Create new session
        new_session_id = f"session_{uuid.uuid4().hex[:12]}"
        manager = ConversationManager(session_id=new_session_id)

        # Restore messages
        for msg in transcript.messages:
            manager.add_message(msg.role, msg.content)

        # Store session
        _active_sessions[new_session_id] = manager

        # Get coverage
        course = _load_course(course_id)
        activity = _find_activity(course, activity_id)

        coverage = {}
        if activity and activity.content:
            guardrails = GuardrailEngine(
                tasks=activity.content.get("tasks", []),
                evaluation_criteria=activity.content.get("evaluation_criteria", [])
            )
            coverage_result = guardrails.check_coverage(transcript.messages)
            coverage = coverage_result.to_dict()

        return jsonify({
            "session_id": new_session_id,
            "messages": [msg.to_dict() for msg in transcript.messages],
            "coverage": coverage
        }), 200

    except FileNotFoundError:
        return jsonify({"error": "Transcript not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@coach_bp.route('/api/courses/<course_id>/activities/<activity_id>/transcripts', methods=['GET'])
@login_required
def list_transcripts(course_id: str, activity_id: str):
    """List all transcripts for an activity.

    Query params:
        user_id: Optional filter by user

    Returns:
        {
            "transcripts": list
        }

    Status Codes:
        200: Transcripts found
        404: Course not found
        500: Error listing transcripts
    """
    try:
        user_id = request.args.get('user_id')
        transcripts = _transcript_store.list_transcripts(
            course_id,
            activity_id=activity_id,
            user_id=user_id
        )

        return jsonify({
            "transcripts": [t.to_dict() for t in transcripts]
        }), 200

    except FileNotFoundError:
        return jsonify({"error": "Course not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@coach_bp.route('/api/courses/<course_id>/transcripts/<transcript_id>', methods=['GET'])
@login_required
def get_transcript(course_id: str, transcript_id: str):
    """Get a specific transcript.

    Returns:
        {
            "transcript": dict
        }

    Status Codes:
        200: Transcript found
        404: Transcript not found
        500: Error retrieving transcript
    """
    try:
        transcript = _transcript_store.get_transcript(course_id, transcript_id)

        return jsonify({
            "transcript": transcript.to_dict()
        }), 200

    except FileNotFoundError:
        return jsonify({"error": "Transcript not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Helper functions

def _load_course(course_id: str):
    """Load course by owner ID."""
    from src.collab.models import Collaborator
    owner_id = Collaborator.get_course_owner_id(course_id)
    if not owner_id:
        return None
    return _project_store.load(owner_id, course_id)


def _find_activity(course, activity_id: str):
    """Find activity by ID in course structure."""
    for module in course.modules:
        for lesson in module.lessons:
            for activity in lesson.activities:
                if activity.id == activity_id:
                    return activity
    return None


def _get_personality_style(personality: str) -> str:
    """Get style description for personality type."""
    styles = {
        "supportive": "encouraging and patient",
        "challenging": "direct and thought-provoking",
        "formal": "professional and structured",
        "friendly": "warm and conversational"
    }
    return styles.get(personality, "encouraging and patient")


def _build_system_message(persona, coach_content: dict) -> str:
    """Build system message for coaching session."""
    from src.coach.persona import PersonaBuilder

    # Get personality prompt
    personality_prompt = PersonaBuilder.get_personality_prompt(persona)

    # Add coaching context
    system_message = f"""{personality_prompt}

**Coaching Context:**

Scenario: {coach_content.get('scenario', '')}

Learning Objectives:
{chr(10).join(f"- {obj}" for obj in coach_content.get('learning_objectives', []))}

Tasks for this session:
{chr(10).join(f"- {task}" for task in coach_content.get('tasks', []))}

Evaluation Criteria:
{chr(10).join(f"- {criterion}" for criterion in coach_content.get('evaluation_criteria', []))}

**Your Role:**
Guide the student through the scenario using the tasks and evaluation criteria.
Adapt your approach based on the student's responses.
Stay focused on the learning objectives."""

    return system_message


def _generate_welcome_message(persona, scenario: str, tasks: list) -> str:
    """Generate welcome message based on persona and scenario."""
    # Simple greeting based on personality
    greetings = {
        "supportive": "Hello! I'm excited to work with you today.",
        "challenging": "Welcome. Let's dive in and challenge ourselves.",
        "formal": "Good day. We have important work ahead.",
        "friendly": "Hey there! Ready to explore together?"
    }
    greeting = greetings.get(persona.personality, "Hello!")

    message = f"{greeting}\n\n"
    message += f"Today we'll be working through: {scenario}\n\n"

    if tasks:
        message += "Here's what we'll focus on:\n"
        for i, task in enumerate(tasks, 1):
            message += f"{i}. {task}\n"
        message += "\n"

    message += "Let's get started! What are your initial thoughts?"

    return message


def _evaluate_response(
    course_id: str,
    activity_id: str,
    student_response: str,
    conversation_context: list
):
    """Evaluate a student response."""
    try:
        # Get activity content
        course = _load_course(course_id)
        activity = _find_activity(course, activity_id)

        if not activity or not activity.content:
            return None

        # Create evaluator
        evaluation_criteria = activity.content.get("evaluation_criteria", [])
        evaluator = CoachEvaluator(evaluation_criteria)

        # Build context
        context = {
            "scenario": activity.content.get("scenario", ""),
            "tasks": activity.content.get("tasks", []),
            "conversation_history": conversation_context
        }

        # Evaluate
        return evaluator.evaluate_response(student_response, context)

    except Exception:
        return None
