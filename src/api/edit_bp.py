"""Edit API endpoints for AI-powered text suggestions.

Provides endpoints for generating suggestions for selected text with multiple
action types (improve, expand, simplify, etc.) and diff visualization.
Also provides undo/redo history, version management, autocomplete, and Bloom's
taxonomy analysis.
"""

from flask import Blueprint, request, jsonify, Response, stream_with_context, session
from flask_login import login_required, current_user
import json
import uuid

from src.editing.suggestions import SuggestionEngine


def _get_session_id():
    """Get or create a unique session identifier.

    Flask's SecureCookieSession doesn't have a .sid attribute,
    so we generate and store our own session ID.
    """
    if '_edit_session_id' not in session:
        session['_edit_session_id'] = str(uuid.uuid4())
    return session['_edit_session_id']
from src.editing.history import get_session_manager, EditCommand
from src.editing.version_store import VersionStore
from src.editing.autocomplete import AutocompleteEngine
from src.editing.bloom_analyzer import BloomAnalyzer
from src.core.models import BloomLevel


# Create Blueprint
edit_bp = Blueprint('edit', __name__)

# Module-level instances
_suggestion_engine = None
_version_store = None
_autocomplete_engine = None
_bloom_analyzer = None


def init_edit_bp(project_store=None):
    """Initialize the edit blueprint with dependencies.

    Args:
        project_store: ProjectStore instance for version persistence

    Returns:
        Blueprint: Configured edit blueprint
    """
    global _suggestion_engine, _version_store, _autocomplete_engine, _bloom_analyzer
    _suggestion_engine = SuggestionEngine()
    _autocomplete_engine = AutocompleteEngine()
    _bloom_analyzer = BloomAnalyzer()
    if project_store:
        _version_store = VersionStore(project_store)
    return edit_bp


@edit_bp.route('/suggest', methods=['POST'])
@login_required
def suggest():
    """Generate AI suggestion for selected text.

    Request JSON:
        {
            "text": str,         # Text to improve/modify
            "action": str,       # Action type (improve, expand, simplify, etc.)
            "context": dict      # Optional context (learning_outcomes, bloom_level, etc.)
        }

    Returns:
        {
            "original": str,
            "suggestion": str,
            "action": str,
            "diff": {
                "unified_diff": str,
                "html_diff": str,
                "changes": list
            },
            "explanation": str
        }

    Status Codes:
        200: Suggestion generated successfully
        400: Invalid request (missing text/action, invalid action type)
        500: AI generation error
    """
    data = request.json

    # Validate required fields
    if not data or 'text' not in data or 'action' not in data:
        return jsonify({
            'error': 'Missing required fields: text, action'
        }), 400

    text = data['text']
    action = data['action']
    context = data.get('context', {})

    # Validate action type
    valid_actions = [
        'improve', 'expand', 'simplify', 'rewrite', 'fix_grammar',
        'make_academic', 'make_conversational', 'summarize',
        'add_examples', 'custom'
    ]
    if action not in valid_actions:
        return jsonify({
            'error': f'Invalid action type: {action}',
            'valid_actions': valid_actions
        }), 400

    # Custom action requires prompt in context
    if action == 'custom' and 'prompt' not in context:
        return jsonify({
            'error': 'Custom action requires "prompt" in context'
        }), 400

    try:
        # Generate suggestion
        suggestion = _suggestion_engine.suggest(text, action, context)

        # Convert to response format
        return jsonify({
            'original': suggestion.original,
            'suggestion': suggestion.suggestion,
            'action': suggestion.action,
            'diff': {
                'unified_diff': suggestion.diff.unified_diff,
                'html_diff': suggestion.diff.html_diff,
                'changes': suggestion.diff.changes
            },
            'explanation': suggestion.explanation
        })

    except Exception as e:
        return jsonify({
            'error': f'Failed to generate suggestion: {str(e)}'
        }), 500


