"""Developer notes API endpoints.

Provides endpoints for CRUD operations on developer notes at course,
module, lesson, and activity levels. Notes are internal author annotations
that are excluded from learner exports.
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime

from src.core.models import DeveloperNote
from src.collab.decorators import require_permission
from src.collab.models import Collaborator


# Create Blueprint
notes_bp = Blueprint('notes', __name__)

# Module-level project_store reference (set during registration)
_project_store = None


def init_notes_bp(project_store):
    """Initialize the notes blueprint with a ProjectStore instance.

    Args:
        project_store: ProjectStore instance for course persistence.
    """
    global _project_store
    _project_store = project_store


def _find_note_in_list(notes_list, note_id):
    """Find a note by ID in a notes list.

    Args:
        notes_list: List of DeveloperNote objects.
        note_id: Note ID to find.

    Returns:
        Tuple of (index, note) or (None, None) if not found.
    """
    for i, note in enumerate(notes_list):
        if note.id == note_id:
            return i, note
    return None, None


def _find_note_location(course, note_id):
    """Find which entity contains a note.

    Args:
        course: Course object to search.
        note_id: Note ID to find.

    Returns:
        Tuple of (entity_type, entity, index, note) or (None, None, None, None).
    """
    # Check course-level notes
    idx, note = _find_note_in_list(course.developer_notes, note_id)
    if note:
        return 'course', course, idx, note

    # Check modules
    for module in course.modules:
        idx, note = _find_note_in_list(module.developer_notes, note_id)
        if note:
            return 'module', module, idx, note

        # Check lessons
        for lesson in module.lessons:
            idx, note = _find_note_in_list(lesson.developer_notes, note_id)
            if note:
                return 'lesson', lesson, idx, note

            # Check activities
            for activity in lesson.activities:
                idx, note = _find_note_in_list(activity.developer_notes, note_id)
                if note:
                    return 'activity', activity, idx, note

    return None, None, None, None


def _find_module(course, module_id):
    """Find a module by ID."""
    for module in course.modules:
        if module.id == module_id:
            return module
    return None


def _find_lesson(course, lesson_id):
    """Find a lesson by ID."""
    for module in course.modules:
        for lesson in module.lessons:
            if lesson.id == lesson_id:
                return lesson
    return None


def _find_activity(course, activity_id):
    """Find an activity by ID."""
    for module in course.modules:
        for lesson in module.lessons:
            for activity in lesson.activities:
                if activity.id == activity_id:
                    return activity
    return None


def _sort_notes(notes_list):
    """Sort notes with pinned first, then by created_at descending."""
    return sorted(
        notes_list,
        key=lambda n: (not n.pinned, n.created_at),
        reverse=False  # pinned=True (not False) comes first
    )


# ===========================
# List All Notes
# ===========================


@notes_bp.route('/api/courses/<course_id>/notes', methods=['GET'])
@login_required
def list_all_notes(course_id):
    """List all developer notes in a course.

    Returns notes from all levels: course, modules, lessons, and activities.

    Returns:
        JSON with notes grouped by entity type.
    """
    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        result = {
            "course": [n.to_dict() for n in _sort_notes(course.developer_notes)],
            "modules": {},
            "lessons": {},
            "activities": {}
        }

        for module in course.modules:
            if module.developer_notes:
                result["modules"][module.id] = {
                    "title": module.title,
                    "notes": [n.to_dict() for n in _sort_notes(module.developer_notes)]
                }

            for lesson in module.lessons:
                if lesson.developer_notes:
                    result["lessons"][lesson.id] = {
                        "title": lesson.title,
                        "notes": [n.to_dict() for n in _sort_notes(lesson.developer_notes)]
                    }

                for activity in lesson.activities:
                    if activity.developer_notes:
                        result["activities"][activity.id] = {
                            "title": activity.title,
                            "notes": [n.to_dict() for n in _sort_notes(activity.developer_notes)]
                        }

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===========================
# Course-Level Notes
# ===========================


@notes_bp.route('/api/courses/<course_id>/notes', methods=['POST'])
@login_required
@require_permission('edit_content')
def create_course_note(course_id):
    """Create a note at course level.

    Request JSON:
        {
            "content": "Note content",
            "pinned": false  // optional
        }

    Returns:
        JSON with created note.
    """
    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        data = request.get_json() or {}
        content = data.get('content', '').strip()

        if not content:
            return jsonify({"error": "Note content is required"}), 400

        note = DeveloperNote(
            content=content,
            author_id=current_user.id,
            author_name=current_user.name or current_user.email,
            pinned=data.get('pinned', False)
        )

        course.developer_notes.append(note)
        course.updated_at = datetime.now().isoformat()
        _project_store.save(owner_id, course)

        return jsonify(note.to_dict()), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===========================
# Module-Level Notes
# ===========================


@notes_bp.route('/api/courses/<course_id>/modules/<module_id>/notes', methods=['GET'])
@login_required
def list_module_notes(course_id, module_id):
    """List notes for a module."""
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

        notes = [n.to_dict() for n in _sort_notes(module.developer_notes)]
        return jsonify({"notes": notes}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@notes_bp.route('/api/courses/<course_id>/modules/<module_id>/notes', methods=['POST'])
@login_required
@require_permission('edit_content')
def create_module_note(course_id, module_id):
    """Create a note on a module."""
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

        data = request.get_json() or {}
        content = data.get('content', '').strip()

        if not content:
            return jsonify({"error": "Note content is required"}), 400

        note = DeveloperNote(
            content=content,
            author_id=current_user.id,
            author_name=current_user.name or current_user.email,
            pinned=data.get('pinned', False)
        )

        module.developer_notes.append(note)
        course.updated_at = datetime.now().isoformat()
        _project_store.save(owner_id, course)

        return jsonify(note.to_dict()), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===========================
# Lesson-Level Notes
# ===========================


@notes_bp.route('/api/courses/<course_id>/lessons/<lesson_id>/notes', methods=['GET'])
@login_required
def list_lesson_notes(course_id, lesson_id):
    """List notes for a lesson."""
    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        lesson = _find_lesson(course, lesson_id)
        if not lesson:
            return jsonify({"error": "Lesson not found"}), 404

        notes = [n.to_dict() for n in _sort_notes(lesson.developer_notes)]
        return jsonify({"notes": notes}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@notes_bp.route('/api/courses/<course_id>/lessons/<lesson_id>/notes', methods=['POST'])
@login_required
@require_permission('edit_content')
def create_lesson_note(course_id, lesson_id):
    """Create a note on a lesson."""
    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        lesson = _find_lesson(course, lesson_id)
        if not lesson:
            return jsonify({"error": "Lesson not found"}), 404

        data = request.get_json() or {}
        content = data.get('content', '').strip()

        if not content:
            return jsonify({"error": "Note content is required"}), 400

        note = DeveloperNote(
            content=content,
            author_id=current_user.id,
            author_name=current_user.name or current_user.email,
            pinned=data.get('pinned', False)
        )

        lesson.developer_notes.append(note)
        course.updated_at = datetime.now().isoformat()
        _project_store.save(owner_id, course)

        return jsonify(note.to_dict()), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===========================
# Activity-Level Notes
# ===========================


@notes_bp.route('/api/courses/<course_id>/activities/<activity_id>/notes', methods=['GET'])
@login_required
def list_activity_notes(course_id, activity_id):
    """List notes for an activity."""
    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        activity = _find_activity(course, activity_id)
        if not activity:
            return jsonify({"error": "Activity not found"}), 404

        notes = [n.to_dict() for n in _sort_notes(activity.developer_notes)]
        return jsonify({"notes": notes}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@notes_bp.route('/api/courses/<course_id>/activities/<activity_id>/notes', methods=['POST'])
@login_required
@require_permission('edit_content')
def create_activity_note(course_id, activity_id):
    """Create a note on an activity."""
    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        activity = _find_activity(course, activity_id)
        if not activity:
            return jsonify({"error": "Activity not found"}), 404

        data = request.get_json() or {}
        content = data.get('content', '').strip()

        if not content:
            return jsonify({"error": "Note content is required"}), 400

        note = DeveloperNote(
            content=content,
            author_id=current_user.id,
            author_name=current_user.name or current_user.email,
            pinned=data.get('pinned', False)
        )

        activity.developer_notes.append(note)
        course.updated_at = datetime.now().isoformat()
        _project_store.save(owner_id, course)

        return jsonify(note.to_dict()), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===========================
# Update/Delete Notes
# ===========================


@notes_bp.route('/api/courses/<course_id>/notes/<note_id>', methods=['PUT'])
@login_required
@require_permission('edit_content')
def update_note(course_id, note_id):
    """Update a note's content or pinned status.

    Request JSON:
        {
            "content": "Updated content",  // optional
            "pinned": true  // optional
        }

    Returns:
        JSON with updated note.
    """
    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        entity_type, entity, idx, note = _find_note_location(course, note_id)
        if not note:
            return jsonify({"error": "Note not found"}), 404

        data = request.get_json() or {}

        if 'content' in data:
            content = data['content'].strip()
            if not content:
                return jsonify({"error": "Note content cannot be empty"}), 400
            note.content = content

        if 'pinned' in data:
            note.pinned = bool(data['pinned'])

        note.updated_at = datetime.now().isoformat()
        course.updated_at = datetime.now().isoformat()
        _project_store.save(owner_id, course)

        return jsonify(note.to_dict()), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@notes_bp.route('/api/courses/<course_id>/notes/<note_id>', methods=['DELETE'])
@login_required
@require_permission('edit_content')
def delete_note(course_id, note_id):
    """Delete a note.

    Returns:
        JSON with success message.
    """
    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        entity_type, entity, idx, note = _find_note_location(course, note_id)
        if not note:
            return jsonify({"error": "Note not found"}), 404

        # Remove note from the entity's notes list
        entity.developer_notes.pop(idx)

        course.updated_at = datetime.now().isoformat()
        _project_store.save(owner_id, course)

        return jsonify({"message": "Note deleted"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
