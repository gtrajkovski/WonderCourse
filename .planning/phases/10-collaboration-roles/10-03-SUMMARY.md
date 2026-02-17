---
phase: 10-collaboration-roles
plan: 03
subsystem: collaboration
tags: [decorators, rbac, flask, permissions, access-control]

# Dependency graph
requires:
  - phase: 10-01
    provides: Permission system and Role/Collaborator models
  - phase: 09-03
    provides: Flask-Login authentication for current_user
provides:
  - Permission enforcement decorators for API routes
  - Owner auto-creation utility for new courses
  - Fresh permission checks on every request
affects:
  - All course API endpoints needing permission checks
  - Course creation flow needing owner setup

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Decorator pattern for permission enforcement"
    - "Route parameter extraction from kwargs and view_args"
    - "JSON error responses for permission denial"

key-files:
  created:
    - src/collab/decorators.py
    - tests/test_permission_decorator.py
  modified:
    - src/collab/__init__.py

key-decisions:
  - "Extract course_id from kwargs first, then view_args for flexibility"
  - "Return 403 JSON for permission denial, 400 for missing course_id"
  - "Query permissions fresh on every request (no caching)"
  - "Three decorator variants: single permission, any of multiple, any collaborator"
  - "ensure_owner_collaborator is idempotent (safe to call multiple times)"

patterns-established:
  - "@login_required must come before @require_permission in decorator stack"
  - "Decorators return JSON errors for API consistency"
  - "Permission checks use has_permission() for database queries"
  - "ensure_owner_collaborator creates Owner role from template on first call"

# Metrics
duration: 4min
completed: 2026-02-10
---

# Phase 10 Plan 03: Permission Enforcement Decorators Summary

**Flask decorators for route-level permission checks with fresh database queries, course_id extraction, and automatic owner setup**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-10T04:21:27Z
- **Completed:** 2026-02-10T04:25:55Z
- **Tasks:** 3 (Task 2 combined with Task 1)
- **Files modified:** 4

## Accomplishments
- Permission enforcement decorators for API routes
- Three decorator variants: require_permission, require_any_permission, require_collaborator
- ensure_owner_collaborator utility for automatic owner setup
- 12 comprehensive tests covering all decorator behaviors
- Fresh permission checks on every request (no caching)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create permission enforcement decorator** - `64e7b49` (feat)
   - Also included Task 2 (ensure_owner_collaborator utility)
2. **Task 3: Create permission decorator tests** - `f4d37dc` (test)

## Files Created/Modified

- `src/collab/decorators.py` - Permission enforcement decorators (170 lines)
  - require_permission(permission_code) - Single permission check
  - require_any_permission(*permission_codes) - Multiple permission options
  - require_collaborator() - Simple collaborator check
  - ensure_owner_collaborator(course_id, user_id) - Auto-create owner
- `tests/test_permission_decorator.py` - Comprehensive decorator tests (330 lines)
  - 12 tests covering permission checks, unauthorized access, missing params
  - Tests for all three decorator variants
  - Tests for owner creation and idempotency
  - Tests for fresh permission checks (no stale cache)
- `src/collab/__init__.py` - Updated exports to include decorators

## Decisions Made

**Extract course_id from kwargs first, then view_args:**
Provides flexibility for different Flask routing patterns. Checks `kwargs.get('course_id')` first (function parameter), then falls back to `request.view_args.get('course_id')` (route parameter).

**Return 403 for permission denial, 400 for missing course_id:**
Distinguishes between permission issues (403 Forbidden) and malformed requests (400 Bad Request). Consistent with REST API conventions.

**Query permissions fresh on every request:**
No caching layer - every permission check queries the database via `has_permission()`. Ensures permission changes take effect immediately. Acceptable performance for expected usage patterns.

**Three decorator variants for common patterns:**
- `require_permission` for specific permission checks
- `require_any_permission` for endpoints accepting multiple permission levels
- `require_collaborator` for read-only endpoints any collaborator can access

**ensure_owner_collaborator is idempotent:**
Safe to call multiple times - checks for existing collaborator first. Returns existing if found, creates new if not. Prevents duplicate owner entries.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

**Test database configuration:**
Initial tests failed because `:memory:` SQLite database creates a new database per connection. Fixed by using temp file database shared across all connections within test.

**Linter auto-imports:**
VSCode linter auto-imported from non-existent `src.collab.comments` and `src.collab.audit` modules. Reverted __init__.py to only import existing modules.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for integration:**
- ✅ Decorators ready for use on course API endpoints
- ✅ ensure_owner_collaborator ready for course creation flow
- ✅ Permission checks enforce access control on all routes
- ✅ 12 tests verify decorator behavior

**Next steps:**
- Apply decorators to existing course API endpoints in app.py
- Add ensure_owner_collaborator() call when POST /api/courses creates new course
- Create invitation API endpoints (10-04) that use these decorators

**No blockers.**

---
*Phase: 10-collaboration-roles*
*Completed: 2026-02-10*
