"""Content variants API endpoints for UDL support.

Provides endpoints for listing, generating, and retrieving content variants
that support Universal Design for Learning (UDL) and depth layers.
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime

from src.core.models import (
    VariantType, DepthLevel, ContentVariant, BuildState, ContentType,
    LearningPreference, LearnerProfile
)
from src.collab.decorators import require_permission
from src.generators.variant_generators import get_variant_generator, DepthAdapter

# Mapping of learner preferences to recommended variant types
PREFERENCE_TO_VARIANTS = {
    LearningPreference.VISUAL: [VariantType.ILLUSTRATED, VariantType.INFOGRAPHIC, VariantType.PRIMARY],
    LearningPreference.AUDITORY: [VariantType.AUDIO_ONLY, VariantType.PRIMARY],
    LearningPreference.READING: [VariantType.TRANSCRIPT, VariantType.PRIMARY],
    LearningPreference.HANDS_ON: [VariantType.GUIDED, VariantType.CHALLENGE, VariantType.PRIMARY],
    LearningPreference.MIXED: [VariantType.PRIMARY],
}

# Create Blueprint
variants_bp = Blueprint('variants', __name__)

# Module-level project_store reference (set during registration)
_project_store = None


def init_variants_bp(project_store):
    """Initialize the variants blueprint with a ProjectStore instance.

    Must be called before registering the blueprint with Flask app.

    Args:
        project_store: ProjectStore instance for course persistence.
    """
    global _project_store
    _project_store = project_store


# Mapping of content types to supported variant types
SUPPORTED_VARIANTS = {
    ContentType.VIDEO: [
        VariantType.PRIMARY,
        VariantType.AUDIO_ONLY,
        VariantType.TRANSCRIPT,
        VariantType.ILLUSTRATED,
    ],
    ContentType.READING: [
        VariantType.PRIMARY,
        VariantType.AUDIO_ONLY,
        VariantType.INFOGRAPHIC,
    ],
    ContentType.QUIZ: [
        VariantType.PRIMARY,
        VariantType.SELF_CHECK,
    ],
    ContentType.HOL: [
        VariantType.PRIMARY,
        VariantType.GUIDED,
        VariantType.CHALLENGE,
    ],
}


def _find_activity(course, activity_id):
    """Find activity and its parent containers by activity ID."""
    for module in course.modules:
        for lesson in module.lessons:
            for activity in lesson.activities:
                if activity.id == activity_id:
                    return module, lesson, activity
    return None, None, None


@variants_bp.route('/courses/<course_id>/activities/<activity_id>/variants', methods=['GET'])
@login_required
@require_permission('view')
def list_variants(course_id, activity_id):
    """List all available and generated variants for an activity.

    Returns:
        200 with list of variants and their status
        404 if course or activity not found
    """
    course = _project_store.load(str(current_user.id), course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404

    module, lesson, activity = _find_activity(course, activity_id)
    if not activity:
        return jsonify({"error": "Activity not found"}), 404

    # Get supported variants for this content type
    supported = SUPPORTED_VARIANTS.get(activity.content_type, [VariantType.PRIMARY])

    # Build response with variant status
    variants = []

    # Primary variant (always present if content generated)
    for depth in DepthLevel:
        is_primary_standard = depth == DepthLevel.STANDARD
        if is_primary_standard:
            # Primary + Standard is in main content field
            variants.append({
                "variant_type": VariantType.PRIMARY.value,
                "depth_level": depth.value,
                "build_state": activity.build_state.value,
                "generated": activity.build_state != BuildState.DRAFT,
                "word_count": activity.word_count if is_primary_standard else 0,
                "estimated_duration_minutes": activity.estimated_duration_minutes if is_primary_standard else 0,
            })
        else:
            # Check if this depth variant exists
            variant = activity.get_variant(VariantType.PRIMARY, depth)
            if variant and variant.id != f"{activity.id}_primary_standard":
                variants.append({
                    "variant_type": VariantType.PRIMARY.value,
                    "depth_level": depth.value,
                    "build_state": variant.build_state.value,
                    "generated": variant.build_state != BuildState.DRAFT,
                    "word_count": variant.word_count,
                    "estimated_duration_minutes": variant.estimated_duration_minutes,
                })
            else:
                variants.append({
                    "variant_type": VariantType.PRIMARY.value,
                    "depth_level": depth.value,
                    "build_state": BuildState.DRAFT.value,
                    "generated": False,
                    "word_count": 0,
                    "estimated_duration_minutes": 0,
                })

    # Other supported variants
    for variant_type in supported:
        if variant_type == VariantType.PRIMARY:
            continue  # Already handled above

        for depth in DepthLevel:
            variant = activity.get_variant(variant_type, depth)
            if variant:
                variants.append({
                    "variant_type": variant_type.value,
                    "depth_level": depth.value,
                    "build_state": variant.build_state.value,
                    "generated": variant.build_state != BuildState.DRAFT,
                    "word_count": variant.word_count,
                    "estimated_duration_minutes": variant.estimated_duration_minutes,
                })
            else:
                variants.append({
                    "variant_type": variant_type.value,
                    "depth_level": depth.value,
                    "build_state": BuildState.DRAFT.value,
                    "generated": False,
                    "word_count": 0,
                    "estimated_duration_minutes": 0,
                })

    return jsonify({
        "activity_id": activity_id,
        "content_type": activity.content_type.value,
        "supported_variants": [v.value for v in supported],
        "variants": variants,
    })


@variants_bp.route('/courses/<course_id>/activities/<activity_id>/variants/generate', methods=['POST'])
@login_required
@require_permission('edit')
def generate_variant(course_id, activity_id):
    """Generate a content variant for an activity.

    Request body:
        variant_type: Target variant type (e.g., "transcript")
        depth_level: Target depth level (e.g., "standard")

    Returns:
        200 with generated variant
        400 if invalid parameters
        404 if course or activity not found
        422 if variant generation not supported
    """
    course = _project_store.load(str(current_user.id), course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404

    module, lesson, activity = _find_activity(course, activity_id)
    if not activity:
        return jsonify({"error": "Activity not found"}), 404

    # Check that primary content exists
    if activity.build_state == BuildState.DRAFT or not activity.content:
        return jsonify({"error": "Primary content must be generated first"}), 400

    data = request.get_json() or {}
    variant_type_str = data.get("variant_type", "transcript")
    depth_level_str = data.get("depth_level", "standard")

    # Parse variant type
    try:
        target_variant_type = VariantType(variant_type_str)
    except ValueError:
        return jsonify({"error": f"Invalid variant_type: {variant_type_str}"}), 400

    # Parse depth level
    try:
        target_depth = DepthLevel(depth_level_str)
    except ValueError:
        return jsonify({"error": f"Invalid depth_level: {depth_level_str}"}), 400

    # Check if variant type is supported for this content type
    supported = SUPPORTED_VARIANTS.get(activity.content_type, [VariantType.PRIMARY])
    if target_variant_type not in supported:
        return jsonify({
            "error": f"Variant type '{target_variant_type.value}' not supported for {activity.content_type.value}"
        }), 422

    # Check if variant already exists
    existing = activity.get_variant(target_variant_type, target_depth)
    if existing and existing.id != f"{activity.id}_primary_standard":
        return jsonify({
            "error": "Variant already exists",
            "variant": existing.to_dict()
        }), 400

    # Handle PRIMARY variant with different depth
    if target_variant_type == VariantType.PRIMARY and target_depth != DepthLevel.STANDARD:
        # Use DepthAdapter to create depth variant
        adapter = DepthAdapter()
        try:
            adapted_content, metadata = adapter.adapt_depth(
                activity.content,
                DepthLevel.STANDARD,
                target_depth,
                activity.content_type.value
            )
        except Exception as e:
            return jsonify({"error": f"Depth adaptation failed: {str(e)}"}), 500

        new_variant = ContentVariant(
            variant_type=VariantType.PRIMARY,
            depth_level=target_depth,
            content=adapted_content,
            build_state=BuildState.GENERATED,
            word_count=metadata.get("word_count", 0),
            estimated_duration_minutes=metadata.get("estimated_duration_minutes", 0.0),
            generated_from_variant_id=f"{activity.id}_primary_standard",
        )
    else:
        # Get variant generator
        generator = get_variant_generator(VariantType.PRIMARY, target_variant_type)
        if not generator:
            return jsonify({
                "error": f"No generator available for {target_variant_type.value} variant"
            }), 422

        # Create source variant wrapper
        source_variant = ContentVariant(
            id=f"{activity.id}_primary_standard",
            variant_type=VariantType.PRIMARY,
            depth_level=DepthLevel.STANDARD,
            content=activity.content,
            build_state=activity.build_state,
            word_count=activity.word_count,
            estimated_duration_minutes=activity.estimated_duration_minutes,
        )

        # Generate variant
        try:
            new_variant = generator.generate_variant(source_variant, target_depth)
        except Exception as e:
            return jsonify({"error": f"Variant generation failed: {str(e)}"}), 500

    # Add to activity's content_variants
    activity.content_variants.append(new_variant)
    activity.updated_at = datetime.now().isoformat()

    # Save course
    _project_store.save(str(current_user.id), course)

    return jsonify({
        "message": "Variant generated successfully",
        "variant": new_variant.to_dict()
    })


@variants_bp.route('/courses/<course_id>/activities/<activity_id>/variants/<variant_type>', methods=['GET'])
@login_required
@require_permission('view')
def get_variant(course_id, activity_id, variant_type):
    """Get specific variant content.

    Query params:
        depth: Depth level (default: standard)

    Returns:
        200 with variant content
        404 if not found
    """
    course = _project_store.load(str(current_user.id), course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404

    module, lesson, activity = _find_activity(course, activity_id)
    if not activity:
        return jsonify({"error": "Activity not found"}), 404

    # Parse variant type
    try:
        target_variant_type = VariantType(variant_type)
    except ValueError:
        return jsonify({"error": f"Invalid variant_type: {variant_type}"}), 400

    # Parse depth level
    depth_str = request.args.get("depth", "standard")
    try:
        target_depth = DepthLevel(depth_str)
    except ValueError:
        return jsonify({"error": f"Invalid depth: {depth_str}"}), 400

    # Get variant
    variant = activity.get_variant(target_variant_type, target_depth)
    if not variant:
        return jsonify({"error": "Variant not found"}), 404

    return jsonify(variant.to_dict())


@variants_bp.route('/courses/<course_id>/activities/<activity_id>/variants/<variant_type>', methods=['DELETE'])
@login_required
@require_permission('edit')
def delete_variant(course_id, activity_id, variant_type):
    """Delete a specific variant.

    Query params:
        depth: Depth level (default: standard)

    Returns:
        200 on success
        400 if trying to delete primary/standard variant
        404 if not found
    """
    course = _project_store.load(str(current_user.id), course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404

    module, lesson, activity = _find_activity(course, activity_id)
    if not activity:
        return jsonify({"error": "Activity not found"}), 404

    # Parse variant type
    try:
        target_variant_type = VariantType(variant_type)
    except ValueError:
        return jsonify({"error": f"Invalid variant_type: {variant_type}"}), 400

    # Parse depth level
    depth_str = request.args.get("depth", "standard")
    try:
        target_depth = DepthLevel(depth_str)
    except ValueError:
        return jsonify({"error": f"Invalid depth: {depth_str}"}), 400

    # Cannot delete primary/standard variant
    if target_variant_type == VariantType.PRIMARY and target_depth == DepthLevel.STANDARD:
        return jsonify({
            "error": "Cannot delete primary/standard variant. Use content regeneration instead."
        }), 400

    # Find and remove variant
    found = False
    for i, variant in enumerate(activity.content_variants):
        if variant.variant_type == target_variant_type and variant.depth_level == target_depth:
            activity.content_variants.pop(i)
            found = True
            break

    if not found:
        return jsonify({"error": "Variant not found"}), 404

    activity.updated_at = datetime.now().isoformat()
    _project_store.save(str(current_user.id), course)

    return jsonify({"message": "Variant deleted"})


@variants_bp.route('/courses/<course_id>/activities/<activity_id>/variants/recommended', methods=['GET'])
@login_required
@require_permission('view')
def get_recommended_variants(course_id, activity_id):
    """Get recommended variants based on learner profile.

    Query params:
        learning_preference: Learning preference value (visual, auditory, reading, hands_on, mixed)

    Returns:
        200 with list of recommended variant types sorted by relevance
        404 if course or activity not found
    """
    course = _project_store.load(str(current_user.id), course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404

    module, lesson, activity = _find_activity(course, activity_id)
    if not activity:
        return jsonify({"error": "Activity not found"}), 404

    # Get learning preference from query params
    pref_str = request.args.get("learning_preference", "mixed")
    try:
        learning_pref = LearningPreference(pref_str)
    except ValueError:
        learning_pref = LearningPreference.MIXED

    # Get recommended variant types for this preference
    recommended_types = PREFERENCE_TO_VARIANTS.get(learning_pref, [VariantType.PRIMARY])

    # Get supported variants for this content type
    supported = SUPPORTED_VARIANTS.get(activity.content_type, [VariantType.PRIMARY])

    # Filter to only supported variants
    filtered_recommendations = [v for v in recommended_types if v in supported]

    # If no overlap, default to PRIMARY
    if not filtered_recommendations:
        filtered_recommendations = [VariantType.PRIMARY]

    # Check which recommended variants are already generated
    recommendations = []
    for variant_type in filtered_recommendations:
        # Check for standard depth first
        variant = activity.get_variant(variant_type, DepthLevel.STANDARD)
        is_generated = False
        if variant_type == VariantType.PRIMARY and activity.content:
            is_generated = activity.build_state != BuildState.DRAFT
        elif variant:
            is_generated = variant.build_state != BuildState.DRAFT

        recommendations.append({
            "variant_type": variant_type.value,
            "depth_level": "standard",
            "is_generated": is_generated,
            "priority": filtered_recommendations.index(variant_type) + 1,
        })

    return jsonify({
        "activity_id": activity_id,
        "learning_preference": learning_pref.value,
        "recommendations": recommendations,
    })
