"""Learning outcome CRUD API endpoints using Flask Blueprint pattern.

Provides endpoints for creating, reading, updating, and deleting learning outcomes
with ABCD components and Bloom's taxonomy levels. All endpoints follow atomic save
pattern with project_store load/modify/save.

Includes validation endpoints to verify that learning objective text matches claimed
Bloom's level using verb-based detection.
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from src.core.models import LearningOutcome, BloomLevel
from src.editing.bloom_analyzer import BloomAnalyzer
from src.collab.decorators import require_permission
from src.collab.audit import (
    log_audit_entry,
    ACTION_STRUCTURE_ADDED,
    ACTION_STRUCTURE_UPDATED,
    ACTION_STRUCTURE_DELETED,
)
from src.collab.models import Collaborator

# Create Blueprint
learning_outcomes_bp = Blueprint('learning_outcomes', __name__)

# Module-level project_store reference (set during registration)
_project_store = None


def init_learning_outcomes_bp(project_store):
    """Initialize the learning outcomes blueprint with a ProjectStore instance.

    Must be called before registering the blueprint with Flask app.

    Args:
        project_store: ProjectStore instance for course persistence.
    """
    global _project_store
    _project_store = project_store


@learning_outcomes_bp.route('/api/courses/<course_id>/outcomes', methods=['GET'])
@login_required
@require_permission('manage_outcomes')
def list_outcomes(course_id):
    """List all learning outcomes for a course.

    Args:
        course_id: Course identifier.

    Returns:
        JSON array of learning outcome dictionaries.

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

        # Include effective_audience in each outcome
        outcomes_with_effective = []
        for outcome in course.learning_outcomes:
            outcome_dict = outcome.to_dict()
            outcome_dict["effective_audience"] = outcome.get_effective_audience(course.default_audience)
            outcomes_with_effective.append(outcome_dict)

        return jsonify(outcomes_with_effective)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@learning_outcomes_bp.route('/api/courses/<course_id>/outcomes', methods=['POST'])
@login_required
@require_permission('manage_outcomes')
def create_outcome(course_id):
    """Create a new learning outcome in a course.

    Args:
        course_id: Course identifier.

    Request JSON:
        {
            "audience": str (optional, default ""),
            "behavior": str (optional, default ""),
            "condition": str (optional, default ""),
            "degree": str (optional, default ""),
            "bloom_level": str (optional, default "apply"),
            "tags": list[str] (optional, default [])
        }

    Returns:
        JSON outcome object with 201 status.

    Errors:
        404 if course not found.
        400 if request JSON is invalid or bloom_level is invalid.
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

        # Parse bloom_level if provided
        bloom_level = BloomLevel.APPLY  # default
        if 'bloom_level' in data:
            try:
                bloom_level = BloomLevel(data['bloom_level'])
            except ValueError:
                return jsonify({
                    "error": f"Invalid bloom_level: {data['bloom_level']}. Valid values: {[b.value for b in BloomLevel]}"
                }), 400

        # Create new learning outcome
        outcome = LearningOutcome(
            audience=data.get('audience', ''),
            behavior=data.get('behavior', ''),
            condition=data.get('condition', ''),
            degree=data.get('degree', ''),
            bloom_level=bloom_level,
            tags=data.get('tags', [])
        )

        # Add to course and save
        course.learning_outcomes.append(outcome)
        _project_store.save(owner_id, course)

        # Log audit entry
        log_audit_entry(
            course_id=course_id,
            user_id=current_user.id,
            action=ACTION_STRUCTURE_ADDED,
            entity_type='learning_outcome',
            entity_id=outcome.id,
            after={'name': outcome.behavior, 'bloom_level': outcome.bloom_level.value}
        )

        # Include effective_audience in response
        outcome_dict = outcome.to_dict()
        outcome_dict["effective_audience"] = outcome.get_effective_audience(course.default_audience)
        return jsonify(outcome_dict), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@learning_outcomes_bp.route('/api/courses/<course_id>/outcomes/<outcome_id>', methods=['PUT'])
@login_required
@require_permission('manage_outcomes')
def update_outcome(course_id, outcome_id):
    """Update a learning outcome.

    Args:
        course_id: Course identifier.
        outcome_id: Learning outcome identifier.

    Request JSON:
        {
            "audience": str (optional),
            "behavior": str (optional),
            "condition": str (optional),
            "degree": str (optional),
            "bloom_level": str (optional),
            "tags": list[str] (optional)
        }

    Returns:
        JSON updated outcome object.

    Errors:
        404 if course or outcome not found.
        400 if request JSON is invalid or bloom_level is invalid.
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

        # Find outcome by ID
        outcome = next((o for o in course.learning_outcomes if o.id == outcome_id), None)
        if not outcome:
            return jsonify({"error": "Learning outcome not found"}), 404

        # Capture before state for audit
        before_state = {'behavior': outcome.behavior, 'bloom_level': outcome.bloom_level.value}

        # Update fields
        if 'audience' in data:
            outcome.audience = data['audience']
        if 'behavior' in data:
            outcome.behavior = data['behavior']
        if 'condition' in data:
            outcome.condition = data['condition']
        if 'degree' in data:
            outcome.degree = data['degree']
        if 'bloom_level' in data:
            try:
                outcome.bloom_level = BloomLevel(data['bloom_level'])
            except ValueError:
                return jsonify({
                    "error": f"Invalid bloom_level: {data['bloom_level']}. Valid values: {[b.value for b in BloomLevel]}"
                }), 400
        if 'tags' in data:
            outcome.tags = data['tags']

        # Save course
        _project_store.save(owner_id, course)

        # Log audit entry with before/after
        log_audit_entry(
            course_id=course_id,
            user_id=current_user.id,
            action=ACTION_STRUCTURE_UPDATED,
            entity_type='learning_outcome',
            entity_id=outcome_id,
            before=before_state,
            after={'behavior': outcome.behavior, 'bloom_level': outcome.bloom_level.value}
        )

        # Include effective_audience in response
        outcome_dict = outcome.to_dict()
        outcome_dict["effective_audience"] = outcome.get_effective_audience(course.default_audience)
        return jsonify(outcome_dict)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@learning_outcomes_bp.route('/api/courses/<course_id>/outcomes/<outcome_id>', methods=['DELETE'])