@edit_bp.route('/suggest/stream', methods=['POST'])
@login_required
def suggest_stream():
    """Stream AI suggestion generation in real-time.

    Request JSON:
        {
            "text": str,         # Text to improve/modify
            "action": str,       # Action type
            "context": dict      # Optional context
        }

    Returns:
        Server-Sent Events stream with:
        - event: chunk, data: {"type": "chunk", "text": str}
        - event: done, data: {"type": "done"}

    Status Codes:
        200: Stream started
        400: Invalid request
        500: AI generation error
    """
    data = request.json

    # Validate required fields
    if not data or 'text' not in data or 'action' not in data:
        return jsonify({
            'error': 'Missing required fields: text, action'
        }), 400

    text = data['text']
    action = data['action']
    context = data.get('context', {})

    # Validate action type
    valid_actions = [
        'improve', 'expand', 'simplify', 'rewrite', 'fix_grammar',
        'make_academic', 'make_conversational', 'summarize',
        'add_examples', 'custom'
    ]
    if action not in valid_actions:
        return jsonify({
            'error': f'Invalid action type: {action}',
            'valid_actions': valid_actions
        }), 400

    # Custom action requires prompt in context
    if action == 'custom' and 'prompt' not in context:
        return jsonify({
            'error': 'Custom action requires "prompt" in context'
        }), 400

    def generate():
        """Generator function for SSE stream."""
        try:
            # Stream suggestion chunks
            for chunk in _suggestion_engine.stream_suggest(text, action, context):
                event_data = json.dumps({'type': 'chunk', 'text': chunk})
                yield f"event: chunk\ndata: {event_data}\n\n"

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


@edit_bp.route('/diff', methods=['POST'])
@login_required
def generate_diff():
    """Generate diff between original and modified text.

    Request JSON:
        {
            "original": str,
            "modified": str
        }

    Returns:
        {
            "unified_diff": str,
            "html_diff": str,
            "changes": list
        }

    Status Codes:
        200: Diff generated successfully
        400: Missing required fields
    """
    data = request.json

    # Validate required fields
    if not data or 'original' not in data or 'modified' not in data:
        return jsonify({
            'error': 'Missing required fields: original, modified'
        }), 400

    original = data['original']
    modified = data['modified']

    # Generate diff
    diff_result = _suggestion_engine.diff_generator.generate_diff(original, modified)

    return jsonify({
        'unified_diff': diff_result.unified_diff,
        'html_diff': diff_result.html_diff,
        'changes': diff_result.changes
    })


@edit_bp.route('/actions', methods=['GET'])
@login_required
def get_actions():
    """Get list of available action types with descriptions.

    Returns:
        [
            {
                "action": str,
                "description": str
            },
            ...
        ]

    Status Codes:
        200: Actions list returned
    """
    actions = _suggestion_engine.get_available_actions()
    return jsonify(actions)


@edit_bp.route('/autocomplete', methods=['POST'])
@login_required
def autocomplete():
    """Generate context-aware autocomplete suggestion.

    Request JSON:
        {
            "text": str,         # Partial text to complete
            "context": dict      # Optional context (learning_outcomes, activity_title, etc.)
        }

    Returns:
        {
            "suggestion": str,      # Ghost text to display
            "confidence": float,    # Confidence score (0.0 to 1.0)
            "full_text": str       # Original + suggestion
        }

    Status Codes:
        200: Autocomplete generated successfully
        400: Missing text field
        500: AI generation error
    """
    data = request.json

    # Validate required fields
    if not data or 'text' not in data:
        return jsonify({
            'error': 'Missing required field: text'
        }), 400

    text = data['text']
    context = data.get('context', {})

    try:
        # Generate autocomplete
        result = _autocomplete_engine.complete(text, context)

        return jsonify({
            'suggestion': result.suggestion,
            'confidence': result.confidence,
            'full_text': result.full_text
        })

    except RuntimeError as e:
        # Engine not initialized (missing API key)
        return jsonify({
            'error': str(e)
        }), 503

    except Exception as e:
        return jsonify({
            'error': f'Failed to generate autocomplete: {str(e)}'
        }), 500


@edit_bp.route('/bloom/analyze', methods=['POST'])
@login_required
def bloom_analyze():
    """Analyze text for Bloom's Taxonomy cognitive level.

    Request JSON:
        {
            "text": str         # Text to analyze
        }

    Returns:
        {
            "detected_level": str,     # Bloom level (remember, understand, etc.)
            "confidence": float,       # Confidence score (0.0 to 1.0)
            "evidence": list,          # List of verbs found
            "verb_counts": dict        # Count of verbs per level
        }

    Status Codes:
        200: Analysis complete
        400: Missing text field
    """
    data = request.json

    # Validate required fields
    if not data or 'text' not in data:
        return jsonify({
            'error': 'Missing required field: text'
        }), 400

    text = data['text']

    # Analyze text
    analysis = _bloom_analyzer.analyze(text)

    return jsonify({
        'detected_level': analysis.detected_level.value,
        'confidence': analysis.confidence,
        'evidence': analysis.evidence,
        'verb_counts': analysis.verb_counts
    })


