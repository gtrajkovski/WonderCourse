"""Course Builder Studio - Flask web application.

Provides dashboard UI and REST API for course management.
"""

import os
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, timezone

from src.config import Config
from src.core.project_store import ProjectStore
from src.core.models import Course

# Initialize Flask app
app = Flask(__name__, template_folder='templates', static_folder='static')

# Configure app settings for auth
app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['DATABASE'] = str(Config.DATABASE)

# Configure Flask-Mail
app.config['MAIL_SERVER'] = Config.MAIL_SERVER
app.config['MAIL_PORT'] = Config.MAIL_PORT
app.config['MAIL_USE_TLS'] = Config.MAIL_USE_TLS
app.config['MAIL_USERNAME'] = Config.MAIL_USERNAME
app.config['MAIL_PASSWORD'] = Config.MAIL_PASSWORD
app.config['MAIL_DEFAULT_SENDER'] = Config.MAIL_DEFAULT_SENDER
app.config['APP_URL'] = Config.APP_URL

# Ensure directories exist
Config.ensure_dirs()

# Register error handlers for consistent API error responses
from src.utils.error_handlers import register_error_handlers
register_error_handlers(app)

# Initialize ProjectStore singleton
project_store = ProjectStore(Config.PROJECTS_DIR)

# Initialize auth infrastructure
from src.auth import init_app as init_auth_db
from src.auth import init_login_manager
from src.auth.routes import auth_bp, init_auth_bp
from src.auth.mail import init_mail

init_auth_db(app)  # Register db teardown and init-db CLI command
init_login_manager(app)  # Configure Flask-Login
init_auth_bp(app)  # Configure rate limiter
init_mail(app)  # Configure Flask-Mail for password reset emails

# Register auth blueprint
app.register_blueprint(auth_bp)

# Try to initialize AIClient singleton (may fail if no API key)
try:
    from src.ai.client import AIClient
    ai_client = AIClient()
except ValueError:
    # No API key set - AI features will be disabled
    ai_client = None

# Register API Blueprints
from src.api.modules import modules_bp, init_modules_bp
init_modules_bp(project_store)
app.register_blueprint(modules_bp)

from src.api.lessons import lessons_bp, init_lessons_bp
init_lessons_bp(project_store)
app.register_blueprint(lessons_bp)

from src.api.activities import activities_bp, init_activities_bp
init_activities_bp(project_store)
app.register_blueprint(activities_bp)

from src.api.learning_outcomes import learning_outcomes_bp, init_learning_outcomes_bp
init_learning_outcomes_bp(project_store)
app.register_blueprint(learning_outcomes_bp)

from src.api.blueprint import blueprint_bp, init_blueprint_bp
init_blueprint_bp(project_store)
app.register_blueprint(blueprint_bp)

from src.api.content import content_bp, init_content_bp
init_content_bp(project_store)
app.register_blueprint(content_bp)

from src.api.build_state import build_state_bp, init_build_state_bp
init_build_state_bp(project_store)
app.register_blueprint(build_state_bp)

from src.api.textbook import textbook_bp, init_textbook_bp
init_textbook_bp(project_store)
app.register_blueprint(textbook_bp)

from src.api.validation import validation_bp, init_validation_bp
init_validation_bp(project_store)
app.register_blueprint(validation_bp)

from src.api.export import export_bp, init_export_bp
init_export_bp(project_store)
app.register_blueprint(export_bp)

from src.api.collab import collab_bp, init_collab_bp
init_collab_bp(project_store)
app.register_blueprint(collab_bp)

from src.api.edit_bp import edit_bp, init_edit_bp
init_edit_bp()
app.register_blueprint(edit_bp, url_prefix='/api/edit')

from src.api.import_bp import import_bp, init_import_bp
init_import_bp(project_store)
app.register_blueprint(import_bp)

from src.api.coach_bp import coach_bp, init_coach_bp
init_coach_bp(project_store)
app.register_blueprint(coach_bp)

from src.api.help import init_help_bp
help_bp = init_help_bp()
app.register_blueprint(help_bp)

