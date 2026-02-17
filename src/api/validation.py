"""Validation API endpoints.

Provides endpoints for running course validation and viewing comprehensive reports.
"""

from flask import Blueprint, jsonify
from flask_login import login_required, current_user

from src.validators.validation_report import ValidationReport
from src.collab.models import Collaborator

# Create Blueprint
validation_bp = Blueprint('validation', __name__)

# Module-level references
_project_store = None
_validation_report = None


def init_validation_bp(project_store):
    """Initialize validation blueprint with dependencies.

    Args:
        project_store: ProjectStore instance for course loading.
    """
    global _project_store, _validation_report
    _project_store = project_store
    _validation_report = ValidationReport()


@validation_bp.route('/api/courses/<course_id>/validate', methods=['GET'])
@login_required
def validate_course(course_id):
    """Run all validation checks and return comprehensive report.

    Args:
        course_id: Course identifier.

    Returns:
        JSON with:
        - is_publishable: bool (true if no errors)
        - validators: Dict of validator name -> result
        - summary: Aggregate counts

    Errors:
        404 if course not found.
        500 on validation error.
    """
    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        # Run all validators
        results = _validation_report.validate_course(course)
        is_publishable = _validation_report.is_publishable(course)

        # Convert ValidationResult objects to dicts
        results_dict = {
            name: result.to_dict()
            for name, result in results.items()
        }

        # Summary counts
        total_errors = sum(len(r.errors) for r in results.values())
        total_warnings = sum(len(r.warnings) for r in results.values())
        total_suggestions = sum(len(r.suggestions) for r in results.values())

        return jsonify({
            "is_publishable": is_publishable,
            "validators": results_dict,
            "summary": {
                "total_errors": total_errors,
                "total_warnings": total_warnings,
                "total_suggestions": total_suggestions
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@validation_bp.route('/api/courses/<course_id>/publishable', methods=['GET'])
@login_required
def check_publishable(course_id):
    """Quick check if course is publishable.

    Args:
        course_id: Course identifier.

    Returns:
        JSON with:
        - is_publishable: bool
        - error_count: int

    Errors:
        404 if course not found.
    """
    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        results = _validation_report.validate_course(course)
        is_publishable = all(r.is_valid for r in results.values())
        error_count = sum(len(r.errors) for r in results.values())

        return jsonify({
            "is_publishable": is_publishable,
            "error_count": error_count
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
