"""Course audit API endpoints.

Provides endpoints for:
- Running course audits
- Retrieving audit results
- Updating issue status
- Getting audit history
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime

from src.core.models import AuditCheckType, AuditIssueStatus
from src.validators.course_auditor import CourseAuditor
from src.collab.decorators import require_permission
from src.collab.models import Collaborator


# Create Blueprint
audit_bp = Blueprint('audit', __name__)

# Module-level project_store reference (set during registration)
_project_store = None


def init_audit_bp(project_store):
    """Initialize the audit blueprint with a ProjectStore instance.

    Args:
        project_store: ProjectStore instance for course persistence.
    """
    global _project_store
    _project_store = project_store


def _find_issue(course, issue_id):
    """Find an audit issue by ID across all audit results."""
    for result in course.audit_results:
        for issue in result.issues:
            if issue.id == issue_id:
                return result, issue
    return None, None


# ===========================
# Run Audit
# ===========================


@audit_bp.route('/api/courses/<course_id>/audit', methods=['POST'])
@login_required
@require_permission('edit_content')
def run_audit(course_id):
    """Run a course audit.

    Request JSON (optional):
        {
            "checks": ["flow_analysis", "repetition"]  // Specific checks to run
        }

    Returns:
        JSON with audit results.
    """
    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        data = request.get_json() or {}
        specific_checks = data.get('checks', [])

        auditor = CourseAuditor(course)

        if specific_checks:
            # Run only specified checks
            all_issues = []
            checks_run = []
            for check_name in specific_checks:
                try:
                    check_type = AuditCheckType(check_name)
                    result = auditor.run_check(check_type)
                    all_issues.extend(result.issues)
                    checks_run.append(check_name)
                except ValueError:
                    return jsonify({"error": f"Invalid check type: {check_name}"}), 400

            # Combine into single result
            from src.core.models import AuditResult, AuditSeverity
            error_count = sum(1 for i in all_issues if i.severity == AuditSeverity.ERROR)
            warning_count = sum(1 for i in all_issues if i.severity == AuditSeverity.WARNING)
            info_count = sum(1 for i in all_issues if i.severity == AuditSeverity.INFO)

            score = 100 - (error_count * 15) - (warning_count * 5) - (info_count * 1)
            score = max(0, min(100, score))

            audit_result = AuditResult(
                issues=all_issues,
                checks_run=checks_run,
                score=score,
                error_count=error_count,
                warning_count=warning_count,
                info_count=info_count
            )
        else:
            # Run all checks
            audit_result = auditor.run_all_checks()

        # Store result (keep last 5 audits)
        course.audit_results.insert(0, audit_result)
        course.audit_results = course.audit_results[:5]
        course.updated_at = datetime.now().isoformat()
        _project_store.save(owner_id, course)

        return jsonify({
            "message": "Audit completed",
            "result": audit_result.to_dict()
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===========================
# Get Audit Results
# ===========================


@audit_bp.route('/api/courses/<course_id>/audit', methods=['GET'])
@login_required
def get_latest_audit(course_id):
    """Get the most recent audit result.

    Returns:
        JSON with latest audit result, or 404 if no audits run.
    """
    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        if not course.audit_results:
            return jsonify({
                "message": "No audits have been run yet",
                "result": None
            })

        return jsonify({
            "result": course.audit_results[0].to_dict()
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@audit_bp.route('/api/courses/<course_id>/audit/history', methods=['GET'])
@login_required
def get_audit_history(course_id):
    """Get audit history (last 5 audits).

    Returns:
        JSON array of audit result summaries.
    """
    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        history = []
        for result in course.audit_results:
            history.append({
                "id": result.id,
                "score": result.score,
                "error_count": result.error_count,
                "warning_count": result.warning_count,
                "info_count": result.info_count,
                "checks_run": result.checks_run,
                "created_at": result.created_at
            })

        return jsonify({"history": history})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===========================
# Update Issue Status
# ===========================


@audit_bp.route('/api/courses/<course_id>/audit/issues/<issue_id>', methods=['PUT'])
@login_required
@require_permission('edit_content')
def update_issue_status(course_id, issue_id):
    """Update the status of an audit issue.

    Request JSON:
        {
            "status": "resolved",
            "resolution_notes": "Fixed by updating content"
        }

    Returns:
        JSON with updated issue.
    """
    try:
        data = request.get_json()
        if not data or 'status' not in data:
            return jsonify({"error": "Missing required field: status"}), 400

        try:
            new_status = AuditIssueStatus(data['status'])
        except ValueError:
            valid = [s.value for s in AuditIssueStatus]
            return jsonify({"error": f"Invalid status. Must be one of: {valid}"}), 400

        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        result, issue = _find_issue(course, issue_id)
        if not issue:
            return jsonify({"error": "Issue not found"}), 404

        # Update issue
        issue.status = new_status
        if 'resolution_notes' in data:
            issue.resolution_notes = data['resolution_notes']

        if new_status in {AuditIssueStatus.RESOLVED, AuditIssueStatus.WONT_FIX, AuditIssueStatus.FALSE_POSITIVE}:
            issue.resolved_at = datetime.now().isoformat()

        course.updated_at = datetime.now().isoformat()
        _project_store.save(owner_id, course)

        return jsonify({
            "message": "Issue status updated",
            "issue": issue.to_dict()
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===========================
# Get Available Check Types
# ===========================


@audit_bp.route('/api/audit/check-types', methods=['GET'])
@login_required
def get_check_types():
    """Get list of available audit check types.

    Returns:
        JSON array of check type info.
    """
    check_info = {
        "flow_analysis": {
            "name": "Flow Analysis",
            "description": "Checks logical progression through modules and lessons"
        },
        "repetition": {
            "name": "Repetition Detection",
            "description": "Finds duplicate or highly similar content"
        },
        "objective_alignment": {
            "name": "Objective Alignment",
            "description": "Verifies activities map to learning outcomes"
        },
        "content_gaps": {
            "name": "Content Gaps",
            "description": "Identifies missing required content elements"
        },
        "duration_balance": {
            "name": "Duration Balance",
            "description": "Checks time distribution across modules"
        },
        "bloom_progression": {
            "name": "Bloom Progression",
            "description": "Ensures cognitive levels progress appropriately"
        }
    }

    return jsonify({
        "check_types": [
            {"value": ct.value, **check_info.get(ct.value, {"name": ct.value, "description": ""})}
            for ct in AuditCheckType
        ]
    })
