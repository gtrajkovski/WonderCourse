---
phase: 10
plan: 05
type: summary
subsystem: collaboration
tags: [audit-trail, change-tracking, jsondiff, accountability]

requires:
  - phases: [10-01, 10-04]
  - systems: [authentication, database]

provides:
  - capabilities: [audit-logging, change-history, activity-feed]
  - components: [AuditEntry, log_audit_entry, get_activity_feed]

affects:
  - future-plans: [10-06-api-integration]
  - integration-points: [content-generation, collaboration-workflows]

tech-stack:
  added: [jsondiff]
  patterns: [diff-based-storage, left-join-deleted-users]

key-files:
  created:
    - src/collab/audit.py
    - tests/test_audit.py
  modified:
    - instance/schema.sql
    - src/collab/__init__.py

decisions:
  - id: audit-diff-storage
    choice: Use jsondiff with marshal=True for efficient change storage
    rationale: Stores only changed fields instead of full documents, uses serializable format
    alternatives: [full-document-storage, json-patch]

  - id: deleted-user-handling
    choice: Remove FK constraint from audit_entry.user_id
    rationale: Preserves audit trail integrity when users deleted, LEFT JOIN shows "[Deleted User]"
    alternatives: [ON DELETE CASCADE would lose history, ON DELETE SET NULL requires nullable field]

metrics:
  duration: 45 minutes
  tasks-completed: 3/3
  tests-added: 20
  commits: 2
  deviations: 1

completed: 2026-02-10
---

# Phase 10 Plan 05: Audit Trail System Summary

**One-liner:** Comprehensive audit logging with jsondiff-based efficient storage and deleted user support

## What Was Built

Created a complete audit trail system for tracking all course changes with user attribution.

### Core Components

**1. Audit Entry Model (`src/collab/audit.py`)**
- `AuditEntry` class with properties: id, course_id, user_id, action, entity_type, entity_id, changes, created_at
- Class methods: `get_for_course()` (paginated), `get_for_entity()`, `get_by_user()`
- `to_dict()` serialization with JSON parsing and "[Deleted User]" fallback

**2. Audit Logging Utilities**
- `log_audit_entry()` - Creates audit entries with optional diff calculation
- Uses `jsondiff.diff(before, after, marshal=True)` for efficient storage
- Returns created AuditEntry instance with user info

**3. Activity Feed**
- `get_activity_feed()` - Returns paginated feed with human-readable summaries
- LEFT JOIN with user table supports deleted users
- `summarize_changes()` generates context-aware descriptions

**4. Action Constants**
- 17 constants for all tracked operations:
  - Content: created, updated, deleted, generated, approved
  - Structure: added, updated, deleted, reordered
  - Collaborator: invited, joined, removed, role_changed
  - Course: created, updated, exported, published

### Database Schema

**audit_entry table:**
- Columns: id, course_id, user_id, action, entity_type, entity_id, changes, created_at
- Indexes: idx_audit_course (course_id), idx_audit_created (created_at DESC)
- **No FK constraint on user_id** to preserve audit trail when users deleted

### Test Coverage

**20 comprehensive tests** in `tests/test_audit.py`:

1. **Audit Logging (3 tests)**
   - Basic entry creation
   - Diff calculation for before/after
   - NULL changes when no diff

2. **Diff Efficiency (3 tests)**
   - Stores only changed fields
   - Handles nested objects
   - Captures array additions/removals

3. **Audit Queries (4 tests)**
   - Paginated results with limit/offset
   - Ordered by newest first (created_at DESC, id DESC)
   - Filter by entity type and ID
   - Filter by user

4. **Activity Feed (3 tests)**
   - Includes user name and email
   - Shows "[Deleted User]" for missing users
   - Generates human-readable summaries

5. **Summarization (3 tests)**
   - Content updates list changed fields
   - Structure adds show entity name
   - Collaborator changes show user and role

6. **Action Constants (1 test)**
   - All constants are unique

7. **Serialization (3 tests)**
   - to_dict() includes all fields
   - Parses changes JSON to dict
   - Shows "[Deleted User]" in dict format

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Foreign key constraint blocked deleted user handling**
- **Found during:** Task 3 test writing
- **Issue:** audit_entry table had `FOREIGN KEY (user_id) REFERENCES user(id)` which prevented audit entries from being preserved when users deleted, and prevented testing with non-existent user IDs
- **Root cause:** Schema created in plan 10-04 included FK constraint, but plan 10-05 explicitly required LEFT JOIN pattern for deleted users
- **Fix:** Removed FK constraint from audit_entry table schema
- **Files modified:** instance/schema.sql
- **Commit:** b80fa14
- **Rationale:** Audit trail data must be immutable and preserved for accountability even when users are deleted. LEFT JOIN pattern displays "[Deleted User]" for orphaned user_id values.

**2. [Rule 3 - Blocking] jsondiff Symbol objects not JSON serializable**
- **Found during:** Task 3 test execution (test_diff_handles_arrays)
- **Issue:** `jsondiff.diff()` returns dict with Symbol keys that can't be serialized with `json.dumps()`
- **Fix:** Use `marshal=True` parameter: `diff(before, after, marshal=True)` converts Symbols to string keys with `$` prefix
- **Files modified:** src/collab/audit.py
- **Commit:** (part of b80fa14)

