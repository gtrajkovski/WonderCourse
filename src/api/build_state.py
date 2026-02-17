"""Build state tracking API endpoints.

Provides endpoints for viewing content generation progress and managing build states
through the review/approve workflow (GENERATED -> REVIEWED -> APPROVED -> PUBLISHED).
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime

from src.core.models import BuildState
from src.validators.validation_report import ValidationReport
from src.collab.decorators import require_permission
from src.collab.permissions import has_permission
from src.collab.audit import (
    log_audit_entry,
    ACTION_CONTENT_UPDATED,
    ACTION_CONTENT_APPROVED,
)
from src.collab.models import Collaborator

# Create Blueprint
build_state_bp = Blueprint('build_state', __name__)

# Module-level project_store reference (set during registration)
_project_store = None
_validation_report = None


def init_build_state_bp(project_store):
    """Initialize the build_state blueprint with a ProjectStore instance.

    Must be called before registering the blueprint with Flask app.

    Args:
        project_store: ProjectStore instance for course persistence.
    """
    global _project_store, _validation_report
    _project_store = project_store
    _validation_report = ValidationReport()


def _find_activity(course, activity_id):
    """Find activity and its parent containers by activity ID.

    Args:
        course: Course instance to search.
        activity_id: Activity identifier.

    Returns:
        Tuple of (module, lesson, activity) if found, (None, None, None) otherwise.
    """
    for module in course.modules:
        for lesson in module.lessons:
            for activity in lesson.activities:
                if activity.id == activity_id:
                    return module, lesson, activity
    return None, None, None


# Valid state transitions
# Format: {from_state: [allowed_to_states]}
_MANUAL_TRANSITIONS = {
    BuildState.GENERATED: [BuildState.REVIEWED, BuildState.DRAFT],  # forward to reviewed, or revert to draft
    BuildState.REVIEWED: [BuildState.APPROVED, BuildState.GENERATED],  # forward to approved, or revert to generated
    BuildState.APPROVED: [BuildState.PUBLISHED, BuildState.REVIEWED],  # forward to published, or revert to reviewed
    BuildState.PUBLISHED: [],  # published is terminal
    BuildState.DRAFT: [],  # draft can only transition via generate endpoint
    BuildState.GENERATING: [],  # generating is transient, managed by generate endpoint
}


def _is_valid_transition(from_state, to_state):
    """Check if a build state transition is valid.

    Args:
        from_state: Current BuildState enum value.
        to_state: Target BuildState enum value.

    Returns:
        True if transition is allowed, False otherwise.
    """
    allowed = _MANUAL_TRANSITIONS.get(from_state, [])
    return to_state in allowed


@build_state_bp.route('/api/courses/<course_id>/progress', methods=['GET'])
@login_required
@require_permission('view_content')
def get_progress(course_id):
    """Get comprehensive build progress metrics for a course.

    Args:
        course_id: Course identifier.

    Returns:
        JSON with:
        - total_activities: Total number of activities in course
        - by_state: Dictionary mapping state names to counts
        - completion_percentage: Percentage of approved or published activities
        - activities: List of all activities with id, title, content_type, build_state, word_count, module_id
        - content_metrics: Word counts and duration stats
        - structure: Module, lesson, activity counts
        - by_content_type: Breakdown by content type
        - by_module: Per-module progress
        - quality: Audit score and issues (if available)

    Errors:
        404 if course not found.
    """
    try:
        # Look up course owner
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        # Load course
        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        # Initialize counters
        total_activities = 0
        total_word_count = 0
        total_duration_minutes = 0.0
        by_state = {
            "draft": 0,
            "generating": 0,
            "generated": 0,
            "reviewed": 0,
            "approved": 0,
            "published": 0
        }
        by_content_type = {}
        by_module = []
        activities = []

        # Traverse all modules -> lessons -> activities
        for module in course.modules:
            module_total = 0
            module_completed = 0

            for lesson in module.lessons:
                for activity in lesson.activities:
                    total_activities += 1
                    module_total += 1
                    by_state[activity.build_state.value] += 1

                    # Track completion per module
                    if activity.build_state.value in ["approved", "published"]:
                        module_completed += 1

                    # Track by content type
                    ct = activity.content_type.value
                    if ct not in by_content_type:
                        by_content_type[ct] = {"count": 0, "completed": 0}
                    by_content_type[ct]["count"] += 1
                    if activity.build_state.value in ["approved", "published"]:
                        by_content_type[ct]["completed"] += 1

                    # Sum word counts and duration
                    wc = activity.word_count or 0
                    total_word_count += wc

                    # Calculate duration from metadata or word count
                    duration = activity.estimated_duration_minutes or 0
                    if duration == 0 and wc > 0:
                        # Estimate: video 150 WPM, reading 238 WPM, quiz 1.5 min/question
                        if ct == "video":
                            duration = wc / 150.0
                        elif ct == "reading":
                            duration = wc / 238.0
                        else:
                            duration = wc / 200.0  # Default rate
                    total_duration_minutes += duration

                    # Add activity detail
                    activities.append({
                        "id": activity.id,
                        "title": activity.title,
                        "content_type": ct,
                        "build_state": activity.build_state.value,
                        "word_count": wc,
                        "module_id": module.id,
                        "module_title": module.title
                    })

            # Add module progress
            by_module.append({
                "id": module.id,
                "title": module.title,
                "total": module_total,
                "completed": module_completed,
                "percentage": (module_completed / module_total * 100.0) if module_total > 0 else 0.0
            })

        # Calculate completion percentage
        completed_count = by_state["approved"] + by_state["published"]
        completion_percentage = (completed_count / total_activities * 100.0) if total_activities > 0 else 0.0

        # Structure counts
        structure = {
            "module_count": len(course.modules),
            "lesson_count": sum(len(m.lessons) for m in course.modules),
            "activity_count": total_activities
        }

        # Content metrics
        target_duration = course.target_duration_minutes or 60
        content_metrics = {
            "total_word_count": total_word_count,
            "total_duration_minutes": round(total_duration_minutes, 1),
            "target_duration_minutes": target_duration,
            "duration_percentage": round((total_duration_minutes / target_duration * 100.0) if target_duration > 0 else 0.0, 1)
        }

        # Quality metrics (from last audit if available)
        quality = {
            "audit_score": None,
            "open_issues": 0,
            "last_audit": None
        }
        if hasattr(course, 'last_audit_result') and course.last_audit_result:
            audit = course.last_audit_result
            quality["audit_score"] = audit.get("score")
            quality["open_issues"] = len([i for i in audit.get("issues", []) if i.get("status") == "open"])
            quality["last_audit"] = audit.get("timestamp")

        return jsonify({
            "total_activities": total_activities,
            "by_state": by_state,
            "completion_percentage": round(completion_percentage, 1),
            "activities": activities,
            "content_metrics": content_metrics,
            "structure": structure,
            "by_content_type": by_content_type,
            "by_module": by_module,
            "quality": quality
        }), 200

    except Exception as e:
        import traceback
        print(f"Progress API error: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@build_state_bp.route('/api/courses/<course_id>/activities/<activity_id>/state', methods=['PUT'])
@login_required
@require_permission('edit_content')
def update_state(course_id, activity_id):
    """Update build state for an activity with transition validation.

    Args:
        course_id: Course identifier.
        activity_id: Activity identifier.

    Request JSON:
        {
            "build_state": "reviewed"  # Target state as string
        }

    Returns:
        JSON updated activity object.

    Errors:
        404 if course or activity not found.
        400 if build_state missing or invalid transition.
    """
    try:
        # Look up course owner
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        # Load course
        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        # Find activity
        module, lesson, activity = _find_activity(course, activity_id)
        if not activity:
            return jsonify({"error": "Activity not found"}), 404

        # Get request data
        data = request.get_json()
        if not data or "build_state" not in data:
            return jsonify({"error": "Missing required field: build_state"}), 400

        # Parse target state
        try:
            target_state = BuildState(data["build_state"])
        except ValueError:
            valid_states = [state.value for state in BuildState]
            return jsonify({
                "error": f"Invalid build_state: {data['build_state']}",
                "valid_states": valid_states
            }), 400

        # Validate transition
        current_state = activity.build_state
        if not _is_valid_transition(current_state, target_state):
            allowed = _MANUAL_TRANSITIONS.get(current_state, [])
            allowed_values = [state.value for state in allowed]
            return jsonify({
                "error": f"Invalid state transition from {current_state.value} to {target_state.value}",
                "current_state": current_state.value,
                "allowed_transitions": allowed_values
            }), 400

        # Special permission check for APPROVED transition
        if target_state == BuildState.APPROVED:
            if not has_permission(current_user.id, course_id, 'approve_content'):
                return jsonify({"error": "Approval requires approve_content permission"}), 403

        # Special validation gate for publishing
        if target_state == BuildState.PUBLISHED:
            if not _validation_report.is_publishable(course):
                return jsonify({
                    "error": "Cannot publish: course has validation errors",
                    "hint": f"Run GET /api/courses/{course_id}/validate to see errors"
                }), 400

        # Update state
        activity.build_state = target_state
        activity.updated_at = datetime.now().isoformat()

        # Save course
        _project_store.save(owner_id, course)

        # Log audit entry
        action = ACTION_CONTENT_APPROVED if target_state == BuildState.APPROVED else ACTION_CONTENT_UPDATED
        log_audit_entry(
            course_id=course_id,
            user_id=current_user.id,
            action=action,
            entity_type='activity',
            entity_id=activity_id,
            before={'build_state': current_state.value},
            after={'build_state': target_state.value}
        )

        return jsonify(activity.to_dict()), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@build_state_bp.route('/api/courses/<course_id>/activities/<activity_id>/approve', methods=['POST'])
@login_required
@require_permission('approve_content')
def approve_activity(course_id, activity_id):
    """Convenience endpoint to approve an activity.

    Only allowed from REVIEWED state. Sets build_state to APPROVED.

    Args:
        course_id: Course identifier.
        activity_id: Activity identifier.

    Returns:
        JSON updated activity object.

    Errors:
        404 if course or activity not found.
        400 if activity not in REVIEWED state.
    """
    try:
        # Look up course owner
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        # Load course
        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        # Find activity
        module, lesson, activity = _find_activity(course, activity_id)
        if not activity:
            return jsonify({"error": "Activity not found"}), 404

        # Check current state
        if activity.build_state != BuildState.REVIEWED:
            return jsonify({
                "error": f"Cannot approve activity in state: {activity.build_state.value}",
                "current_state": activity.build_state.value,
                "required_state": "reviewed"
            }), 400

        # Approve activity
        activity.build_state = BuildState.APPROVED
        activity.updated_at = datetime.now().isoformat()

        # Save course
        _project_store.save(owner_id, course)

        # Log audit entry
        log_audit_entry(
            course_id=course_id,
            user_id=current_user.id,
            action=ACTION_CONTENT_APPROVED,
            entity_type='activity',
            entity_id=activity_id,
            before={'build_state': 'reviewed'},
            after={'build_state': 'approved'}
        )

        return jsonify(activity.to_dict()), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
