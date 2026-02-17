"""Blueprint generation API endpoints.

Provides endpoints for generating, validating, accepting, and refining
AI-generated course blueprints. Blueprints are generated as proposals
that must be explicitly accepted before modifying the course structure.
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
import anthropic

from src.config import Config
from src.generators.blueprint_generator import BlueprintGenerator, CourseBlueprint, _fix_schema_additional_properties
from src.validators.course_validator import CourseraValidator
from src.generators.blueprint_converter import blueprint_to_course
from src.collab.decorators import require_permission
from src.collab.models import Collaborator
from src.utils.audience_level_inference import suggest_audience_level, infer_audience_level

blueprint_bp = Blueprint('blueprint', __name__)
_project_store = None


def init_blueprint_bp(project_store):
    """Initialize the blueprint blueprint with a ProjectStore instance.

    Must be called before registering the blueprint with Flask app.

    Args:
        project_store: ProjectStore instance for course persistence.
    """
    global _project_store
    _project_store = project_store


@blueprint_bp.route('/api/courses/<course_id>/blueprint', methods=['GET'])
@login_required
def get_blueprint(course_id):
    """Get the accepted blueprint for a course.

    Returns the previously accepted blueprint if one exists, allowing
    users to view and modify it when revisiting the planner.

    Args:
        course_id: Course identifier.

    Returns:
        JSON with blueprint data and has_blueprint flag.

    Errors:
        404 if course not found.
    """
    # Look up course owner
    owner_id = Collaborator.get_course_owner_id(course_id)
    if not owner_id:
        return jsonify({"error": "Course not found"}), 404

    # Load course
    try:
        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Return blueprint if exists
    if course.accepted_blueprint:
        return jsonify({
            "has_blueprint": True,
            "blueprint": course.accepted_blueprint
        })
    else:
        return jsonify({
            "has_blueprint": False,
            "blueprint": None
        })


@blueprint_bp.route('/api/courses/<course_id>/suggest-audience-level', methods=['POST'])
@login_required
def suggest_audience_level_endpoint(course_id):
    """Suggest audience level based on learner description.

    Analyzes the target learner description and suggests an appropriate
    audience level (beginner, intermediate, or advanced) with reasoning.

    Args:
        course_id: Course identifier.

    Request JSON:
        {
            "learner_description": "Description of target learners..."
        }

    Returns:
        JSON with suggested_level, confidence, reasoning, and matches.

    Errors:
        404 if course not found.
        400 if learner_description is missing.
    """
    # Look up course owner
    owner_id = Collaborator.get_course_owner_id(course_id)
    if not owner_id:
        return jsonify({"error": "Course not found"}), 404

    # Load course to verify access
    try:
        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Extract learner description from request
    data = request.get_json() or {}
    learner_description = data.get('learner_description', '')

    if not learner_description:
        # Fall back to course's target_learner_description
        learner_description = getattr(course, 'target_learner_description', '')

    # Get suggestion
    suggestion = suggest_audience_level(learner_description)

    return jsonify(suggestion)


@blueprint_bp.route('/api/courses/<course_id>/audience-level', methods=['PUT'])
@login_required
@require_permission('edit_structure')
def update_audience_level(course_id):
    """Update course audience level and optionally save learner description.

    Args:
        course_id: Course identifier.

    Request JSON:
        {
            "audience_level": "beginner|intermediate|advanced",
            "target_learner_description": "Optional description..." (optional)
        }

    Returns:
        JSON with updated course fields.

    Errors:
        404 if course not found.
        400 if audience_level is invalid.
    """
    # Look up course owner
    owner_id = Collaborator.get_course_owner_id(course_id)
    if not owner_id:
        return jsonify({"error": "Course not found"}), 404

    # Load course
    try:
        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Extract data from request
    data = request.get_json() or {}

    if 'audience_level' in data:
        level = data['audience_level']
        if level not in ['beginner', 'intermediate', 'advanced']:
            return jsonify({"error": "Invalid audience_level. Must be beginner, intermediate, or advanced"}), 400
        course.audience_level = level

    if 'target_learner_description' in data:
        course.target_learner_description = data['target_learner_description']

    # Save course
    try:
        _project_store.save(owner_id, course)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "audience_level": course.audience_level,
        "target_learner_description": course.target_learner_description
    })


@blueprint_bp.route('/api/courses/<course_id>/blueprint/generate', methods=['POST'])
@login_required
@require_permission('generate_content')
def generate_blueprint(course_id):
    """Generate a course blueprint proposal using AI.

    Args:
        course_id: Course identifier.

    Request JSON:
        {
            "description": "Course description (optional, falls back to course.description)",
            "learning_outcomes": ["outcome 1", "outcome 2"],
            "target_duration": 90,
            "audience_level": "intermediate"
        }

    Returns:
        JSON with blueprint, validation results, and status "pending_review".

    Errors:
        404 if course not found.
        400 if description or learning_outcomes are missing/invalid.
        503 if AI not available (no API key).
        502 if AI API error.
    """
    # Look up course owner
    owner_id = Collaborator.get_course_owner_id(course_id)
    if not owner_id:
        return jsonify({"error": "Course not found"}), 404

    # Load course
    try:
        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Check AI is available
    if not Config.ANTHROPIC_API_KEY:
        return jsonify({"error": "AI not available - ANTHROPIC_API_KEY not configured"}), 503

    # Extract parameters from request JSON, falling back to course fields
    data = request.get_json() or {}

    description = data.get('description') or course.description

    # Extract learning_outcomes from request or format from course
    if 'learning_outcomes' in data:
        learning_outcomes = data['learning_outcomes']
    else:
        # Format course.learning_outcomes as strings
        learning_outcomes = [
            f"{lo.audience} {lo.behavior} {lo.condition} {lo.degree}".strip()
            for lo in course.learning_outcomes
        ]

    target_duration = data.get('target_duration', course.target_duration_minutes)
    audience_level = data.get('audience_level', course.audience_level)

    # Validate inputs
    if not description or description.strip() == "":
        return jsonify({"error": "Description is required"}), 400

    if not learning_outcomes or len(learning_outcomes) == 0:
        return jsonify({"error": "At least one learning outcome is required"}), 400

    # Auto-fix is enabled by default to automatically resolve common issues
    auto_fix = data.get('auto_fix', True)
    max_refinements = data.get('max_refinements', 1)

    # Generate blueprint using AI
    try:
        generator = BlueprintGenerator()

        if auto_fix:
            # Use generate_with_autofix for automatic issue resolution
            blueprint, fix_result, validation = generator.generate_with_autofix(
                course_description=description,
                learning_outcomes=learning_outcomes,
                target_duration_minutes=target_duration,
                audience_level=audience_level,
                max_refinements=max_refinements
            )

            # Include auto-fix information in response
            return jsonify({
                "blueprint": blueprint.model_dump(),
                "validation": {
                    "is_valid": validation.is_valid,
                    "errors": validation.errors,
                    "warnings": validation.warnings,
                    "suggestions": validation.suggestions,
                    "metrics": validation.metrics
                },
                "auto_fix": {
                    "fixes_applied": fix_result.fixes_applied,
                    "remaining_issues": fix_result.remaining_issues,
                    "was_modified": fix_result.was_modified
                },
                "status": "pending_review"
            })
        else:
            # Standard generation without auto-fix
            blueprint = generator.generate(
                course_description=description,
                learning_outcomes=learning_outcomes,
                target_duration_minutes=target_duration,
                audience_level=audience_level
            )
    except anthropic.APIError as e:
        return jsonify({"error": f"AI API error: {str(e)}"}), 502
    except Exception as e:
        return jsonify({"error": f"Blueprint generation failed: {str(e)}"}), 502

    # Validate blueprint
    validator = CourseraValidator()
    validation = validator.validate(blueprint, target_duration)

    # Return blueprint, validation, and status
    return jsonify({
        "blueprint": blueprint.model_dump(),
        "validation": {
            "is_valid": validation.is_valid,
            "errors": validation.errors,
            "warnings": validation.warnings,
            "suggestions": validation.suggestions,
            "metrics": validation.metrics
        },
        "status": "pending_review"
    })


@blueprint_bp.route('/api/courses/<course_id>/blueprint/accept', methods=['POST'])
@login_required
@require_permission('add_structure')
def accept_blueprint(course_id):
    """Accept a blueprint proposal and apply structure to course.

    Args:
        course_id: Course identifier.

    Request JSON:
        {
            "blueprint": { ... }
        }

    Returns:
        JSON with success message and structure counts.

    Errors:
        404 if course not found.
        400 if blueprint is missing or invalid schema.
        422 if blueprint has validation errors.
        500 if save fails.
    """
    # Look up course owner
    owner_id = Collaborator.get_course_owner_id(course_id)
    if not owner_id:
        return jsonify({"error": "Course not found"}), 404

    # Load course
    try:
        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Parse blueprint from request
    data = request.get_json()
    if not data or 'blueprint' not in data:
        return jsonify({"error": "Missing required field: blueprint"}), 400

    # Validate blueprint schema
    try:
        blueprint_data = data['blueprint']
        # Handle old dict-style content_distribution by converting or removing it
        if 'content_distribution' in blueprint_data:
            cd = blueprint_data['content_distribution']
            if isinstance(cd, dict) and not all(k in cd for k in ['video', 'reading', 'quiz', 'hands_on']):
                # Old format or incompatible - remove and use defaults
                blueprint_data['content_distribution'] = None
        blueprint = CourseBlueprint.model_validate(blueprint_data)
    except Exception as e:
        return jsonify({"error": f"Invalid blueprint schema: {str(e)}"}), 400

    # Run validation - reject if errors present
    validator = CourseraValidator()
    validation = validator.validate(blueprint, course.target_duration_minutes)

    if not validation.is_valid:
        return jsonify({
            "error": "Blueprint validation failed",
            "validation": {
                "is_valid": False,
                "errors": validation.errors,
                "warnings": validation.warnings,
                "suggestions": validation.suggestions,
                "metrics": validation.metrics
            }
        }), 422

    # Apply blueprint to course structure and save blueprint for reference
    try:
        blueprint_to_course(blueprint, course)
        # Store the accepted blueprint for later reference
        course.accepted_blueprint = blueprint.model_dump()
        _project_store.save(owner_id, course)
    except Exception as e:
        return jsonify({"error": f"Failed to apply blueprint: {str(e)}"}), 500

    # Count modules, lessons, activities
    module_count = len(course.modules)
    lesson_count = sum(len(module.lessons) for module in course.modules)
    activity_count = sum(
        len(lesson.activities)
        for module in course.modules
        for lesson in module.lessons
    )

    return jsonify({
        "message": "Blueprint accepted and applied to course",
        "module_count": module_count,
        "lesson_count": lesson_count,
        "activity_count": activity_count
    })


@blueprint_bp.route('/api/courses/<course_id>/blueprint/refine', methods=['POST'])
@login_required
@require_permission('generate_content')
def refine_blueprint(course_id):
    """Refine a blueprint based on user feedback.

    Args:
        course_id: Course identifier.

    Request JSON:
        {
            "blueprint": { ... },
            "feedback": "string"
        }

    Returns:
        JSON with refined blueprint, validation results, and status "pending_review".

    Errors:
        404 if course not found.
        400 if blueprint or feedback are missing.
        503 if AI not available (no API key).
        502 if AI API error.
    """
    # Look up course owner
    owner_id = Collaborator.get_course_owner_id(course_id)
    if not owner_id:
        return jsonify({"error": "Course not found"}), 404

    # Load course
    try:
        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Check AI is available
    if not Config.ANTHROPIC_API_KEY:
        return jsonify({"error": "AI not available - ANTHROPIC_API_KEY not configured"}), 503

    # Extract blueprint and feedback
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    if 'blueprint' not in data:
        return jsonify({"error": "Missing required field: blueprint"}), 400

    if 'feedback' not in data:
        return jsonify({"error": "Missing required field: feedback"}), 400

    blueprint_data = data['blueprint']
    feedback = data['feedback']

    # Parse previous blueprint
    try:
        previous_blueprint = CourseBlueprint.model_validate(blueprint_data)
    except Exception as e:
        return jsonify({"error": f"Invalid blueprint schema: {str(e)}"}), 400

    # Build refinement prompt including previous blueprint and feedback
    import json

    # Format course outcomes
    learning_outcomes = [
        f"{lo.audience} {lo.behavior} {lo.condition} {lo.degree}".strip()
        for lo in course.learning_outcomes
    ]

    outcomes_text = "\n".join(f"{i+1}. {outcome}" for i, outcome in enumerate(learning_outcomes))

    refinement_prompt = f"""Refine the following course blueprint based on user feedback.

