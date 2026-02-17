"""Export API endpoints for Course Builder Studio.

Provides endpoints for previewing and downloading course content in various formats:
- Instructor Package (ZIP)
- LMS Manifest (JSON)
- DOCX Textbook
- SCORM 1.2 Package (ZIP)
"""

import tempfile
from io import BytesIO
from pathlib import Path
from typing import Dict, Any, Optional

from flask import Blueprint, request, jsonify, send_file
from flask_login import login_required, current_user

from src.exporters import (
    ExportValidator,
    InstructorPackageExporter,
    LMSManifestExporter,
    DOCXTextbookExporter,
    SCORMPackageExporter,
)
from src.collab.decorators import require_permission
from src.collab.audit import log_audit_entry, ACTION_COURSE_EXPORTED
from src.collab.models import Collaborator

# Create Blueprint
export_bp = Blueprint('export', __name__)

# Module-level references (set during initialization)
_project_store = None
_export_validator = None


def init_export_bp(project_store):
    """Initialize the export blueprint with a ProjectStore instance.

    Must be called before registering the blueprint with Flask app.

    Args:
        project_store: ProjectStore instance for course persistence.
    """
    global _project_store, _export_validator
    _project_store = project_store
    _export_validator = ExportValidator()


# Content types for each format
CONTENT_TYPES = {
    'instructor': 'application/zip',
    'lms': 'application/json',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'scorm': 'application/zip',
}


def _get_exporter(format_name: str, output_dir: Optional[Path] = None):
    """Return exporter instance for the specified format.

    Args:
        format_name: Export format name (instructor, lms, docx, scorm).
        output_dir: Optional output directory for file-based exporters.

    Returns:
        Exporter instance or None if format is invalid.
    """
    exporters = {
        'instructor': lambda: InstructorPackageExporter(),
        'lms': lambda: LMSManifestExporter(output_dir),
        'docx': lambda: DOCXTextbookExporter(output_dir),
        'scorm': lambda: SCORMPackageExporter(output_dir),
    }
    factory = exporters.get(format_name)
    return factory() if factory else None


def _get_preview_files(course, format_name: str) -> list:
    """Get list of files that would be included in export.

    Args:
        course: Course object to analyze.
        format_name: Export format name.

    Returns:
        List of file paths that would be included.
    """
    files = []

    if format_name == 'instructor':
        # Instructor package contains syllabus, lesson plans, rubrics, quizzes, keys
        files.append('syllabus.txt')
        for module in course.modules:
            module_folder = _sanitize_filename(module.title)
            for lesson in module.lessons:
                lesson_name = _sanitize_filename(lesson.title)
                files.append(f'lesson_plans/{module_folder}/{lesson_name}.txt')
                for activity in lesson.activities:
                    if activity.content_type.value == 'rubric':
                        files.append(f'rubrics/{_sanitize_filename(activity.title)}.txt')
                    elif activity.content_type.value == 'quiz':
                        files.append(f'quizzes/{_sanitize_filename(activity.title)}_questions.txt')
                        files.append(f'answer_keys/{_sanitize_filename(activity.title)}_key.txt')
        if course.textbook_chapters:
            files.append('textbook.docx')

    elif format_name == 'lms':
        files.append('course_manifest.json')

    elif format_name == 'docx':
        files.append(f'{_sanitize_filename(course.title)}.docx')

    elif format_name == 'scorm':
        files.append('imsmanifest.xml')
        files.append('shared/style.css')
        for mod_idx, module in enumerate(course.modules):
            for les_idx, lesson in enumerate(module.lessons):
                files.append(f'content/module_{mod_idx}/lesson_{les_idx}.html')

    return files


def _sanitize_filename(name: str) -> str:
    """Remove special characters and replace spaces with underscores.

    Args:
        name: Original name.

    Returns:
        Sanitized string safe for filesystem use.
    """
    import re
    sanitized = re.sub(r"[^\w\s\-]", "", name)
    sanitized = sanitized.replace(" ", "_")
    sanitized = re.sub(r"_+", "_", sanitized)
    sanitized = sanitized.strip("_")
    return sanitized or "untitled"


