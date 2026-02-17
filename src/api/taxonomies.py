"""Cognitive taxonomy API endpoints.

Provides CRUD operations for taxonomy management and course assignment.
System presets (Bloom's, SOLO, Webb's DOK, Marzano, Fink) cannot be
modified or deleted.
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from pathlib import Path

from src.core.models import (
    CognitiveTaxonomy,
    TaxonomyLevel,
    ActivityLevelMapping,
    TaxonomyType,
    ActivityType,
)
from src.core.taxonomy_store import TaxonomyStore
from src.collab.decorators import require_permission
from src.collab.models import Collaborator


# Create Blueprint
taxonomies_bp = Blueprint('taxonomies', __name__)

# Module-level store reference
_taxonomy_store = None
_project_store = None


def init_taxonomies_bp(taxonomy_store: TaxonomyStore, project_store=None):
    """Initialize the taxonomies blueprint.

    Args:
        taxonomy_store: TaxonomyStore instance for taxonomy persistence.
        project_store: Optional ProjectStore for course operations.
    """
    global _taxonomy_store, _project_store
    _taxonomy_store = taxonomy_store
    _project_store = project_store


@taxonomies_bp.route('/api/taxonomies', methods=['GET'])
@login_required
def list_taxonomies():
    """List all taxonomies.

    System presets are listed first, then custom taxonomies sorted by name.

    Returns:
        JSON array of taxonomy dictionaries.
    """
    try:
        taxonomies = _taxonomy_store.list_all()
        return jsonify([t.to_dict() for t in taxonomies])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@taxonomies_bp.route('/api/taxonomies', methods=['POST'])
@login_required
def create_taxonomy():
    """Create a custom taxonomy.

    Request JSON:
        {
            "name": str,
            "description": str (optional),
            "taxonomy_type": "linear" | "categorical" (default "linear"),
            "levels": [
                {
                    "name": str,
                    "value": str,
                    "description": str,
                    "order": int,
                    "example_verbs": [str],
                    "color": str (optional)
                }
            ],
            "require_progression": bool (optional),
            "allow_regression_within": int (optional),
            "minimum_unique_levels": int (optional),
            "require_higher_order": bool (optional),
            "higher_order_threshold": int (optional)
        }

    Returns:
        JSON taxonomy object with 201 status.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    if 'name' not in data:
        return jsonify({"error": "Missing required field: name"}), 400

    if 'levels' not in data or not data['levels']:
        return jsonify({"error": "Taxonomy must have at least one level"}), 400

    try:
        # Parse taxonomy type
        taxonomy_type = TaxonomyType.LINEAR
        if 'taxonomy_type' in data:
            try:
                taxonomy_type = TaxonomyType(data['taxonomy_type'])
            except ValueError:
                return jsonify({"error": f"Invalid taxonomy_type: {data['taxonomy_type']}"}), 400

        # Parse levels
        levels = []
        for i, level_data in enumerate(data['levels']):
            if 'name' not in level_data or 'value' not in level_data:
                return jsonify({"error": f"Level {i} missing required fields: name, value"}), 400

            levels.append(TaxonomyLevel(
                name=level_data['name'],
                value=level_data['value'],
                description=level_data.get('description', ''),
                order=level_data.get('order', i + 1),
                example_verbs=level_data.get('example_verbs', []),
                color=level_data.get('color', '#808080')
            ))

        # Parse activity mappings if provided
        activity_mappings = []
        if 'activity_mappings' in data:
            for mapping_data in data['activity_mappings']:
                try:
                    activity_type = ActivityType(mapping_data['activity_type'])
                except (KeyError, ValueError):
                    continue
                activity_mappings.append(ActivityLevelMapping(
                    activity_type=activity_type,
                    compatible_levels=mapping_data.get('compatible_levels', []),
                    primary_levels=mapping_data.get('primary_levels', [])
                ))

        # Create taxonomy
        taxonomy = CognitiveTaxonomy(
            name=data['name'],
            description=data.get('description', ''),
            taxonomy_type=taxonomy_type,
            is_system_preset=False,
            levels=levels,
            activity_mappings=activity_mappings,
            require_progression=data.get('require_progression', taxonomy_type == TaxonomyType.LINEAR),
            allow_regression_within=data.get('allow_regression_within', 1),
            minimum_unique_levels=data.get('minimum_unique_levels', 2),
            require_higher_order=data.get('require_higher_order', True),
            higher_order_threshold=data.get('higher_order_threshold', len(levels) // 2 + 1)
        )

        _taxonomy_store.save(taxonomy)
        return jsonify(taxonomy.to_dict()), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@taxonomies_bp.route('/api/taxonomies/default', methods=['GET'])
@login_required
def get_default_taxonomy():
    """Get the default taxonomy (Bloom's).

    Returns:
        JSON taxonomy object.
    """
    try:
        taxonomy = _taxonomy_store.get_default()
        return jsonify(taxonomy.to_dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@taxonomies_bp.route('/api/taxonomies/<taxonomy_id>', methods=['GET'])
@login_required
def get_taxonomy(taxonomy_id):
    """Get a single taxonomy by ID.

    Args:
        taxonomy_id: Taxonomy identifier.

    Returns:
        JSON taxonomy object.
    """
    try:
        taxonomy = _taxonomy_store.load(taxonomy_id)
        if not taxonomy:
            return jsonify({"error": "Taxonomy not found"}), 404
        return jsonify(taxonomy.to_dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@taxonomies_bp.route('/api/taxonomies/<taxonomy_id>', methods=['PUT'])
@login_required
def update_taxonomy(taxonomy_id):
    """Update a custom taxonomy.

    System presets cannot be modified.

    Args:
        taxonomy_id: Taxonomy identifier.

    Request JSON: Same as create, all fields optional.

    Returns:
        JSON updated taxonomy object.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    try:
        taxonomy = _taxonomy_store.load(taxonomy_id)
        if not taxonomy:
            return jsonify({"error": "Taxonomy not found"}), 404

        if taxonomy.is_system_preset:
            return jsonify({"error": "Cannot modify system preset taxonomies"}), 403

        # Update simple fields
        if 'name' in data:
            taxonomy.name = data['name']
        if 'description' in data:
            taxonomy.description = data['description']

        # Update taxonomy type
        if 'taxonomy_type' in data:
            try:
                taxonomy.taxonomy_type = TaxonomyType(data['taxonomy_type'])
            except ValueError:
                return jsonify({"error": f"Invalid taxonomy_type: {data['taxonomy_type']}"}), 400

        # Update levels
        if 'levels' in data:
            levels = []
            for i, level_data in enumerate(data['levels']):
                if 'name' not in level_data or 'value' not in level_data:
                    return jsonify({"error": f"Level {i} missing required fields: name, value"}), 400
                levels.append(TaxonomyLevel(
                    id=level_data.get('id', f"tl_{i}"),
                    name=level_data['name'],
                    value=level_data['value'],
                    description=level_data.get('description', ''),
                    order=level_data.get('order', i + 1),
                    example_verbs=level_data.get('example_verbs', []),
                    color=level_data.get('color', '#808080')
                ))
            taxonomy.levels = levels

        # Update activity mappings
        if 'activity_mappings' in data:
            activity_mappings = []
            for mapping_data in data['activity_mappings']:
                try:
                    activity_type = ActivityType(mapping_data['activity_type'])
                except (KeyError, ValueError):
                    continue
                activity_mappings.append(ActivityLevelMapping(
                    activity_type=activity_type,
                    compatible_levels=mapping_data.get('compatible_levels', []),
                    primary_levels=mapping_data.get('primary_levels', [])
                ))
            taxonomy.activity_mappings = activity_mappings

        # Update validation settings
        if 'require_progression' in data:
            taxonomy.require_progression = data['require_progression']
        if 'allow_regression_within' in data:
            taxonomy.allow_regression_within = data['allow_regression_within']
        if 'minimum_unique_levels' in data:
            taxonomy.minimum_unique_levels = data['minimum_unique_levels']
        if 'require_higher_order' in data:
            taxonomy.require_higher_order = data['require_higher_order']
        if 'higher_order_threshold' in data:
            taxonomy.higher_order_threshold = data['higher_order_threshold']

        taxonomy.updated_at = datetime.now().isoformat()
        _taxonomy_store.save(taxonomy)
        return jsonify(taxonomy.to_dict())

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@taxonomies_bp.route('/api/taxonomies/<taxonomy_id>', methods=['DELETE'])
@login_required
def delete_taxonomy(taxonomy_id):
    """Delete a custom taxonomy.

    System presets cannot be deleted.

    Args:
        taxonomy_id: Taxonomy identifier.

    Returns:
        JSON success message.
    """
    try:
        taxonomy = _taxonomy_store.load(taxonomy_id)
        if not taxonomy:
            return jsonify({"error": "Taxonomy not found"}), 404

        if taxonomy.is_system_preset:
            return jsonify({"error": "Cannot delete system preset taxonomies"}), 403

        if _taxonomy_store.delete(taxonomy_id):
            return jsonify({"message": "Taxonomy deleted successfully"})
        else:
            return jsonify({"error": "Failed to delete taxonomy"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@taxonomies_bp.route('/api/taxonomies/<taxonomy_id>/duplicate', methods=['POST'])
@login_required
def duplicate_taxonomy(taxonomy_id):
    """Create a copy of a taxonomy.

    Request JSON:
        {
            "name": str  # Name for the new taxonomy
        }

    Returns:
        JSON new taxonomy object with 201 status.
    """
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({"error": "Missing required field: name"}), 400

    try:
        new_taxonomy = _taxonomy_store.duplicate(taxonomy_id, data['name'])
        if not new_taxonomy:
            return jsonify({"error": "Source taxonomy not found"}), 404
        return jsonify(new_taxonomy.to_dict()), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@taxonomies_bp.route('/api/taxonomies/<taxonomy_id>/prompt-context', methods=['GET'])
@login_required
def get_taxonomy_prompt_context(taxonomy_id):
    """Get AI prompt context for a taxonomy.

    Returns formatted text suitable for AI prompt injection.

    Args:
        taxonomy_id: Taxonomy identifier.

    Returns:
        JSON with prompt_context string.
    """
    try:
        taxonomy = _taxonomy_store.load(taxonomy_id)
        if not taxonomy:
            return jsonify({"error": "Taxonomy not found"}), 404
        return jsonify({"prompt_context": taxonomy.to_prompt_context()})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@taxonomies_bp.route('/api/taxonomies/types', methods=['GET'])
@login_required
def get_taxonomy_types():
    """Get available taxonomy types.

    Returns:
        JSON with taxonomy types and their descriptions.
    """
    return jsonify({
        "types": [
            {
                "value": TaxonomyType.LINEAR.value,
                "label": "Linear",
                "description": "Ordered progression where higher levels build on lower levels"
            },
            {
                "value": TaxonomyType.CATEGORICAL.value,
                "label": "Categorical",
                "description": "Independent categories that can occur simultaneously"
            }
        ]
    })


# Course taxonomy assignment endpoints

@taxonomies_bp.route('/api/courses/<course_id>/taxonomy', methods=['GET'])
@login_required
@require_permission('view_content')
def get_course_taxonomy(course_id):
    """Get the taxonomy assigned to a course.

    Falls back to default (Bloom's) if no taxonomy assigned.

    Args:
        course_id: Course identifier.

    Returns:
        JSON taxonomy object.
    """
    if not _project_store:
        return jsonify({"error": "Project store not configured"}), 500

    owner_id = Collaborator.get_course_owner_id(course_id)
    if not owner_id:
        return jsonify({"error": "Course not found"}), 404

    try:
        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        taxonomy = _taxonomy_store.get_for_course(course)
        return jsonify({
            "taxonomy_id": course.taxonomy_id,
            "taxonomy": taxonomy.to_dict(),
            "is_default": course.taxonomy_id is None
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@taxonomies_bp.route('/api/courses/<course_id>/taxonomy', methods=['PUT'])
@login_required
@require_permission('edit_content')
def set_course_taxonomy(course_id):
    """Set the taxonomy for a course.

    Request JSON:
        {
            "taxonomy_id": str  # Set to null to use default (Bloom's)
        }

    Args:
        course_id: Course identifier.

    Returns:
        JSON with updated taxonomy assignment.
    """
    if not _project_store:
        return jsonify({"error": "Project store not configured"}), 500

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    owner_id = Collaborator.get_course_owner_id(course_id)
    if not owner_id:
        return jsonify({"error": "Course not found"}), 404

    try:
        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        taxonomy_id = data.get('taxonomy_id')

        # Validate taxonomy exists if ID provided
        if taxonomy_id:
            taxonomy = _taxonomy_store.load(taxonomy_id)
            if not taxonomy:
                return jsonify({"error": f"Taxonomy not found: {taxonomy_id}"}), 404
        else:
            taxonomy = _taxonomy_store.get_default()

        # Update course
        course.taxonomy_id = taxonomy_id
        course.updated_at = datetime.now().isoformat()
        _project_store.save(owner_id, course)

        return jsonify({
            "taxonomy_id": course.taxonomy_id,
            "taxonomy": taxonomy.to_dict(),
            "is_default": course.taxonomy_id is None,
            "message": f"Course taxonomy set to {taxonomy.name}"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
