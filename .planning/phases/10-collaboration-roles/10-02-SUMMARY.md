---
phase: 10-collaboration-roles
plan: 02
subsystem: collaboration
tags: [invitations, tokens, sqlite, flask, email-invites, shareable-links]

# Dependency graph
requires:
  - phase: 09-auth
    provides: User model and authentication database
  - phase: 10-01
    provides: course_role and collaborator tables
provides:
  - Invitation system with email and shareable link support
  - Token generation using secrets.token_urlsafe
  - Validation with expiry and revocation checks
  - Acceptance flow creating collaborator entries
affects: [10-03-invitation-api, 10-04-permissions-api]

# Tech tracking
tech-stack:
  added: []
  patterns: [token-based-invitations, expiry-management, revocation-without-delete]

key-files:
  created:
    - src/collab/invitations.py
    - tests/test_invitations.py
  modified:
    - instance/schema.sql
    - src/collab/__init__.py

key-decisions:
  - "URL-safe 32-character tokens using secrets.token_urlsafe"
  - "Default 7-day expiry for email invitations, configurable or None for permanent"
  - "Revocation flag preserves audit trail (soft delete)"
  - "Shareable links work without email (email=NULL)"
  - "Validation checks both revocation and expiry"
  - "Accept prevents duplicate collaborators"
  - "Handle SQLite datetime objects and ISO strings for Python 3.13 compatibility"

patterns-established:
  - "Invitation.create() for email invitations with default expiry"
  - "Invitation.create_shareable_link() wrapper for link-only invitations"
  - "validate_invitation_token() returns (course_id, role_id) tuple or None"
  - "accept_invitation() creates collaborator and prevents duplicates"
  - "Datetime handling compatible with SQLite detect_types"

# Metrics
duration: 10min
completed: 2026-02-09
---

# Phase 10-02: Invitation Management Summary

**URL-safe token invitations with email and shareable links, configurable expiry, revocation, and collaborator acceptance**

## Performance

- **Duration:** 10 min
- **Started:** 2026-02-10T04:06:02Z
- **Completed:** 2026-02-10T04:16:18Z
- **Tasks:** 3
- **Files modified:** 4 files created/modified

## Accomplishments
- Invitation table with token, expiry, and revocation support
- Email invitation and shareable link creation
- Token validation checking revocation and expiry
- Invitation acceptance creating collaborator entries
- 18 comprehensive tests covering all scenarios
- SQLite datetime compatibility fix for Python 3.13

## Task Commits

Each task was committed atomically:

1. **Task 1: Add invitation table to schema** - `48d4d2a` (feat)
2. **Task 2: Create Invitation model and token utilities** - `40101f4` (feat)
3. **Task 3: Add invitation tests** - `711b228` (fix)

## Files Created/Modified

- `instance/schema.sql` - Added invitation table with token, expiry, revocation
- `src/collab/invitations.py` - Invitation model with CRUD, validation, acceptance
- `src/collab/__init__.py` - Exported invitation functions
- `tests/test_invitations.py` - 18 tests covering token generation, email invites, shareable links, validation, revocation, acceptance

## Decisions Made

1. **Token generation:** Using `secrets.token_urlsafe(32)` for cryptographically strong URL-safe tokens
2. **Expiry configuration:** Default 7 days for email invitations, configurable via `expires_in` parameter, or None for permanent links
3. **Revocation approach:** Soft delete with `revoked` flag preserves audit trail instead of hard delete
4. **Shareable links:** Set `email=None` to allow anyone with the link to accept
5. **Validation return:** Returns `(course_id, role_id)` tuple on success, None on failure (revoked, expired, or nonexistent)
6. **Duplicate prevention:** `accept_invitation()` checks for existing collaborator and returns None if already added

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed SQLite datetime type handling**
- **Found during:** Task 3 (Running tests)
- **Issue:** TypeError when SQLite returns datetime objects (detect_types=PARSE_DECLTYPES enabled). Code attempted to call `datetime.fromisoformat()` on datetime objects instead of strings
- **Fix:** Added type checking in get_by_id(), get_by_token(), and get_for_course() to handle both datetime objects (from SQLite) and ISO format strings
- **Files modified:** src/collab/invitations.py
- **Verification:** All 18 tests pass
- **Committed in:** 711b228 (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Bug fix necessary for tests to pass. Python 3.13 with SQLite detect_types returns datetime objects directly. No scope creep.

## Issues Encountered

None - plan executed smoothly after datetime handling fix.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Invitation system complete and tested
- Ready for API endpoints (10-03) to expose invitation creation, listing, and acceptance
- Ready for permission checking (10-04) to validate user access before creating invitations
- Invitation tokens can be sent via email (requires email service integration in future phase)

---
*Phase: 10-collaboration-roles*
*Completed: 2026-02-09*