@login_required
@require_permission('manage_outcomes')
def delete_outcome(course_id, outcome_id):
    """Delete a learning outcome.

    Args:
        course_id: Course identifier.
        outcome_id: Learning outcome identifier.

    Returns:
        JSON success message with 200 status.

    Errors:
        404 if course or outcome not found.
        500 if save fails.
    """
    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        # Find outcome by ID
        outcome = next((o for o in course.learning_outcomes if o.id == outcome_id), None)
        if not outcome:
            return jsonify({"error": "Learning outcome not found"}), 404

        # Store outcome info for audit before deletion
        deleted_outcome_behavior = outcome.behavior

        # Remove outcome from course
        course.learning_outcomes = [o for o in course.learning_outcomes if o.id != outcome_id]

        # Save course
        _project_store.save(owner_id, course)

        # Log audit entry
        log_audit_entry(
            course_id=course_id,
            user_id=current_user.id,
            action=ACTION_STRUCTURE_DELETED,
            entity_type='learning_outcome',
            entity_id=outcome_id,
            before={'name': deleted_outcome_behavior}
        )

        return jsonify({"message": "Learning outcome deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _get_all_activities(course):
    """Get all activities from course structure.

    Helper function that traverses course modules/lessons/activities hierarchy.

    Args:
        course: Course instance to traverse.

    Returns:
        List of Activity instances from all modules and lessons.
    """
    activities = []
    for module in course.modules:
        for lesson in module.lessons:
            activities.extend(lesson.activities)
    return activities


@learning_outcomes_bp.route('/api/courses/<course_id>/outcomes/<outcome_id>/map', methods=['POST'])
@login_required
@require_permission('manage_outcomes')
def map_outcome_to_activity(course_id, outcome_id):
    """Map a learning outcome to an activity.

    Adds activity_id to outcome.mapped_activity_ids list (idempotent).

    Args:
        course_id: Course identifier.
        outcome_id: Learning outcome identifier.

    Request JSON:
        {
            "activity_id": str
        }

    Returns:
        JSON updated outcome object with 200 status.

    Errors:
        404 if course or outcome not found.
        404 if activity not found.
        400 if request JSON is invalid.
        500 if save fails.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    if 'activity_id' not in data:
        return jsonify({"error": "Missing required field: activity_id"}), 400

    activity_id = data['activity_id']

    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        # Find outcome by ID
        outcome = next((o for o in course.learning_outcomes if o.id == outcome_id), None)
        if not outcome:
            return jsonify({"error": "Learning outcome not found"}), 404

        # Validate activity exists
        all_activities = _get_all_activities(course)
        activity = next((a for a in all_activities if a.id == activity_id), None)
        if not activity:
            return jsonify({"error": "Activity not found"}), 404

        # Add mapping (idempotent - no duplicates)
        was_new_mapping = activity_id not in outcome.mapped_activity_ids
        if was_new_mapping:
            outcome.mapped_activity_ids.append(activity_id)

        # Save course
        _project_store.save(owner_id, course)

        # Log audit entry (only if mapping was new)
        if was_new_mapping:
            log_audit_entry(
                course_id=course_id,
                user_id=current_user.id,
                action=ACTION_STRUCTURE_UPDATED,
                entity_type='learning_outcome_mapping',
                entity_id=outcome_id,
                after={'activity_id': activity_id, 'action': 'mapped'}
            )

        return jsonify(outcome.to_dict()), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@learning_outcomes_bp.route('/api/courses/<course_id>/outcomes/<outcome_id>/map/<activity_id>', methods=['DELETE'])
@login_required
@require_permission('manage_outcomes')
def unmap_outcome_from_activity(course_id, outcome_id, activity_id):
    """Unmap a learning outcome from an activity.

    Removes activity_id from outcome.mapped_activity_ids list (idempotent).

    Args:
        course_id: Course identifier.
        outcome_id: Learning outcome identifier.
        activity_id: Activity identifier.

    Returns:
        JSON success message with 200 status.

    Errors:
        404 if course or outcome not found.
        500 if save fails.
    """
    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        # Find outcome by ID
        outcome = next((o for o in course.learning_outcomes if o.id == outcome_id), None)
        if not outcome:
            return jsonify({"error": "Learning outcome not found"}), 404

        # Check if mapping existed before removal
        was_mapped = activity_id in outcome.mapped_activity_ids

        # Remove mapping (idempotent - no error if not present)
        outcome.mapped_activity_ids = [
            aid for aid in outcome.mapped_activity_ids
            if aid != activity_id
        ]

        # Save course
        _project_store.save(owner_id, course)

        # Log audit entry (only if mapping was removed)
        if was_mapped:
            log_audit_entry(
                course_id=course_id,
                user_id=current_user.id,
                action=ACTION_STRUCTURE_UPDATED,
                entity_type='learning_outcome_mapping',
                entity_id=outcome_id,
                after={'activity_id': activity_id, 'action': 'unmapped'}
            )

        return jsonify({"message": "Mapping removed successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@learning_outcomes_bp.route('/api/courses/<course_id>/alignment', methods=['GET'])
@login_required
@require_permission('manage_outcomes')
def get_alignment_matrix(course_id):
    """Get outcome-activity alignment matrix with coverage analysis.

    Returns alignment data showing which outcomes are mapped to which activities,
    plus unmapped outcomes/activities and overall coverage score.

    Args:
        course_id: Course identifier.

    Returns:
        JSON alignment object:
        {
            "outcomes": [
                {
                    "id": "lo_xxx",
                    "behavior": "implement a REST API",
                    "bloom_level": "apply",
                    "mapped_activities": [
                        {"id": "act_xxx", "title": "Build API", "content_type": "video"}
                    ]
                }
            ],
            "unmapped_outcomes": ["lo_yyy"],
            "unmapped_activities": ["act_zzz"],
            "coverage_score": 0.75
        }

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

        # Get all activities from course structure
        all_activities = _get_all_activities(course)

        # Build activity lookup dictionary
        activity_dict = {a.id: a for a in all_activities}

        # Build outcomes with mapped activity details
        outcomes_with_mappings = []
        unmapped_outcomes = []

        for outcome in course.learning_outcomes:
            mapped_activities = []
            for activity_id in outcome.mapped_activity_ids:
                activity = activity_dict.get(activity_id)
                if activity:
                    mapped_activities.append({
                        "id": activity.id,
                        "title": activity.title,
                        "content_type": activity.content_type.value
                    })

            outcome_data = {
                "id": outcome.id,
                "behavior": outcome.behavior,
                "bloom_level": outcome.bloom_level.value,
                "mapped_activities": mapped_activities
            }
            outcomes_with_mappings.append(outcome_data)

            if len(outcome.mapped_activity_ids) == 0:
                unmapped_outcomes.append(outcome.id)

        # Find unmapped activities
        mapped_activity_ids = set()
        for outcome in course.learning_outcomes:
            mapped_activity_ids.update(outcome.mapped_activity_ids)

        unmapped_activities = [
            activity.id for activity in all_activities
            if activity.id not in mapped_activity_ids
        ]

        # Calculate coverage score
        if len(course.learning_outcomes) > 0:
            coverage_score = (len(course.learning_outcomes) - len(unmapped_outcomes)) / len(course.learning_outcomes)
        else:
            coverage_score = 0.0

        return jsonify({
            "outcomes": outcomes_with_mappings,
            "unmapped_outcomes": unmapped_outcomes,
            "unmapped_activities": unmapped_activities,
            "coverage_score": coverage_score
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@learning_outcomes_bp.route('/api/courses/<course_id>/activities/<activity_id>/outcomes', methods=['GET'])
@login_required
@require_permission('manage_outcomes')
def get_activity_outcomes(course_id, activity_id):
    """Get learning outcomes mapped to a specific activity (reverse lookup).

    Args:
        course_id: Course identifier.
        activity_id: Activity identifier.

    Returns:
        JSON array of outcome dictionaries that are mapped to the activity.

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

        # Find outcomes that have this activity mapped, include effective_audience
        mapped_outcomes = []
        for outcome in course.learning_outcomes:
            if activity_id in outcome.mapped_activity_ids:
                outcome_dict = outcome.to_dict()
                outcome_dict["effective_audience"] = outcome.get_effective_audience(course.default_audience)
                mapped_outcomes.append(outcome_dict)

        return jsonify(mapped_outcomes)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===========================
# Bloom's Level Validation
# ===========================

# Module-level analyzer instance
_bloom_analyzer = BloomAnalyzer()


@learning_outcomes_bp.route('/api/outcomes/analyze-text', methods=['POST'])
@login_required
def analyze_text():
    """Auto-detect Bloom's level from objective text.

    Useful for suggesting the correct Bloom level when creating outcomes.

    Request JSON:
        {
            "text": str  # The objective text to analyze
        }

    Returns:
        JSON object with detected level and analysis:
        {
            "detected_level": "apply",
            "detected_level_name": "Apply",
            "confidence": 0.75,
            "evidence": ["implement", "use"],
            "suggestions": [...]
        }

    Errors:
        400 if request JSON is invalid or text is missing.
    """
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({"error": "Missing required field: text"}), 400

    text = data['text']
    if not text or not text.strip():
        return jsonify({"error": "Text cannot be empty"}), 400

    analysis = _bloom_analyzer.analyze(text)

    # Map level to display name
    level_names = {
        BloomLevel.REMEMBER: "Remember",
        BloomLevel.UNDERSTAND: "Understand",
        BloomLevel.APPLY: "Apply",
        BloomLevel.ANALYZE: "Analyze",
        BloomLevel.EVALUATE: "Evaluate",
        BloomLevel.CREATE: "Create"
    }

    return jsonify({
        "detected_level": analysis.detected_level.value,
        "detected_level_name": level_names.get(analysis.detected_level, analysis.detected_level.value.title()),
        "confidence": analysis.confidence,
        "evidence": analysis.evidence,
        "verb_counts": analysis.verb_counts
    })


@learning_outcomes_bp.route('/api/courses/<course_id>/outcomes/<outcome_id>/validate', methods=['GET'])
@login_required
@require_permission('manage_outcomes')
def validate_outcome(course_id, outcome_id):
    """Validate that a learning outcome's text matches its claimed Bloom level.

    Analyzes the objective behavior text and compares detected level to
    the claimed bloom_level. Returns warnings if there's a mismatch.

    Args:
        course_id: Course identifier.
        outcome_id: Learning outcome identifier.

    Returns:
        JSON validation result:
        {
            "outcome_id": "lo_xxx",
            "claimed_level": "create",
            "detected_level": "understand",
            "aligned": false,
            "gap": -4,
            "severity": "warning",
            "message": "Objective text suggests 'Understand' but claimed 'Create'",
            "suggestions": [...],
            "evidence": ["explain", "describe"]
        }

    Errors:
        404 if course or outcome not found.
        500 if validation fails.
    """
    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        outcome = next((o for o in course.learning_outcomes if o.id == outcome_id), None)
        if not outcome:
            return jsonify({"error": "Learning outcome not found"}), 404

        return jsonify(_validate_single_outcome(outcome))

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@learning_outcomes_bp.route('/api/courses/<course_id>/outcomes/validate', methods=['GET'])
@login_required
@require_permission('manage_outcomes')
def validate_all_outcomes(course_id):
    """Validate all learning outcomes in a course.

    Returns validation results for each outcome, highlighting mismatches
    between claimed Bloom levels and detected levels from text.

    Args:
        course_id: Course identifier.

    Returns:
        JSON object with validation summary and per-outcome results:
        {
            "total_outcomes": 5,
            "aligned_count": 3,
            "misaligned_count": 2,
            "outcomes": [
                {
                    "outcome_id": "lo_xxx",
                    "behavior": "explain key concepts",
                    "claimed_level": "create",
                    "detected_level": "understand",
                    "aligned": false,
                    ...
                }
            ]
        }

    Errors:
        404 if course not found.
        500 if validation fails.
    """
    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        results = []
        aligned_count = 0
        misaligned_count = 0

        for outcome in course.learning_outcomes:
            result = _validate_single_outcome(outcome)
            results.append(result)

            if result["aligned"]:
                aligned_count += 1
            else:
                misaligned_count += 1

        return jsonify({
            "total_outcomes": len(course.learning_outcomes),
            "aligned_count": aligned_count,
            "misaligned_count": misaligned_count,
            "outcomes": results
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _validate_single_outcome(outcome: LearningOutcome) -> dict:
    """Validate a single learning outcome.

    Args:
        outcome: LearningOutcome to validate.

    Returns:
        Dictionary with validation results.
    """
    # The behavior field contains the action verb (e.g., "design a REST API")
    text_to_analyze = outcome.behavior
    if not text_to_analyze:
        return {
            "outcome_id": outcome.id,
            "behavior": outcome.behavior,
            "claimed_level": outcome.bloom_level.value,
            "detected_level": None,
            "aligned": True,  # Can't detect without text
            "gap": 0,
            "severity": "info",
            "message": "No behavior text to analyze",
            "suggestions": ["Add a behavior statement with an action verb"],
            "evidence": []
        }

    # Check alignment
    alignment = _bloom_analyzer.check_alignment(text_to_analyze, outcome.bloom_level)

    # Build display names
    level_names = {
        BloomLevel.REMEMBER: "Remember",
        BloomLevel.UNDERSTAND: "Understand",
        BloomLevel.APPLY: "Apply",
        BloomLevel.ANALYZE: "Analyze",
        BloomLevel.EVALUATE: "Evaluate",
        BloomLevel.CREATE: "Create"
    }

    claimed_name = level_names.get(outcome.bloom_level, outcome.bloom_level.value.title())
    detected_name = level_names.get(alignment.current_level, alignment.current_level.value.title())

    # Determine severity
    if alignment.aligned:
        severity = "success"
        message = f"Objective text aligns with claimed level ({claimed_name})"
    elif abs(alignment.gap) == 1:
        severity = "info"
        message = f"Minor difference: text suggests '{detected_name}' but claimed '{claimed_name}'"
    elif abs(alignment.gap) <= 2:
        severity = "warning"
        message = f"Objective text suggests '{detected_name}' but claimed '{claimed_name}'"
    else:
        severity = "error"
        message = f"Significant mismatch: text suggests '{detected_name}' but claimed '{claimed_name}'"

    # Run analysis to get evidence
    analysis = _bloom_analyzer.analyze(text_to_analyze)

    return {
        "outcome_id": outcome.id,
        "behavior": outcome.behavior,
        "claimed_level": outcome.bloom_level.value,
        "claimed_level_name": claimed_name,
        "detected_level": alignment.current_level.value,
        "detected_level_name": detected_name,
        "aligned": alignment.aligned,
        "gap": alignment.gap,
        "severity": severity,
        "message": message,
        "suggestions": alignment.suggestions,
        "evidence": analysis.evidence,
        "confidence": analysis.confidence
    }
