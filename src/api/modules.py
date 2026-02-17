"""Module CRUD API endpoints using Flask Blueprint pattern.

Provides endpoints for creating, reading, updating, deleting, and reordering
modules within a course. All endpoints follow atomic save pattern with
project_store load/modify/save.
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime

from src.core.models import Module
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
modules_bp = Blueprint('modules', __name__)

# Module-level project_store reference (set during registration)
_project_store = None


def init_modules_bp(project_store):
    """Initialize the modules blueprint with a ProjectStore instance.

    Must be called before registering the blueprint with Flask app.

    Args:
        project_store: ProjectStore instance for course persistence.
    """
    global _project_store
    _project_store = project_store


@modules_bp.route('/api/courses/<course_id>/modules', methods=['GET'])
@login_required
@require_permission('view_content')
def list_modules(course_id):
    """List all modules for a course.

    Args:
        course_id: Course identifier.

    Returns:
        JSON array of module dictionaries sorted by order.

    Errors:
        404 if course not found.
        500 if load fails.
    """
    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        # Return modules sorted by order
        modules = sorted(course.modules, key=lambda m: m.order)
        return jsonify([m.to_dict() for m in modules])

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@modules_bp.route('/api/courses/<course_id>/modules', methods=['POST'])
@login_required
@require_permission('add_structure')
def create_module(course_id):
    """Create a new module in a course.

    Args:
        course_id: Course identifier.

    Request JSON:
        {
            "title": str,
            "description": str (optional)
        }

    Returns:
        JSON module object with 201 status.

    Errors:
        404 if course not found.
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

        # Create new module with auto-assigned order
        module = Module(
            title=data['title'],
            description=data.get('description', ''),
            order=len(course.modules)
        )

        # Add to course and save
        course.modules.append(module)
        _project_store.save(owner_id, course)

        # Log audit entry
        log_audit_entry(
            course_id=course_id,
            user_id=current_user.id,
            action=ACTION_STRUCTURE_ADDED,
            entity_type='module',
            entity_id=module.id,
            after={'name': module.title, 'description': module.description}
        )

        return jsonify(module.to_dict()), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@modules_bp.route('/api/courses/<course_id>/modules/<module_id>', methods=['PUT'])
@login_required
@require_permission('add_structure')
def update_module(course_id, module_id):
    """Update module title and/or description.

    Args:
        course_id: Course identifier.
        module_id: Module identifier.

    Request JSON:
        {
            "title": str (optional),
            "description": str (optional)
        }

    Returns:
        JSON updated module object.

    Errors:
        404 if course or module not found.
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

        # Find module by ID
        module = next((m for m in course.modules if m.id == module_id), None)
        if not module:
            return jsonify({"error": "Module not found"}), 404

        # Capture before state for audit
        before_state = {'title': module.title, 'description': module.description}

        # Update fields
        if 'title' in data:
            module.title = data['title']
        if 'description' in data:
            module.description = data['description']

        module.updated_at = datetime.now().isoformat()

        # Save course
        _project_store.save(owner_id, course)

        # Log audit entry with before/after
        log_audit_entry(
            course_id=course_id,
            user_id=current_user.id,
            action=ACTION_STRUCTURE_UPDATED,
            entity_type='module',
            entity_id=module_id,
            before=before_state,
            after={'title': module.title, 'description': module.description}
        )

        return jsonify(module.to_dict())

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@modules_bp.route('/api/courses/<course_id>/modules/<module_id>', methods=['DELETE'])
@login_required
@require_permission('delete_structure')
def delete_module(course_id, module_id):
    """Delete a module and clean up learning outcome mappings.

    Collects all activity IDs from module's lessons and removes them from
    all learning outcome mapped_activity_ids. Removes module from course
    and renumbers remaining modules.

    Args:
        course_id: Course identifier.
        module_id: Module identifier.

    Returns:
        JSON success message with 200 status.

    Errors:
        404 if course or module not found.
        500 if save fails.
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

        # Store module info for audit before deletion
        deleted_module_title = module.title

        # Collect all activity IDs from module's lessons
        activity_ids = set()
        for lesson in module.lessons:
            for activity in lesson.activities:
                activity_ids.add(activity.id)

        # Remove activity IDs from all learning outcome mappings
        for outcome in course.learning_outcomes:
            outcome.mapped_activity_ids = [
                aid for aid in outcome.mapped_activity_ids
                if aid not in activity_ids
            ]

        # Remove module from course
        course.modules = [m for m in course.modules if m.id != module_id]

        # Renumber remaining modules
        for i, mod in enumerate(course.modules):
            mod.order = i

        # Save course
        _project_store.save(owner_id, course)

        # Log audit entry
        log_audit_entry(
            course_id=course_id,
            user_id=current_user.id,
            action=ACTION_STRUCTURE_DELETED,
            entity_type='module',
            entity_id=module_id,
            before={'name': deleted_module_title}
        )

        return jsonify({"message": "Module deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@modules_bp.route('/api/courses/<course_id>/modules/reorder', methods=['PUT'])
@login_required
@require_permission('reorder_structure')
def reorder_modules(course_id):
    """Reorder modules within a course.

    Moves module from old_index to new_index and renumbers all modules.

    Args:
        course_id: Course identifier.

    Request JSON:
        {
            "old_index": int,
            "new_index": int
        }

    Returns:
        JSON array of reordered modules with 200 status.

    Errors:
        404 if course not found.
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

        # Validate indices
        if not isinstance(old_index, int) or not isinstance(new_index, int):
            return jsonify({"error": "Indices must be integers"}), 400

        if old_index < 0 or old_index >= len(course.modules):
            return jsonify({"error": "old_index out of range"}), 400

        if new_index < 0 or new_index >= len(course.modules):
            return jsonify({"error": "new_index out of range"}), 400

        # Reorder modules
        module = course.modules.pop(old_index)
        course.modules.insert(new_index, module)

        # Renumber all modules
        for i, mod in enumerate(course.modules):
            mod.order = i

        # Save course
        _project_store.save(owner_id, course)

        # Log audit entry
        log_audit_entry(
            course_id=course_id,
            user_id=current_user.id,
            action=ACTION_STRUCTURE_REORDERED,
            entity_type='modules',
            after={'old_index': old_index, 'new_index': new_index}
        )

        # Return updated modules list
        return jsonify([m.to_dict() for m in course.modules]), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