from src.api.standards import standards_bp, init_standards_bp
init_standards_bp()
app.register_blueprint(standards_bp)

from src.api.duration import duration_bp, init_duration_bp
init_duration_bp(project_store)
app.register_blueprint(duration_bp)

from src.api.learner_profiles import learner_profiles_bp, init_learner_profiles_bp
init_learner_profiles_bp()
app.register_blueprint(learner_profiles_bp)

from src.core.taxonomy_store import TaxonomyStore
from src.api.taxonomies import taxonomies_bp, init_taxonomies_bp
taxonomy_store = TaxonomyStore()
init_taxonomies_bp(taxonomy_store, project_store)
app.register_blueprint(taxonomies_bp)

from src.api.flow_control import flow_bp, init_flow_bp
init_flow_bp(project_store)
app.register_blueprint(flow_bp)

from src.api.course_pages import course_pages_bp, init_course_pages_bp
init_course_pages_bp(project_store)
app.register_blueprint(course_pages_bp)

from src.api.audit import audit_bp, init_audit_bp
init_audit_bp(project_store)
app.register_blueprint(audit_bp)

from src.api.notes import notes_bp, init_notes_bp
init_notes_bp(project_store)
app.register_blueprint(notes_bp)

from src.api.images import init_images_bp
images_bp = init_images_bp(project_store)
app.register_blueprint(images_bp)

# Seed permissions on startup (idempotent, skip if table doesn't exist)
from src.collab.permissions import seed_permissions
with app.app_context():
    from src.auth.db import get_db
    try:
        db = get_db()
        # Check if permission table exists before seeding
        table_check = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='permission'"
        ).fetchone()
        if table_check:
            seed_permissions(db)
    except Exception:
        # Database not initialized yet, skip seeding
        pass


# ===========================
# Page Routes
# ===========================

@app.route('/')
def index():
    """Redirect root to login or dashboard based on auth status."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login_page'))


@app.route('/login')
def login_page():
    """Render login page.

    If user is already authenticated, redirect to dashboard.
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('auth/login.html')


@app.route('/register')
def register_page():
    """Render registration page.

    If user is already authenticated, redirect to dashboard.
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('auth/register.html')


@app.route('/forgot-password')
def forgot_password_page():
    """Render forgot password page.

    If user is already authenticated, redirect to dashboard.
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    # For now, redirect to login until we build the forgot password UI
    return redirect(url_for('login_page'))


@app.route('/dashboard')
@login_required
def dashboard():
    """Render dashboard page with course list.

    Requires authentication.
    """
    courses = project_store.list_courses(current_user.id)
    return render_template('dashboard.html',
                         courses=courses,
                         active_page='dashboard')


@app.route('/courses/<course_id>/planner')
@login_required
def planner(course_id):
    """Render planner page for course setup and blueprint generation.

    Requires authentication. Redirects to dashboard if course not found
    or not owned by current user.

    Args:
        course_id: Course identifier.
    """
    course = project_store.load(current_user.id, course_id)
    if not course:
        return redirect(url_for('dashboard'))
    return render_template('planner.html',
                         course=course,
                         active_page='planner')


@app.route('/courses/<course_id>/builder')
@login_required
def builder(course_id):
    """Render builder page for course structure editing.

    Provides hierarchical tree view for modules, lessons, and activities
    with drag-drop reordering and CRUD operations.

    Requires authentication. Redirects to dashboard if course not found
    or not owned by current user.

    Args:
        course_id: Course identifier.
    """
    course = project_store.load(current_user.id, course_id)
    if not course:
        return redirect(url_for('dashboard'))
    return render_template('builder.html',
                         course=course,
                         active_page='builder')


@app.route('/courses/<course_id>/studio')
@login_required
def studio(course_id):
    """Render studio page for content generation and editing.

    Provides three-panel layout for activity selection, content preview
    with streaming generation, and workflow controls.

    Requires authentication. Redirects to dashboard if course not found
    or not owned by current user.

    Args:
        course_id: Course identifier.
    """
    course = project_store.load(current_user.id, course_id)
    if not course:
        return redirect(url_for('dashboard'))
    selected_activity_id = request.args.get('activity')
    return render_template('studio.html',
                         course=course,
                         selected_activity_id=selected_activity_id,
                         active_page='studio')