@export_bp.route('/api/courses/<course_id>/export/preview', methods=['GET'])
@login_required
@require_permission('export_course')
def preview_export(course_id):
    """Preview export contents before downloading.

    Query Parameters:
        format: Export format (instructor, lms, docx, scorm)

    Returns:
        JSON with export preview including:
        - format: Export format name
        - course_id: Course identifier
        - course_title: Course title
        - ready: Whether course is ready for export
        - files: List of files that would be included
        - missing_content: List of activities missing content
        - validation_errors: List of validation issues
        - warnings: List of warnings

    Errors:
        404 if course not found.
        400 if format is missing or invalid.
    """
    # Get format parameter
    format_name = request.args.get('format')
    if not format_name:
        return jsonify({"error": "Missing required parameter: format"}), 400

    if format_name not in CONTENT_TYPES:
        return jsonify({
            "error": f"Invalid format: {format_name}",
            "valid_formats": list(CONTENT_TYPES.keys())
        }), 400

    # Load course
    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        # Run validation
        validation_result = _export_validator.validate_for_export(course)

        # Get file list
        files = _get_preview_files(course, format_name)

        # Build validation errors list
        validation_errors = []
        for item in validation_result.incomplete_activities:
            validation_errors.append(
                f"Activity '{item['title']}' is in state '{item['current_state']}' (requires approved/published)"
            )

        return jsonify({
            "format": format_name,
            "course_id": course_id,
            "course_title": course.title,
            "ready": validation_result.is_exportable,
            "files": files,
            "missing_content": validation_result.missing_content,
            "validation_errors": validation_errors,
            "warnings": validation_result.warnings,
            "metrics": validation_result.metrics,
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@export_bp.route('/api/courses/<course_id>/export/instructor', methods=['GET'])
@login_required
@require_permission('export_course')
def download_instructor_package(course_id):
    """Download instructor package as ZIP file.

    Query Parameters:
        force: If 'true', bypass validation check.

    Returns:
        ZIP file download.

    Errors:
        404 if course not found.
        400 if course not ready for export and force not specified.
    """
    return _handle_export(course_id, 'instructor')


@export_bp.route('/api/courses/<course_id>/export/lms', methods=['GET'])
@login_required
@require_permission('export_course')
def download_lms_manifest(course_id):
    """Download LMS manifest as JSON file.

    Query Parameters:
        force: If 'true', bypass validation check.

    Returns:
        JSON file download.

    Errors:
        404 if course not found.
        400 if course not ready for export and force not specified.
    """
    return _handle_export(course_id, 'lms')


@export_bp.route('/api/courses/<course_id>/export/docx', methods=['GET'])
@login_required
@require_permission('export_course')
def download_docx_textbook(course_id):
    """Download textbook as DOCX file.

    Query Parameters:
        force: If 'true', bypass validation check.

    Returns:
        DOCX file download.

    Errors:
        404 if course not found.
        400 if course not ready for export and force not specified.
    """
    return _handle_export(course_id, 'docx')


@export_bp.route('/api/courses/<course_id>/export/scorm', methods=['GET'])
@login_required
@require_permission('export_course')
def download_scorm_package(course_id):
    """Download SCORM 1.2 package as ZIP file.

    Query Parameters:
        force: If 'true', bypass validation check.

    Returns:
        ZIP file download.

    Errors:
        404 if course not found.
        400 if course not ready for export and force not specified.
    """
    return _handle_export(course_id, 'scorm')


def _handle_export(course_id: str, format_name: str):
    """Handle export request for any format.

    Args:
        course_id: Course identifier.
        format_name: Export format (instructor, lms, docx, scorm).

    Returns:
        File download response or error JSON.
    """
    # Check force parameter
    force = request.args.get('force', '').lower() == 'true'

    # Load course
    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        # Validate unless force=true
        if not force:
            validation_result = _export_validator.validate_for_export(course)
            if not validation_result.is_exportable:
                return jsonify({
                    "error": "Course is not ready for export",
                    "missing_content": validation_result.missing_content,
                    "incomplete_activities": validation_result.incomplete_activities,
                    "warnings": validation_result.warnings,
                    "hint": "Use ?force=true to bypass validation"
                }), 400

        # Log audit entry for export
        log_audit_entry(
            course_id=course_id,
            user_id=current_user.id,
            action=ACTION_COURSE_EXPORTED,
            entity_type='course',
            entity_id=course_id,
            after={'format': format_name}
        )

        # Handle instructor package differently (returns BytesIO)
        if format_name == 'instructor':
            exporter = InstructorPackageExporter()
            buffer, filename = exporter.export(course)
            return send_file(
                buffer,
                mimetype=CONTENT_TYPES[format_name],
                as_attachment=True,
                download_name=filename
            )

        # File-based exporters need a temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            exporter = _get_exporter(format_name, temp_path)

            # Run export
            output_path = exporter.export(course)

            # Read file into buffer for send_file
            with open(output_path, 'rb') as f:
                buffer = BytesIO(f.read())
            buffer.seek(0)

            filename = output_path.name

            return send_file(
                buffer,
                mimetype=CONTENT_TYPES[format_name],
                as_attachment=True,
                download_name=filename
            )

    except ValueError as e:
        # Handle validation errors from exporters (e.g., SCORM with no modules)
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Export failed: {str(e)}"}), 500
