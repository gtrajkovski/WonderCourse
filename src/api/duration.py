"""Course duration configuration API endpoints.

Provides endpoints for:
- Getting/setting course target duration
- Listing available duration presets
- Getting duration comparison (actual vs target)
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime

from src.core.models import Course, DURATION_PRESETS
from src.collab.decorators import require_permission
from src.collab.models import Collaborator

# Create Blueprint
duration_bp = Blueprint('duration', __name__)

# Module-level project_store reference
_project_store = None


def init_duration_bp(project_store):
    """Initialize the duration blueprint with a ProjectStore instance.

    Must be called before registering the blueprint with Flask app.

    Args:
        project_store: ProjectStore instance for course persistence.
    """
    global _project_store
    _project_store = project_store


@duration_bp.route('/api/duration/presets', methods=['GET'])
def get_duration_presets():
    """Get available duration presets.

    Returns:
        JSON with list of duration presets.
    """
    presets = [
        {
            "id": preset_id,
            "minutes": preset_data["minutes"],
            "label": preset_data["label"],
            "description": preset_data["description"]
        }
        for preset_id, preset_data in DURATION_PRESETS.items()
    ]

    return jsonify({
        "presets": presets,
        "min_minutes": 30,
        "max_minutes": 180
    })


@duration_bp.route('/api/courses/<course_id>/duration', methods=['GET'])
@login_required
@require_permission('view_content')
def get_course_duration(course_id):
    """Get course duration configuration and comparison.

    Returns:
        JSON with target duration, actual duration, and comparison metrics.
    """
    # Load course
    owner_id = Collaborator.get_course_owner_id(course_id)
    if not owner_id:
        return jsonify({"error": "Course not found"}), 404

    try:
        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Get comparison data
    comparison = course.get_duration_comparison()

    # Find matching preset
    preset_id = None
    for pid, pdata in DURATION_PRESETS.items():
        if pdata["minutes"] == course.target_duration_minutes:
            preset_id = pid
            break

    return jsonify({
        "target_duration_minutes": course.target_duration_minutes,
        "preset_id": preset_id,
        "comparison": comparison,
        "presets": list(DURATION_PRESETS.keys())
    })


@duration_bp.route('/api/courses/<course_id>/duration', methods=['PUT'])
@login_required
@require_permission('edit_content')
def set_course_duration(course_id):
    """Set course target duration.

    Request JSON:
        {
            "target_duration_minutes": 90
        }
    Or:
        {
            "preset_id": "standard"
        }

    Returns:
        JSON with updated duration configuration and comparison.
    """
    # Load course
    owner_id = Collaborator.get_course_owner_id(course_id)
    if not owner_id:
        return jsonify({"error": "Course not found"}), 404

    try:
        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    # Handle preset_id or direct minutes
    if "preset_id" in data:
        preset_id = data["preset_id"]
        if preset_id not in DURATION_PRESETS:
            return jsonify({"error": f"Unknown preset: {preset_id}"}), 400
        new_duration = DURATION_PRESETS[preset_id]["minutes"]
    elif "target_duration_minutes" in data:
        new_duration = data["target_duration_minutes"]
        if not isinstance(new_duration, (int, float)):
            return jsonify({"error": "target_duration_minutes must be a number"}), 400
        new_duration = int(new_duration)
        if new_duration < 30 or new_duration > 180:
            return jsonify({
                "error": "target_duration_minutes must be between 30 and 180"
            }), 400
    else:
        return jsonify({
            "error": "Either preset_id or target_duration_minutes is required"
        }), 400

    # Update course
    course.target_duration_minutes = new_duration
    course.updated_at = datetime.now().isoformat()

    # Save
    try:
        _project_store.save(owner_id, course)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Get comparison data
    comparison = course.get_duration_comparison()

    # Find matching preset
    preset_id = None
    for pid, pdata in DURATION_PRESETS.items():
        if pdata["minutes"] == course.target_duration_minutes:
            preset_id = pid
            break

    return jsonify({
        "target_duration_minutes": course.target_duration_minutes,
        "preset_id": preset_id,
        "comparison": comparison,
        "message": f"Duration updated to {course.target_duration_minutes} minutes"
    })


@duration_bp.route('/api/courses/<course_id>/duration/comparison', methods=['GET'])
@login_required
@require_permission('view_content')
def get_duration_comparison(course_id):
    """Get detailed duration comparison for a course.

    Returns:
        JSON with detailed breakdown of actual vs target duration.
    """
    # Load course
    owner_id = Collaborator.get_course_owner_id(course_id)
    if not owner_id:
        return jsonify({"error": "Course not found"}), 404

    try:
        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Get basic comparison
    comparison = course.get_duration_comparison()

    # Add module breakdown
    module_breakdown = []
    for module in course.modules:
        module_duration = 0.0
        lesson_details = []
        for lesson in module.lessons:
            lesson_duration = sum(
                a.estimated_duration_minutes for a in lesson.activities
            )
            module_duration += lesson_duration
            lesson_details.append({
                "id": lesson.id,
                "title": lesson.title,
                "duration_minutes": round(lesson_duration, 1),
                "activity_count": len(lesson.activities)
            })

        module_breakdown.append({
            "id": module.id,
            "title": module.title,
            "duration_minutes": round(module_duration, 1),
            "lesson_count": len(module.lessons),
            "lessons": lesson_details
        })

    return jsonify({
        **comparison,
        "module_breakdown": module_breakdown
    })
