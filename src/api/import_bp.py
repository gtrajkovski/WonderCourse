"""
Import API endpoints for content upload, analysis, and conversion.

Provides endpoints for:
- Analyzing uploaded content without saving
- Importing content into course structure (blueprint)
- Importing content into specific activities
- AI-powered content conversion (plain text to structured formats)
- Content type suggestion
"""

from flask import Blueprint, request, jsonify, session, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, timezone
from werkzeug.utils import secure_filename
import io
import os

from src.core.models import BuildState, ContentType
from src.collab.decorators import require_permission
from src.config import Config
# from src.collab.audit import log_audit_entry, ACTION_CONTENT_UPDATED

# Create Blueprint
import_bp = Blueprint('import', __name__)

# Module-level references (set during registration)
_project_store = None
_converter = None
_url_fetcher = None
_google_client = None


def init_import_bp(project_store):
    """
    Initialize the import blueprint with a ProjectStore instance.

    Must be called before registering the blueprint with Flask app.

    Args:
        project_store: ProjectStore instance for course persistence.
    """
    global _project_store, _converter, _url_fetcher, _google_client
    _project_store = project_store

    # Import from src.importers package
    try:
        from src.importers import ContentConverter, URLFetcher, GoogleDocsClient
        _converter = ContentConverter()
        _url_fetcher = URLFetcher()

        # Initialize Google OAuth client if credentials available
        google_client_id = os.environ.get('GOOGLE_CLIENT_ID')
        google_client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')

        if google_client_id and google_client_secret:
            redirect_uri = f"{Config.APP_URL}/api/import/oauth/google/callback"
            _google_client = GoogleDocsClient(
                client_id=google_client_id,
                client_secret=google_client_secret,
                redirect_uri=redirect_uri
            )
        else:
            _google_client = None

    except (ImportError, AttributeError):
        # ContentConverter not available
        _converter = None
        _url_fetcher = None
        _google_client = None

    return import_bp


