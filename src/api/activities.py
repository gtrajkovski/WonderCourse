"""Activity CRUD API endpoints using Flask Blueprint pattern.

Provides endpoints for creating, reading, updating, deleting, and reordering
activities within a lesson. All endpoints follow atomic save pattern with
project_store load/modify/save.
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime

from src.core.models import Activity, ContentType, ActivityType, WWHAAPhase, BloomLevel
from src.collab.decorators import require_permission
from src.collab.audit import (
    log_audit_entry,
    ACTION_STRUCTURE_ADDED,
    ACTION_STRUCTURE_UPDATED,
    ACTION_STRUCTURE_DELETED,
    ACTION_STRUCTURE_REORDERED,
)
from src.collab.models import Collaborator

# Create Blueprint
activities_bp = Blueprint('activities', __name__)

# Module-level project_store reference (set during registration)
_project_store = None


def init_activities_bp(project_store):
    """Initialize the activities blueprint with a ProjectStore instance.

    Must be called before registering the blueprint with Flask app.

    Args:
        project_store: ProjectStore instance for course persistence.
    """
    global _project_store
    _project_store = project_store


def _find_activity(course, activity_id):
    """Find activity and its parent lesson by activity ID.

    Args:
        course: Course instance to search.
        activity_id: Activity identifier.

    Returns:
        Tuple of (activity, lesson) if found, (None, None) otherwise.
    """
    for module in course.modules:
        for lesson in module.lessons:
            for activity in lesson.activities:
                if activity.id == activity_id:
                    return activity, lesson
    return None, None


@activities_bp.route('/api/courses/<course_id>/lessons/<lesson_id>/activities', methods=['GET'])
@login_required
@require_permission('view_content')
def list_activities(course_id, lesson_id):
    """List activities for a lesson with optional pagination.

    Query Parameters:
        page: Page number (default 1)
        per_page: Items per page (default 20, max 100)
        summary_only: If true, return activity summaries without full content (default false)

    Args:
        course_id: Course identifier.
        lesson_id: Lesson identifier.

    Returns:
        JSON object with activities array and pagination metadata if page/per_page specified,
        otherwise JSON array of activity dictionaries (backward compatible).

    Errors:
        404 if course or lesson not found.
        500 if load fails.
    """
    try:
        # Parse query parameters
        page = request.args.get('page', type=int)
        per_page = request.args.get('per_page', type=int)
        summary_only = request.args.get('summary_only', 'false').lower() == 'true'

        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        # Find lesson by traversing course structure
        lesson = None
        for module in course.modules:
            for les in module.lessons:
                if les.id == lesson_id:
                    lesson = les
                    break
            if lesson:
                break

        if not lesson:
            return jsonify({"error": "Lesson not found"}), 404

        # Sort activities by order
        activities = sorted(lesson.activities, key=lambda a: a.order)

        # If pagination not requested, return all activities (backward compatible)
        if page is None and per_page is None:
            if summary_only:
                # Return summaries without full content
                summaries = [{
                    "id": a.id,
                    "title": a.title,
                    "content_type": a.content_type.value,
                    "activity_type": a.activity_type.value,
                    "build_state": a.build_state.value,
                    "order": a.order,
                    "estimated_duration_minutes": a.estimated_duration_minutes
                } for a in activities]
                return jsonify(summaries)
            else:
                return jsonify([a.to_dict() for a in activities])

        # Validate pagination parameters
        if page is None:
            page = 1
        if per_page is None:
            per_page = 20
        per_page = min(max(per_page, 1), 100)
        page = max(page, 1)

        total_count = len(activities)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_activities = activities[start_idx:end_idx]

        if summary_only:
            # Return summaries without full content
            activity_data = [{
                "id": a.id,
                "title": a.title,
                "content_type": a.content_type.value,
                "activity_type": a.activity_type.value,
                "build_state": a.build_state.value,
                "order": a.order,
                "estimated_duration_minutes": a.estimated_duration_minutes
            } for a in paginated_activities]
        else:
            activity_data = [a.to_dict() for a in paginated_activities]

        return jsonify({
            "activities": activity_data,
            "page": page,
            "per_page": per_page,
            "total": total_count,
            "has_more": page * per_page < total_count
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@activities_bp.route('/api/courses/<course_id>/lessons/<lesson_id>/activities', methods=['POST'])
@login_required
@require_permission('add_structure')
def create_activity(course_id, lesson_id):
    """Create a new activity in a lesson.

    Args:
        course_id: Course identifier.
        lesson_id: Lesson identifier.

    Request JSON:
        {
            "title": str,
            "content_type": str (optional, default "video"),
            "activity_type": str (optional, default "video_lecture")
        }

    Returns:
        JSON activity object with 201 status.

    Errors:
        404 if course or lesson not found.
        400 if request JSON is invalid.
        500 if save fails.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    if 'title' not in data:
        return jsonify({"error": "Missing required field: title"}), 400

    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        # Find lesson by traversing course structure
        lesson = None
        for module in course.modules:
            for les in module.lessons:
                if les.id == lesson_id:
                    lesson = les
                    break
            if lesson:
                break

        if not lesson:
            return jsonify({"error": "Lesson not found"}), 404

        # Parse enum values with defaults
        content_type = ContentType.VIDEO
        if 'content_type' in data:
            try:
                content_type = ContentType(data['content_type'])
            except ValueError:
                return jsonify({"error": f"Invalid content_type: {data['content_type']}"}), 400

        activity_type = ActivityType.VIDEO_LECTURE
        if 'activity_type' in data:
            try:
                activity_type = ActivityType(data['activity_type'])
            except ValueError:
                return jsonify({"error": f"Invalid activity_type: {data['activity_type']}"}), 400

        # Create new activity with auto-assigned order
        activity = Activity(
            title=data['title'],
            content_type=content_type,
            activity_type=activity_type,
            order=len(lesson.activities),
            estimated_duration_minutes=data.get('estimated_duration_minutes', 0.0)
        )

        # Add to lesson and save
        lesson.activities.append(activity)
        _project_store.save(owner_id, course)

        # Log audit entry
        log_audit_entry(
            course_id=course_id,
            user_id=current_user.id,
            action=ACTION_STRUCTURE_ADDED,
            entity_type='activity',
            entity_id=activity.id,
            after={'name': activity.title, 'content_type': activity.content_type.value}
        )

        return jsonify(activity.to_dict()), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@activities_bp.route('/api/courses/<course_id>/activities/<activity_id>', methods=['PUT'])