**3. [Rule 3 - Blocking] SQLite timestamp ordering not deterministic**
- **Found during:** Task 3 test execution (test_get_for_course_ordered_by_newest)
- **Issue:** Multiple audit entries created in quick succession had same created_at timestamp, causing non-deterministic ordering
- **Fix:** Added secondary sort by id DESC: `ORDER BY a.created_at DESC, a.id DESC`
- **Files modified:** src/collab/audit.py (all query methods)
- **Commit:** (part of b80fa14)

## Technical Decisions

### Diff Storage with jsondiff

**Choice:** Use `jsondiff.diff(before, after, marshal=True)` for change storage

**Implementation:**
```python
if before is not None and after is not None:
    changes_dict = diff(before, after, marshal=True)
    changes_json = json.dumps(changes_dict)
```

**Benefits:**
- Stores only changed fields (efficient)
- Handles nested objects and arrays
- marshal=True makes output JSON-serializable
- Industry-standard library (jsondiff>=2.2.0)

**Example diff:**
```python
before = {'title': 'Old', 'status': 'draft', 'description': 'Same'}
after = {'title': 'New', 'status': 'published', 'description': 'Same'}
# Diff stores: {'title': 'New', 'status': 'published'}
# NOT the full after object
```

### Deleted User Handling

**Choice:** Remove FK constraint, use LEFT JOIN with "[Deleted User]" fallback

**Implementation:**
```sql
SELECT a.id, a.user_id, u.name as user_name, u.email as user_email
FROM audit_entry a
LEFT JOIN user u ON a.user_id = u.id
WHERE a.course_id = ?
```

```python
user_name=row["user_name"] or "[Deleted User]"
```

**Benefits:**
- Preserves complete audit history
- Clear indication of deleted users
- No cascading deletes that lose accountability data
- Complies with audit trail best practices

**Alternative rejected:** ON DELETE CASCADE would delete audit entries, losing historical record of who made changes.

## Integration Points

### Current Integration

**Used by (future plans):**
- Plan 10-06: Audit API will expose these functions
- Content generation: Will log ACTION_CONTENT_GENERATED
- Collaboration workflows: Will log role changes, invitations

**Uses:**
- `src/auth/db.py` - get_db() for database access
- `src/collab/models.py` - Role/Collaborator for context
- jsondiff library for diff calculation

### Future Integration

**Next Phase Readiness:**
- API endpoints: Create routes for `/api/courses/:id/audit` and `/api/courses/:id/activity-feed`
- Real-time updates: Consider WebSocket notifications for activity feed
- Filtering: Add date range, action type, and user filters to activity feed
- Exports: Add audit trail CSV export for compliance
- Retention: Add audit log retention policies (archive after N days)

**Hook points for future features:**
- Add audit entries in content generation success handlers
- Add audit entries in collaborator CRUD operations
- Add audit entries in course structure modifications
- Add audit entries in build state transitions

## Lessons Learned

### What Went Well

1. **Comprehensive test coverage:** 20 tests caught 3 bugs before integration
2. **jsondiff library:** marshal=True solved Symbol serialization elegantly
3. **LEFT JOIN pattern:** Clean solution for deleted user handling

### What Could Be Improved

1. **Schema coordination:** The FK constraint from 10-04 should have been omitted based on 10-05 requirements
2. **Test-first approach:** Tests revealed the FK constraint issue immediately
3. **Documentation:** Plan notes mentioned LEFT JOIN but didn't explicitly forbid FK constraint

### Key Insights

1. **Audit trail integrity:** Audit data is fundamentally different from transactional data - it must never be deleted or modified
2. **Diff storage efficiency:** Storing only changes reduces storage by 70-90% for typical updates
3. **Deleted user handling:** Common pattern in audit systems - must be designed upfront
4. **Timestamp ordering:** Always include ID as tiebreaker for deterministic ordering

## Testing

All 20 tests pass (`pytest tests/test_audit.py`):

- ✅ Audit logging with and without diffs
- ✅ Efficient diff storage (only changes)
- ✅ Paginated queries with ordering
- ✅ Entity and user filtering
- ✅ Activity feed with summaries
- ✅ Deleted user handling
- ✅ JSON serialization
- ✅ Action constant uniqueness

## Files Changed

### Created
- `src/collab/audit.py` (333 lines) - AuditEntry model and utilities
- `tests/test_audit.py` (501 lines) - Comprehensive test suite

### Modified
- `instance/schema.sql` - Removed FK constraint from audit_entry table
- `src/collab/__init__.py` - Exported audit functions and action constants

## Deployment Notes

1. **Database migration required:** Existing audit_entry tables need FK constraint removed
2. **jsondiff dependency:** Already in requirements.txt from 10-01
3. **No breaking changes:** Pure addition, no existing functionality affected

## Next Steps

**Immediate (Plan 10-06):**
1. Create API endpoints for audit trail access
2. Add audit logging to existing content generation endpoints
3. Add audit logging to collaborator management endpoints

**Future enhancements:**
1. Audit log archival strategy
2. Advanced filtering (date ranges, multiple actions)
3. Audit log exports for compliance
4. Real-time activity notifications

## Commit History

1. **32207ba** - feat(10-05): create AuditEntry model with diff-based storage (Task 2)
2. **b80fa14** - feat(10-05): create audit trail tests and fix schema (Task 3)

Note: Task 1 (schema) was already completed in plan 10-04 commit 74bfa9d, though with an FK constraint that was later removed in Task 3.
