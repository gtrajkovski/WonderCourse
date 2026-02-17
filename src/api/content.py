"""Content generation API endpoints.

Provides endpoints for generating, regenerating, and editing content for activities.
Orchestrates all 11 content generators (Video, Reading, Quiz, Rubric, HOL, Coach,
PracticeQuiz, Lab, Discussion, Assignment, Project) and manages the generate-edit-approve
workflow with build state tracking.
"""

from flask import Blueprint, request, jsonify, Response, stream_with_context
from flask_login import login_required, current_user
from datetime import datetime
import anthropic
import json
import time
import threading
import queue

from src.core.models import ContentType, BuildState, ActivityType, BloomLevel
from src.collab.decorators import require_permission
from src.collab.audit import (
    log_audit_entry,
    ACTION_CONTENT_GENERATED,
    ACTION_CONTENT_UPDATED,
)
from src.collab.models import Collaborator
from src.generators.video_script_generator import VideoScriptGenerator
from src.generators.reading_generator import ReadingGenerator
from src.generators.quiz_generator import QuizGenerator
from src.generators.rubric_generator import RubricGenerator
from src.generators.hol_generator import HOLGenerator
from src.generators.coach_generator import CoachGenerator
from src.generators.practice_quiz_generator import PracticeQuizGenerator
from src.generators.lab_generator import LabGenerator
from src.generators.discussion_generator import DiscussionGenerator
from src.generators.assignment_generator import AssignmentGenerator
from src.generators.project_generator import ProjectMilestoneGenerator
from src.generators.screencast_generator import ScreencastGenerator
from src.utils.content_metadata import ContentMetadata
from src.utils.standards_loader import load_standards, build_all_prompt_rules
from src.utils.content_humanizer import humanize_content, get_content_score

# Create Blueprint
content_bp = Blueprint('content', __name__)

# Module-level project_store reference (set during registration)
_project_store = None


def init_content_bp(project_store):
    """Initialize the content blueprint with a ProjectStore instance.

    Must be called before registering the blueprint with Flask app.

    Args:
        project_store: ProjectStore instance for course persistence.
    """
    global _project_store
    _project_store = project_store


def _find_activity(course, activity_id):
    """Find activity and its parent containers by activity ID.

    Args:
        course: Course instance to search.
        activity_id: Activity identifier.

    Returns:
        Tuple of (module, lesson, activity) if found, (None, None, None) otherwise.
    """
    for module in course.modules:
        for lesson in module.lessons:
            for activity in lesson.activities:
                if activity.id == activity_id:
                    return module, lesson, activity
    return None, None, None


def _content_type_to_standards_key(content_type, activity_type):
    """Map ContentType enum to standards loader key.

    Args:
        content_type: ContentType enum value.
        activity_type: ActivityType enum value (needed to distinguish practice quiz).

    Returns:
        String key for build_all_prompt_rules, or None if not supported.
    """
    # Handle practice quiz specially since it has same ContentType as quiz
    if content_type == ContentType.QUIZ and activity_type == ActivityType.PRACTICE_QUIZ:
        return "practice_quiz"

    mapping = {
        ContentType.VIDEO: "video",
        ContentType.READING: "reading",
        ContentType.QUIZ: "quiz",
        ContentType.RUBRIC: "rubric",
        ContentType.HOL: "hol",
        ContentType.COACH: "coach",
        ContentType.LAB: "lab",
        ContentType.DISCUSSION: "discussion",
        ContentType.ASSIGNMENT: "assignment",
        ContentType.PROJECT: "project",
        ContentType.SCREENCAST: "screencast",
    }
    return mapping.get(content_type)


def _get_bloom_level_for_activity(course, activity):
    """Get the Bloom's taxonomy level for an activity.

    Priority order:
    1. Activity's own bloom_level if set
    2. First mapped learning outcome's bloom_level
    3. Default to 'apply'

    Args:
        course: Course containing the activity and learning outcomes.
        activity: Activity to get bloom level for.

    Returns:
        str: Bloom level string (remember, understand, apply, etc.)
    """
    # Priority 1: Activity's own bloom_level
    if activity.bloom_level:
        if hasattr(activity.bloom_level, 'value'):
            return activity.bloom_level.value
        return str(activity.bloom_level)

    # Priority 2: Check mapped learning outcomes
    for lo in course.learning_outcomes:
        if activity.id in lo.mapped_activity_ids:
            if lo.bloom_level:
                if hasattr(lo.bloom_level, 'value'):
                    return lo.bloom_level.value
                return str(lo.bloom_level)

    # Default fallback
    return 'apply'


