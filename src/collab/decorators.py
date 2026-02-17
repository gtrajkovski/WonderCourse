"""Permission enforcement decorators for API routes.

Provides decorators to check user permissions on courses before allowing
access to protected endpoints. Extracts course_id from route parameters
and queries permission database fresh on each request.
"""

from functools import wraps
from typing import Callable
from flask import request, jsonify
from flask_login import current_user
from src.collab.permissions import has_permission
from src.collab.models import Collaborator, Role


def require_permission(permission_code: str) -> Callable:
    """Decorator to require specific permission on course.

    Extracts course_id from route parameters and checks if current_user
    has the required permission on that course.

    Usage:
        @app.route('/api/courses/<course_id>/content', methods=['POST'])
        @login_required
        @require_permission('edit_content')
        def update_content(course_id):
            # User has edit_content permission on this course
            pass

    Args:
        permission_code: Permission code to require (e.g., "edit_content")

    Returns:
        Decorator function that enforces permission check
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Extract course_id from kwargs or view_args
            course_id = kwargs.get('course_id') or request.view_args.get('course_id')

            if not course_id:
                return jsonify({"error": "course_id not found in route"}), 400

            # Check if course exists first (return 404 if not)
            owner_id = Collaborator.get_course_owner_id(course_id)
            if not owner_id:
                return jsonify({"error": "Course not found"}), 404

            # Check permission
            try:
                if not has_permission(current_user.id, course_id, permission_code):
                    return jsonify({"error": "Permission denied"}), 403
            except Exception as e:
                import traceback
                print(f"Permission check error for {permission_code} on course {course_id}: {e}")
                traceback.print_exc()
                return jsonify({"error": f"Permission check failed: {str(e)}"}), 500

            return f(*args, **kwargs)

        return decorated_function
    return decorator


def require_any_permission(*permission_codes: str) -> Callable:
    """Decorator to require any of multiple permissions on course.

    Passes if user has ANY of the specified permissions. Useful for
    endpoints that accept multiple permission levels.

    Usage:
        @app.route('/api/courses/<course_id>/content', methods=['GET'])
        @login_required
        @require_any_permission('view_content', 'edit_content')
        def view_content(course_id):
            # User has either view_content or edit_content permission
            pass

    Args:
        *permission_codes: Permission codes to check (at least one required)

    Returns:
        Decorator function that enforces permission check
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Extract course_id from kwargs or view_args
            course_id = kwargs.get('course_id') or request.view_args.get('course_id')

            if not course_id:
                return jsonify({"error": "course_id not found in route"}), 400

            # Check if user has any of the required permissions
            has_any = any(
                has_permission(current_user.id, course_id, code)
                for code in permission_codes
            )

            if not has_any:
                return jsonify({"error": "Permission denied"}), 403

            return f(*args, **kwargs)

        return decorated_function
    return decorator


def require_collaborator() -> Callable:
    """Decorator to require user is a collaborator on course.

    Simpler check that just verifies user is a collaborator, without
    checking specific permission. Useful for read-only endpoints that
    any collaborator can access.

    Usage:
        @app.route('/api/courses/<course_id>/info', methods=['GET'])
        @login_required
        @require_collaborator()
        def course_info(course_id):
            # User is a collaborator on this course
            pass

    Returns:
        Decorator function that enforces collaborator check
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Extract course_id from kwargs or view_args
            course_id = kwargs.get('course_id') or request.view_args.get('course_id')

            if not course_id:
                return jsonify({"error": "course_id not found in route"}), 400

            # Check if user is a collaborator
            collaborator = Collaborator.get_by_user_and_course(current_user.id, course_id)
            if not collaborator:
                return jsonify({"error": "Permission denied"}), 403

            return f(*args, **kwargs)

        return decorated_function
    return decorator


def ensure_owner_collaborator(course_id: str, user_id: int):
    """Ensure user is owner of course. Creates Owner role and collaborator if needed.

    Called when a user creates a new course to automatically make them the owner.

    Args:
        course_id: The course identifier
        user_id: The user who should be owner

    Returns:
        Collaborator instance
    """
    # Check if already collaborator
    existing = Collaborator.get_by_user_and_course(user_id, course_id)
    if existing:
        return existing

    # Create Owner role for this course from template
    owner_role = Role.create_from_template(course_id, "Owner")

    # Make user the owner (invited_by self for initial owner)
    collaborator = Collaborator.create(course_id, user_id, owner_role.id, invited_by=user_id)

    return collaborator