@login_required
@require_permission('add_structure')
def update_activity(course_id, activity_id):
    """Update activity fields.

    Args:
        course_id: Course identifier.
        activity_id: Activity identifier.

    Request JSON (all optional):
        {
            "title": str,
            "content_type": str,
            "activity_type": str,
            "wwhaa_phase": str,
            "content": str,
            "bloom_level": str (or null),
            "word_count": int,
            "estimated_duration_minutes": float
        }

    Returns:
        JSON updated activity object.

    Errors:
        404 if course or activity not found.
        400 if request JSON is invalid or enum values are invalid.
        500 if save fails.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        # Find activity by traversing course structure
        activity, lesson = _find_activity(course, activity_id)
        if not activity:
            return jsonify({"error": "Activity not found"}), 404

        # Capture before state for audit
        before_state = {
            'title': activity.title,
            'content_type': activity.content_type.value
        }

        # Update simple fields
        if 'title' in data:
            activity.title = data['title']
        if 'content' in data:
            activity.content = data['content']
        if 'word_count' in data:
            activity.word_count = data['word_count']
        if 'estimated_duration_minutes' in data:
            activity.estimated_duration_minutes = data['estimated_duration_minutes']

        # Update enum fields with validation
        if 'content_type' in data:
            try:
                new_content_type = ContentType(data['content_type'])
                # If content_type changes, reset build state and clear content
                # (old content is for a different type)
                if new_content_type != activity.content_type:
                    from src.core.models import BuildState
                    activity.content_type = new_content_type
                    activity.content = None
                    activity.word_count = 0
                    activity.estimated_duration_minutes = 0.0
                    activity.build_state = BuildState.DRAFT
                else:
                    activity.content_type = new_content_type
            except ValueError:
                return jsonify({"error": f"Invalid content_type: {data['content_type']}"}), 400

        if 'activity_type' in data:
            try:
                activity.activity_type = ActivityType(data['activity_type'])
            except ValueError:
                return jsonify({"error": f"Invalid activity_type: {data['activity_type']}"}), 400

        if 'wwhaa_phase' in data:
            try:
                activity.wwhaa_phase = WWHAAPhase(data['wwhaa_phase'])
            except ValueError:
                return jsonify({"error": f"Invalid wwhaa_phase: {data['wwhaa_phase']}"}), 400

        if 'bloom_level' in data:
            if data['bloom_level'] is None:
                activity.bloom_level = None
            else:
                try:
                    activity.bloom_level = BloomLevel(data['bloom_level'])
                except ValueError:
                    return jsonify({"error": f"Invalid bloom_level: {data['bloom_level']}"}), 400

        activity.updated_at = datetime.now().isoformat()

        # Save course
        _project_store.save(owner_id, course)

        # Log audit entry with before/after
        log_audit_entry(
            course_id=course_id,
            user_id=current_user.id,
            action=ACTION_STRUCTURE_UPDATED,
            entity_type='activity',
            entity_id=activity_id,
            before=before_state,
            after={'title': activity.title, 'content_type': activity.content_type.value}
        )

        return jsonify(activity.to_dict())

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@activities_bp.route('/api/courses/<course_id>/activities/<activity_id>', methods=['DELETE'])
@login_required
@require_permission('delete_structure')
def delete_activity(course_id, activity_id):
    """Delete an activity and clean up learning outcome mappings.

    Removes activity ID from all learning outcome mapped_activity_ids.
    Removes activity from lesson and renumbers remaining activities.

    Args:
        course_id: Course identifier.
        activity_id: Activity identifier.

    Returns:
        JSON success message with 200 status.

    Errors:
        404 if course or activity not found.
        500 if save fails.
    """
    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        # Find activity by traversing course structure
        activity, lesson = _find_activity(course, activity_id)
        if not activity:
            return jsonify({"error": "Activity not found"}), 404

        # Store activity info for audit before deletion
        deleted_activity_title = activity.title

        # Remove activity ID from all learning outcome mappings
        for outcome in course.learning_outcomes:
            outcome.mapped_activity_ids = [
                aid for aid in outcome.mapped_activity_ids
                if aid != activity_id
            ]

        # Remove activity from lesson
        lesson.activities = [a for a in lesson.activities if a.id != activity_id]

        # Renumber remaining activities
        for i, act in enumerate(lesson.activities):
            act.order = i

        # Save course
        _project_store.save(owner_id, course)

        # Log audit entry
        log_audit_entry(
            course_id=course_id,
            user_id=current_user.id,
            action=ACTION_STRUCTURE_DELETED,
            entity_type='activity',
            entity_id=activity_id,
            before={'name': deleted_activity_title}
        )

        return jsonify({"message": "Activity deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@activities_bp.route('/api/courses/<course_id>/lessons/<lesson_id>/activities/reorder', methods=['PUT'])
@login_required
@require_permission('reorder_structure')
def reorder_activities(course_id, lesson_id):
    """Reorder activities within a lesson.

    Moves activity from old_index to new_index and renumbers all activities.

    Args:
        course_id: Course identifier.
        lesson_id: Lesson identifier.

    Request JSON:
        {
            "old_index": int,
            "new_index": int
        }

    Returns:
        JSON array of reordered activities with 200 status.

    Errors:
        404 if course or lesson not found.
        400 if indices are invalid or request JSON is invalid.
        500 if save fails.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    if 'old_index' not in data or 'new_index' not in data:
        return jsonify({"error": "Missing required fields: old_index, new_index"}), 400

    old_index = data['old_index']
    new_index = data['new_index']

    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        # Find lesson by traversing course structure
        lesson = None
        for module in course.modules:
            for les in module.lessons:
                if les.id == lesson_id:
                    lesson = les
                    break
            if lesson:
                break

        if not lesson:
            return jsonify({"error": "Lesson not found"}), 404

        # Validate indices
        if not isinstance(old_index, int) or not isinstance(new_index, int):
            return jsonify({"error": "Indices must be integers"}), 400

        if old_index < 0 or old_index >= len(lesson.activities):
            return jsonify({"error": "old_index out of range"}), 400

        if new_index < 0 or new_index >= len(lesson.activities):
            return jsonify({"error": "new_index out of range"}), 400

        # Reorder activities
        activity = lesson.activities.pop(old_index)
        lesson.activities.insert(new_index, activity)

        # Renumber all activities
        for i, act in enumerate(lesson.activities):
            act.order = i

        # Save course
        _project_store.save(owner_id, course)

        # Log audit entry
        log_audit_entry(
            course_id=course_id,
            user_id=current_user.id,
            action=ACTION_STRUCTURE_REORDERED,
            entity_type='activities',
            after={'old_index': old_index, 'new_index': new_index, 'lesson_id': lesson_id}
        )

        # Return updated activities list
        return jsonify([a.to_dict() for a in lesson.activities]), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
