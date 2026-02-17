# 06-05 Summary: Textbook API Endpoints

## Completed

### Task 1: Update TextbookChapter model and create textbook API blueprint

**Model updates (src/core/models.py):**
- Added `image_placeholders: List[Dict[str, str]]` field
- Added `references: List[Dict[str, str]]` field
- Added `coherence_issues: List[str]` field
- Updated `to_dict()` to include all 3 new fields

**API blueprint (src/api/textbook.py):**
- Created `textbook_bp` Blueprint with `init_textbook_bp(project_store)` pattern
- `POST /api/courses/<id>/textbook/generate` - Returns 202 with task_id for async generation
- `GET /api/jobs/<task_id>` - Returns job status with progress, current_step, result
- `_generate_with_progress()` background function orchestrates:
  1. TextbookGenerator.generate_chapter() with progress_callback
  2. CoherenceValidator.check_consistency() for post-generation quality checks
  3. TextbookChapter creation and save to course.textbook_chapters
  4. JobTracker updates at each step (pending -> running -> completed/failed)

**Blueprint registration (app.py):**
- Added import and registration for textbook_bp

### Task 2: Write textbook API integration tests

**Created tests/test_textbook_api.py with 10 tests:**
1. `test_generate_textbook_returns_202_with_task_id` - Verifies async response
2. `test_generate_textbook_requires_learning_outcome_id` - 400 validation
3. `test_generate_textbook_404_for_missing_course` - Course not found
4. `test_generate_textbook_404_for_missing_outcome` - Outcome not found
5. `test_get_job_status` - Job status polling works
6. `test_get_job_status_404` - Unknown task_id returns 404
7. `test_textbook_chapter_saved_to_course` - Chapter persisted correctly
8. `test_job_transitions_to_completed` - Status lifecycle verified
9. `test_job_transitions_to_failed_on_error` - Error handling works
10. `test_updated_textbook_chapter_model` - Model fields verified

**Updated tests/conftest.py:**
- Added `init_textbook_bp` to client fixture initialization

## Verification

- `py -c "from src.api.textbook import textbook_bp, init_textbook_bp; print('OK')"` ✅
- `py -c "from src.core.models import TextbookChapter; ch = TextbookChapter(); d = ch.to_dict(); assert 'image_placeholders' in d"` ✅
- All 10 new tests pass ✅
- All 354 tests pass (including existing 344) ✅

## Files Modified

- `src/core/models.py` - Added 3 fields to TextbookChapter, updated to_dict()
- `src/api/textbook.py` - New file (165 lines)
- `app.py` - Added textbook blueprint registration
- `tests/test_textbook_api.py` - New file (10 tests)
- `tests/conftest.py` - Added textbook blueprint initialization

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Background thread with daemon=False | Ensures generation completes even if request terminates |
| Progress callback wired to JobTracker | Decouples generator from job tracking infrastructure |
| Re-load course before save | Prevents stale state issues in async context |
| Synchronous thread mock in tests | Deterministic testing without sleep/polling |

## Phase 6 Status

**Completed:** 5/5 plans (Phase complete!)
- 06-01: Textbook Schemas ✅
- 06-02: Job Tracker ✅
- 06-03: Textbook Chapter Generator ✅
- 06-04: Coherence Validator ✅
- 06-05: Textbook API Endpoints ✅
