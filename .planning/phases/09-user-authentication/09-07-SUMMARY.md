---
phase: 09
plan: 07
subsystem: auth
tags: [password-reset, tokens, email, itsdangerous, flask-mail]
depends_on:
  requires: ["09-04", "09-05"]
  provides: ["password-reset-flow", "reset-tokens", "email-integration"]
  affects: ["09-ui-integration", "production-deployment"]
tech_stack:
  added: ["flask-mail", "itsdangerous"]
  patterns: ["time-limited-tokens", "email-based-reset"]
key_files:
  created:
    - src/auth/tokens.py
    - src/auth/mail.py
    - tests/test_password_reset.py
  modified:
    - src/config.py
    - src/auth/routes.py
    - src/auth/__init__.py
    - app.py
    - .env.example
decisions:
  - id: token-library
    choice: "itsdangerous URLSafeTimedSerializer"
    rationale: "Already bundled with Flask, proven security, time-limited tokens"
  - id: email-approach
    choice: "Flask-Mail with configurable SMTP"
    rationale: "Standard Flask extension, works with any SMTP provider"
  - id: enumeration-protection
    choice: "Same response for valid/invalid email"
    rationale: "Prevents attackers from discovering which emails are registered"
metrics:
  duration: "~8 minutes"
  completed: "2026-02-07"
  tests_added: 19
  test_file_lines: 322
---

# Phase 9 Plan 7: Password Reset Flow Summary

Password reset with time-limited tokens using itsdangerous and Flask-Mail integration for email delivery.

## What Was Built

### Token Utilities (`src/auth/tokens.py`)
- `generate_reset_token(email)`: Creates URL-safe time-limited token encoding email
- `verify_reset_token(token, max_age)`: Validates token, returns email or None
- Uses itsdangerous URLSafeTimedSerializer with salt 'password-reset'
- Default 1-hour expiration (configurable via `PASSWORD_RESET_TOKEN_MAX_AGE`)

### Email Integration (`src/auth/mail.py`)
- Flask-Mail instance with `init_mail(app)` initializer
- `send_password_reset_email(to_email, token)`: Sends reset email with link
- Development mode: logs instead of sending when MAIL_SERVER='localhost'
- Reset URL format: `{APP_URL}/reset-password?token={token}`

### Password Reset Endpoints (`src/auth/routes.py`)
- **POST /api/auth/forgot-password**: Request reset email
  - Accepts `{"email": str}`
  - Returns 200 regardless of email existence (prevents enumeration)
  - Sends email only if user exists
- **POST /api/auth/reset-password**: Reset password with token
  - Accepts `{"token": str, "new_password": str}`
  - Validates token (invalid/expired returns 400)
  - Enforces 8-character minimum password
  - Updates password in database

### Configuration (`src/config.py`)
New settings:
- `MAIL_SERVER`: SMTP server (default: localhost)
- `MAIL_PORT`: SMTP port (default: 25)
- `MAIL_USE_TLS`: Enable TLS (default: true)
- `MAIL_USERNAME`: SMTP username
- `MAIL_PASSWORD`: SMTP password
- `MAIL_DEFAULT_SENDER`: From address (default: noreply@coursebuilder.local)
- `PASSWORD_RESET_TOKEN_MAX_AGE`: Token expiry in seconds (default: 3600)
- `APP_URL`: Base URL for reset links (default: http://localhost:5003)

## Commits

| Hash | Type | Description |
|------|------|-------------|
| d21aa47 | feat | Add password reset token utilities |
| 725f00f | feat | Configure Flask-Mail for password reset emails |
| f695cec | feat | Add password reset endpoints |
| 15bf98b | test | Add comprehensive password reset tests (19 tests) |

## Test Coverage

19 tests in `tests/test_password_reset.py`:

**Token Generation (5 tests)**
- Token returns URL-safe string
- Valid token verification returns email
- Expired token returns None
- Invalid token returns None
- Tampered token returns None

**Forgot-Password Endpoint (4 tests)**
- Valid email returns 200 and sends email
- Unknown email returns 200 (no enumeration)
- Missing email returns 400
- Empty request returns 400

**Reset-Password Endpoint (7 tests)**
- Valid token resets password successfully
- Invalid token returns 400
- Expired token returns 400
- Short password returns 400
- Missing token returns 400
- Missing password returns 400
- No JSON body returns 400

**Integration (3 tests)**
- Full flow: forgot -> reset -> login with new password
- Old password fails after reset
- Token reuse behavior

## Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Token library | itsdangerous URLSafeTimedSerializer | Already bundled with Flask, proven security |
| Email library | Flask-Mail | Standard Flask extension, any SMTP provider |
| Enumeration protection | Same 200 response for all emails | Prevents email harvesting attacks |
| Token expiry | 1 hour default | Balance between security and user convenience |
| Password minimum | 8 characters | Consistent with registration requirements |

## Deviations from Plan

None - plan executed exactly as written.

## Security Considerations

1. **User Enumeration Prevention**: Forgot-password always returns 200, whether email exists or not
2. **Time-Limited Tokens**: Tokens expire after 1 hour by default
3. **Cryptographic Signing**: Tokens are signed with SECRET_KEY, tamper-resistant
4. **Password Validation**: Same 8-character minimum as registration

## Next Phase Readiness

Password reset flow complete. Ready for:
- UI integration (reset form pages)
- Email service configuration in production
- Optional: Token single-use enforcement (currently tokens valid within time window)