@edit_bp.route('/bloom/check', methods=['POST'])
@login_required
def bloom_check():
    """Check if text aligns with target Bloom's level.

    Request JSON:
        {
            "text": str,            # Text to analyze
            "target_level": str     # Target Bloom level (remember, understand, etc.)
        }

    Returns:
        {
            "aligned": bool,           # Whether content aligns with target
            "current_level": str,      # Detected cognitive level
            "target_level": str,       # Target cognitive level
            "gap": int,                # Level difference (negative if below target)
            "suggestions": list        # Actionable suggestions for adjustment
        }

    Status Codes:
        200: Alignment check complete
        400: Missing required fields or invalid target level
    """
    data = request.json

    # Validate required fields
    if not data or 'text' not in data or 'target_level' not in data:
        return jsonify({
            'error': 'Missing required fields: text, target_level'
        }), 400

    text = data['text']
    target_level_str = data['target_level']

    # Parse target level
    try:
        target_level = BloomLevel(target_level_str.lower())
    except ValueError:
        valid_levels = [level.value for level in BloomLevel]
        return jsonify({
            'error': f'Invalid target_level: {target_level_str}',
            'valid_levels': valid_levels
        }), 400

    # Check alignment
    result = _bloom_analyzer.check_alignment(text, target_level)

    return jsonify({
        'aligned': result.aligned,
        'current_level': result.current_level.value,
        'target_level': result.target_level.value,
        'gap': result.gap,
        'suggestions': result.suggestions
    })


@edit_bp.route('/courses/<course_id>/activities/<activity_id>/bloom', methods=['GET'])
@login_required
def activity_bloom_check(course_id, activity_id):
    """Analyze activity content against target Bloom level.

    This endpoint retrieves the activity, extracts its content and target
    Bloom level, and performs alignment checking.

    Args:
        course_id: Course ID
        activity_id: Activity ID

    Returns:
        {
            "activity_id": str,
            "activity_title": str,
            "target_level": str,
            "analysis": {
                "aligned": bool,
                "current_level": str,
                "target_level": str,
                "gap": int,
                "suggestions": list
            }
        }

    Status Codes:
        200: Analysis complete
        404: Course or activity not found
        400: Activity has no content or target Bloom level
    """
    # Import here to avoid circular imports
    from src.core.project_store import ProjectStore
    from src.collab.models import Collaborator

    try:
        # Load course
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({'error': f'Course not found: {course_id}'}), 404

        project_store = ProjectStore()
        course = project_store.load(owner_id, course_id)

        if not course:
            return jsonify({
                'error': f'Course not found: {course_id}'
            }), 404

        # Find activity
        activity = None
        for module in course.modules:
            for lesson in module.lessons:
                for act in lesson.activities:
                    if act.id == activity_id:
                        activity = act
                        break
                if activity:
                    break
            if activity:
                break

        if not activity:
            return jsonify({
                'error': f'Activity not found: {activity_id}'
            }), 404

        # Check if activity has content
        if not activity.content or not activity.content.strip():
            return jsonify({
                'error': 'Activity has no content to analyze'
            }), 400

        # Get target Bloom level from metadata (or use default APPLY)
        target_level = BloomLevel.APPLY  # Default
        if activity.metadata and 'bloom_level' in activity.metadata:
            try:
                target_level = BloomLevel(activity.metadata['bloom_level'])
            except (ValueError, KeyError):
                pass

        # Analyze content
        result = _bloom_analyzer.check_alignment(activity.content, target_level)

        return jsonify({
            'activity_id': activity.id,
            'activity_title': activity.title,
            'target_level': target_level.value,
            'analysis': {
                'aligned': result.aligned,
                'current_level': result.current_level.value,
                'target_level': result.target_level.value,
                'gap': result.gap,
                'suggestions': result.suggestions
            }
        })

    except Exception as e:
        return jsonify({
            'error': f'Failed to analyze activity: {str(e)}'
        }), 500


# ============================================================================
# History Endpoints (Undo/Redo)
# ============================================================================

