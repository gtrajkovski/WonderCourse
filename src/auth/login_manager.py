"""Flask-Login LoginManager configuration.

Configures user session management and provides the user_loader callback
that Flask-Login uses to restore users from sessions on each request.
"""

from flask import request, jsonify
from flask_login import LoginManager
from src.auth.models import User

login_manager = LoginManager()


def init_login_manager(app):
    """Initialize Flask-Login with the Flask app.

    Args:
        app: Flask application instance
    """
    login_manager.init_app(app)
    login_manager.login_view = 'login_page'  # Redirect for @login_required
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        """Load user from database by ID.

        This callback is called on every request to restore the user
        from the session.

        Args:
            user_id: String user ID from session

        Returns:
            User object or None if not found
        """
        return User.get_by_id(user_id)

    @login_manager.unauthorized_handler
    def unauthorized():
        """Handle unauthorized access.

        Returns JSON 401 for API requests, redirects for page requests.
        """
        if request.path.startswith('/api/'):
            return jsonify({"error": "Unauthorized"}), 401
        # For non-API requests, redirect to login page
        from flask import redirect, url_for, flash
        flash(login_manager.login_message, login_manager.login_message_category)
        return redirect(url_for(login_manager.login_view))
