"""Flow control and completion criteria API endpoints.

Provides endpoints for:
- Course/module flow mode management (sequential vs open)
- Activity prerequisite management
- Completion criteria configuration
- Completion status checking
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required
from datetime import datetime

from src.core.models import FlowMode, CompletionCriteria
from src.collab.decorators import require_permission
from src.collab.models import Collaborator


# Create Blueprint
flow_bp = Blueprint('flow', __name__)

# Module-level project_store reference (set during registration)
_project_store = None


def init_flow_bp(project_store):
    """Initialize the flow control blueprint with a ProjectStore instance.

    Args:
        project_store: ProjectStore instance for course persistence.
    """
    global _project_store
    _project_store = project_store


def _find_activity(course, activity_id):
    """Find activity and its parent containers by activity ID."""
    for module in course.modules:
        for lesson in module.lessons:
            for activity in lesson.activities:
                if activity.id == activity_id:
                    return module, lesson, activity
    return None, None, None


def _find_module(course, module_id):
    """Find module by ID."""
    for module in course.modules:
        if module.id == module_id:
            return module
    return None


# ===========================
# Course Flow Mode
# ===========================


@flow_bp.route('/api/courses/<course_id>/flow-mode', methods=['GET'])
@login_required
def get_course_flow_mode(course_id):
    """Get the flow mode for a course.

    Returns:
        JSON with flow_mode value.
    """
    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        return jsonify({
            "flow_mode": course.flow_mode.value
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@flow_bp.route('/api/courses/<course_id>/flow-mode', methods=['PUT'])
@login_required
@require_permission('edit_structure')
def set_course_flow_mode(course_id):
    """Set the flow mode for a course.

    Request JSON:
        {
            "flow_mode": "sequential" | "open"
        }

    Returns:
        JSON with updated flow_mode.
    """
    data = request.get_json()
    if not data or 'flow_mode' not in data:
        return jsonify({"error": "Missing required field: flow_mode"}), 400

    try:
        flow_mode = FlowMode(data['flow_mode'])
    except ValueError:
        return jsonify({"error": f"Invalid flow_mode: {data['flow_mode']}. Must be 'sequential' or 'open'"}), 400

    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        course.flow_mode = flow_mode
        course.updated_at = datetime.now().isoformat()
        _project_store.save(owner_id, course)

        return jsonify({
            "flow_mode": course.flow_mode.value,
            "message": "Flow mode updated successfully"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===========================
# Module Flow Mode
# ===========================


@flow_bp.route('/api/courses/<course_id>/modules/<module_id>/flow-mode', methods=['GET'])
@login_required
def get_module_flow_mode(course_id, module_id):
    """Get the flow mode for a module.

    Returns:
        JSON with flow_mode value.
    """
    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        module = _find_module(course, module_id)
        if not module:
            return jsonify({"error": "Module not found"}), 404

        return jsonify({
            "flow_mode": module.flow_mode.value
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@flow_bp.route('/api/courses/<course_id>/modules/<module_id>/flow-mode', methods=['PUT'])
@login_required
@require_permission('edit_structure')
def set_module_flow_mode(course_id, module_id):
    """Set the flow mode for a module.

    Request JSON:
        {
            "flow_mode": "sequential" | "open"
        }

    Returns:
        JSON with updated flow_mode.
    """
    data = request.get_json()
    if not data or 'flow_mode' not in data:
        return jsonify({"error": "Missing required field: flow_mode"}), 400

    try:
        flow_mode = FlowMode(data['flow_mode'])
    except ValueError:
        return jsonify({"error": f"Invalid flow_mode: {data['flow_mode']}. Must be 'sequential' or 'open'"}), 400

    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        module = _find_module(course, module_id)
        if not module:
            return jsonify({"error": "Module not found"}), 404

        module.flow_mode = flow_mode
        course.updated_at = datetime.now().isoformat()
        _project_store.save(owner_id, course)

        return jsonify({
            "flow_mode": module.flow_mode.value,
            "message": "Module flow mode updated successfully"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===========================
# Activity Prerequisites
# ===========================


@flow_bp.route('/api/courses/<course_id>/activities/<activity_id>/prerequisites', methods=['GET'])
@login_required
def get_activity_prerequisites(course_id, activity_id):
    """Get prerequisites for an activity.

    Returns:
        JSON with prerequisite_ids list.
    """
    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        _, _, activity = _find_activity(course, activity_id)
        if not activity:
            return jsonify({"error": "Activity not found"}), 404

        return jsonify({
            "prerequisite_ids": activity.prerequisite_ids
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@flow_bp.route('/api/courses/<course_id>/activities/<activity_id>/prerequisites', methods=['PUT'])
@login_required
@require_permission('edit_structure')
def set_activity_prerequisites(course_id, activity_id):
    """Set prerequisites for an activity.

    Request JSON:
        {
            "prerequisite_ids": ["act_123", "act_456"]
        }

    Returns:
        JSON with updated prerequisite_ids.
    """
    data = request.get_json()
    if not data or 'prerequisite_ids' not in data:
        return jsonify({"error": "Missing required field: prerequisite_ids"}), 400

    prerequisite_ids = data['prerequisite_ids']
    if not isinstance(prerequisite_ids, list):
        return jsonify({"error": "prerequisite_ids must be a list"}), 400

    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        _, _, activity = _find_activity(course, activity_id)
        if not activity:
            return jsonify({"error": "Activity not found"}), 404

        # Validate that all prerequisite IDs exist
        all_activity_ids = set()
        for module in course.modules:
            for lesson in module.lessons:
                for act in lesson.activities:
                    all_activity_ids.add(act.id)

        invalid_ids = [pid for pid in prerequisite_ids if pid not in all_activity_ids]
        if invalid_ids:
            return jsonify({"error": f"Invalid activity IDs: {invalid_ids}"}), 400

        # Prevent self-reference
        if activity_id in prerequisite_ids:
            return jsonify({"error": "Activity cannot be a prerequisite of itself"}), 400

        activity.prerequisite_ids = prerequisite_ids
        course.updated_at = datetime.now().isoformat()
        _project_store.save(owner_id, course)

        return jsonify({
            "prerequisite_ids": activity.prerequisite_ids,
            "message": "Prerequisites updated successfully"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===========================
# Completion Criteria
# ===========================


@flow_bp.route('/api/courses/<course_id>/activities/<activity_id>/completion-criteria', methods=['GET'])
@login_required
def get_completion_criteria(course_id, activity_id):
    """Get completion criteria for an activity.

    Returns:
        JSON with completion criteria. If no custom criteria set, returns defaults.
    """
    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        _, _, activity = _find_activity(course, activity_id)
        if not activity:
            return jsonify({"error": "Activity not found"}), 404

        # Return custom criteria or defaults
        if activity.completion_criteria:
            criteria = activity.completion_criteria.to_dict()
            criteria['is_custom'] = True
        else:
            criteria = CompletionCriteria().to_dict()
            criteria['is_custom'] = False

        return jsonify(criteria)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@flow_bp.route('/api/courses/<course_id>/activities/<activity_id>/completion-criteria', methods=['PUT'])
@login_required
@require_permission('edit_structure')
def set_completion_criteria(course_id, activity_id):
    """Set completion criteria for an activity.

    Request JSON:
        {
            "video_watch_percent": 90,
            "quiz_passing_score_percent": 80,
            ...
        }

    Pass an empty object {} to reset to defaults.

    Returns:
        JSON with updated completion criteria.
    """
    data = request.get_json()
    if data is None:
        return jsonify({"error": "Request body must be JSON"}), 400

    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        _, _, activity = _find_activity(course, activity_id)
        if not activity:
            return jsonify({"error": "Activity not found"}), 404

        # Empty object resets to defaults (None)
        if not data:
            activity.completion_criteria = None
        else:
            activity.completion_criteria = CompletionCriteria.from_dict(data)

        course.updated_at = datetime.now().isoformat()
        _project_store.save(owner_id, course)

        # Return the effective criteria
        if activity.completion_criteria:
            criteria = activity.completion_criteria.to_dict()
            criteria['is_custom'] = True
        else:
            criteria = CompletionCriteria().to_dict()
            criteria['is_custom'] = False

        return jsonify({
            **criteria,
            "message": "Completion criteria updated successfully"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===========================
# Default Completion Criteria (by content type)
# ===========================


@flow_bp.route('/api/completion-criteria/defaults', methods=['GET'])
@login_required
def get_default_completion_criteria():
    """Get default completion criteria values.

    Returns:
        JSON with default CompletionCriteria values.
    """
    defaults = CompletionCriteria()
    return jsonify(defaults.to_dict())


@flow_bp.route('/api/completion-criteria/defaults/<content_type>', methods=['GET'])
@login_required
def get_content_type_defaults(content_type):
    """Get relevant completion criteria for a specific content type.

    Args:
        content_type: video, reading, quiz, hol, coach, lab, discussion, assignment, project

    Returns:
        JSON with relevant fields for the content type.
    """
    defaults = CompletionCriteria()
    full = defaults.to_dict()

    # Return only relevant fields for each content type
    type_fields = {
        'video': ['video_watch_percent'],
        'reading': ['reading_scroll_to_bottom', 'reading_min_time_seconds'],
        'quiz': ['quiz_must_submit', 'quiz_passing_score_percent', 'quiz_max_attempts'],
        'practice_quiz': ['practice_quiz_must_attempt'],
        'hol': ['submission_required'],
        'assignment': ['submission_required'],
        'project': ['submission_required'],
        'discussion': ['discussion_must_post', 'discussion_min_word_count'],
        'coach': ['coach_must_complete_dialogue'],
        'lab': ['lab_must_complete_exercises', 'lab_min_exercises_completed'],
    }

    fields = type_fields.get(content_type)
    if not fields:
        return jsonify({"error": f"Unknown content type: {content_type}"}), 400

    result = {k: full[k] for k in fields if k in full}
    result['content_type'] = content_type

    return jsonify(result)
