# Phase 9: User Authentication & Accounts - Research

**Researched:** 2026-02-06
**Domain:** Flask authentication, session management, user data isolation
**Confidence:** HIGH

## Summary

This phase adds user authentication to transform Course Builder from a single-user localhost tool into a multi-user web service. The Flask ecosystem has mature, well-tested libraries for this: Flask-Login for session management, Werkzeug (already installed) for password hashing, and itsdangerous (already installed via Flask) for token generation.

The key architectural decision is storage: the app currently uses file-based JSON persistence via ProjectStore. For user authentication, SQLite is the right choice because it provides ACID transactions for user data, built-in Python support, and works well with Flask-Login's user loader pattern. Course data can remain file-based, organized under `projects/{user_id}/{course_id}/`.

**Primary recommendation:** Use Flask-Login + SQLite for auth, keep file-based course storage with user-scoped directories.

## Standard Stack

The established libraries for Flask authentication:

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Flask-Login | 0.7.0 | Session management, login_required decorator | De facto standard for Flask auth, handles sessions, remember-me, route protection |
| Werkzeug | 3.1.5 (installed) | Password hashing via `generate_password_hash`, `check_password_hash` | Already included with Flask, uses scrypt by default, no additional dependency |
| itsdangerous | 2.x (installed) | Secure token generation for password reset | Included with Flask, provides URLSafeTimedSerializer for expiring tokens |
| sqlite3 | stdlib | User database storage | Built into Python, zero-config, ACID compliant |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Flask-Mail | 0.10.0 | Email sending for password reset | Required for AUTH-07 (password reset via email) |
| Flask-Limiter | 4.1.1 | Rate limiting for brute-force protection | Recommended for login/register endpoints |
| Flask-WTF | 1.2.x | CSRF protection for forms | If using HTML forms for login (optional for API-only) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Flask-Login | Flask-JWT-Extended | JWT better for pure API/mobile clients; sessions better for browser apps. This app uses browser UI, so sessions are simpler. |
| Flask-Login | Flask-Security | More batteries-included but heavier; overkill for these 7 requirements |
| SQLite | PostgreSQL | PostgreSQL needed for production multi-tenant; SQLite fine for small deployments |
| File storage | Full DB | Course data is document-shaped, file storage works; user data needs relational integrity |

**Installation:**
```bash
pip install Flask-Login Flask-Mail Flask-Limiter
```

## Architecture Patterns

### Recommended Project Structure

```
src/
├── auth/                   # NEW: Authentication module
│   ├── __init__.py
│   ├── models.py           # User model with UserMixin
│   ├── db.py               # SQLite connection management
│   ├── routes.py           # Login, register, logout, profile endpoints
│   └── decorators.py       # Custom decorators if needed
├── api/                    # Existing blueprints (unchanged structure)
│   ├── modules.py          # Add @login_required
│   └── ...
├── core/
│   ├── project_store.py    # Modify to accept user_id for scoping
│   └── ...
└── ...

instance/                   # NEW: Instance folder for SQLite
└── users.db

projects/                   # Modified structure
└── {user_id}/
    └── {course_id}/
        └── course_data.json
```

### Pattern 1: Flask-Login Integration

**What:** Initialize LoginManager with app, define user_loader callback
**When to use:** App startup, before any routes are registered

**Example:**
```python
# Source: https://flask-login.readthedocs.io/
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'  # Redirect target for @login_required

@login_manager.user_loader
def load_user(user_id):
    """Load user from database by ID. Return None if not found."""
    return User.get_by_id(user_id)
```

### Pattern 2: User Model with Werkzeug Password Hashing

**What:** User class inheriting UserMixin with password hash methods
**When to use:** User registration and login verification

**Example:**
```python
# Source: https://werkzeug.palletsprojects.com/en/stable/utils/
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin):
    def __init__(self, id, email, password_hash, name=None):
        self.id = id
        self.email = email
        self.password_hash = password_hash
        self.name = name

    def set_password(self, password):
        """Hash password using scrypt (Werkzeug default)."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify password against stored hash."""
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        """Required by Flask-Login. Return string ID."""
        return str(self.id)
```

### Pattern 3: SQLite User Storage with g Object

**What:** Connection management using Flask's g object
**When to use:** Database operations during request lifecycle

**Example:**
```python
# Source: https://flask.palletsprojects.com/en/stable/tutorial/database/
import sqlite3
from flask import g, current_app

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row  # Access columns by name
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_app(app):
    app.teardown_appcontext(close_db)
```

### Pattern 4: Password Reset Token Generation

**What:** Time-limited tokens for password reset links
**When to use:** AUTH-07 password reset flow

**Example:**
```python
# Source: https://itsdangerous.palletsprojects.com/en/stable/url_safe/
from itsdangerous import URLSafeTimedSerializer
from flask import current_app

def generate_reset_token(email):
    """Create a time-limited token for password reset."""
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return s.dumps(email, salt='password-reset')

def verify_reset_token(token, max_age=3600):
    """Verify token and return email. Returns None if invalid/expired."""
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = s.loads(token, salt='password-reset', max_age=max_age)
        return email
    except Exception:
        return None
```