@app.route('/courses/<course_id>/textbook')
@login_required
def textbook(course_id):
    """Render textbook page for chapter generation and glossary management.

    Provides chapter list with generation controls, preview panel,
    and glossary CRUD operations.

    Requires authentication. Redirects to dashboard if course not found
    or not owned by current user.

    Args:
        course_id: Course identifier.
    """
    course = project_store.load(current_user.id, course_id)
    if not course:
        return redirect(url_for('dashboard'))
    return render_template('textbook.html',
                         course=course,
                         active_page='textbook')


@app.route('/courses/<course_id>/pages')
@login_required
def pages(course_id):
    """Render course pages for syllabus, about, and resources generation.

    Provides auto-generation of course documentation pages from
    course metadata and structure.

    Requires authentication. Redirects to dashboard if course not found
    or not owned by current user.

    Args:
        course_id: Course identifier.
    """
    course = project_store.load(current_user.id, course_id)
    if not course:
        return redirect(url_for('dashboard'))
    return render_template('pages.html',
                         course=course,
                         active_page='pages')


@app.route('/courses/<course_id>/audit')
@login_required
def audit(course_id):
    """Render audit page for course quality analysis.

    Provides comprehensive course auditing including flow analysis,
    repetition detection, objective alignment, and content gap checks.

    Requires authentication. Redirects to dashboard if course not found
    or not owned by current user.

    Args:
        course_id: Course identifier.
    """
    course = project_store.load(current_user.id, course_id)
    if not course:
        return redirect(url_for('dashboard'))
    return render_template('audit.html',
                         course=course,
                         active_page='audit')


@app.route('/courses/<course_id>/progress')
@login_required
def progress(course_id):
    """Render progress dashboard for course completion tracking.

    Provides visualization of build state progress, content metrics,
    module completion, and quality indicators.

    Requires authentication. Redirects to dashboard if course not found
    or not owned by current user.

    Args:
        course_id: Course identifier.
    """
    course = project_store.load(current_user.id, course_id)
    if not course:
        return redirect(url_for('dashboard'))
    return render_template('progress.html',
                         course=course,
                         active_page='progress')


@app.route('/courses/<course_id>/publish')
@login_required
def publish(course_id):
    """Render publish page for course validation and export.

    Provides validation summary, export format selection, preview
    capability, and download functionality.

    Requires authentication. Redirects to dashboard if course not found
    or not owned by current user.

    Args:
        course_id: Course identifier.
    """
    course = project_store.load(current_user.id, course_id)
    if not course:
        return redirect(url_for('dashboard'))
    return render_template('publish.html',
                         course=course,
                         active_page='publish')


@app.route('/courses/<course_id>/activities/<activity_id>/coach')
@login_required
def coach(course_id, activity_id):
    """Render interactive coach chat page for student interaction.

    Provides full-screen chat interface with streaming responses,
    real-time evaluation, and session management.

    Requires authentication. Redirects to dashboard if course or activity
    not found or not owned by current user.

    Args:
        course_id: Course identifier.
        activity_id: Activity identifier.
    """
    course = project_store.load(current_user.id, course_id)
    if not course:
        return redirect(url_for('dashboard'))

    # Find activity
    activity = None
    for module in course.modules:
        for lesson in module.lessons:
            for act in lesson.activities:
                if act.id == activity_id:
                    activity = act
                    break

    if not activity:
        return redirect(url_for('dashboard'))

    # Build persona from activity content
    persona = {
        "name": activity.content.get("title", "Coach") if activity.content else "Coach",
        "type": "supportive"
    }

    # Build dialogue structure
    dialogue_structure = {}
    if activity.content:
        dialogue_structure = {
            "scenario": activity.content.get("scenario", ""),
            "tasks": activity.content.get("tasks", []),
            "conversation_starters": activity.content.get("conversation_starters", [])
        }

    return render_template('coach.html',
                         course=course,
                         activity=activity,
                         persona=persona,
                         dialogue_structure=dialogue_structure,
                         hints_enabled=False)