@edit_bp.route('/history/push', methods=['POST'])
@login_required
def push_history():
    """Push edit command to undo stack.

    Request JSON:
        {
            "activity_id": str,
            "command": {
                "id": str,
                "action": str,
                "before": str,
                "after": str,
                "timestamp": str,
                "metadata": dict
            }
        }

    Returns:
        {
            "pushed": true,
            "can_undo": bool,
            "can_redo": bool
        }

    Status Codes:
        200: Command pushed successfully
        400: Missing required fields
    """
    data = request.json

    # Validate required fields
    if not data or 'activity_id' not in data or 'command' not in data:
        return jsonify({
            'error': 'Missing required fields: activity_id, command'
        }), 400

    activity_id = data['activity_id']
    command_data = data['command']

    # Get session history manager
    manager = get_session_manager()
    history = manager.get_history(_get_session_id(), activity_id)

    # Create EditCommand from data
    command = EditCommand.from_dict(command_data)

    # Push to history
    history.push(command)

    return jsonify({
        'pushed': True,
        'can_undo': history.can_undo(),
        'can_redo': history.can_redo()
    })


@edit_bp.route('/history/undo', methods=['POST'])
@login_required
def undo_history():
    """Undo last edit command.

    Request JSON:
        {
            "activity_id": str
        }

    Returns:
        {
            "command": EditCommand,
            "content_before": str
        }

    Status Codes:
        200: Command undone successfully
        400: Missing required fields
        404: Nothing to undo
    """
    data = request.json

    # Validate required fields
    if not data or 'activity_id' not in data:
        return jsonify({
            'error': 'Missing required field: activity_id'
        }), 400

    activity_id = data['activity_id']

    # Get session history manager
    manager = get_session_manager()
    history = manager.get_history(_get_session_id(), activity_id)

    # Undo last command
    command = history.undo()

    if not command:
        return jsonify({
            'error': 'Nothing to undo'
        }), 404

    return jsonify({
        'command': command.to_dict(),
        'content_before': command.before,
        'can_undo': history.can_undo(),
        'can_redo': history.can_redo()
    })


@edit_bp.route('/history/redo', methods=['POST'])
@login_required
def redo_history():
    """Redo last undone edit command.

    Request JSON:
        {
            "activity_id": str
        }

    Returns:
        {
            "command": EditCommand,
            "content_after": str
        }

    Status Codes:
        200: Command redone successfully
        400: Missing required fields
        404: Nothing to redo
    """
    data = request.json

    # Validate required fields
    if not data or 'activity_id' not in data:
        return jsonify({
            'error': 'Missing required field: activity_id'
        }), 400

    activity_id = data['activity_id']

    # Get session history manager
    manager = get_session_manager()
    history = manager.get_history(_get_session_id(), activity_id)

    # Redo last undone command
    command = history.redo()

    if not command:
        return jsonify({
            'error': 'Nothing to redo'
        }), 404

    return jsonify({
        'command': command.to_dict(),
        'content_after': command.after,
        'can_undo': history.can_undo(),
        'can_redo': history.can_redo()
    })


@edit_bp.route('/history/<activity_id>', methods=['GET'])
@login_required
def get_history(activity_id):
    """Get edit history for activity.

    Returns:
        {
            "undo_stack": [EditCommand, ...],
            "redo_stack": [EditCommand, ...],
            "can_undo": bool,
            "can_redo": bool
        }

    Status Codes:
        200: History returned successfully
    """
    # Get session history manager
    manager = get_session_manager()
    history = manager.get_history(_get_session_id(), activity_id)

    return jsonify({
        'undo_stack': [cmd.to_dict() for cmd in history.get_undo_stack()],
        'redo_stack': [cmd.to_dict() for cmd in history.get_redo_stack()],
        'can_undo': history.can_undo(),
        'can_redo': history.can_redo()
    })


# ============================================================================
# Version Endpoints (Named Snapshots)
# ============================================================================

