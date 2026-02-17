"""Standards profile API endpoints.

Provides CRUD operations for ContentStandardsProfile management.
Standards are global (not per-course) and support system presets
that cannot be deleted or modified.
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required
from datetime import datetime

from src.core.standards_store import StandardsStore
from src.core.models import ContentStandardsProfile
from src.validators.standards_validator import (
    StandardsValidator,
    validate_content,
)


# Create Blueprint
standards_bp = Blueprint('standards', __name__)

# Module-level store reference (lazy initialization)
_standards_store = None


def get_standards_store() -> StandardsStore:
    """Get or create the standards store singleton."""
    global _standards_store
    if _standards_store is None:
        _standards_store = StandardsStore()
    return _standards_store


def init_standards_bp(standards_store: StandardsStore = None):
    """Initialize the standards blueprint with optional store override.

    Args:
        standards_store: Optional StandardsStore instance. If None, uses default.
    """
    global _standards_store
    if standards_store is not None:
        _standards_store = standards_store


@standards_bp.route('/api/standards', methods=['GET'])
@login_required
def list_standards():
    """List all standards profiles.

    Returns:
        JSON array of profile dictionaries.
        System presets are listed first, then custom profiles sorted by name.
    """
    try:
        store = get_standards_store()
        profiles = store.list_all()
        return jsonify([p.to_dict() for p in profiles])

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@standards_bp.route('/api/standards/<profile_id>', methods=['GET'])
@login_required
def get_standard(profile_id):
    """Get a single standards profile by ID.

    Args:
        profile_id: Profile identifier.

    Returns:
        JSON profile object.

    Errors:
        404 if profile not found.
    """
    try:
        store = get_standards_store()
        profile = store.load(profile_id)

        if not profile:
            return jsonify({"error": "Standards profile not found"}), 404

        return jsonify(profile.to_dict())

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@standards_bp.route('/api/standards', methods=['POST'])
@login_required
def create_standard():
    """Create a new custom standards profile.

    Request JSON:
        {
            "name": str (required),
            "description": str (optional),
            ...other profile fields
        }

    Returns:
        JSON profile object with 201 status.

    Errors:
        400 if name is missing or JSON is invalid.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    if 'name' not in data:
        return jsonify({"error": "Missing required field: name"}), 400

    try:
        # Ensure it's not marked as system preset
        data['is_system_preset'] = False

        # Create profile from data
        profile = ContentStandardsProfile.from_dict(data)

        # Save to store
        store = get_standards_store()
        store.save(profile)

        return jsonify(profile.to_dict()), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@standards_bp.route('/api/standards/<profile_id>', methods=['PUT'])
@login_required
def update_standard(profile_id):
    """Update a standards profile.

    System presets cannot be modified.

    Args:
        profile_id: Profile identifier.

    Request JSON:
        {
            ...profile fields to update
        }

    Returns:
        JSON updated profile object.

    Errors:
        404 if profile not found.
        403 if attempting to modify a system preset.
        400 if JSON is invalid.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    try:
        store = get_standards_store()
        profile = store.load(profile_id)

        if not profile:
            return jsonify({"error": "Standards profile not found"}), 404

        if profile.is_system_preset:
            return jsonify({
                "error": "Cannot modify system preset. Duplicate it first to create a custom profile."
            }), 403

        # Update fields from data (preserve id and is_system_preset)
        updated_data = profile.to_dict()
        for key, value in data.items():
            if key not in ('id', 'is_system_preset'):
                updated_data[key] = value

        updated_profile = ContentStandardsProfile.from_dict(updated_data)
        store.save(updated_profile)

        return jsonify(updated_profile.to_dict())

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@standards_bp.route('/api/standards/<profile_id>', methods=['DELETE'])
@login_required
def delete_standard(profile_id):
    """Delete a standards profile.

    System presets cannot be deleted.

    Args:
        profile_id: Profile identifier.

    Returns:
        JSON success message with 200 status.

    Errors:
        404 if profile not found.
        403 if attempting to delete a system preset.
    """
    try:
        store = get_standards_store()
        profile = store.load(profile_id)

        if not profile:
            return jsonify({"error": "Standards profile not found"}), 404

        if profile.is_system_preset:
            return jsonify({"error": "Cannot delete system preset"}), 403

        store.delete(profile_id)
        return jsonify({"message": "Standards profile deleted successfully"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@standards_bp.route('/api/standards/<profile_id>/duplicate', methods=['POST'])
@login_required
def duplicate_standard(profile_id):
    """Duplicate a standards profile.

    Creates a copy of the profile with a new name.
    This is how users customize system presets.

    Args:
        profile_id: Profile identifier to duplicate.

    Request JSON:
        {
            "name": str (required - name for the new profile)
        }

    Returns:
        JSON new profile object with 201 status.

    Errors:
        404 if source profile not found.
        400 if name is missing or JSON is invalid.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    if 'name' not in data:
        return jsonify({"error": "Missing required field: name"}), 400

    try:
        store = get_standards_store()
        new_profile = store.duplicate(profile_id, data['name'])

        if not new_profile:
            return jsonify({"error": "Source profile not found"}), 404

        return jsonify(new_profile.to_dict()), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@standards_bp.route('/api/standards/default', methods=['GET'])