### Pattern 5: Protecting Existing Endpoints

**What:** Add @login_required and user scoping to existing blueprints
**When to use:** All API endpoints except register/login/health

**Example:**
```python
from flask_login import login_required, current_user

@modules_bp.route('/api/courses/<course_id>/modules', methods=['GET'])
@login_required
def list_modules(course_id):
    # Load course scoped to current user
    course = _project_store.load(current_user.id, course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404
    # ... rest unchanged
```

### Pattern 6: User-Scoped Project Storage

**What:** Modify ProjectStore to namespace courses by user_id
**When to use:** All course operations after authentication is added

**Example:**
```python
class ProjectStore:
    def __init__(self, base_dir: Path = Path("projects")):
        self.base_dir = base_dir

    def _user_dir(self, user_id: str) -> Path:
        """Get user's project directory."""
        safe_user_id = self._sanitize_id(user_id)
        user_path = self.base_dir / safe_user_id
        user_path.mkdir(parents=True, exist_ok=True)
        return user_path

    def _course_dir(self, user_id: str, course_id: str) -> Path:
        """Get course directory scoped to user."""
        safe_course_id = self._sanitize_id(course_id)
        return self._user_dir(user_id) / safe_course_id

    def save(self, user_id: str, course: Course) -> Path:
        """Save course under user's directory."""
        course_dir = self._course_dir(user_id, course.id)
        # ... rest of save logic

    def list_courses(self, user_id: str) -> List[dict]:
        """List only this user's courses."""
        user_dir = self._user_dir(user_id)
        # Only iterate courses within user's directory
```

### Anti-Patterns to Avoid

- **Storing passwords in plain text:** Always use `generate_password_hash()`
- **Rolling your own session management:** Use Flask-Login, not custom cookies
- **Trusting client-provided user_id:** Always use `current_user.id` from Flask-Login
- **Exposing user existence in login errors:** Use generic "Invalid credentials" message
- **Skipping rate limiting on login:** Always rate-limit auth endpoints
- **Storing SECRET_KEY in code:** Load from environment variable

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Password hashing | Custom hash function | `werkzeug.security.generate_password_hash()` | Timing attacks, salt handling, algorithm updates |
| Session management | Custom session cookies | Flask-Login | Session fixation, remember-me cookies, secure defaults |
| Token generation | Random strings | `itsdangerous.URLSafeTimedSerializer` | Cryptographic signing, expiration, tampering detection |
| Rate limiting | Counter dictionary | Flask-Limiter | Distributed state, sliding windows, proper 429 responses |
| CSRF protection | Hidden form fields | Flask-WTF | Token rotation, secure comparison, integration with forms |

**Key insight:** Authentication code has many subtle security pitfalls (timing attacks, session fixation, token prediction). Battle-tested libraries handle edge cases that are easy to miss.

## Common Pitfalls

### Pitfall 1: Timing Attacks on Password Verification

**What goes wrong:** Using `==` to compare passwords leaks timing information
**Why it happens:** String comparison short-circuits on first mismatch
**How to avoid:** Use `check_password_hash()` which uses constant-time comparison
**Warning signs:** Direct password comparisons anywhere in code

### Pitfall 2: Session Fixation

**What goes wrong:** Attacker sets session ID before user logs in, then hijacks session
**Why it happens:** Session ID not regenerated on login
**How to avoid:** Call `session.clear()` before `login_user()` (Flask-Login handles this)
**Warning signs:** Session ID unchanged before and after login

### Pitfall 3: User Enumeration

**What goes wrong:** Different error messages for "user not found" vs "wrong password" reveal valid emails
**Why it happens:** Helpful error messages leak information
**How to avoid:** Return identical "Invalid credentials" for both cases
**Warning signs:** Error messages that distinguish between invalid email and wrong password

### Pitfall 4: Missing Rate Limiting

**What goes wrong:** Brute force attacks can try unlimited passwords
**Why it happens:** Rate limiting not implemented on login endpoint
**How to avoid:** Use Flask-Limiter with strict limits (e.g., 5/minute) on login
**Warning signs:** No 429 responses from login endpoint under load

### Pitfall 5: Insecure Password Reset

**What goes wrong:** Predictable tokens, non-expiring tokens, or token reuse
**Why it happens:** Using random.randint or similar for tokens
**How to avoid:** Use `URLSafeTimedSerializer` with expiration; invalidate after use
**Warning signs:** Tokens that don't expire or can be reused

### Pitfall 6: Missing HTTPS in Production

**What goes wrong:** Session cookies transmitted in plain text
**Why it happens:** Development setup copied to production
**How to avoid:** Set `SESSION_COOKIE_SECURE=True` in production config
**Warning signs:** Cookies without Secure flag in production

### Pitfall 7: Broken Access Control

**What goes wrong:** User can access/modify another user's courses
**Why it happens:** Course ID lookup not scoped to current user
**How to avoid:** Always include `user_id` in course queries; verify ownership
**Warning signs:** API accepts arbitrary course_id without ownership check

## Code Examples

Verified patterns from official sources:

### User Schema (SQLite)