@edit_bp.route('/courses/<course_id>/activities/<activity_id>/versions', methods=['POST'])
@login_required
def save_version(course_id, activity_id):
    """Save named version of activity content.

    Request JSON:
        {
            "name": str,
            "content": dict
        }

    Returns:
        {
            "version": {
                "id": str,
                "name": str,
                "activity_id": str,
                "content": dict,
                "created_at": str,
                "created_by": str
            }
        }

    Status Codes:
        200: Version saved successfully
        400: Missing required fields or version store not initialized
        404: Course or activity not found
    """
    if not _version_store:
        return jsonify({
            'error': 'Version store not initialized'
        }), 400

    data = request.json

    # Validate required fields
    if not data or 'name' not in data or 'content' not in data:
        return jsonify({
            'error': 'Missing required fields: name, content'
        }), 400

    name = data['name']
    content = data['content']
    user_id = str(current_user.id)

    try:
        # Save version
        version = _version_store.save_version(
            course_id, activity_id, name, content, user_id
        )

        return jsonify({
            'version': version.to_dict()
        })

    except ValueError as e:
        return jsonify({
            'error': str(e)
        }), 404


@edit_bp.route('/courses/<course_id>/activities/<activity_id>/versions', methods=['GET'])
@login_required
def list_versions(course_id, activity_id):
    """List all versions for activity.

    Returns:
        {
            "versions": [Version, ...]
        }

    Status Codes:
        200: Versions returned successfully
        400: Version store not initialized
        404: Course or activity not found
    """
    if not _version_store:
        return jsonify({
            'error': 'Version store not initialized'
        }), 400

    user_id = str(current_user.id)

    try:
        # List versions
        versions = _version_store.list_versions(course_id, activity_id, user_id)

        return jsonify({
            'versions': [v.to_dict() for v in versions]
        })

    except ValueError as e:
        return jsonify({
            'error': str(e)
        }), 404


@edit_bp.route('/courses/<course_id>/activities/<activity_id>/versions/<version_id>/restore', methods=['POST'])
@login_required
def restore_version(course_id, activity_id, version_id):
    """Restore activity content from version.

    Returns:
        {
            "restored": true,
            "content": dict
        }

    Status Codes:
        200: Version restored successfully
        400: Version store not initialized
        404: Course, activity, or version not found
    """
    if not _version_store:
        return jsonify({
            'error': 'Version store not initialized'
        }), 400

    user_id = str(current_user.id)

    try:
        # Restore version
        content = _version_store.restore_version(
            course_id, activity_id, version_id, user_id
        )

        return jsonify({
            'restored': True,
            'content': content
        })

    except ValueError as e:
        return jsonify({
            'error': str(e)
        }), 404


@edit_bp.route('/courses/<course_id>/activities/<activity_id>/versions/<version_id>', methods=['DELETE'])
@login_required
def delete_version(course_id, activity_id, version_id):
    """Delete a version.

    Returns:
        {
            "deleted": true
        }

    Status Codes:
        200: Version deleted successfully
        400: Version store not initialized
        404: Course, activity, or version not found
    """
    if not _version_store:
        return jsonify({
            'error': 'Version store not initialized'
        }), 400

    user_id = str(current_user.id)

    try:
        # Delete version
        deleted = _version_store.delete_version(
            course_id, activity_id, version_id, user_id
        )

        if not deleted:
            return jsonify({
                'error': 'Version not found'
            }), 404

        return jsonify({
            'deleted': True
        })

    except ValueError as e:
        return jsonify({
            'error': str(e)
        }), 404


@edit_bp.route('/courses/<course_id>/activities/<activity_id>/versions/compare', methods=['GET'])
@login_required
def compare_versions(course_id, activity_id):
    """Compare two versions.

    Query params:
        v1: First version ID (original)
        v2: Second version ID (modified)

    Returns:
        {
            "diff": {
                "unified_diff": str,
                "html_diff": str,
                "changes": list
            }
        }

    Status Codes:
        200: Diff generated successfully
        400: Missing query params or version store not initialized
        404: Course, activity, or versions not found
    """
    if not _version_store:
        return jsonify({
            'error': 'Version store not initialized'
        }), 400

    # Get query params
    v1_id = request.args.get('v1')
    v2_id = request.args.get('v2')

    if not v1_id or not v2_id:
        return jsonify({
            'error': 'Missing query params: v1, v2'
        }), 400

    user_id = str(current_user.id)

    try:
        # Compare versions
        diff_result = _version_store.compare_versions(
            course_id, activity_id, v1_id, v2_id, user_id
        )

        return jsonify({
            'diff': {
                'unified_diff': diff_result.unified_diff,
                'html_diff': diff_result.html_diff,
                'changes': diff_result.changes
            }
        })

    except ValueError as e:
        return jsonify({
            'error': str(e)
        }), 404
