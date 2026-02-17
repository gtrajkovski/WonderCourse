"""Auth API routes for registration, login, and logout."""

import re
import sqlite3

from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from src.auth.models import User

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# Rate limiter (initialized with app in init_auth_bp)
limiter = None
# Track if we're in test mode (persists across re-inits)
# Check for pytest environment before any initialization
import os
import sys
_testing_mode = 'pytest' in sys.modules or os.environ.get('PYTEST_CURRENT_TEST')


def init_auth_bp(app):
    """Initialize auth blueprint with app context.

    Sets up rate limiting for brute-force protection on login endpoint.
    Rate limiting is disabled during testing.

    Args:
        app: Flask application instance
    """
    global limiter, _testing_mode

    # Disable rate limiting during tests (detect via config or pytest presence)
    if app.config.get('TESTING') or _testing_mode:
        _testing_mode = True
        limiter = None
        # Clear Flask-Limiter from app extensions if present
        for key in list(getattr(app, 'extensions', {}).keys()):
            if 'limiter' in key.lower():
                del app.extensions[key]
        return

    # Only create limiter if not already created
    if limiter is None:
        limiter = Limiter(
            key_func=get_remote_address,
            app=app,
            default_limits=["200 per day", "50 per hour"],
            storage_uri="memory://"
        )


def _validate_email(email):
    """Basic email format validation.

    Args:
        email: Email string to validate

    Returns:
        True if email has valid format, False otherwise
    """
    if not email:
        return False
    # Basic pattern: something@something.something
    pattern = r'^[^@\s]+@[^@\s]+\.[^@\s]+$'
    return bool(re.match(pattern, email))


@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user.

    Request JSON:
        {
            "email": str (required),
            "password": str (required),
            "name": str (optional)
        }

    Returns:
        201: {message, user: {id, email, name}}
        400: {error: str} for missing fields or duplicate email
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    email = data.get('email')
    password = data.get('password')
    name = data.get('name')

    # Validate required fields
    if not email:
        return jsonify({"error": "Email is required"}), 400

    if not password:
        return jsonify({"error": "Password is required"}), 400

    # Validate email format
    if not _validate_email(email):
        return jsonify({"error": "Invalid email format"}), 400

    try:
        user = User.create(email=email, password=password, name=name)
        return jsonify({
            "message": "User registered successfully",
            "user": user.to_dict()
        }), 201

    except sqlite3.IntegrityError:
        return jsonify({"error": "Email already registered"}), 400


@auth_bp.route('/login', methods=['POST'])
def login():
    """Log in a user.

    Request JSON:
        {
            "email": str (required),
            "password": str (required),
            "remember": bool (optional, default False)
        }

    Returns:
        200: {message, user: {id, email, name}} with session cookie
        400: {error: str} for missing fields
        401: {error: "Invalid credentials"} for wrong email or password

    Note:
        Rate limited to 5 requests per minute for brute-force protection.
        Returns same error for unknown email and wrong password to prevent
        user enumeration attacks.
    """
    # Apply rate limiting if limiter is configured (skip in test mode)
    if limiter and not _testing_mode:
        # Get the limit decorator and apply it
        limit_decorator = limiter.limit("5 per minute")
        # Check if we've exceeded the limit
        try:
            limit_decorator(lambda: None)()
        except Exception:
            # Rate limit exceeded
            return jsonify({"error": "Too many login attempts. Please try again later."}), 429

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    email = data.get('email')
    password = data.get('password')
    remember = data.get('remember', False)

    # Validate required fields
    if not email:
        return jsonify({"error": "Email is required"}), 400

    if not password:
        return jsonify({"error": "Password is required"}), 400

    # Attempt to find user by email
    user = User.get_by_email(email)

    # SECURITY: Return same error for both unknown email and wrong password
    # to prevent user enumeration attacks
    if user is None or not user.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 401

    # Log in the user with Flask-Login
    login_user(user, remember=remember)

    return jsonify({
        "message": "Logged in successfully",
        "user": user.to_dict()
    }), 200


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """Log out the current user.

    Requires authentication.

    Returns:
        200: {message: str}
        401: Unauthorized if not logged in
    """
    logout_user()
    return jsonify({"message": "Logged out successfully"}), 200


