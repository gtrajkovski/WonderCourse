"""Course pages API endpoints.

Provides endpoints for:
- Generating course pages (syllabus, about, resources)
- Retrieving existing course pages
- Regenerating specific pages
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime

from src.core.models import PageType, BuildState
from src.generators.course_page_generator import CoursePageGenerator
from src.collab.decorators import require_permission
from src.collab.models import Collaborator


# Create Blueprint
course_pages_bp = Blueprint('course_pages', __name__)

# Module-level project_store reference (set during registration)
_project_store = None


def init_course_pages_bp(project_store):
    """Initialize the course pages blueprint with a ProjectStore instance.

    Args:
        project_store: ProjectStore instance for course persistence.
    """
    global _project_store
    _project_store = project_store


def _find_page_by_type(course, page_type_str):
    """Find a course page by type."""
    try:
        page_type = PageType(page_type_str)
    except ValueError:
        return None

    for page in course.course_pages:
        if page.page_type == page_type:
            return page
    return None


# ===========================
# List/Get Pages
# ===========================


@course_pages_bp.route('/api/courses/<course_id>/pages', methods=['GET'])
@login_required
def list_course_pages(course_id):
    """List all course pages for a course.

    Returns:
        JSON array of course page summaries.
    """
    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        pages = []
        for page in course.course_pages:
            pages.append({
                "id": page.id,
                "page_type": page.page_type.value,
                "title": page.title,
                "build_state": page.build_state.value,
                "updated_at": page.updated_at
            })

        # Also return which page types are available but not generated
        generated_types = {p.page_type.value for p in course.course_pages}
        all_types = [pt.value for pt in PageType]
        available_types = [t for t in all_types if t not in generated_types]

        return jsonify({
            "pages": pages,
            "available_types": available_types
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@course_pages_bp.route('/api/courses/<course_id>/pages/<page_type>', methods=['GET'])
@login_required
def get_course_page(course_id, page_type):
    """Get a specific course page by type.

    Args:
        page_type: syllabus, about, or resources

    Returns:
        JSON with full page content.
    """
    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        page = _find_page_by_type(course, page_type)
        if not page:
            return jsonify({"error": f"Page '{page_type}' not found. Generate it first."}), 404

        return jsonify(page.to_dict())

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===========================
# Generate Pages
# ===========================


@course_pages_bp.route('/api/courses/<course_id>/pages/<page_type>', methods=['POST'])
@login_required
@require_permission('edit_content')
def generate_course_page(course_id, page_type):
    """Generate a specific course page.

    Args:
        page_type: syllabus, about, or resources

    Request JSON (optional):
        {
            "regenerate": true  // Force regeneration if page exists
        }

    Returns:
        JSON with generated page content.
    """
    try:
        # Validate page type
        try:
            pt = PageType(page_type)
        except ValueError:
            return jsonify({
                "error": f"Invalid page type: {page_type}. Must be: syllabus, about, or resources"
            }), 400

        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        # Check if page already exists
        data = request.get_json() or {}
        regenerate = data.get('regenerate', False)

        existing_page = _find_page_by_type(course, page_type)
        if existing_page and not regenerate:
            return jsonify({
                "error": f"Page '{page_type}' already exists. Set regenerate=true to regenerate.",
                "existing": existing_page.to_dict()
            }), 409

        # Generate the page
        generator = CoursePageGenerator()
        language = getattr(course, 'language', 'English')

        if pt == PageType.SYLLABUS:
            new_page = generator.generate_syllabus(course, language)
        elif pt == PageType.ABOUT:
            new_page = generator.generate_about(course, language)
        elif pt == PageType.RESOURCES:
            new_page = generator.generate_resources(course, language)
        else:
            return jsonify({"error": f"Unsupported page type: {page_type}"}), 400

        # Replace existing or add new
        if existing_page:
            # Update existing page
            for i, p in enumerate(course.course_pages):
                if p.page_type == pt:
                    course.course_pages[i] = new_page
                    break
        else:
            course.course_pages.append(new_page)

        course.updated_at = datetime.now().isoformat()
        _project_store.save(owner_id, course)

        return jsonify({
            "message": f"Page '{page_type}' generated successfully",
            "page": new_page.to_dict()
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@course_pages_bp.route('/api/courses/<course_id>/pages/generate-all', methods=['POST'])
@login_required
@require_permission('edit_content')
def generate_all_pages(course_id):
    """Generate all course pages at once.

    Request JSON (optional):
        {
            "regenerate": true  // Force regeneration of existing pages
        }

    Returns:
        JSON with all generated pages.
    """
    try:
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        data = request.get_json() or {}
        regenerate = data.get('regenerate', False)

        generator = CoursePageGenerator()
        language = getattr(course, 'language', 'English')

        results = {}
        pages_generated = generator.generate_all(course, language)

        for page_type_str, new_page in pages_generated.items():
            pt = PageType(page_type_str)

            # Find and replace or append
            replaced = False
            for i, p in enumerate(course.course_pages):
                if p.page_type == pt:
                    if regenerate:
                        course.course_pages[i] = new_page
                        results[page_type_str] = "regenerated"
                        replaced = True
                    else:
                        results[page_type_str] = "skipped (already exists)"
                        replaced = True
                    break

            if not replaced:
                course.course_pages.append(new_page)
                results[page_type_str] = "generated"

        course.updated_at = datetime.now().isoformat()
        _project_store.save(owner_id, course)

        return jsonify({
            "message": "Course pages processed",
            "results": results,
            "pages": [p.to_dict() for p in course.course_pages]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===========================
# Delete Pages
# ===========================


@course_pages_bp.route('/api/courses/<course_id>/pages/<page_type>', methods=['DELETE'])
@login_required
@require_permission('edit_content')
def delete_course_page(course_id, page_type):
    """Delete a specific course page.

    Args:
        page_type: syllabus, about, or resources

    Returns:
        JSON confirmation.
    """
    try:
        try:
            pt = PageType(page_type)
        except ValueError:
            return jsonify({"error": f"Invalid page type: {page_type}"}), 400

        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return jsonify({"error": "Course not found"}), 404

        course = _project_store.load(owner_id, course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        # Find and remove the page
        original_count = len(course.course_pages)
        course.course_pages = [p for p in course.course_pages if p.page_type != pt]

        if len(course.course_pages) == original_count:
            return jsonify({"error": f"Page '{page_type}' not found"}), 404

        course.updated_at = datetime.now().isoformat()
        _project_store.save(owner_id, course)

        return jsonify({
            "message": f"Page '{page_type}' deleted successfully"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