@login_required
def get_default_standard():
    """Get the default standards profile (Coursera Short Course).

    Returns:
        JSON profile object.
    """
    try:
        store = get_standards_store()
        profile = store.get_default()
        return jsonify(profile.to_dict())

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@standards_bp.route('/api/standards/validate', methods=['POST'])
@login_required
def validate_content_standards():
    """Validate content against a standards profile.

    Request JSON:
        {
            "profile_id": str (optional - uses default if not provided),
            "item_type": str (required - video, reading, quiz, etc.),
            "content": dict (required - the content to validate)
        }

    Returns:
        JSON object with violations list:
        {
            "valid": bool,
            "violation_count": int,
            "violations": [
                {
                    "field": str,
                    "rule": str,
                    "expected": str,
                    "actual": str,
                    "severity": str,
                    "auto_fixable": bool,
                    "fix_suggestion": str or null
                }
            ]
        }

    Errors:
        400 if item_type or content is missing.
        404 if profile_id provided but not found.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    if 'item_type' not in data:
        return jsonify({"error": "Missing required field: item_type"}), 400

    if 'content' not in data:
        return jsonify({"error": "Missing required field: content"}), 400

    try:
        store = get_standards_store()

        # Load profile (use default if not specified)
        profile_id = data.get('profile_id')
        if profile_id:
            profile = store.load(profile_id)
            if not profile:
                return jsonify({"error": "Standards profile not found"}), 404
        else:
            profile = store.get_default()

        # Validate content
        violations = validate_content(
            item_type=data['item_type'],
            content=data['content'],
            standards=profile
        )

        return jsonify({
            "valid": len(violations) == 0,
            "violation_count": len(violations),
            "violations": [v.to_dict() for v in violations]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@standards_bp.route('/api/courses/<course_id>/standards', methods=['GET'])
@login_required
def get_course_standards(course_id):
    """Get the active standards profile for a course.

    Args:
        course_id: Course identifier.

    Returns:
        JSON profile object (course's assigned profile or default).

    Errors:
        404 if course not found.
    """
    # Import here to avoid circular import
    from src.collab.models import Collaborator

    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        # Import project store dynamically
        from app import project_store
        course = project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        store = get_standards_store()
        profile = store.get_for_course(course)

        return jsonify(profile.to_dict())

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@standards_bp.route('/api/standards/<profile_id>/export', methods=['GET'])
@login_required
def export_standard(profile_id):
    """Export a standards profile as JSON for download/sharing.

    Args:
        profile_id: Profile identifier to export.

    Returns:
        JSON profile object with export metadata.

    Errors:
        404 if profile not found.
    """
    try:
        store = get_standards_store()
        profile = store.load(profile_id)

        if not profile:
            return jsonify({"error": "Standards profile not found"}), 404

        # Create export format with metadata
        export_data = profile.to_dict()
        export_data["_export_version"] = "1.0"
        export_data["_exported_at"] = datetime.now().isoformat()

        # Remove internal fields that shouldn't be exported
        export_data.pop("id", None)  # New ID will be assigned on import
        export_data["is_system_preset"] = False  # Exported presets are custom

        return jsonify(export_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@standards_bp.route('/api/standards/import', methods=['POST'])
@login_required
def import_standard():
    """Import a standards profile from JSON.

    Request JSON:
        {
            "name": str (optional - uses profile's name if not provided),
            "profile": { ...profile fields }
        }

    Returns:
        JSON new profile object with 201 status.

    Errors:
        400 if profile is missing or invalid.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    if 'profile' not in data:
        return jsonify({"error": "Missing required field: profile"}), 400

    try:
        profile_data = data['profile']

        # Override name if provided
        if 'name' in data:
            profile_data['name'] = data['name']

        if 'name' not in profile_data:
            return jsonify({"error": "Profile must have a name"}), 400

        # Remove export metadata if present
        profile_data.pop("_export_version", None)
        profile_data.pop("_exported_at", None)
        profile_data.pop("id", None)  # Generate new ID

        # Ensure it's not marked as system preset
        profile_data['is_system_preset'] = False

        # Create and save profile
        profile = ContentStandardsProfile.from_dict(profile_data)
        store = get_standards_store()
        store.save(profile)

        return jsonify(profile.to_dict()), 201

    except ValueError as e:
        return jsonify({"error": f"Invalid profile data: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@standards_bp.route('/api/courses/<course_id>/standards', methods=['PUT'])
@login_required
def set_course_standards(course_id):
    """Set the standards profile for a course.

    Args:
        course_id: Course identifier.

    Request JSON:
        {
            "profile_id": str (required)
        }

    Returns:
        JSON updated course object.

    Errors:
        404 if course or profile not found.
        400 if profile_id is missing.
    """
    from src.collab.models import Collaborator

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    if 'profile_id' not in data:
        return jsonify({"error": "Missing required field: profile_id"}), 400

    try:
        # Verify profile exists
        store = get_standards_store()
        profile = store.load(data['profile_id'])
        if not profile:
            return jsonify({"error": "Standards profile not found"}), 404

        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        from app import project_store
        course = project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        # Update course's standards profile
        course.standards_profile_id = data['profile_id']
        project_store.save(owner_id, course)

        return jsonify({
            "message": "Standards profile updated",
            "profile": profile.to_dict()
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
