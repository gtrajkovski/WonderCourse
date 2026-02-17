"""Learner profile API endpoints.

Provides CRUD operations for LearnerProfile management.
Learner profiles describe target audience characteristics that
influence content generation.
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from pathlib import Path
import json

from src.core.models import (
    LearnerProfile,
    TechnicalLevel,
    LanguageProficiency,
    LearningPreference,
    LearningContext
)
from src.collab.decorators import require_permission
from src.collab.models import Collaborator


# Create Blueprint
learner_profiles_bp = Blueprint('learner_profiles', __name__)

# Module-level store path
_profiles_dir = Path("learner_profiles")


def init_learner_profiles_bp(profiles_dir: Path = None):
    """Initialize the learner profiles blueprint.

    Args:
        profiles_dir: Optional path to profiles directory.
    """
    global _profiles_dir
    if profiles_dir is not None:
        _profiles_dir = profiles_dir
    _profiles_dir.mkdir(parents=True, exist_ok=True)
    _ensure_default_profiles()


def _ensure_default_profiles():
    """Create default learner profiles if they don't exist."""
    defaults = [
        LearnerProfile(
            id="lp_beginner_professional",
            name="Beginner Professional",
            description="Entry-level professional with limited technical background seeking foundational skills.",
            technical_level=TechnicalLevel.BASIC,
            learning_context=LearningContext.PROFESSIONAL,
            attention_span_minutes=10,
            prefers_examples=True,
            prefers_analogies=True,
        ),
        LearnerProfile(
            id="lp_intermediate_developer",
            name="Intermediate Developer",
            description="Software developer with 2-5 years experience looking to expand skills.",
            technical_level=TechnicalLevel.INTERMEDIATE,
            prior_knowledge=["Programming fundamentals", "Version control"],
            learning_context=LearningContext.UPSKILLING,
            learning_preference=LearningPreference.HANDS_ON,
            attention_span_minutes=20,
        ),
        LearnerProfile(
            id="lp_career_changer",
            name="Career Changer",
            description="Professional transitioning into tech from another field.",
            technical_level=TechnicalLevel.BASIC,
            learning_context=LearningContext.CAREER_CHANGE,
            prefers_examples=True,
            prefers_analogies=True,
            available_hours_per_week=10,
            learning_goals=["Build portfolio", "Land entry-level role"],
        ),
        LearnerProfile(
            id="lp_esl_learner",
            name="ESL Learner",
            description="Non-native English speaker with intermediate language proficiency.",
            technical_level=TechnicalLevel.INTERMEDIATE,
            language_proficiency=LanguageProficiency.INTERMEDIATE,
            attention_span_minutes=12,
            prefers_examples=True,
        ),
    ]

    for profile in defaults:
        path = _profiles_dir / f"{profile.id}.json"
        if not path.exists():
            _save_profile(profile)


def _save_profile(profile: LearnerProfile):
    """Save a profile to disk."""
    path = _profiles_dir / f"{profile.id}.json"
    path.write_text(json.dumps(profile.to_dict(), indent=2))


def _load_profile(profile_id: str) -> LearnerProfile:
    """Load a profile from disk."""
    path = _profiles_dir / f"{profile_id}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return LearnerProfile.from_dict(data)


def _list_profiles() -> list:
    """List all profiles."""
    profiles = []
    for path in _profiles_dir.glob("*.json"):
        try:
            data = json.loads(path.read_text())
            profiles.append(LearnerProfile.from_dict(data))
        except Exception:
            continue
    return sorted(profiles, key=lambda p: p.name)


def _delete_profile(profile_id: str) -> bool:
    """Delete a profile from disk."""
    path = _profiles_dir / f"{profile_id}.json"
    if path.exists():
        path.unlink()
        return True
    return False


@learner_profiles_bp.route('/api/learner-profiles', methods=['GET'])
@login_required
def list_learner_profiles():
    """List all learner profiles.

    Returns:
        JSON array of profile dictionaries.
    """
    try:
        profiles = _list_profiles()
        return jsonify([p.to_dict() for p in profiles])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@learner_profiles_bp.route('/api/learner-profiles/<profile_id>', methods=['GET'])
