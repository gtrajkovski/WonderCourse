"""Password reset token generation and verification.

Uses itsdangerous URLSafeTimedSerializer for secure, time-limited tokens.
"""

from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from flask import current_app


def generate_reset_token(email: str) -> str:
    """Generate a time-limited password reset token.

    Args:
        email: User's email address to encode in token

    Returns:
        URL-safe token string
    """
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return s.dumps(email, salt='password-reset')


def verify_reset_token(token: str, max_age: int = 3600) -> str | None:
    """Verify a password reset token.

    Args:
        token: Token string to verify
        max_age: Maximum token age in seconds (default: 1 hour)

    Returns:
        Email address if valid, None if invalid or expired
    """
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = s.loads(token, salt='password-reset', max_age=max_age)
        return email
    except (SignatureExpired, BadSignature):
        return None