@app.route('/coach/preview/<course_id>/<activity_id>')
@login_required
def coach_preview(course_id, activity_id):
    """Render coach preview page for instructor testing.

    Allows instructors to test coaching interactions before releasing
    to students.

    Requires authentication. Redirects to dashboard if course or activity
    not found or not owned by current user.

    Args:
        course_id: Course identifier.
        activity_id: Activity identifier.
    """
    # Reuse coach route for preview
    return coach(course_id, activity_id)


@app.route('/glossary')
@login_required
def glossary_page():
    """Render glossary page with instructional design terms.

    Provides searchable glossary of educational and instructional design
    concepts used throughout the application.

    Requires authentication.
    """
    return render_template('help/glossary.html',
                         active_page='glossary')


@app.route('/import')
@login_required
def import_page():
    """Render import page for content upload, paste, and URL fetch.

    Provides full-page import interface with multiple sources:
    - Paste from clipboard
    - File upload (drag & drop)
    - Public URL fetch
    - Google Docs OAuth import

    Requires authentication.
    """
    return render_template('import.html',
                         active_page='import')


@app.route('/courses/<course_id>/import')
@login_required
def import_page_with_course(course_id):
    """Render import page with course context.

    Same as /import but with course context for direct activity import.

    Requires authentication. Redirects to dashboard if course not found
    or not owned by current user.

    Args:
        course_id: Course identifier.
    """
    course = project_store.load(current_user.id, course_id)
    if not course:
        return redirect(url_for('dashboard'))

    return render_template('import.html',
                         course=course,
                         course_id=course_id,
                         active_page='import')


# ===========================
# API Endpoints
# ===========================

def _count_activities(course):
    """Count total activities in a course without loading full content.

    Args:
        course: Course instance to traverse.

    Returns:
        Integer count of total activities.
    """
    count = 0
    for module in course.modules:
        for lesson in module.lessons:
            count += len(lesson.activities)
    return count


def _compute_build_state(course):
    """Compute overall build state for a course.

    Args:
        course: Course instance to analyze.

    Returns:
        String representing overall state: empty, draft, in_progress, or complete.
    """
    activity_count = 0
    activity_states = []

    for module in course.modules:
        for lesson in module.lessons:
            activity_count += len(lesson.activities)
            for activity in lesson.activities:
                activity_states.append(activity.build_state.value)

    if activity_count == 0:
        return "empty"
    elif all(state in ["approved", "published"] for state in activity_states):
        return "complete"
    elif any(state == "generated" for state in activity_states):
        return "in_progress"
    else:
        return "draft"