@auth_bp.route('/me', methods=['GET'])
@login_required
def me():
    """Get current authenticated user.

    Requires authentication.

    Returns:
        200: {id, email, name, created_at}
        401: Unauthorized if not logged in
    """
    return jsonify(current_user.to_dict()), 200


@auth_bp.route('/profile', methods=['GET'])
@login_required
def get_profile():
    """Get current user's profile.

    Requires authentication.

    Returns:
        200: {id, email, name, created_at}
        401: Unauthorized if not logged in
    """
    return jsonify(current_user.to_dict()), 200


@auth_bp.route('/profile', methods=['PUT'])
@login_required
def update_profile():
    """Update current user's profile.

    Request JSON:
        {
            "name": str (optional),
            "email": str (optional)
        }

    Returns:
        200: Updated user data {id, email, name, created_at}
        400: {error: str} for invalid email or duplicate
        401: Unauthorized if not logged in
    """
    data = request.get_json()
    if data is None:
        return jsonify({"error": "Request body must be JSON"}), 400

    try:
        current_user.update_profile(
            name=data.get('name'),
            email=data.get('email')
        )
        return jsonify(current_user.to_dict()), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@auth_bp.route('/password', methods=['POST'])
@login_required
def change_password():
    """Change current user's password.

    Request JSON:
        {
            "current_password": str (required),
            "new_password": str (required, min 8 chars)
        }

    Returns:
        200: {message: "Password changed successfully"}
        400: {error: str} for missing fields, wrong password, or short password
        401: Unauthorized if not logged in
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    current_password = data.get('current_password')
    new_password = data.get('new_password')

    if not current_password or not new_password:
        return jsonify({"error": "Current and new password required"}), 400

    if len(new_password) < 8:
        return jsonify({"error": "New password must be at least 8 characters"}), 400

    try:
        current_user.update_password(current_password, new_password)
        return jsonify({"message": "Password changed successfully"}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Request password reset email.

    Request JSON:
        {"email": str}

    Returns:
        200: {message: str} always (prevents user enumeration)

    Note:
        Returns 200 even if email not found to prevent user enumeration attacks.
    """
    data = request.get_json()
    email = data.get('email') if data else None

    if not email:
        return jsonify({"error": "Email required"}), 400

    # Always return success to prevent user enumeration
    user = User.get_by_email(email)
    if user:
        from src.auth.tokens import generate_reset_token
        from src.auth.mail import send_password_reset_email

        token = generate_reset_token(email)
        send_password_reset_email(email, token)

    return jsonify({"message": "If that email exists, a reset link has been sent"}), 200


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    """Reset password using token.

    Request JSON:
        {
            "token": str,
            "new_password": str (min 8 characters)
        }

    Returns:
        200: {message: "Password reset successfully"}
        400: {error: str} for invalid token, expired token, or short password
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    token = data.get('token')
    new_password = data.get('new_password')

    if not token or not new_password:
        return jsonify({"error": "Token and new password required"}), 400

    if len(new_password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    from src.auth.tokens import verify_reset_token
    from src.config import Config
    from src.auth.db import get_db

    email = verify_reset_token(token, Config.PASSWORD_RESET_TOKEN_MAX_AGE)
    if not email:
        return jsonify({"error": "Invalid or expired reset token"}), 400

    user = User.get_by_email(email)
    if not user:
        return jsonify({"error": "User not found"}), 400

    # Update password
    user.set_password(new_password)
    db = get_db()
    db.execute(
        "UPDATE user SET password_hash = ? WHERE id = ?",
        (user.password_hash, user.id)
    )
    db.commit()

    return jsonify({"message": "Password reset successfully"}), 200