```sql
-- Source: https://flask.palletsprojects.com/en/stable/tutorial/database/
CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Registration Endpoint

```python
# Source: Werkzeug + Flask-Login patterns
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
from src.auth.db import get_db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    name = data.get('name')

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    db = get_db()
    try:
        db.execute(
            "INSERT INTO user (email, password_hash, name) VALUES (?, ?, ?)",
            (email, generate_password_hash(password), name)
        )
        db.commit()
    except db.IntegrityError:
        return jsonify({"error": "Email already registered"}), 400

    return jsonify({"message": "Registration successful"}), 201
```

### Login Endpoint

```python
# Source: Flask-Login patterns
from flask_login import login_user
from werkzeug.security import check_password_hash

@auth_bp.route('/api/auth/login', methods=['POST'])
@limiter.limit("5 per minute")  # Rate limit for brute force protection
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    user = User.get_by_email(email)

    # Generic error message prevents user enumeration
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 401

    login_user(user, remember=data.get('remember', False))
    return jsonify({"message": "Login successful", "user": user.to_dict()}), 200
```

### Logout Endpoint

```python
# Source: Flask-Login documentation
from flask_login import logout_user, login_required

@auth_bp.route('/api/auth/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logout successful"}), 200
```

### Secure Cookie Configuration

```python
# Source: https://flask.palletsprojects.com/en/stable/web-security/
app.config.update(
    SECRET_KEY=os.environ['SECRET_KEY'],  # Never hardcode
    SESSION_COOKIE_SECURE=True,            # HTTPS only (production)
    SESSION_COOKIE_HTTPONLY=True,          # No JavaScript access
    SESSION_COOKIE_SAMESITE='Lax',         # CSRF protection
    PERMANENT_SESSION_LIFETIME=86400,      # 24 hours
)
```

### Flask-Limiter Setup

```python
# Source: https://flask-limiter.readthedocs.io/
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",  # Use Redis in production
)

def init_app(app):
    limiter.init_app(app)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| MD5/SHA1 hashing | scrypt/Argon2/PBKDF2 | ~2015 | Use Werkzeug default (scrypt) |
| Custom session cookies | Flask-Login sessions | N/A | Don't roll your own |
| JWT for everything | JWT for APIs, sessions for browser apps | ~2020 | Use sessions for this app (browser-based) |
| No rate limiting | Rate limiting standard | ~2018 | Flask-Limiter is essential |

**Deprecated/outdated:**
- `werkzeug.security.safe_str_cmp`: Removed in Werkzeug 3.0, use `hmac.compare_digest`
- SHA256 with low iterations: Use scrypt or PBKDF2 with 600K+ iterations

## Open Questions

Things that couldn't be fully resolved:

1. **Email Provider for Password Reset**
   - What we know: Flask-Mail supports SMTP, various providers work (Gmail, SendGrid, Mailgun)
   - What's unclear: User's preferred email provider, whether to use environment-based SMTP config
   - Recommendation: Configure via environment variables, document common setups (Gmail, SendGrid)

2. **Remember-Me Duration**
   - What we know: Flask-Login defaults to 365 days, can be configured
   - What's unclear: Appropriate duration for this application's use case
   - Recommendation: Start with 30 days, make configurable

3. **Database Migration Strategy**
   - What we know: SQLite schema can be managed with raw SQL or Flask-Migrate
   - What's unclear: Whether to add Flask-Migrate or keep simple with init-db command
   - Recommendation: Use simple `flask init-db` command for v1, add migrations if schema evolves

## Sources

### Primary (HIGH confidence)
- [Flask-Login 0.7.0 documentation](https://flask-login.readthedocs.io/) - Session management, UserMixin, login_required
- [Werkzeug 3.1.x documentation](https://werkzeug.palletsprojects.com/en/stable/utils/) - Password hashing functions
- [Flask documentation - Database](https://flask.palletsprojects.com/en/stable/tutorial/database/) - SQLite integration pattern
- [Flask documentation - Security](https://flask.palletsprojects.com/en/stable/web-security/) - Cookie security, headers
- [itsdangerous documentation](https://itsdangerous.palletsprojects.com/en/stable/url_safe/) - URLSafeTimedSerializer

### Secondary (MEDIUM confidence)
- [Flask-Limiter documentation](https://flask-limiter.readthedocs.io/) - Rate limiting
- [Flask-Mail documentation](https://flask-mail.readthedocs.io/) - Email sending
- [Mailtrap Flask Email Guide 2026](https://mailtrap.io/blog/flask-email-sending/) - Password reset patterns
- [DigitalOcean Flask-Login Tutorial](https://www.digitalocean.com/community/tutorials/how-to-add-authentication-to-your-app-with-flask-login) - Integration patterns

### Tertiary (LOW confidence)
- Various Medium articles on multi-tenancy - Reviewed for data isolation patterns but not authoritative

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Flask-Login, Werkzeug well-documented, already have dependencies
- Architecture: HIGH - Flask patterns well-established, follows official tutorials
- Pitfalls: HIGH - Security pitfalls well-documented across multiple official sources

**Research date:** 2026-02-06
**Valid until:** 2026-03-08 (30 days - stable domain, mature libraries)