@app.route('/api/courses', methods=['GET'])
@login_required
def get_courses():
    """Get list of all courses with pagination and optional summary mode.

    Query Parameters:
        page: Page number (default 1)
        per_page: Items per page (default 20, max 100)
        summary_only: If true, return lightweight summaries (default true)

    Returns:
        JSON object with courses array and pagination metadata:
        {
            "courses": [...],
            "page": int,
            "per_page": int,
            "total": int,
            "has_more": bool
        }
    """
    # Parse query parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    summary_only = request.args.get('summary_only', 'true').lower() == 'true'

    # Validate and cap per_page
    per_page = min(max(per_page, 1), 100)
    page = max(page, 1)

    # Get all courses for the user
    basic_courses = project_store.list_courses(current_user.id)
    total_count = len(basic_courses)

    # Apply pagination
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_courses = basic_courses[start_idx:end_idx]

    enhanced_courses = []

    for basic_info in paginated_courses:
        # Load full course data to compute status indicators
        course = project_store.load(current_user.id, basic_info['id'])
        if not course:
            continue

        if summary_only:
            # Lightweight summary - truncate description, count without deep traversal
            lesson_count = sum(len(module.lessons) for module in course.modules)
            activity_count = _count_activities(course)
            build_state = _compute_build_state(course)

            enhanced_courses.append({
                "id": course.id,
                "title": course.title,
                "description": course.description[:200] if course.description else "",
                "module_count": len(course.modules),
                "activity_count": activity_count,
                "build_state": build_state,
                "updated_at": course.updated_at
            })
        else:
            # Full metadata with all fields
            lesson_count = 0
            activity_count = 0
            activity_states = []

            for module in course.modules:
                lesson_count += len(module.lessons)
                for lesson in module.lessons:
                    activity_count += len(lesson.activities)
                    for activity in lesson.activities:
                        activity_states.append(activity.build_state.value)

            # Determine overall build state
            if activity_count == 0:
                build_state = "empty"
            elif all(state in ["approved", "published"] for state in activity_states):
                build_state = "complete"
            elif any(state == "generated" for state in activity_states):
                build_state = "in_progress"
            else:
                build_state = "draft"

            # Build enhanced metadata
            enhanced_courses.append({
                "id": course.id,
                "title": course.title,
                "description": course.description,
                "audience_level": course.audience_level,
                "modality": course.modality,
                "target_duration_minutes": course.target_duration_minutes,
                "module_count": len(course.modules),
                "lesson_count": lesson_count,
                "activity_count": activity_count,
                "build_state": build_state,
                "updated_at": course.updated_at
            })

    return jsonify({
        "courses": enhanced_courses,
        "page": page,
        "per_page": per_page,
        "total": total_count,
        "has_more": page * per_page < total_count
    })


@app.route('/api/courses', methods=['POST'])
@login_required
def create_course():
    """Create a new course.

    Request JSON:
        {
            "title": str,
            "description": str (optional),
            "audience_level": str (optional),
            "target_duration_minutes": int (optional),
            "modality": str (optional)
        }

    Returns:
        JSON course object with 201 status.

    Errors:
        400 if request JSON is invalid.
        500 if save fails.
    """
    from src.collab.decorators import ensure_owner_collaborator

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    try:
        # Create new course with provided data
        course = Course(
            title=data.get('title', 'Untitled Course'),
            description=data.get('description', ''),
            target_learner_description=data.get('target_learner_description', ''),
            audience_level=data.get('audience_level', 'intermediate'),
            default_audience=data.get('default_audience', 'Learners'),
            target_duration_minutes=data.get('target_duration_minutes', 60),
            modality=data.get('modality', 'online'),
            prerequisites=data.get('prerequisites'),
            tools=data.get('tools', []),
            grading_policy=data.get('grading_policy'),
            language=data.get('language', 'English'),
            standards_profile_id=data.get('standards_profile_id')
        )

        # Save to disk
        project_store.save(current_user.id, course)

        # Make creator the owner (seeds permissions if needed)
        ensure_owner_collaborator(course.id, current_user.id)

        return jsonify(course.to_dict()), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/courses/import', methods=['POST'])