def _find_activity(course, activity_id):
    """
    Find activity and its parent containers by activity ID.

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


@import_bp.route('/api/import/analyze', methods=['POST'])
@login_required
def analyze_content():
    """
    Analyze uploaded content without saving it.

    Detects format, parses content, and provides AI-powered analysis
    including content type suggestions, Bloom's level, and structural feedback.

    Request:
        multipart/form-data with 'file' field
        OR
        JSON with 'content' (text) and optional 'format_hint'

    Query params:
        format_hint: Optional format override (json, markdown, text, etc.)

    Returns:
        JSON with:
        {
            "format_detected": "json|markdown|text|...",
            "parse_result": {
                "content_type": "...",
                "content": {...},
                "metadata": {...},
                "warnings": [...]
            },
            "analysis": {
                "suggested_type": "video_script|reading|quiz|...",
                "bloom_level": "apply",
                "word_count": 450,
                "estimated_duration": 3,
                "structure_issues": [...],
                "suggestions": [...]
            }
        }

    Errors:
        400 if no content provided or invalid format
        500 if parsing or analysis fails
    """
    # Import here to avoid circular dependency
    from src.importers import ImportPipeline

    pipeline = ImportPipeline()
    format_hint = request.args.get('format_hint')

    # Get content from file upload or JSON
    if 'file' in request.files:
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        filename = secure_filename(file.filename)
        content = file.read()

    elif request.is_json:
        data = request.get_json()
        content = data.get('content')
        filename = data.get('filename')

        if not content:
            return jsonify({'error': 'No content provided'}), 400

        if isinstance(content, str):
            content = content.encode('utf-8')

    else:
        return jsonify({'error': 'Request must be multipart/form-data or JSON'}), 400

    # Import and analyze
    try:
        result = pipeline.import_content(
            source=content,
            filename=filename,
            format_hint=format_hint,
            analyze=True
        )

        return jsonify(result.to_dict()), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500


@import_bp.route('/api/courses/<course_id>/import', methods=['POST'])
@login_required
@require_permission('edit_structure')
def import_to_course(course_id):
    """
    Import content into course (blueprint or structure).

    Request:
        multipart/form-data with 'file'
        OR
        JSON with 'content' and optional parameters

    Query params:
        target_type: 'blueprint' (replace course structure) or 'activity' (update activity content)
        target_id: Activity ID if target_type='activity'
        conflict_action: 'replace' (default), 'merge', or 'cancel'
        format_hint: Optional format override

    Returns:
        JSON with:
        {
            "imported": true,
            "content_type": "blueprint|activity",
            "target": "course_id|activity_id",
            "conflicts_resolved": ["..."]
        }

    Errors:
        400 if invalid parameters
        404 if course or target not found
        422 if content validation fails
    """
    # Import here to avoid circular dependency
    from src.importers import ImportPipeline

    # Load course
    course = _project_store.load(str(current_user.id), course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404

    # Get import parameters
    target_type = request.args.get('target_type', 'blueprint')
    target_id = request.args.get('target_id')
    conflict_action = request.args.get('conflict_action', 'replace')
    format_hint = request.args.get('format_hint')

    # Validate parameters
    if target_type not in ['blueprint', 'activity']:
        return jsonify({'error': 'target_type must be "blueprint" or "activity"'}), 400

    if conflict_action not in ['replace', 'merge', 'cancel']:
        return jsonify({'error': 'conflict_action must be "replace", "merge", or "cancel"'}), 400

    # Get content
    if 'file' in request.files:
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        filename = secure_filename(file.filename)
        content = file.read()

    elif request.is_json:
        data = request.get_json()
        content = data.get('content')
        filename = data.get('filename')

        if not content:
            return jsonify({'error': 'No content provided'}), 400

        if isinstance(content, str):
            content = content.encode('utf-8')

    else:
        return jsonify({'error': 'Request must be multipart/form-data or JSON'}), 400

    # Import content
    pipeline = ImportPipeline()

    try:
        result = pipeline.import_content(
            source=content,
            filename=filename,
            format_hint=format_hint,
            analyze=True
        )

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Import failed: {str(e)}'}), 500

    conflicts_resolved = []

    # Handle blueprint import
    if target_type == 'blueprint':
        # Blueprint import: replace course structure
        if result.parse_result.content_type != 'blueprint':
            return jsonify({
                'error': f'Content is not a blueprint (detected: {result.parse_result.content_type})'
            }), 422

        # Import blueprint structure
        from src.validators.course_validator import convert_blueprint_to_course

        try:
            blueprint_data = result.parse_result.content
            convert_blueprint_to_course(course, blueprint_data)

            if conflict_action == 'replace':
                conflicts_resolved.append('Replaced existing course structure with imported blueprint')

            # Save course
            _project_store.save(str(current_user.id), course)

            # Log audit entry

            return jsonify({
                'imported': True,
                'content_type': 'blueprint',
                'target': course_id,
                'conflicts_resolved': conflicts_resolved
            }), 200

        except Exception as e:
            return jsonify({'error': f'Blueprint import failed: {str(e)}'}), 422

    # Handle activity content import
    elif target_type == 'activity':
        if not target_id:
            return jsonify({'error': 'target_id required for activity import'}), 400

        # Find activity
        module, lesson, activity = _find_activity(course, target_id)
        if not activity:
            return jsonify({'error': 'Activity not found'}), 404

        # Update activity content
        activity.content = result.parse_result.content
        activity.metadata = activity.metadata or {}
        activity.metadata.update(result.parse_result.metadata)

        # Update word count
        if result.analysis:
            activity.word_count = result.analysis.word_count

        # Set state to GENERATED if currently DRAFT
        if activity.build_state == BuildState.DRAFT:
            activity.build_state = BuildState.GENERATED

        activity.updated_at = datetime.now(timezone.utc).isoformat()

        if conflict_action == 'replace':
            conflicts_resolved.append(f'Replaced content for activity {activity.title}')

        # Save course
        _project_store.save(str(current_user.id), course)

        # Log audit entry (commented out - signature mismatch)

        return jsonify({
            'imported': True,
            'content_type': 'activity',
            'target': target_id,
            'conflicts_resolved': conflicts_resolved
        }), 200


@import_bp.route('/api/courses/<course_id>/activities/<activity_id>/import', methods=['POST'])
@login_required
@require_permission('generate_content')
def import_to_activity(course_id, activity_id):
    """
    Import content directly into a specific activity.

    Convenience endpoint for importing content into an activity without
    needing to specify target_type and target_id as query params.

    Request:
        multipart/form-data with 'file'
        OR
        JSON with 'content' and optional 'filename'

    Query params:
        format_hint: Optional format override

    Returns:
        JSON with:
        {
            "imported": true,
            "content": {...},
            "analysis": {...}
        }

    Errors:
        400 if invalid content
        404 if course or activity not found
    """
    # Import here to avoid circular dependency
    from src.importers import ImportPipeline

    # Load course
    course = _project_store.load(str(current_user.id), course_id)
    if not course:
        return jsonify({'error': 'Course not found'}), 404

    # Find activity
    module, lesson, activity = _find_activity(course, activity_id)
    if not activity:
        return jsonify({'error': 'Activity not found'}), 404

    format_hint = request.args.get('format_hint')

    # Get content
    if 'file' in request.files:
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        filename = secure_filename(file.filename)
        content = file.read()

    elif request.is_json:
        data = request.get_json()
        content = data.get('content')
        filename = data.get('filename')

        if not content:
            return jsonify({'error': 'No content provided'}), 400

        if isinstance(content, str):
            content = content.encode('utf-8')

    else:
        return jsonify({'error': 'Request must be multipart/form-data or JSON'}), 400

    # Import content
    pipeline = ImportPipeline()

    try:
        result = pipeline.import_content(
            source=content,
            filename=filename,
            format_hint=format_hint,
            analyze=True
        )

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Import failed: {str(e)}'}), 500

    # Update activity
    activity.content = result.parse_result.content
    activity.metadata = activity.metadata or {}
    activity.metadata.update(result.parse_result.metadata)

    # Update word count from analysis
    if result.analysis:
        activity.word_count = result.analysis.word_count

    # Set state to GENERATED if currently DRAFT
    if activity.build_state == BuildState.DRAFT:
        activity.build_state = BuildState.GENERATED

    activity.updated_at = datetime.now(timezone.utc).isoformat()

    # Save course
    _project_store.save(str(current_user.id), course)

    # Log audit entry

    return jsonify({
        'imported': True,
        'content': result.parse_result.to_dict(),
        'analysis': result.analysis.to_dict() if result.analysis else None
    }), 200


@import_bp.route('/api/import/convert', methods=['POST'])
@login_required
def convert_content():
    """
    Convert plain text content to structured format using AI.

    Does not save to database, just returns conversion result.

    Request JSON:
        {
            "content": str,           # Plain text content to convert
            "target_type": str,       # Target ContentType (video, reading, quiz)
            "context": dict           # Optional context (topic, learning_objective, etc.)
        }

    Returns:
        {
            "original": str,
            "structured": dict,       # Structured output matching target schema
            "target_type": str,
            "confidence": float,      # 0.0-1.0 conversion confidence
            "changes": list[str]      # Description of changes made
        }

    Status Codes:
        200: Conversion successful
        400: Invalid request (missing fields, unsupported type)
        500: AI conversion error
    """
    data = request.json

    # Validate required fields
    if not data or 'content' not in data:
        return jsonify({"error": "Missing 'content' field"}), 400

    if 'target_type' not in data:
        return jsonify({"error": "Missing 'target_type' field"}), 400

    content = data['content']
    target_type_str = data['target_type'].upper()
    context = data.get('context', {})

    # Parse target type
    try:
        target_type = ContentType[target_type_str]
    except KeyError:
        return jsonify({
            "error": f"Invalid target_type: {target_type_str}",
            "valid_types": ["VIDEO", "READING", "QUIZ"]
        }), 400

    # Validate content type is supported
    if target_type not in [ContentType.VIDEO, ContentType.READING, ContentType.QUIZ]:
        return jsonify({
            "error": f"Conversion not supported for {target_type_str}",
            "supported_types": ["VIDEO", "READING", "QUIZ"]
        }), 400

    try:
        # Convert content
        result = _converter.convert(content, target_type, context)

        # Return conversion result
        return jsonify({
            "original": result.original,
            "structured": result.structured,
            "target_type": result.target_type.value,
            "confidence": result.confidence,
            "changes": result.changes
        }), 200

    except Exception as e:
        return jsonify({"error": f"Conversion failed: {str(e)}"}), 500


@import_bp.route('/api/import/suggest-type', methods=['GET', 'POST'])
@login_required
def suggest_content_type():
    """
    Suggest most appropriate content type for given content.

    Accepts content either as query param (GET) or in request body (POST).

    Query params (GET):
        content: str  # Content to analyze

    Request JSON (POST):
        {
            "content": str  # Content to analyze
        }

    Returns:
        {
            "suggested_type": str,     # Suggested ContentType
            "confidence": str,         # Confidence level (high/medium/low)
            "alternatives": list[str]  # Other possible types
        }

    Status Codes:
        200: Suggestion generated
        400: Missing content
    """
    # Get content from either query param or request body
    if request.method == 'GET':
        content = request.args.get('content', '')
    else:  # POST
        data = request.json or {}
        content = data.get('content', '')

    if not content:
        return jsonify({"error": "Missing 'content' parameter"}), 400

    try:
        # Get suggestion
        suggested_type = _converter.suggest_type(content)

        # Determine confidence based on content characteristics
        word_count = len(content.split())
        if word_count < 50:
            confidence = "low"
        elif word_count < 150:
            confidence = "medium"
        else:
            confidence = "high"

        # Determine alternatives (all types except suggested)
        all_types = [ContentType.VIDEO, ContentType.READING, ContentType.QUIZ]
        alternatives = [t.value for t in all_types if t != suggested_type]

        return jsonify({
            "suggested_type": suggested_type.value,
            "confidence": confidence,
            "alternatives": alternatives
        }), 200

    except Exception as e:
        return jsonify({"error": f"Type suggestion failed: {str(e)}"}), 500


@import_bp.route('/api/courses/<course_id>/activities/<activity_id>/convert', methods=['POST'])
@login_required
@require_permission('generate_content')
def convert_activity_content(course_id, activity_id):
    """
    Convert content and save to specific activity using AI.

    Target type is determined from the activity's content_type.
    Saves converted content to the activity.

    Request JSON:
        {
            "content": str  # Plain text content to convert
        }

    Returns:
        {
            "converted": bool,
            "content": dict,       # Converted structured content
            "changes": list[str]   # Description of changes made
        }

    Status Codes:
        200: Conversion and save successful
        400: Invalid request
        404: Course or activity not found
        500: Conversion or save error
    """
    data = request.json

    # Validate required fields
    if not data or 'content' not in data:
        return jsonify({"error": "Missing 'content' field"}), 400

    content = data['content']

    try:
        # Load course to get activity
        course = _project_store.load(str(current_user.id), course_id)
        if not course:
            return jsonify({"error": f"Course {course_id} not found"}), 404

        # Find activity
        module, lesson, activity = _find_activity(course, activity_id)
        if not activity:
            return jsonify({"error": f"Activity {activity_id} not found"}), 404

        # Get target type from activity
        target_type = activity.content_type

        # Validate content type is supported
        if target_type not in [ContentType.VIDEO, ContentType.READING, ContentType.QUIZ]:
            return jsonify({
                "error": f"Conversion not supported for activity type {target_type.value}",
                "supported_types": ["video", "reading", "quiz"]
            }), 400

        # Build context from activity
        context = {
            "topic": activity.title,
            "learning_objective": activity.learning_objective or f"Learn about {activity.title}"
        }

        # Convert content
        result = _converter.convert(content, target_type, context)

        # Save to activity
        activity.content = result.structured

        # Update build state
        if activity.build_state == BuildState.DRAFT:
            activity.build_state = BuildState.GENERATED

        activity.updated_at = datetime.now(timezone.utc).isoformat()

        # Save course with updated activity
        _project_store.save(str(current_user.id), course)

        # Log audit entry (commented out - signature mismatch)

        return jsonify({
            "converted": True,
            "content": result.structured,
            "changes": result.changes
        }), 200

    except Exception as e:
        return jsonify({"error": f"Activity conversion failed: {str(e)}"}), 500


@import_bp.route('/api/import/fetch-url', methods=['POST'])
@login_required
def fetch_url():
    """
    Fetch content from public URL.

    Request JSON:
        {
            "url": str  # URL to fetch
        }

    Returns:
        {
            "content": str,
            "content_type": str,
            "source_url": str,
            "fetched_at": str
        }

    Status Codes:
        200: Fetch successful
        400: Invalid URL or request
        500: Fetch error
    """
    if not _url_fetcher:
        return jsonify({"error": "URL fetcher not available"}), 500

    data = request.json

    if not data or 'url' not in data:
        return jsonify({"error": "Missing 'url' field"}), 400

    url = data['url']

    try:
        result = _url_fetcher.fetch(url)
        return jsonify(result.to_dict()), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to fetch URL: {str(e)}"}), 500


@import_bp.route('/api/import/oauth/google', methods=['GET'])
@login_required
def oauth_google():
    """
    Initiate Google OAuth flow.

    Redirects user to Google authorization URL.
    """
    if not _google_client:
        return jsonify({
            "error": "Google OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables."
        }), 500

    try:
        # Generate state for CSRF protection
        import secrets
        state = secrets.token_urlsafe(32)
        session['oauth_state'] = state

        # Get authorization URL
        auth_url = _google_client.get_auth_url(state=state)

        # Redirect to Google
        return redirect(auth_url)

    except Exception as e:
        return jsonify({"error": f"Failed to initiate OAuth: {str(e)}"}), 500


@import_bp.route('/api/import/oauth/google/callback', methods=['GET'])
@login_required
def oauth_google_callback():
    """
    Handle Google OAuth callback.

    Query params:
        code: Authorization code from Google
        state: State parameter for CSRF protection

    Redirects to import page with success/error indicator.
    """
    if not _google_client:
        return "Google OAuth not configured", 500

    # Verify state for CSRF protection
    state = request.args.get('state')
    stored_state = session.get('oauth_state')

    if not state or state != stored_state:
        return redirect('/import?error=invalid_state')

    # Clear state
    session.pop('oauth_state', None)

    # Get authorization code
    code = request.args.get('code')

    if not code:
        error = request.args.get('error', 'unknown')
        return redirect(f'/import?error={error}')

    try:
        # Exchange code for tokens
        token_data = _google_client.exchange_code(code)

        # Store tokens in session
        session['google_oauth'] = token_data.to_dict()

        # Redirect to import page with success indicator
        return redirect('/import?oauth=success')

    except ValueError as e:
        return redirect(f'/import?error={str(e)}')
    except Exception as e:
        return redirect(f'/import?error=Failed to complete OAuth: {str(e)}')


@import_bp.route('/api/import/google-doc', methods=['POST'])
@login_required
def fetch_google_doc():
    """
    Fetch Google Doc content using OAuth.

    Request JSON:
        {
            "doc_id": str,      # Google Doc ID
            OR
            "doc_url": str      # Google Doc URL (will extract ID)
        }

    Returns:
        {
            "content": str,
            "title": str,
            "source_url": str,
            "fetched_at": str
        }

    Status Codes:
        200: Fetch successful
        400: Invalid request or unauthorized
        500: Fetch error
    """
    if not _google_client:
        return jsonify({
            "error": "Google OAuth not configured"
        }), 500

    # Check if user has OAuth token
    oauth_data = session.get('google_oauth')
    if not oauth_data or 'access_token' not in oauth_data:
        return jsonify({
            "error": "Not authenticated with Google. Please connect your Google account first."
        }), 401

    data = request.json

    if not data:
        return jsonify({"error": "Missing request body"}), 400

    # Get doc ID from either doc_id or doc_url
    doc_id = data.get('doc_id')
    doc_url = data.get('doc_url')

    if not doc_id and not doc_url:
        return jsonify({"error": "Missing 'doc_id' or 'doc_url' field"}), 400

    try:
        # Extract doc ID from URL if needed
        if doc_url and not doc_id:
            doc_id = _google_client.extract_doc_id(doc_url)

        # Fetch document
        access_token = oauth_data['access_token']
        result = _google_client.fetch_document(doc_id, access_token)

        return jsonify(result.to_dict()), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to fetch Google Doc: {str(e)}"}), 500


@import_bp.route('/api/import/oauth/status', methods=['GET'])
@login_required
def oauth_status():
    """
    Check OAuth connection status.

    Returns:
        {
            "google_connected": bool
        }

    Status Codes:
        200: Always
    """
    oauth_data = session.get('google_oauth')
    google_connected = bool(oauth_data and 'access_token' in oauth_data)

    return jsonify({
        "google_connected": google_connected
    }), 200