@login_required
def get_learner_profile(profile_id):
    """Get a single learner profile by ID.

    Args:
        profile_id: Profile identifier.

    Returns:
        JSON profile object.

    Errors:
        404 if profile not found.
    """
    try:
        profile = _load_profile(profile_id)
        if not profile:
            return jsonify({"error": "Learner profile not found"}), 404
        return jsonify(profile.to_dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@learner_profiles_bp.route('/api/learner-profiles', methods=['POST'])
@login_required
def create_learner_profile():
    """Create a new learner profile.

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
        profile = LearnerProfile.from_dict(data)
        _save_profile(profile)
        return jsonify(profile.to_dict()), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@learner_profiles_bp.route('/api/learner-profiles/<profile_id>', methods=['PUT'])
@login_required
def update_learner_profile(profile_id):
    """Update a learner profile.

    Args:
        profile_id: Profile identifier.

    Request JSON:
        {...profile fields to update}

    Returns:
        JSON updated profile object.

    Errors:
        404 if profile not found.
        400 if JSON is invalid.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    try:
        profile = _load_profile(profile_id)
        if not profile:
            return jsonify({"error": "Learner profile not found"}), 404

        # Update fields from data (preserve id)
        updated_data = profile.to_dict()
        for key, value in data.items():
            if key != 'id':
                updated_data[key] = value
        updated_data['updated_at'] = datetime.now().isoformat()

        updated_profile = LearnerProfile.from_dict(updated_data)
        _save_profile(updated_profile)

        return jsonify(updated_profile.to_dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@learner_profiles_bp.route('/api/learner-profiles/<profile_id>', methods=['DELETE'])
@login_required
def delete_learner_profile(profile_id):
    """Delete a learner profile.

    Args:
        profile_id: Profile identifier.

    Returns:
        JSON success message with 200 status.

    Errors:
        404 if profile not found.
    """
    try:
        if not _delete_profile(profile_id):
            return jsonify({"error": "Learner profile not found"}), 404
        return jsonify({"message": "Learner profile deleted successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@learner_profiles_bp.route('/api/learner-profiles/<profile_id>/prompt-context', methods=['GET'])
@login_required
def get_profile_prompt_context(profile_id):
    """Get the prompt context string for a learner profile.

    This is the formatted text that gets injected into AI prompts
    to tailor content generation for the target audience.

    Args:
        profile_id: Profile identifier.

    Returns:
        JSON with prompt_context string.

    Errors:
        404 if profile not found.
    """
    try:
        profile = _load_profile(profile_id)
        if not profile:
            return jsonify({"error": "Learner profile not found"}), 404

        return jsonify({
            "profile_id": profile_id,
            "profile_name": profile.name,
            "prompt_context": profile.to_prompt_context()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@learner_profiles_bp.route('/api/courses/<course_id>/learner-profile', methods=['GET'])
@login_required
@require_permission('view_content')
def get_course_learner_profile(course_id):
    """Get the learner profile for a course.

    Args:
        course_id: Course identifier.

    Returns:
        JSON profile object (course's assigned profile or null).

    Errors:
        404 if course not found.
    """
    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        from app import project_store
        course = project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        if not course.learner_profile_id:
            return jsonify({"profile": None})

        profile = _load_profile(course.learner_profile_id)
        if not profile:
            return jsonify({"profile": None})

        return jsonify({"profile": profile.to_dict()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@learner_profiles_bp.route('/api/courses/<course_id>/learner-profile', methods=['PUT'])
@login_required
@require_permission('edit_content')
def set_course_learner_profile(course_id):
    """Set the learner profile for a course.

    Args:
        course_id: Course identifier.

    Request JSON:
        {
            "profile_id": str (required, or null to unset)
        }

    Returns:
        JSON updated profile assignment.

    Errors:
        404 if course or profile not found.
        400 if profile_id is missing.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    if 'profile_id' not in data:
        return jsonify({"error": "Missing required field: profile_id"}), 400

    try:
        profile_id = data['profile_id']

        # Verify profile exists (unless unsetting)
        if profile_id is not None:
            profile = _load_profile(profile_id)
            if not profile:
                return jsonify({"error": "Learner profile not found"}), 404

        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        from app import project_store
        course = project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        # Update course's learner profile
        course.learner_profile_id = profile_id
        course.updated_at = datetime.now().isoformat()
        project_store.save(owner_id, course)

        return jsonify({
            "message": "Learner profile updated",
            "profile_id": profile_id
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@learner_profiles_bp.route('/api/learner-profiles/enum-values', methods=['GET'])
def get_enum_values():
    """Get available enum values for learner profile fields.

    Returns:
        JSON object with enum values for each enum field.
    """
    return jsonify({
        "technical_levels": [e.value for e in TechnicalLevel],
        "language_proficiencies": [e.value for e in LanguageProficiency],
        "learning_preferences": [e.value for e in LearningPreference],
        "learning_contexts": [e.value for e in LearningContext],
    })