@content_bp.route('/api/courses/<course_id>/activities/<activity_id>/generate', methods=['POST'])
@login_required
@require_permission('generate_content')
def generate_content(course_id, activity_id):
    """Generate content for an activity using AI.

    Args:
        course_id: Course identifier.
        activity_id: Activity identifier.

    Request JSON (optional params vary by content_type):
        {
            "learning_objective": "...",
            "topic": "...",
            "audience_level": "intermediate",
            "duration_minutes": 8,
            "num_questions": 5,
            ...
        }

    Returns:
        JSON with content, metadata, and build_state.

    Errors:
        404 if course or activity not found.
        400 if content_type not supported for generation.
        409 if build_state is GENERATING (generation in progress).
        502 if AI API error.
    """
    try:
        # Look up course owner
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        # Load course
        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        # Find activity
        module, lesson, activity = _find_activity(course, activity_id)
        if not activity:
            return jsonify({"error": "Activity not found"}), 404

        # Check build state - only block if currently generating
        if activity.build_state == BuildState.GENERATING:
            return jsonify({"error": "Content generation already in progress"}), 409

        # Allow regeneration from any state except GENERATING and PUBLISHED
        if activity.build_state == BuildState.PUBLISHED:
            return jsonify({"error": "Cannot regenerate published content. Revert to draft first."}), 400

        # Get request parameters
        data = request.get_json() or {}

        # Provide defaults from course/activity context
        if 'topic' not in data:
            data['topic'] = activity.title
        if 'learning_objective' not in data:
            # Use first learning outcome behavior, or activity title as fallback
            if course.learning_outcomes:
                data['learning_objective'] = course.learning_outcomes[0].behavior
            else:
                data['learning_objective'] = f"Understand {activity.title}"
        if 'audience_level' not in data:
            data['audience_level'] = course.audience_level or 'intermediate'
        if 'language' not in data:
            data['language'] = getattr(course, 'language', 'English')

        # Load standards and build rules for the content type
        standards = None
        try:
            standards = load_standards(course)
            content_type_str = _content_type_to_standards_key(activity.content_type, activity.activity_type)
            if content_type_str:
                data['standards_rules'] = build_all_prompt_rules(standards, content_type_str)
        except Exception:
            # If standards loading fails, continue without rules
            pass

        # For quiz types, add bloom_level from activity or mapped learning objective
        if activity.content_type == ContentType.QUIZ and 'bloom_level' not in data:
            data['bloom_level'] = _get_bloom_level_for_activity(course, activity)

        # Determine generator based on content_type
        content_type = activity.content_type
        generator = None
        schema = None

        if content_type == ContentType.VIDEO:
            generator = VideoScriptGenerator()
            from src.generators.schemas.video_script import VideoScriptSchema
            schema = VideoScriptSchema
        elif content_type == ContentType.READING:
            generator = ReadingGenerator()
            from src.generators.schemas.reading import ReadingSchema
            schema = ReadingSchema
        elif content_type == ContentType.QUIZ and activity.activity_type == ActivityType.PRACTICE_QUIZ:
            generator = PracticeQuizGenerator()
            from src.generators.schemas.practice_quiz import PracticeQuizSchema
            schema = PracticeQuizSchema
        elif content_type == ContentType.QUIZ:
            generator = QuizGenerator()
            from src.generators.schemas.quiz import QuizSchema
            schema = QuizSchema
        elif content_type == ContentType.RUBRIC:
            generator = RubricGenerator()
            from src.generators.schemas.rubric import RubricSchema
            schema = RubricSchema
        elif content_type == ContentType.HOL:
            generator = HOLGenerator()
            from src.generators.schemas.hol import HOLSchema
            schema = HOLSchema
        elif content_type == ContentType.COACH:
            generator = CoachGenerator()
            from src.generators.schemas.coach import CoachSchema
            schema = CoachSchema
        elif content_type == ContentType.LAB:
            generator = LabGenerator()
            from src.generators.schemas.lab import LabSchema
            schema = LabSchema
        elif content_type == ContentType.DISCUSSION:
            generator = DiscussionGenerator()
            from src.generators.schemas.discussion import DiscussionSchema
            schema = DiscussionSchema
        elif content_type == ContentType.ASSIGNMENT:
            generator = AssignmentGenerator()
            from src.generators.schemas.assignment import AssignmentSchema
            schema = AssignmentSchema
        elif content_type == ContentType.PROJECT:
            generator = ProjectMilestoneGenerator()
            from src.generators.schemas.project import ProjectMilestoneSchema
            schema = ProjectMilestoneSchema
        elif content_type == ContentType.SCREENCAST:
            # Screencast generates executable Python code, not a schema
            generator = ScreencastGenerator()
            activity.build_state = BuildState.GENERATING
            activity.updated_at = datetime.now().isoformat()
            _project_store.save(owner_id, course)

            try:
                python_code, metadata = generator.generate_screencast(
                    learning_objective=data.get('learning_objective', ''),
                    topic=data.get('topic', activity.title),
                    audience_level=data.get('audience_level', 'intermediate'),
                    duration_minutes=data.get('duration_minutes', 5),
                    programming_language=data.get('programming_language', 'python'),
                    environment=data.get('environment', 'terminal')
                )
            except anthropic.APIError as e:
                activity.build_state = BuildState.DRAFT
                activity.updated_at = datetime.now().isoformat()
                _project_store.save(owner_id, course)
                return jsonify({"error": f"AI API error: {str(e)}"}), 502
            except Exception as e:
                activity.build_state = BuildState.DRAFT
                activity.updated_at = datetime.now().isoformat()
                _project_store.save(owner_id, course)
                return jsonify({"error": f"Content generation failed: {str(e)}"}), 502

            # Store Python code directly as content
            activity.content = python_code
            activity.word_count = metadata.get("narration_word_count", 0)
            activity.estimated_duration_minutes = metadata.get("estimated_duration_minutes", 0.0)
            activity.build_state = BuildState.GENERATED
            activity.updated_at = datetime.now().isoformat()
            _project_store.save(owner_id, course)

            log_audit_entry(
                course_id=course_id,
                user_id=current_user.id,
                action=ACTION_CONTENT_GENERATED,
                entity_type='activity',
                entity_id=activity_id,
                after={'content_type': activity.content_type.value, 'num_screens': metadata.get('num_screens', 0)}
            )

            return jsonify({
                "content": python_code,
                "metadata": metadata,
                "build_state": activity.build_state.value
            }), 200
        else:
            return jsonify({"error": f"Unsupported content type for generation: {content_type.value}"}), 400

        # Set build state to GENERATING
        activity.build_state = BuildState.GENERATING
        activity.updated_at = datetime.now().isoformat()
        _project_store.save(owner_id, course)

        # Generate content
        try:
            content, metadata = generator.generate(schema=schema, **data)
        except anthropic.APIError as e:
            # Restore build state on AI error
            activity.build_state = BuildState.DRAFT
            activity.updated_at = datetime.now().isoformat()
            _project_store.save(owner_id, course)
            return jsonify({"error": f"AI API error: {str(e)}"}), 502
        except Exception as e:
            # Restore build state on generation error
            activity.build_state = BuildState.DRAFT
            activity.updated_at = datetime.now().isoformat()
            _project_store.save(owner_id, course)
            return jsonify({"error": f"Content generation failed: {str(e)}"}), 502

        # Auto-humanize if enabled in standards
        try:
            if standards and standards.enable_auto_humanize:
                humanization = humanize_content(content, schema_name=schema.__name__)
                content = humanization.content
                metadata['humanization_score'] = humanization.score
                metadata['humanization_original_score'] = humanization.original_score
                metadata['patterns_fixed'] = humanization.patterns_fixed
                metadata['patterns_found'] = humanization.patterns_found
        except Exception:
            # If humanization fails, continue with original content
            pass

        # Store generated content
        activity.content = content.model_dump_json()
        activity.word_count = metadata.get("word_count", 0)
        activity.estimated_duration_minutes = metadata.get("estimated_duration_minutes", 0.0)
        activity.build_state = BuildState.GENERATED
        activity.updated_at = datetime.now().isoformat()

        # Save course
        _project_store.save(owner_id, course)

        # Log audit entry
        log_audit_entry(
            course_id=course_id,
            user_id=current_user.id,
            action=ACTION_CONTENT_GENERATED,
            entity_type='activity',
            entity_id=activity_id,
            after={'content_type': activity.content_type.value, 'word_count': activity.word_count}
        )

        return jsonify({
            "content": content.model_dump(),
            "metadata": metadata,
            "build_state": activity.build_state.value
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@content_bp.route('/api/courses/<course_id>/activities/<activity_id>/regenerate', methods=['POST'])
@login_required
@require_permission('generate_content')
def regenerate_content(course_id, activity_id):
    """Regenerate content for an activity, preserving previous version.

    Args:
        course_id: Course identifier.
        activity_id: Activity identifier.

    Request JSON (same as generate, plus optional feedback):
        {
            "feedback": "Make it more beginner-friendly",
            "learning_objective": "...",
            ...
        }

    Returns:
        JSON with content, metadata, and build_state.

    Errors:
        404 if course or activity not found.
        400 if no existing content to regenerate or content_type not supported.
        409 if build_state is GENERATING.
        502 if AI API error.
    """
    try:
        # Look up course owner
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        # Load course
        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        # Find activity
        module, lesson, activity = _find_activity(course, activity_id)
        if not activity:
            return jsonify({"error": "Activity not found"}), 404

        # Check build state - must have existing content
        if activity.build_state == BuildState.GENERATING:
            return jsonify({"error": "Content generation already in progress"}), 409

        if activity.build_state not in [BuildState.GENERATED, BuildState.REVIEWED]:
            return jsonify({"error": "No existing content to regenerate. Use generate endpoint first."}), 400

        # Preserve previous content
        if "previous_content" not in activity.metadata:
            activity.metadata["previous_content"] = []

        activity.metadata["previous_content"].append({
            "content": activity.content,
            "word_count": activity.word_count,
            "timestamp": datetime.now().isoformat()
        })

        # Get request parameters
        data = request.get_json() or {}
        feedback = data.pop("feedback", None)

        # Provide defaults from course/activity context
        if 'topic' not in data:
            data['topic'] = activity.title
        if 'learning_objective' not in data:
            if course.learning_outcomes:
                data['learning_objective'] = course.learning_outcomes[0].behavior
            else:
                data['learning_objective'] = f"Understand {activity.title}"
        if 'audience_level' not in data:
            data['audience_level'] = course.audience_level or 'intermediate'
        if 'language' not in data:
            data['language'] = getattr(course, 'language', 'English')

        # Load standards and build rules for the content type
        standards = None
        try:
            standards = load_standards(course)
            content_type_str = _content_type_to_standards_key(activity.content_type, activity.activity_type)
            if content_type_str:
                data['standards_rules'] = build_all_prompt_rules(standards, content_type_str)
        except Exception:
            # If standards loading fails, continue without rules
            pass

        # For quiz types, add bloom_level from activity or mapped learning objective
        if activity.content_type == ContentType.QUIZ and 'bloom_level' not in data:
            data['bloom_level'] = _get_bloom_level_for_activity(course, activity)

        # Add feedback to prompt parameters if provided
        if feedback:
            data["feedback"] = feedback

        # Determine generator based on content_type
        content_type = activity.content_type
        generator = None
        schema = None

        if content_type == ContentType.VIDEO:
            generator = VideoScriptGenerator()
            from src.generators.schemas.video_script import VideoScriptSchema
            schema = VideoScriptSchema
        elif content_type == ContentType.READING:
            generator = ReadingGenerator()
            from src.generators.schemas.reading import ReadingSchema
            schema = ReadingSchema
        elif content_type == ContentType.QUIZ and activity.activity_type == ActivityType.PRACTICE_QUIZ:
            generator = PracticeQuizGenerator()
            from src.generators.schemas.practice_quiz import PracticeQuizSchema
            schema = PracticeQuizSchema
        elif content_type == ContentType.QUIZ:
            generator = QuizGenerator()
            from src.generators.schemas.quiz import QuizSchema
            schema = QuizSchema
        elif content_type == ContentType.RUBRIC:
            generator = RubricGenerator()
            from src.generators.schemas.rubric import RubricSchema
            schema = RubricSchema
        elif content_type == ContentType.HOL:
            generator = HOLGenerator()
            from src.generators.schemas.hol import HOLSchema
            schema = HOLSchema
        elif content_type == ContentType.COACH:
            generator = CoachGenerator()
            from src.generators.schemas.coach import CoachSchema
            schema = CoachSchema
        elif content_type == ContentType.LAB:
            generator = LabGenerator()
            from src.generators.schemas.lab import LabSchema
            schema = LabSchema
        elif content_type == ContentType.DISCUSSION:
            generator = DiscussionGenerator()
            from src.generators.schemas.discussion import DiscussionSchema
            schema = DiscussionSchema
        elif content_type == ContentType.ASSIGNMENT:
            generator = AssignmentGenerator()
            from src.generators.schemas.assignment import AssignmentSchema
            schema = AssignmentSchema
        elif content_type == ContentType.PROJECT:
            generator = ProjectMilestoneGenerator()
            from src.generators.schemas.project import ProjectMilestoneSchema
            schema = ProjectMilestoneSchema
        elif content_type == ContentType.SCREENCAST:
            # Screencast generates executable Python code
            generator = ScreencastGenerator()
            activity.build_state = BuildState.GENERATING
            activity.updated_at = datetime.now().isoformat()
            _project_store.save(owner_id, course)

            try:
                python_code, metadata = generator.generate_screencast(
                    learning_objective=data.get('learning_objective', ''),
                    topic=data.get('topic', activity.title),
                    audience_level=data.get('audience_level', 'intermediate'),
                    duration_minutes=data.get('duration_minutes', 5),
                    programming_language=data.get('programming_language', 'python'),
                    environment=data.get('environment', 'terminal')
                )
            except anthropic.APIError as e:
                activity.build_state = BuildState.GENERATED
                activity.updated_at = datetime.now().isoformat()
                _project_store.save(owner_id, course)
                return jsonify({"error": f"AI API error: {str(e)}"}), 502
            except Exception as e:
                activity.build_state = BuildState.GENERATED
                activity.updated_at = datetime.now().isoformat()
                _project_store.save(owner_id, course)
                return jsonify({"error": f"Content generation failed: {str(e)}"}), 502

            activity.content = python_code
            activity.word_count = metadata.get("narration_word_count", 0)
            activity.estimated_duration_minutes = metadata.get("estimated_duration_minutes", 0.0)
            activity.build_state = BuildState.GENERATED
            activity.updated_at = datetime.now().isoformat()
            _project_store.save(owner_id, course)

            log_audit_entry(
                course_id=course_id,
                user_id=current_user.id,
                action=ACTION_CONTENT_UPDATED,
                entity_type='activity',
                entity_id=activity_id,
                after={'content_type': activity.content_type.value, 'num_screens': metadata.get('num_screens', 0), 'regenerated': True}
            )

            return jsonify({
                "content": python_code,
                "metadata": metadata,
                "build_state": activity.build_state.value
            }), 200
        else:
            return jsonify({"error": f"Unsupported content type for generation: {content_type.value}"}), 400

        # Set build state to GENERATING
        activity.build_state = BuildState.GENERATING
        activity.updated_at = datetime.now().isoformat()
        _project_store.save(owner_id, course)

        # Generate content
        try:
            content, metadata = generator.generate(schema=schema, **data)
        except anthropic.APIError as e:
            # Restore build state on AI error
            activity.build_state = BuildState.GENERATED
            activity.updated_at = datetime.now().isoformat()
            _project_store.save(owner_id, course)
            return jsonify({"error": f"AI API error: {str(e)}"}), 502
        except Exception as e:
            # Restore build state on generation error
            activity.build_state = BuildState.GENERATED
            activity.updated_at = datetime.now().isoformat()
            _project_store.save(owner_id, course)
            return jsonify({"error": f"Content generation failed: {str(e)}"}), 502

        # Auto-humanize if enabled in standards
        try:
            if standards and standards.enable_auto_humanize:
                humanization = humanize_content(content, schema_name=schema.__name__)
                content = humanization.content
                metadata['humanization_score'] = humanization.score
                metadata['humanization_original_score'] = humanization.original_score
                metadata['patterns_fixed'] = humanization.patterns_fixed
                metadata['patterns_found'] = humanization.patterns_found
        except Exception:
            # If humanization fails, continue with original content
            pass

        # Store regenerated content
        activity.content = content.model_dump_json()
        activity.word_count = metadata.get("word_count", 0)
        activity.estimated_duration_minutes = metadata.get("estimated_duration_minutes", 0.0)
        activity.build_state = BuildState.GENERATED
        activity.updated_at = datetime.now().isoformat()

        # Save course
        _project_store.save(owner_id, course)

        # Log audit entry with before (previous content preserved in metadata)
        log_audit_entry(
            course_id=course_id,
            user_id=current_user.id,
            action=ACTION_CONTENT_UPDATED,
            entity_type='activity',
            entity_id=activity_id,
            after={'content_type': activity.content_type.value, 'word_count': activity.word_count, 'regenerated': True}
        )

        return jsonify({
            "content": content.model_dump(),
            "metadata": metadata,
            "build_state": activity.build_state.value
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@content_bp.route('/api/courses/<course_id>/activities/<activity_id>/content', methods=['PUT'])
@login_required
@require_permission('edit_content')
def edit_content(course_id, activity_id):
    """Edit activity content inline and optionally update build state.

    Args:
        course_id: Course identifier.
        activity_id: Activity identifier.

    Request JSON:
        {
            "content": "...",  # JSON string or plain text
            "build_state": "reviewed"  # optional
        }

    Returns:
        JSON updated activity object.

    Errors:
        404 if course or activity not found.
        400 if request JSON is invalid or build_state is invalid.
        500 if save fails.
    """
    try:
        # Look up course owner
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        # Load course
        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        # Find activity
        module, lesson, activity = _find_activity(course, activity_id)
        if not activity:
            return jsonify({"error": "Activity not found"}), 404

        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        if "content" not in data:
            return jsonify({"error": "Missing required field: content"}), 400

        # Capture before state for audit
        before_word_count = activity.word_count

        # Update content
        activity.content = data["content"]

        # Recalculate word count
        activity.word_count = ContentMetadata.count_words(activity.content)

        # Update build state if provided
        if "build_state" in data:
            try:
                activity.build_state = BuildState(data["build_state"])
            except ValueError:
                return jsonify({"error": f"Invalid build_state: {data['build_state']}"}), 400

        activity.updated_at = datetime.now().isoformat()

        # Save course
        _project_store.save(owner_id, course)

        # Log audit entry with before/after
        log_audit_entry(
            course_id=course_id,
            user_id=current_user.id,
            action=ACTION_CONTENT_UPDATED,
            entity_type='activity',
            entity_id=activity_id,
            before={'word_count': before_word_count},
            after={'word_count': activity.word_count}
        )

        return jsonify(activity.to_dict()), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _get_generator_and_schema(content_type, activity_type):
    """Get generator and schema for a content type.

    Args:
        content_type: ContentType enum value.
        activity_type: ActivityType enum value.

    Returns:
        Tuple of (generator, schema) or (None, None) if not supported.
    """
    if content_type == ContentType.VIDEO:
        from src.generators.schemas.video_script import VideoScriptSchema
        return VideoScriptGenerator(), VideoScriptSchema
    elif content_type == ContentType.READING:
        from src.generators.schemas.reading import ReadingSchema
        return ReadingGenerator(), ReadingSchema
    elif content_type == ContentType.QUIZ and activity_type == ActivityType.PRACTICE_QUIZ:
        from src.generators.schemas.practice_quiz import PracticeQuizSchema
        return PracticeQuizGenerator(), PracticeQuizSchema
    elif content_type == ContentType.QUIZ:
        from src.generators.schemas.quiz import QuizSchema
        return QuizGenerator(), QuizSchema
    elif content_type == ContentType.RUBRIC:
        from src.generators.schemas.rubric import RubricSchema
        return RubricGenerator(), RubricSchema
    elif content_type == ContentType.HOL:
        from src.generators.schemas.hol import HOLSchema
        return HOLGenerator(), HOLSchema
    elif content_type == ContentType.COACH:
        from src.generators.schemas.coach import CoachSchema
        return CoachGenerator(), CoachSchema
    elif content_type == ContentType.LAB:
        from src.generators.schemas.lab import LabSchema
        return LabGenerator(), LabSchema
    elif content_type == ContentType.DISCUSSION:
        from src.generators.schemas.discussion import DiscussionSchema
        return DiscussionGenerator(), DiscussionSchema
    elif content_type == ContentType.ASSIGNMENT:
        from src.generators.schemas.assignment import AssignmentSchema
        return AssignmentGenerator(), AssignmentSchema
    elif content_type == ContentType.PROJECT:
        from src.generators.schemas.project import ProjectMilestoneSchema
        return ProjectMilestoneGenerator(), ProjectMilestoneSchema
    elif content_type == ContentType.SCREENCAST:
        from src.generators.schemas.screencast import ScreencastSchema
        return ScreencastGenerator(), ScreencastSchema
    return None, None


@content_bp.route('/api/courses/<course_id>/activities/<activity_id>/generate/stream', methods=['GET'])
@login_required
def generate_content_stream(course_id, activity_id):
    """Stream content generation via Server-Sent Events.

    Provides real-time streaming of generated content chunks to the client.
    Uses SSE format with 'chunk', 'complete', and 'error' message types.

    Args:
        course_id: Course identifier.
        activity_id: Activity identifier.

    Returns:
        SSE stream with content chunks.

    Errors:
        404 if course or activity not found (returned as JSON before stream).
        400 if content_type not supported.
        409 if generation already in progress.
    """
    # Look up course owner
    owner_id = Collaborator.get_course_owner_id(course_id)
    if not owner_id:
        return jsonify({"error": "Course not found"}), 404

    # Load course
    course = _project_store.load(owner_id, course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404

    # Find activity
    module, lesson, activity = _find_activity(course, activity_id)
    if not activity:
        return jsonify({"error": "Activity not found"}), 404

    # Check build state - only block if currently generating
    if activity.build_state == BuildState.GENERATING:
        return jsonify({"error": "Content generation already in progress"}), 409

    # Allow regeneration from any state except GENERATING and PUBLISHED
    if activity.build_state == BuildState.PUBLISHED:
        return jsonify({"error": "Cannot regenerate published content. Revert to draft first."}), 400

    # Get generator
    generator, schema = _get_generator_and_schema(activity.content_type, activity.activity_type)
    if not generator:
        return jsonify({"error": f"Unsupported content type: {activity.content_type.value}"}), 400

    # Prepare generation parameters from course/activity context
    gen_params = {
        'topic': activity.title,
        'audience_level': course.audience_level or 'intermediate',
        'language': getattr(course, 'language', 'English')
    }
    if course.learning_outcomes:
        gen_params['learning_objective'] = course.learning_outcomes[0].behavior
    else:
        gen_params['learning_objective'] = f"Understand {activity.title}"

    # Load standards and build rules for the content type
    try:
        standards = load_standards(course)
        content_type_str = _content_type_to_standards_key(activity.content_type, activity.activity_type)
        if content_type_str:
            gen_params['standards_rules'] = build_all_prompt_rules(standards, content_type_str)
    except Exception:
        # If standards loading fails, continue without rules
        pass

    # For quiz types, add bloom_level from activity or mapped learning objective
    if activity.content_type == ContentType.QUIZ:
        gen_params['bloom_level'] = _get_bloom_level_for_activity(course, activity)

    # Capture user_id before entering generator context
    user_id = current_user.id

    # Set build state to GENERATING
    activity.build_state = BuildState.GENERATING
    activity.updated_at = datetime.now().isoformat()
    _project_store.save(owner_id, course)

    def generate():
        """Generator function for SSE stream with heartbeats to keep connection alive."""
        result_queue = queue.Queue()

        def run_generation():
            """Run AI generation in a thread."""
            try:
                content, metadata = generator.generate(schema=schema, **gen_params)
                result_queue.put(('success', content, metadata))
            except anthropic.APIError as e:
                result_queue.put(('api_error', str(e), None))
            except Exception as e:
                result_queue.put(('error', str(e), None))

        # Start generation in a background thread
        gen_thread = threading.Thread(target=run_generation)
        gen_thread.start()

        # Send heartbeats while waiting for generation to complete
        heartbeat_interval = 10  # seconds
        while gen_thread.is_alive():
            # Check if result is ready (non-blocking)
            try:
                result = result_queue.get_nowait()
                break
            except queue.Empty:
                pass

            # Send heartbeat to keep connection alive
            yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"

            # Wait for either result or next heartbeat
            gen_thread.join(timeout=heartbeat_interval)

        # Get result if we didn't already
        if result_queue.empty():
            gen_thread.join()  # Ensure thread is done

        try:
            result = result_queue.get_nowait()
        except queue.Empty:
            result = ('error', 'Generation thread completed without result', None)

        status, content_or_error, metadata = result

        if status == 'success':
            content = content_or_error
            # Get the JSON representation
            content_json = content.model_dump()
            content_str = json.dumps(content_json)

            # Simulate streaming by sending chunks
            chunk_size = 100
            for i in range(0, len(content_str), chunk_size):
                chunk = content_str[i:i+chunk_size]
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
                time.sleep(0.01)  # Small delay for visual effect

            # Reload course to update activity (in case of concurrent access)
            try:
                course_updated = _project_store.load(owner_id, course_id)
                if course_updated:
                    _, _, activity_updated = _find_activity(course_updated, activity_id)

                    if activity_updated:
                        # Store generated content
                        activity_updated.content = content.model_dump_json()
                        activity_updated.word_count = metadata.get("word_count", 0)
                        activity_updated.estimated_duration_minutes = metadata.get("estimated_duration_minutes", 0.0)
                        activity_updated.build_state = BuildState.GENERATED
                        activity_updated.updated_at = datetime.now().isoformat()
                        _project_store.save(owner_id, course_updated)

                        # Log audit entry (use captured user_id)
                        try:
                            log_audit_entry(
                                course_id=course_id,
                                user_id=user_id,
                                action=ACTION_CONTENT_GENERATED,
                                entity_type='activity',
                                entity_id=activity_id,
                                after={'content_type': activity_updated.content_type.value, 'word_count': activity_updated.word_count}
                            )
                        except Exception:
                            pass  # Don't fail on audit log errors
            except Exception as save_err:
                # Log but don't fail - content was generated successfully
                print(f"Warning: Failed to save generated content: {save_err}")

            # Send complete message (always send, even if save failed)
            yield f"data: {json.dumps({'type': 'complete', 'content': content_json})}\n\n"

        elif status == 'api_error':
            # Restore build state on AI error
            try:
                course_err = _project_store.load(owner_id, course_id)
                _, _, activity_err = _find_activity(course_err, activity_id)
                if activity_err:
                    activity_err.build_state = BuildState.DRAFT
                    activity_err.updated_at = datetime.now().isoformat()
                    _project_store.save(owner_id, course_err)
            except Exception:
                pass
            yield f"data: {json.dumps({'type': 'error', 'message': f'AI API error: {content_or_error}'})}\n\n"

        else:  # error
            # Restore build state on error
            try:
                course_err = _project_store.load(owner_id, course_id)
                _, _, activity_err = _find_activity(course_err, activity_id)
                if activity_err:
                    activity_err.build_state = BuildState.DRAFT
                    activity_err.updated_at = datetime.now().isoformat()
                    _project_store.save(owner_id, course_err)
            except Exception:
                pass
            yield f"data: {json.dumps({'type': 'error', 'message': content_or_error})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )


@content_bp.route('/api/courses/<course_id>/activities/<activity_id>/humanize', methods=['POST'])
@login_required
@require_permission('edit_content')
def humanize_activity_content(course_id, activity_id):
    """Humanize content for an activity.

    Applies text humanization to reduce AI-sounding patterns in generated content.

    Args:
        course_id: Course identifier.
        activity_id: Activity identifier.

    Request JSON (optional):
        {
            "detect_only": false  // If true, only detect patterns without fixing
        }

    Returns:
        JSON with humanized content, score, and pattern details.

    Errors:
        404 if course or activity not found.
        400 if no content to humanize.
    """
    try:
        # Look up course owner
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        # Load course
        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        # Find activity
        module, lesson, activity = _find_activity(course, activity_id)
        if not activity:
            return jsonify({"error": "Activity not found"}), 404

        # Check if there's content to humanize
        if not activity.content:
            return jsonify({"error": "No content to humanize. Generate content first."}), 400

        # Get request parameters
        data = request.get_json() or {}
        detect_only = data.get('detect_only', False)

        # Parse content JSON
        try:
            content_data = json.loads(activity.content)
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid content format"}), 400

        # Get schema name from content type
        schema_name = _content_type_to_schema_name(activity.content_type, activity.activity_type)

        # Humanize content
        result = humanize_content(content_data, schema_name=schema_name, detect_only=detect_only)

        # Update activity content if not detect_only
        if not detect_only:
            activity.content = json.dumps(result.content)
            activity.updated_at = datetime.now().isoformat()
            _project_store.save(owner_id, course)

            # Log audit entry
            log_audit_entry(
                course_id=course_id,
                user_id=current_user.id,
                action=ACTION_CONTENT_UPDATED,
                entity_type='activity',
                entity_id=activity_id,
                after={'humanized': True, 'patterns_fixed': result.patterns_fixed}
            )

        return jsonify({
            "content": result.content,
            "original_score": result.original_score,
            "score": result.score,
            "patterns_found": result.patterns_found,
            "patterns_fixed": result.patterns_fixed,
            "detect_only": detect_only
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@content_bp.route('/api/courses/<course_id>/activities/<activity_id>/humanize/score', methods=['GET'])
@login_required
def get_humanization_score(course_id, activity_id):
    """Get humanization score for activity content.

    Returns the humanization score and pattern breakdown without modifying content.

    Args:
        course_id: Course identifier.
        activity_id: Activity identifier.

    Returns:
        JSON with score and pattern breakdown.

    Errors:
        404 if course or activity not found.
        400 if no content to score.
    """
    try:
        # Look up course owner
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        # Load course
        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        # Find activity
        module, lesson, activity = _find_activity(course, activity_id)
        if not activity:
            return jsonify({"error": "Activity not found"}), 404

        # Check if there's content to score
        if not activity.content:
            return jsonify({"error": "No content to score. Generate content first."}), 400

        # Parse content JSON
        try:
            content_data = json.loads(activity.content)
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid content format"}), 400

        # Get schema name from content type
        schema_name = _content_type_to_schema_name(activity.content_type, activity.activity_type)

        # Get score
        score_data = get_content_score(content_data, schema_name=schema_name)

        return jsonify(score_data), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _content_type_to_schema_name(content_type, activity_type):
    """Map ContentType enum to schema class name.

    Args:
        content_type: ContentType enum value.
        activity_type: ActivityType enum value.

    Returns:
        String schema name or None if not supported.
    """
    # Handle practice quiz specially since it has same ContentType as quiz
    if content_type == ContentType.QUIZ and activity_type == ActivityType.PRACTICE_QUIZ:
        return "PracticeQuizSchema"

    mapping = {
        ContentType.VIDEO: "VideoScriptSchema",
        ContentType.READING: "ReadingSchema",
        ContentType.QUIZ: "QuizSchema",
        ContentType.RUBRIC: "RubricSchema",
        ContentType.HOL: "HOLSchema",
        ContentType.COACH: "CoachSchema",
        ContentType.LAB: "LabSchema",
        ContentType.DISCUSSION: "DiscussionSchema",
        ContentType.ASSIGNMENT: "AssignmentSchema",
        ContentType.PROJECT: "ProjectMilestoneSchema",
    }
    return mapping.get(content_type)


@content_bp.route('/api/courses/<course_id>/activities/<activity_id>/preview', methods=['GET'])
@login_required
def get_learner_preview(course_id, activity_id):
    """Get learner-facing preview HTML for activity content.

    Renders content as learners would see it, stripping author-only elements
    like speaker notes, correct answer indicators, and explanations.

    Args:
        course_id: Course identifier.
        activity_id: Activity identifier.

    Returns:
        JSON with rendered HTML and viewport CSS.

    Errors:
        404 if course or activity not found.
        400 if no content to preview.
    """
    from src.utils.preview_renderer import render_learner_preview

    try:
        # Look up course owner
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        # Load course
        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        # Find activity
        module, lesson, activity = _find_activity(course, activity_id)
        if not activity:
            return jsonify({"error": "Activity not found"}), 404

        # Check if there's content to preview
        if not activity.content:
            return jsonify({"error": "No content to preview. Generate content first."}), 400

        # Get content type value
        content_type = activity.content_type
        if hasattr(content_type, 'value'):
            content_type = content_type.value

        # Render learner preview
        preview_html = render_learner_preview(content_type, activity.content)

        return jsonify({
            "html": preview_html,
            "content_type": content_type,
            "title": activity.title
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