@login_required
def import_course():
    """Import a course from exported JSON data.

    Request JSON:
        {
            "course_data": dict,        # Full course JSON (from export)
            "new_ids": bool (optional),  # Generate new IDs (default: true)
            "include_content": bool      # Include generated content (default: true)
        }

    Returns:
        JSON course object with 201 status.

    Errors:
        400 if request JSON is invalid or course data is malformed.
        500 if save fails.
    """
    from src.collab.decorators import ensure_owner_collaborator
    import uuid
    from datetime import datetime, timezone

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    course_data = data.get('course_data')
    if not course_data:
        return jsonify({"error": "Missing 'course_data' field"}), 400

    new_ids = data.get('new_ids', True)
    include_content = data.get('include_content', True)

    try:
        # Generate new IDs if requested
        if new_ids:
            # Generate new course ID
            course_data['id'] = f"course_{uuid.uuid4().hex[:12]}"

            # Generate new IDs for modules, lessons, activities
            for module in course_data.get('modules', []):
                module['id'] = f"mod_{uuid.uuid4().hex[:8]}"
                for lesson in module.get('lessons', []):
                    lesson['id'] = f"les_{uuid.uuid4().hex[:8]}"
                    for activity in lesson.get('activities', []):
                        activity['id'] = f"act_{uuid.uuid4().hex[:8]}"

            # Generate new IDs for learning outcomes
            for outcome in course_data.get('learning_outcomes', []):
                outcome['id'] = f"lo_{uuid.uuid4().hex[:8]}"

            # Generate new IDs for textbook chapters
            for chapter in course_data.get('textbook_chapters', []):
                chapter['id'] = f"ch_{uuid.uuid4().hex[:8]}"

        # Clear content if not including it
        if not include_content:
            for module in course_data.get('modules', []):
                for lesson in module.get('lessons', []):
                    for activity in lesson.get('activities', []):
                        activity['content'] = ''
                        activity['build_state'] = 'draft'
                        activity['word_count'] = 0

        # Update timestamps
        now = datetime.now(timezone.utc).isoformat()
        course_data['created_at'] = now
        course_data['updated_at'] = now

        # Create course from dict
        course = Course.from_dict(course_data)

        # Save to disk
        project_store.save(current_user.id, course)

        # Make importer the owner
        ensure_owner_collaborator(course.id, current_user.id)

        return jsonify(course.to_dict()), 201

    except KeyError as e:
        return jsonify({"error": f"Missing required field: {e}"}), 400
    except ValueError as e:
        return jsonify({"error": f"Invalid course data: {e}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/courses/<course_id>', methods=['GET'])
@login_required
def get_course(course_id):
    """Get a specific course by ID.

    Args:
        course_id: Course identifier.

    Returns:
        JSON course object.

    Errors:
        404 if course not found.
        500 if load fails.
    """
    try:
        course = project_store.load(current_user.id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        return jsonify(course.to_dict())

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/courses/<course_id>', methods=['PUT'])
@login_required
def update_course(course_id):
    """Update an existing course.

    Args:
        course_id: Course identifier.

    Request JSON:
        Partial course data to update (any combination of fields).

    Returns:
        JSON updated course object.

    Errors:
        404 if course not found.
        400 if request JSON is invalid.
        500 if save fails.
    """
    # Get update data
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    try:
        # Load existing course
        course = project_store.load(current_user.id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        # Update fields
        if 'title' in data:
            course.title = data['title']
        if 'description' in data:
            course.description = data['description']
        if 'audience_level' in data:
            course.audience_level = data['audience_level']
        if 'target_duration_minutes' in data:
            course.target_duration_minutes = data['target_duration_minutes']
        if 'modality' in data:
            course.modality = data['modality']
        if 'prerequisites' in data:
            course.prerequisites = data['prerequisites']
        if 'tools' in data:
            course.tools = data['tools']
        if 'grading_policy' in data:
            course.grading_policy = data['grading_policy']
        if 'language' in data:
            course.language = data['language']
        if 'target_learner_description' in data:
            course.target_learner_description = data['target_learner_description']
        if 'default_audience' in data:
            course.default_audience = data['default_audience']
        if 'standards_profile_id' in data:
            course.standards_profile_id = data['standards_profile_id']
        if 'flow_mode' in data:
            from src.core.models import FlowMode
            try:
                course.flow_mode = FlowMode(data['flow_mode'])
            except ValueError:
                pass  # Ignore invalid flow_mode

        # Save updated course
        project_store.save(current_user.id, course)

        return jsonify(course.to_dict())

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/courses/<course_id>', methods=['DELETE'])
@login_required
def delete_course(course_id):
    """Delete a course.

    Args:
        course_id: Course identifier.

    Returns:
        JSON success message.

    Errors:
        404 if course not found.
    """
    try:
        deleted = project_store.delete(current_user.id, course_id)
        if not deleted:
            return jsonify({"error": "Course not found"}), 404

        return jsonify({"message": "Course deleted successfully"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/system/health', methods=['GET'])
def health_check():
    """System health check endpoint.

    Returns:
        JSON health status object.
    """
    return jsonify({
        "status": "ok",
        "version": "1.0.0",
        "ai_enabled": ai_client is not None
    })


# ===========================
# Main
# ===========================

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5003))
    app.run(host='127.0.0.1', port=port, debug=True)
