---
phase: 10-collaboration-roles
plan: 07
subsystem: collaboration
tags: [comments, activity-feed, notifications, mentions, api]
one_liner: "Comment and activity feed API endpoints with threading, resolution, and mentions"
completed: 2026-02-10

dependencies:
  requires:
    - "10-04: Comment and Mention models for data layer"
    - "10-05: Audit logging for activity feed"
  provides:
    - "REST endpoints for comment CRUD with threading"
    - "Notification endpoints for @mentions"
    - "Activity feed endpoint with pagination"
  affects:
    - "Frontend can now display and manage comments"
    - "Activity dashboard can show recent changes"

tech_stack:
  added: []
  patterns:
    - "Comment endpoints for course-level and activity-level"
    - "Audit logging for comment actions"
    - "Paginated activity feed with has_more indicator"

key_files:
  created: []
  modified:
    - path: "src/api/collab.py"
      change: "Added comment, notification, and activity feed endpoints"
    - path: "tests/test_collab_api.py"
      change: "Added 21 tests for comment and activity feed API"

decisions:
  - what: "Comments use view_content permission for CRUD"
    why: "Any collaborator should be able to comment on content"
    impact: "All collaborators can create and resolve comments"

  - what: "Only author or owner can update/delete comments"
    why: "Prevent users from modifying others comments"
    impact: "Checked via get_user_role to allow owner override"

  - what: "Activity feed fetches limit+1 to detect has_more"
    why: "Efficient pagination without separate count query"
    impact: "Clients know if more entries exist"

metrics:
  duration: "18 minutes"
  tasks: 3
  commits: 2
  tests_added: 21

---

# Phase 10 Plan 07: Comment and Activity Feed API Summary

**One-liner:** Comment and activity feed API endpoints with threading, resolution, and mentions

## What Was Built

Added comprehensive comment and activity feed endpoints to the Collaboration API.

### Comment Endpoints

**Course-level comments:**
- GET /api/courses/<id>/comments - List with replies, include_resolved param
- POST /api/courses/<id>/comments - Create comment or reply

**Activity-level comments:**
- GET /api/courses/<id>/activities/<aid>/comments - List for specific activity
- POST /api/courses/<id>/activities/<aid>/comments - Create on activity

**Comment management:**
- PUT /api/courses/<id>/comments/<cid> - Update (author or owner only)
- DELETE /api/courses/<id>/comments/<cid> - Delete with replies
- POST /api/courses/<id>/comments/<cid>/resolve - Mark resolved
- POST /api/courses/<id>/comments/<cid>/unresolve - Mark unresolved

### Notification Endpoints

- GET /api/notifications - Get unread mentions with comment context
- POST /api/notifications/<mid>/read - Mark single read
- POST /api/notifications/read-all - Mark all read, returns count

### Activity Feed Endpoint

- GET /api/courses/<id>/activity - Paginated audit trail
  - Query params: limit (default 50, max 100), offset
  - Returns: feed array, limit, offset, has_more

### Integration with Audit System

Comment actions logged to audit trail:
- comment_added when comment created
- comment_resolved when resolved
- collaborator_joined when invitation accepted

## Test Coverage

21 tests covering:

1. **Course-level comments (4 tests)**
   - Create comment
   - List with replies
   - Reply to comment
   - Cannot reply to reply (400)

2. **Activity-level comments (2 tests)**
   - Create on activity
   - List filtered by activity

3. **Comment management (5 tests)**
   - Update own comment
   - Owner can update others
   - Resolve hides from default list
   - Unresolve makes visible
   - Delete removes with replies

4. **Notifications (4 tests)**
   - Mention creates notification
   - Get notifications
   - Mark read
   - Mark all read

5. **Activity feed (4 tests)**
   - Returns feed structure
   - Pagination works
   - Includes user name
   - Comment actions logged

6. **Permissions (2 tests)**
   - Non-collaborator cannot comment
   - Non-collaborator cannot view feed

## Deviations from Plan

None - plan executed exactly as written.

## Files Modified

**Modified:**
- src/api/collab.py - Added 156 lines for comment, notification, and activity endpoints
- tests/test_collab_api.py - Added 21 tests

## Verification Results

All success criteria met:

- [x] POST /api/courses/<id>/comments creates comment
- [x] GET /api/courses/<id>/activities/<aid>/comments returns activity comments
- [x] POST /api/courses/<id>/comments/<cid>/resolve hides comment
- [x] GET /api/notifications returns unread mentions
- [x] GET /api/courses/<id>/activity returns paginated feed
- [x] Comment actions logged to audit trail
- [x] 21 tests pass

## Commit History

1. **1327ec4** - feat(10-07): add collaboration API with comments and activity feed
2. **ab7f8ce** - test(10-07): add tests for comment and activity feed API

## Next Phase Readiness

**Ready for:**
- Frontend integration with comment UI
- Activity dashboard showing recent changes
- Notification bell with unread count

**Blockers:** None

**Concerns:** None
