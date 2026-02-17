---
phase: 10-collaboration-roles
verified: 2026-02-10T14:30:00Z
status: gaps_found
score: 5/6 must-haves verified
gaps:
  - truth: "Invitations can be listed and accepted via API without errors"
    status: failed
    reason: "Two bugs in collab API prevent invitation listing and acceptance from working"
    artifacts:
      - path: "src/api/collab.py"
        issue: "Line 92: calls Invitation.get_pending_for_course() which does not exist (should be get_for_course())"
      - path: "src/api/collab.py"
        issue: "Lines 105-108: validate_invitation_token returns tuple (course_id, role_id), but code treats it as Invitation object with .course_id attribute"
    missing:
      - "Fix line 92: change get_pending_for_course to get_for_course"
      - "Fix lines 105-108: extract course_id from tuple instead of accessing .course_id attribute"
---

# Phase 10: Collaboration & Roles Verification Report

**Phase Goal:** Course owners can invite collaborators with role-based permissions, enabling team-based course development with commenting and audit trails.
**Verified:** 2026-02-10
**Status:** gaps_found
**Re-verification:** No - initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Course owner can invite collaborators by email with a specific role (SME, designer, reviewer) | PARTIAL | API exists at POST /api/courses/<id>/invitations but GET endpoint has bug (see gaps) |
| 2 | Role-based permissions enforced: owner (full), designer (edit), reviewer (comment/approve), SME (view/comment) | VERIFIED | require_permission decorator wired to all API endpoints in modules, lessons, activities, content, build_state, export, blueprint, learning_outcomes |
| 3 | Content changes are tracked with user attribution and timestamps (audit trail) | VERIFIED | log_audit_entry called in modules.py, content.py, build_state.py, collab.py with ACTION_* constants |
| 4 | Users can add comments on content items with threaded replies | VERIFIED | Comment model with single-level threading, /api/courses/<id>/comments endpoints, 488 lines of tests |
| 5 | Approval workflow allows reviewers to approve/reject content items | VERIFIED | POST /api/courses/<id>/activities/<id>/approve requires approve_content permission |
| 6 | Activity feed shows recent changes by all collaborators on a course | VERIFIED | GET /api/courses/<id>/activity returns paginated feed with summarize_changes |

**Score:** 5/6 truths verified (1 partial due to bugs)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/collab/models.py` | Role, Collaborator models | VERIFIED | 400 lines, Role.create_from_template, Collaborator CRUD |
| `src/collab/permissions.py` | PERMISSIONS, ROLE_TEMPLATES, has_permission | VERIFIED | 13 permission codes, 4 role templates |
| `src/collab/invitations.py` | Invitation model with tokens | VERIFIED | 350 lines, create, validate, accept functions |
| `src/collab/decorators.py` | require_permission decorator | VERIFIED | 160 lines, require_permission, require_any_permission, require_collaborator, ensure_owner_collaborator |
| `src/collab/comments.py` | Comment, Mention models | VERIFIED | 522 lines, parse_mentions, threading enforcement |
| `src/collab/audit.py` | AuditEntry, log_audit_entry | VERIFIED | 333 lines, jsondiff integration, summarize_changes |
| `src/api/collab.py` | Collaboration API Blueprint | PARTIAL | 320 lines, endpoints exist but 2 bugs (see gaps) |
| `instance/schema.sql` | collaboration tables | VERIFIED | course_role, permission, role_permission, collaborator, invitation, comment, mention, audit_entry |
| `requirements.txt` | jsondiff dependency | VERIFIED | jsondiff>=2.2.0 present |
| `tests/test_collab_*.py` | integration tests | VERIFIED | 123 tests collected across 6 test files |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| app.py | src/api/collab.py | Blueprint registration | WIRED | `app.register_blueprint(collab_bp)` on line 102 |
| app.py | ensure_owner_collaborator | Course creation | WIRED | Called on line 249 after course save |
| app.py | seed_permissions | App startup | WIRED | Called on line 115 in app context |
| src/api/modules.py | decorators.py | Permission checks | WIRED | @require_permission on all mutating routes |
| src/api/content.py | audit.py | Change tracking | WIRED | log_audit_entry calls for generate/update |
| src/api/build_state.py | audit.py | State logging | WIRED | Approval logged with ACTION_CONTENT_APPROVED |
| src/collab/audit.py | jsondiff | Diff calculation | WIRED | `from jsondiff import diff` on line 10 |

### Requirements Coverage

| Requirement | Status | Blocking Issue |
|-------------|--------|----------------|
| COLLAB-01: Invite collaborators by email with role | PARTIAL | API bug in invitation listing/acceptance |
| COLLAB-02: Audit trail for content changes | SATISFIED | log_audit_entry wired throughout |
| COLLAB-03: Commenting and approval workflows | SATISFIED | Comment API + approve_content permission |
| COLLAB-04: Role-based permissions | SATISFIED | 4 role templates enforced via decorators |
| COLLAB-05: Activity feed for collaborators | SATISFIED | GET /api/courses/<id>/activity endpoint |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| src/api/collab.py | 92 | Method does not exist | BLOCKER | GET /api/courses/<id>/invitations will raise AttributeError |
| src/api/collab.py | 105-108 | Wrong type usage | BLOCKER | POST /api/invitations/<token>/accept will raise AttributeError |

### Human Verification Required

#### 1. Invitation Email Flow
**Test:** Create invitation with email, send invite, accept as different user
**Expected:** User receives invitation, can accept, becomes collaborator with assigned role
**Why human:** Requires email delivery and multi-user interaction

#### 2. Real-time Permission Changes
**Test:** Change user's role while they are logged in, verify next request uses new permissions
**Expected:** Permission change takes effect immediately on next API call
**Why human:** Requires concurrent sessions to verify no caching

#### 3. Approval Workflow UX
**Test:** Designer creates content, Reviewer approves, Designer sees approved status
**Expected:** State change visible to all collaborators, audit entry created
**Why human:** Requires multi-user workflow coordination

### Gaps Summary

Two bugs in `src/api/collab.py` prevent the invitation workflow from functioning:

1. **Line 92:** `Invitation.get_pending_for_course(course_id)` - This method does not exist on the Invitation class. The correct method is `Invitation.get_for_course(course_id)`. This prevents listing pending invitations.

2. **Lines 105-108:** The `validate_invitation_token(token)` function returns a tuple `(course_id, role_id)`, but the code on line 108 attempts to access `invitation.course_id` as if it were an Invitation object. This will raise an AttributeError when users try to accept invitations.

These are straightforward fixes:
- Line 92: Change `get_pending_for_course` to `get_for_course`
- Lines 105-108: Change to extract values from tuple: `course_id, role_id = validate_invitation_token(token)` and use `course_id` directly

All other collaboration infrastructure is correctly implemented and wired:
- Database schema complete (8 tables)
- Permission system (13 codes, 4 templates)
- Decorators wired to all existing APIs
- Audit logging integrated
- Comment system with threading
- 123 tests covering functionality

---

*Verified: 2026-02-10*
*Verifier: Claude (gsd-verifier)*
