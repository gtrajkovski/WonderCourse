"""Lesson CRUD API endpoints using Flask Blueprint pattern.

Provides endpoints for creating, reading, updating, deleting, and reordering
lessons within a module. All endpoints follow atomic save pattern with
project_store load/modify/save.
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime

from src.core.models import Lesson
from src.collab.decorators import require_permission
from src.collab.models import Collaborator
from src.collab.audit import (
    log_audit_entry,
    ACTION_STRUCTURE_ADDED,
    ACTION_STRUCTURE_UPDATED,
    ACTION_STRUCTURE_DELETED,
    ACTION_STRUCTURE_REORDERED,
)

# Create Blueprint
lessons_bp = Blueprint('lessons', __name__)

# Module-level project_store reference (set during registration)
_project_store = None


def init_lessons_bp(project_store):
    """Initialize the lessons blueprint with a ProjectStore instance.

    Must be called before registering the blueprint with Flask app.

    Args:
        project_store: ProjectStore instance for course persistence.
    """
    global _project_store
    _project_store = project_store


def _find_lesson(course, lesson_id):
    """Find lesson and its parent module by lesson ID.

    Args:
        course: Course instance to search.
        lesson_id: Lesson identifier.

    Returns:
        Tuple of (lesson, module) if found, (None, None) otherwise.
    """
    for module in course.modules:
        for lesson in module.lessons:
            if lesson.id == lesson_id:
                return lesson, module
    return None, None


@lessons_bp.route('/api/courses/<course_id>/modules/<module_id>/lessons', methods=['GET'])
@login_required
@require_permission('view_content')
def list_lessons(course_id, module_id):
    """List all lessons for a module.

    Args:
        course_id: Course identifier.
        module_id: Module identifier.

    Returns:
        JSON array of lesson dictionaries sorted by order.

    Errors:
        404 if course or module not found.
        500 if load fails.
    """
    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        # Find module by ID
        module = next((m for m in course.modules if m.id == module_id), None)
        if not module:
            return jsonify({"error": "Module not found"}), 404

        # Return lessons sorted by order
        lessons = sorted(module.lessons, key=lambda l: l.order)
        return jsonify([l.to_dict() for l in lessons])

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@lessons_bp.route('/api/courses/<course_id>/modules/<module_id>/lessons', methods=['POST'])
@login_required
@require_permission('add_structure')
def create_lesson(course_id, module_id):
    """Create a new lesson in a module.

    Args:
        course_id: Course identifier.
        module_id: Module identifier.

    Request JSON:
        {
            "title": str,
            "description": str (optional)
        }

    Returns:
        JSON lesson object with 201 status.

    Errors:
        404 if course or module not found.
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

        # Find module by ID
        module = next((m for m in course.modules if m.id == module_id), None)
        if not module:
            return jsonify({"error": "Module not found"}), 404

        # Create new lesson with auto-assigned order
        lesson = Lesson(
            title=data['title'],
            description=data.get('description', ''),
            order=len(module.lessons)
        )

        # Add to module and save
        module.lessons.append(lesson)
        _project_store.save(owner_id, course)

        # Log audit entry
        log_audit_entry(
            course_id=course_id,
            user_id=current_user.id,
            action=ACTION_STRUCTURE_ADDED,
            entity_type='lesson',
            entity_id=lesson.id,
            after={'name': lesson.title, 'description': lesson.description}
        )

        return jsonify(lesson.to_dict()), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@lessons_bp.route('/api/courses/<course_id>/lessons/<lesson_id>', methods=['PUT'])
