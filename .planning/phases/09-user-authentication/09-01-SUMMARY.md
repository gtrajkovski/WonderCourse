---
phase: 09-user-authentication
plan: 01
subsystem: authentication
tags: [flask-login, sqlite, werkzeug, user-model]

dependency-graph:
  requires: []
  provides:
    - User model with Flask-Login integration
    - SQLite database infrastructure
    - Password hashing utilities
  affects:
    - 09-02 (tests for this plan)
    - 09-03 (auth routes)
    - 09-04 (Flask integration)

tech-stack:
  added:
    - Flask-Login>=0.6.3
    - Flask-Mail>=0.10.0
    - Flask-Limiter>=3.5.0
  patterns:
    - Raw SQLite with Flask g object for request-scoped connections
    - Werkzeug scrypt for password hashing (never plaintext)
    - UserMixin inheritance for Flask-Login compatibility

key-files:
  created:
    - src/auth/__init__.py
    - src/auth/models.py
    - src/auth/db.py
    - src/auth/login_manager.py
    - instance/schema.sql
  modified:
    - requirements.txt
    - src/config.py
    - .env.example
    - .gitignore

decisions:
  - Raw SQLite over SQLAlchemy for simplicity
  - SECRET_KEY defaults to dev value with warning in comments
  - instance/*.db gitignored, schema.sql tracked

metrics:
  duration: 5m 17s
  completed: 2026-02-07
---

# Phase 09 Plan 01: User Model and Database Summary

SQLite-backed User model with Flask-Login integration and Werkzeug password hashing

## One-Liner

User model with scrypt password hashing, SQLite persistence via Flask g object, and Flask-Login UserMixin.

## What Was Built

### User Model (`src/auth/models.py`)
- `User` class inheriting from `flask_login.UserMixin`
- Fields: id, email, password_hash, name, created_at
- Password methods using Werkzeug:
  - `set_password(password)` - hash and store
  - `check_password(password)` - verify against hash
- Database operations:
  - `get_by_id(user_id)` - load by primary key
  - `get_by_email(email)` - load by email for login
  - `create(email, password, name=None)` - create with hashed password
- `to_dict()` excludes password_hash for security

### SQLite Infrastructure (`src/auth/db.py`)
- `get_db()` - request-scoped connection via Flask g object
- `close_db(e=None)` - teardown callback for auto-close
- `init_db()` - execute schema.sql to create tables
- `init_app(app)` - register teardown and CLI command

### Database Schema (`instance/schema.sql`)
```sql
CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_user_email ON user(email);
```

### Flask-Login Integration (`src/auth/login_manager.py`)
- `login_manager` instance configured with login view
- `user_loader` callback for session restoration
- `init_login_manager(app)` for Flask app initialization

### Config Updates (`src/config.py`)
- `SECRET_KEY` - from env or dev default
- `DATABASE` - Path to instance/users.db

## Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| Raw SQLite over SQLAlchemy | Simpler for single-table auth, matches project's minimal-dependency philosophy |
| Flask g object for connections | Standard Flask pattern, request-scoped lifecycle |
| Werkzeug scrypt | Built into Flask's Werkzeug, no additional crypto dependency |
| instance/*.db in gitignore | Database files are runtime artifacts, schema.sql is code |

## Task Completion

| Task | Description | Commit | Status |
|------|-------------|--------|--------|
| 1 | Create auth package with User model | 0cc5bc8 | Complete |
| 2 | Create SQLite database infrastructure | c6119a5 | Complete |
| 3 | Add Flask-Login and Flask-Mail dependencies | c032d4b | Complete |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Flask-Login version constraint**
- **Found during:** Task 3
- **Issue:** Plan specified Flask-Login>=0.7.0 but latest available is 0.6.3
- **Fix:** Updated requirements.txt to Flask-Login>=0.6.3
- **Files modified:** requirements.txt

**2. [Rule 3 - Blocking] .gitignore blocking schema.sql**
- **Found during:** Task 2
- **Issue:** instance/ directory was fully gitignored, preventing schema.sql tracking
- **Fix:** Changed to instance/*.db to allow schema.sql while excluding database files
- **Files modified:** .gitignore

## Test Coverage

17 tests pass in `tests/test_auth_models.py` (added by parallel plan 09-02):
- User creation (2 tests)
- Password hashing (4 tests)
- User retrieval (4 tests)
- User serialization (2 tests)
- Unique constraints (1 test)
- Flask-Login compatibility (4 tests)

## Next Phase Readiness

**Ready for 09-02:** Tests already created and passing
**Ready for 09-03:** User model supports login/register routes
**Ready for 09-04:** Flask-Login manager ready for app integration

## Files Changed

```
src/auth/__init__.py          NEW - Package exports
src/auth/models.py            NEW - User model with password hashing
src/auth/db.py                NEW - SQLite connection management
src/auth/login_manager.py     NEW - Flask-Login configuration
instance/schema.sql           NEW - User table DDL
requirements.txt              MOD - Added auth dependencies
src/config.py                 MOD - Added SECRET_KEY, DATABASE
.env.example                  MOD - Added SECRET_KEY placeholder
.gitignore                    MOD - Changed instance/ to instance/*.db
```
