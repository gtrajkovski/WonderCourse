"""Authentication package for Course Builder Studio.

Provides User model, SQLite database utilities, Flask-Login integration,
auth routes, token utilities, and Flask integration utilities.
"""

from src.auth.models import User
from src.auth.db import get_db, init_db, init_app
from src.auth.login_manager import login_manager, init_login_manager
from src.auth.routes import auth_bp, init_auth_bp
from src.auth.tokens import generate_reset_token, verify_reset_token
from src.auth.mail import mail, init_mail, send_password_reset_email

__all__ = [
    "User",
    "get_db",
    "init_db",
    "init_app",
    "login_manager",
    "init_login_manager",
    "auth_bp",
    "init_auth_bp",
    "generate_reset_token",
    "verify_reset_token",
    "mail",
    "init_mail",
    "send_password_reset_email",
]
