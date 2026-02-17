---
phase: 09-user-authentication
plan: 05
status: complete
---

## Summary

Modified ProjectStore to namespace courses by user_id, fulfilling AUTH-05 requirement for complete course isolation between users.

## What Was Done

### Task 1: Update ProjectStore for user scoping
- Added `_user_dir(self, user_id: str) -> Path` method for user directory management
- Updated `_course_dir()` and `_course_file()` to include user_id in path
- Updated all public methods to require user_id as first parameter:
  - `save(self, user_id: str, course: Course) -> Path`
  - `load(self, user_id: str, course_id: str) -> Optional[Course]`
  - `list_courses(self, user_id: str) -> List[dict]`
  - `delete(self, user_id: str, course_id: str) -> bool`
- Added path traversal protection via `_sanitize_id()`

### Task 2: Update all API blueprints to pass user_id
- Updated all ProjectStore calls to include current_user.id:
  - app.py: get_courses, create_course, get_course, update_course, delete_course
  - src/api/modules.py: all module CRUD operations
  - src/api/lessons.py: all lesson CRUD operations
  - src/api/activities.py: all activity CRUD operations
  - src/api/learning_outcomes.py: all outcome operations
  - src/api/blueprint.py: generate, accept, refine
  - src/api/content.py: generate, regenerate, update
  - src/api/build_state.py: progress, state transitions
  - src/api/textbook.py: textbook operations
  - src/api/validation.py: validate, publishable
  - src/api/export.py: preview and download endpoints

### Task 3: Create user isolation tests
- Created tests/test_user_isolation.py with 9 tests:
  - TestUserIsolation: 5 API-level isolation tests
  - TestProjectStoreUserScoping: 4 unit tests for storage layer

## Test Results

```
tests/test_user_isolation.py: 9 passed
```

## Verification

- [x] ProjectStore creates directories under projects/{user_id}/
- [x] User A cannot see or access User B's courses
- [x] All existing tests pass with updated signatures
- [x] User isolation tests pass
- [x] Course list only shows current user's courses

## New Directory Structure

```
projects/
  {user_id}/
    {course_id}/
      course_data.json
      exports/
      textbook/
```

## Files Modified

- src/core/project_store.py
- app.py
- src/api/modules.py
- src/api/lessons.py
- src/api/activities.py
- src/api/learning_outcomes.py
- src/api/blueprint.py
- src/api/content.py
- src/api/build_state.py
- src/api/textbook.py
- src/api/validation.py
- src/api/export.py
- tests/test_user_isolation.py (created)

## Requirements Satisfied

- AUTH-05: Per-user course isolation
