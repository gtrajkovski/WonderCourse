---
phase: 01-foundation-infrastructure
plan: 03
subsystem: persistence
tags: [file-locking, disk-persistence, json-serialization, security, path-traversal, concurrency]

requires:
  - 01-02  # Course/Module/Lesson/Activity models with to_dict/from_dict

provides:
  - ProjectStore class for disk persistence
  - File locking mechanism for concurrent write safety
  - Path traversal protection
  - Subdirectory auto-creation (exports/, textbook/)
  - Sorted course listing by updated_at

affects:
  - 01-04  # AI client will need ProjectStore for conversation persistence
  - Future phases that need to save/load courses

tech-stack:
  added:
    - Lock file mechanism (cross-platform)
  patterns:
    - Repository pattern for data persistence
    - Path sanitization for security
    - Automatic timestamp management

key-files:
  created:
    - src/core/project_store.py  # 238 lines
    - tests/test_project_store.py  # 336 lines
  modified: []

decisions:
  - id: lock-file-approach
    choice: Lock file mechanism instead of platform-specific file locks
    rationale: "msvcrt.locking on Windows has limitations (requires r+ mode, locks bytes not files). Lock file approach is simpler, portable, and easier to debug."
    alternatives:
      - Platform-specific locks (fcntl on Unix, msvcrt on Windows)
      - Database-style lock table
    impact: Lock files (.lock) appear temporarily in project directories

  - id: subdirectories
    choice: Auto-create exports/ and textbook/ on save
    rationale: Proactive directory creation simplifies downstream code (generators won't need to check/create directories)
    alternatives:
      - Lazy creation when first needed
      - Explicit setup method
    impact: Empty subdirectories exist immediately after course creation

  - id: timestamp-auto-update
    choice: Automatically update updated_at on every save
    rationale: Ensures accurate tracking of course modifications without manual intervention
    alternatives:
      - Manual timestamp management by caller
      - Track separate modified_at vs saved_at
    impact: Timestamp reflects last save time, not last logical edit

metrics:
  duration: ~4 minutes
  completed: 2026-02-02
---

# Phase 1 Plan 3: ProjectStore with File Locking Summary

**One-liner:** Lock file-based disk persistence for Course objects with path traversal protection and concurrent write safety.

## What Was Built

Implemented `ProjectStore` class providing complete CRUD operations for Course objects with file-based persistence:

- **save()**: Serialize Course to `projects/{id}/course_data.json`, auto-create subdirectories, update timestamp
- **load()**: Deserialize Course from JSON with None return for missing courses
- **list_courses()**: Return metadata for all courses sorted by updated_at (newest first)
- **delete()**: Remove entire course directory tree
- **_sanitize_id()**: Strip path traversal characters (/, \, ..) with ValueError on empty result
- **File locking**: Lock file mechanism prevents concurrent write corruption

### TDD Implementation

Followed RED-GREEN-REFACTOR cycle:

1. **RED**: Created 15 failing tests covering save/load round-trips, path security, concurrent writes, subdirectory creation
2. **GREEN**: Implemented ProjectStore with lock file mechanism (initial msvcrt/fcntl approach had Windows compatibility issues, refactored to lock file approach)
3. **REFACTOR**: Code already clean, no significant refactoring needed

### Key Features

**Security:**
- Path traversal protection via `_sanitize_id()` strips `/`, `\`, `..`
- Raises `ValueError` for empty/invalid IDs
- Tested against `../hack` and `a/b\c` attack patterns

**Concurrency:**
- Lock file mechanism with 50 retry attempts (10ms sleep between)
- Orphaned lock recovery after max attempts
- Tested with simultaneous thread writes - no JSON corruption

**Directory Structure:**
```
projects/
  {course_id}/
    course_data.json
    exports/
    textbook/
```

**Metadata Listing:**
Returns dict with: `id`, `title`, `description`, `module_count`, `updated_at`
Sorted by `updated_at` descending (newest first)

## Test Coverage

**15 tests, all passing:**

| Test | Coverage |
|------|----------|
| `test_save_and_load` | Round-trip preserves all nested data (Course → Module → Lesson → Activity) |
| `test_save_creates_subdirectories` | exports/ and textbook/ auto-created |
| `test_save_updates_timestamp` | updated_at changes on save |
| `test_load_nonexistent_returns_none` | Returns None for missing course |
| `test_list_courses_empty` | Empty store returns [] |
| `test_list_courses_multiple` | Correct metadata for 3 courses with different module counts |
| `test_list_courses_sorted_by_updated` | Newest course appears first |
| `test_delete_existing` | Directory tree removed completely |
| `test_delete_nonexistent_returns_false` | Returns False for missing course |
| `test_sanitize_id_strips_path_traversal` | `../hack` → `hack` |
| `test_sanitize_id_strips_slashes` | `a/b\c` → `abc` |
| `test_sanitize_id_empty_raises` | ValueError for empty string |
| `test_sanitize_id_dots_only_raises` | ValueError for `..` |
| `test_concurrent_writes_no_corruption` | Two threads writing simultaneously produce valid JSON |
| `test_course_file_path` | Correct path structure `projects/{id}/course_data.json` |

## Decisions Made

### Lock File Approach vs Platform-Specific Locks

**Chose:** Lock file mechanism (`.json.lock` files)

**Why:**
- `msvcrt.locking` on Windows requires files opened in `r+` mode (can't use `r` for reads)
- `msvcrt.locking` locks byte ranges, not whole files
- Lock files are simpler, cross-platform, and easier to debug
- Orphaned lock detection/recovery built in

**Tradeoff:** Temporary `.lock` files visible in filesystem (cleaned up automatically)

### Automatic Subdirectory Creation

**Chose:** Create `exports/` and `textbook/` on every save

**Why:**
- Downstream generators (slide generator, textbook generator) can assume directories exist
- Simplifies error handling in generator code
- Minimal cost (directories are lightweight)

**Tradeoff:** Empty directories exist immediately, slightly larger filesystem footprint

### Automatic Timestamp Update

**Chose:** Update `course.updated_at` on every save() call

**Why:**
- Accurate tracking without manual intervention
- list_courses() sorting relies on accurate timestamps
- Prevents stale timestamp bugs

**Tradeoff:** Timestamp reflects save time, not logical edit time (could differ if multiple edits before save)

## Integration Points

### Upstream Dependencies
- `src/core/models.py` - Course.to_dict() for serialization, Course.from_dict() for deserialization
- Validated with nested structure: Course → Module → Lesson → Activity with all enums preserved

### Downstream Consumers
- Plan 01-04 (AI client) will use ProjectStore for conversation history persistence
- Future web API will use ProjectStore for all course CRUD operations
- Export features will use subdirectories (exports/, textbook/) for generated content

## Next Phase Readiness

### Blockers Resolved
- ✅ Disk persistence layer complete
- ✅ Concurrent access safety implemented
- ✅ Path traversal protection verified

### Known Limitations
- Lock file approach has 50-attempt limit (500ms max wait) - could deadlock if many concurrent writers
- No transaction support (save is not atomic across multiple courses)
- No versioning/history (each save overwrites previous state)

### Recommendations
- For high-concurrency scenarios, consider database backend
- For multi-course transactions, add batch save method
- For undo/redo, add versioning layer on top of ProjectStore

## Commits

| Hash    | Message |
|---------|---------|
| 2ec9ab5 | test(01-03): add failing tests for ProjectStore |
| cecacfe | feat(01-03): implement ProjectStore with file locking |

## Artifacts

**Created:**
- `src/core/project_store.py` (238 lines) - ProjectStore implementation
- `tests/test_project_store.py` (336 lines) - 15 comprehensive tests

**File Metrics:**
- Implementation exceeds min_lines requirement (80 → 238 lines)
- Tests exceed min_lines requirement (80 → 336 lines)
- Test coverage: All public methods + security edge cases + concurrency

**Verification:**
```bash
py -3 -m pytest tests/test_project_store.py -v
# Result: 15 passed in 0.45s
```