@login_required
@require_permission('add_structure')
def update_lesson(course_id, lesson_id):
    """Update lesson title and/or description.

    Args:
        course_id: Course identifier.
        lesson_id: Lesson identifier.

    Request JSON:
        {
            "title": str (optional),
            "description": str (optional)
        }

    Returns:
        JSON updated lesson object.

    Errors:
        404 if course or lesson not found.
        400 if request JSON is invalid.
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

        # Find lesson by traversing course structure
        lesson, module = _find_lesson(course, lesson_id)
        if not lesson:
            return jsonify({"error": "Lesson not found"}), 404

        # Capture before state for audit
        before_state = {'title': lesson.title, 'description': lesson.description}

        # Update fields
        if 'title' in data:
            lesson.title = data['title']
        if 'description' in data:
            lesson.description = data['description']

        lesson.updated_at = datetime.now().isoformat()

        # Save course
        _project_store.save(owner_id, course)

        # Log audit entry with before/after
        log_audit_entry(
            course_id=course_id,
            user_id=current_user.id,
            action=ACTION_STRUCTURE_UPDATED,
            entity_type='lesson',
            entity_id=lesson_id,
            before=before_state,
            after={'title': lesson.title, 'description': lesson.description}
        )

        return jsonify(lesson.to_dict())

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@lessons_bp.route('/api/courses/<course_id>/lessons/<lesson_id>', methods=['DELETE'])
@login_required
@require_permission('delete_structure')
def delete_lesson(course_id, lesson_id):
    """Delete a lesson and clean up learning outcome mappings.

    Collects all activity IDs from lesson and removes them from
    all learning outcome mapped_activity_ids. Removes lesson from module
    and renumbers remaining lessons.

    Args:
        course_id: Course identifier.
        lesson_id: Lesson identifier.

    Returns:
        JSON success message with 200 status.

    Errors:
        404 if course or lesson not found.
        500 if save fails.
    """
    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        # Find lesson by traversing course structure
        lesson, module = _find_lesson(course, lesson_id)
        if not lesson:
            return jsonify({"error": "Lesson not found"}), 404

        # Store lesson info for audit before deletion
        deleted_lesson_title = lesson.title

        # Collect all activity IDs from lesson
        activity_ids = set()
        for activity in lesson.activities:
            activity_ids.add(activity.id)

        # Remove activity IDs from all learning outcome mappings
        for outcome in course.learning_outcomes:
            outcome.mapped_activity_ids = [
                aid for aid in outcome.mapped_activity_ids
                if aid not in activity_ids
            ]

        # Remove lesson from module
        module.lessons = [l for l in module.lessons if l.id != lesson_id]

        # Renumber remaining lessons
        for i, les in enumerate(module.lessons):
            les.order = i

        # Save course
        _project_store.save(owner_id, course)

        # Log audit entry
        log_audit_entry(
            course_id=course_id,
            user_id=current_user.id,
            action=ACTION_STRUCTURE_DELETED,
            entity_type='lesson',
            entity_id=lesson_id,
            before={'name': deleted_lesson_title}
        )

        return jsonify({"message": "Lesson deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@lessons_bp.route('/api/courses/<course_id>/modules/<module_id>/lessons/reorder', methods=['PUT'])
@login_required
@require_permission('reorder_structure')
def reorder_lessons(course_id, module_id):
    """Reorder lessons within a module.

    Moves lesson from old_index to new_index and renumbers all lessons.

    Args:
        course_id: Course identifier.
        module_id: Module identifier.

    Request JSON:
        {
            "old_index": int,
            "new_index": int
        }

    Returns:
        JSON array of reordered lessons with 200 status.

    Errors:
        404 if course or module not found.
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

        # Find module by ID
        module = next((m for m in course.modules if m.id == module_id), None)
        if not module:
            return jsonify({"error": "Module not found"}), 404

        # Validate indices
        if not isinstance(old_index, int) or not isinstance(new_index, int):
            return jsonify({"error": "Indices must be integers"}), 400

        if old_index < 0 or old_index >= len(module.lessons):
            return jsonify({"error": "old_index out of range"}), 400

        if new_index < 0 or new_index >= len(module.lessons):
            return jsonify({"error": "new_index out of range"}), 400

        # Reorder lessons
        lesson = module.lessons.pop(old_index)
        module.lessons.insert(new_index, lesson)

        # Renumber all lessons
        for i, les in enumerate(module.lessons):
            les.order = i

        # Save course
        _project_store.save(owner_id, course)

        # Log audit entry
        log_audit_entry(
            course_id=course_id,
            user_id=current_user.id,
            action=ACTION_STRUCTURE_REORDERED,
            entity_type='lessons',
            after={'old_index': old_index, 'new_index': new_index, 'module_id': module_id}
        )

        # Return updated lessons list
        return jsonify([l.to_dict() for l in module.lessons]), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