ORIGINAL CONTEXT:
- Description: {course.description}
- Audience: {course.audience_level} learners
- Target duration: {course.target_duration_minutes} minutes

LEARNING OUTCOMES:
{outcomes_text}

PREVIOUS BLUEPRINT:
{json.dumps(previous_blueprint.model_dump(), indent=2)}

USER FEEDBACK:
{feedback}

TASK:
Create a refined blueprint that addresses the user's feedback while maintaining:
1. 2-3 modules covering all learning outcomes
2. 3-5 lessons per module with clear progression
3. 2-4 activities per lesson (mix of video, reading, quiz, hands-on)
4. WWHAA phase assignments for video activities
5. Bloom's taxonomy levels matching outcome complexity
6. Realistic duration estimates per activity
7. Content distribution percentages (as decimal values: video=0.30 means 30%)

Ensure balanced content distribution and complete outcome coverage.
Provide rationale explaining how you addressed the feedback."""

    # Generate refined blueprint
    try:
        generator = BlueprintGenerator()
        # Use the generator's client directly with the refinement prompt
        # Use tool-based structured output
        schema = _fix_schema_additional_properties(CourseBlueprint.model_json_schema())
        tools = [{
            "name": "output_blueprint",
            "description": "Output the refined course blueprint",
            "input_schema": schema
        }]

        response = generator.client.messages.create(
            model=generator.model,
            max_tokens=8192,
            system=BlueprintGenerator.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": refinement_prompt}],
            tools=tools,
            tool_choice={"type": "tool", "name": "output_blueprint"}
        )

        # Extract from tool use response
        content_data = None
        for block in response.content:
            if block.type == "tool_use":
                content_data = block.input
                break

        if content_data is None:
            raise ValueError("No tool_use block in response")

        refined_blueprint = CourseBlueprint.model_validate(content_data)

    except anthropic.APIError as e:
        return jsonify({"error": f"AI API error: {str(e)}"}), 502
    except Exception as e:
        return jsonify({"error": f"Blueprint refinement failed: {str(e)}"}), 502

    # Validate refined blueprint
    validator = CourseraValidator()
    validation = validator.validate(refined_blueprint, course.target_duration_minutes)

    # Return refined blueprint, validation, and status
    return jsonify({
        "blueprint": refined_blueprint.model_dump(),
        "validation": {
            "is_valid": validation.is_valid,
            "errors": validation.errors,
            "warnings": validation.warnings,
            "suggestions": validation.suggestions,
            "metrics": validation.metrics
        },
        "status": "pending_review"
    })
