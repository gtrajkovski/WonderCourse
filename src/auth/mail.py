"""Email utilities for auth module."""

from flask_mail import Mail, Message
from flask import current_app

mail = Mail()


def init_mail(app):
    """Initialize Flask-Mail with app.

    Args:
        app: Flask application instance
    """
    mail.init_app(app)


def send_password_reset_email(to_email: str, reset_token: str):
    """Send password reset email.

    Args:
        to_email: Recipient email address
        reset_token: Password reset token
    """
    reset_url = f"{current_app.config.get('APP_URL', 'http://localhost:5003')}/reset-password?token={reset_token}"

    msg = Message(
        subject="Password Reset Request",
        recipients=[to_email],
        body=f"""You requested a password reset.

Click the following link to reset your password:
{reset_url}

This link will expire in 1 hour.

If you did not request this reset, please ignore this email.
"""
    )

    # Only send if mail server is configured
    if current_app.config.get('MAIL_SERVER') != 'localhost':
        mail.send(msg)
    else:
        # Log for development
        current_app.logger.info(f"Password reset email would be sent to {to_email}")
        current_app.logger.info(f"Reset URL: {reset_url}")
