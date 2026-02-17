"""Textbook generation API endpoints.

Provides async textbook chapter generation with progress tracking via JobTracker.
Orchestrates TextbookGenerator, CoherenceValidator, and ProjectStore.
"""

import logging
import threading
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime

from src.core.models import TextbookChapter
from src.generators.textbook_generator import TextbookGenerator
from src.utils.coherence_validator import CoherenceValidator
from src.api.job_tracker import JobTracker
from src.collab.models import Collaborator

# Create Blueprint
textbook_bp = Blueprint('textbook', __name__)

# Module-level project_store reference (set during registration)
_project_store = None

# Logger for this module
logger = logging.getLogger(__name__)


def init_textbook_bp(project_store):
    """Initialize the textbook blueprint with a ProjectStore instance.

    Must be called before registering the blueprint with Flask app.

    Args:
        project_store: ProjectStore instance for course persistence.
    """
    global _project_store
    _project_store = project_store


def _find_learning_outcome(course, outcome_id):
    """Find learning outcome by ID.

    Args:
        course: Course instance to search.
        outcome_id: Learning outcome identifier.

    Returns:
        LearningOutcome if found, None otherwise.
    """
    for outcome in course.learning_outcomes:
        if outcome.id == outcome_id:
            return outcome
    return None


def _generate_with_progress(task_id, user_id, course_id, learning_outcome, topic):
    """Background function to generate textbook chapter with progress updates.

    Args:
        task_id: Job tracker task ID for progress updates.
        user_id: User identifier for course scoping.
        course_id: Course to save chapter to.
        learning_outcome: LearningOutcome instance.
        topic: Topic for chapter generation.
    """
    try:
        # Define progress callback that updates JobTracker
        def progress_callback(progress: float, step: str):
            JobTracker.update_job(task_id, status="running", progress=progress, current_step=step)

        # Generate chapter with progress tracking
        generator = TextbookGenerator()
        chapter_schema, metadata = generator.generate_chapter(
            learning_objective=learning_outcome.behavior,
            topic=topic,
            audience_level="undergraduate",
            progress_callback=progress_callback
        )

        # Run coherence validation
        progress_callback(0.8, "Running coherence validation")
        validator = CoherenceValidator()
        issues = validator.check_consistency(chapter_schema.sections, chapter_schema.glossary_terms)

        # Save chapter to course
        progress_callback(0.9, "Saving chapter")

        # Re-load course to get fresh state
        course = _project_store.load(user_id, course_id)
        if not course:
            raise ValueError(f"Course {course_id} not found during save")

        # Create TextbookChapter from schema
        chapter = TextbookChapter(
            title=chapter_schema.title,
            sections=[{"heading": s.heading, "content": s.content, "key_concepts": s.key_concepts}
                     for s in chapter_schema.sections],
            glossary_terms=[{"term": t.term, "definition": t.definition, "context": t.context}
                           for t in chapter_schema.glossary_terms],
            word_count=metadata.get("word_count", 0),
            learning_outcome_id=learning_outcome.id,
            image_placeholders=[img.model_dump() for img in chapter_schema.image_placeholders],
            references=[ref.model_dump() for ref in chapter_schema.references],
            coherence_issues=issues
        )

        course.textbook_chapters.append(chapter)
        course.updated_at = datetime.now().isoformat()
        _project_store.save(user_id, course)

        # Complete job
        JobTracker.update_job(
            task_id,
            status="completed",
            progress=1.0,
            current_step="Complete",
            result=chapter.to_dict()
        )

    except Exception as e:
        logger.error(f"Textbook generation failed for job {task_id}: {e}")
        JobTracker.update_job(task_id, status="failed", error=str(e))


@textbook_bp.route('/api/courses/<course_id>/textbook/generate', methods=['POST'])
@login_required
def generate_textbook(course_id):
    """Generate a textbook chapter asynchronously.

    Args:
        course_id: Course identifier.

    Request JSON:
        {
            "learning_outcome_id": "lo_xxx",
            "topic": "Machine Learning Basics"
        }

    Returns:
        202 with {"task_id": "textbook_xxx"} on success.

    Errors:
        400 if missing required fields.
        404 if course or learning outcome not found.
    """
    # Load course
    owner_id = Collaborator.get_course_owner_id(course_id)
    if not owner_id:
        return jsonify({"error": "Course not found"}), 404

    course = _project_store.load(owner_id, course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404

    # Get request data
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    # Validate required fields
    learning_outcome_id = data.get("learning_outcome_id")
    if not learning_outcome_id:
        return jsonify({"error": "Missing required field: learning_outcome_id"}), 400

    topic = data.get("topic", "")

    # Find learning outcome
    learning_outcome = _find_learning_outcome(course, learning_outcome_id)
    if not learning_outcome:
        return jsonify({"error": "Learning outcome not found"}), 404

    # Create job
    task_id = JobTracker.create_job("textbook")

    # Start background thread
    thread = threading.Thread(
        target=_generate_with_progress,
        args=(task_id, owner_id, course_id, learning_outcome, topic),
        daemon=False
    )
    thread.start()

    return jsonify({"task_id": task_id}), 202


@textbook_bp.route('/api/jobs/<task_id>', methods=['GET'])
@login_required
def get_job_status(task_id):
    """Get job status by task ID.

    Args:
        task_id: Job task identifier.

    Returns:
        JSON job status object.

    Errors:
        404 if task not found.
    """
    job = JobTracker.get_job(task_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    return jsonify(job.to_dict()), 200
