---
phase: 03-blueprint-generation
plan: 03
subsystem: api
tags: [flask, blueprint-api, rest, pydantic, anthropic, ai-generation]

# Dependency graph
requires:
  - phase: 03-blueprint-generation
    plan: 01
    provides: BlueprintGenerator with Pydantic schemas (CourseBlueprint, ModuleBlueprint, LessonBlueprint, ActivityBlueprint)
  - phase: 03-blueprint-generation
    plan: 02
    provides: CourseraValidator for blueprint validation and blueprint_to_course converter
provides:
  - Flask Blueprint with 3 API endpoints: generate, accept, refine
  - Review-before-commit workflow for AI-generated course structures
  - 13 integration tests covering success paths, error handling, and validation
affects: [04-activity-generation, frontend-ui, user-workflows]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Flask Blueprint registration pattern (init function + module-level _project_store)"
    - "Review-before-commit workflow (generate → validate → accept)"
    - "AI error handling with 502/503 status codes"

key-files:
  created:
    - src/api/blueprint.py
    - tests/test_blueprint_api.py
  modified:
    - app.py

key-decisions:
  - "Blueprint endpoints follow review-before-commit workflow: generate returns proposal, accept commits to course structure"
  - "Validation runs twice: at generation (informational) and at acceptance (blocking)"
  - "Refine endpoint rebuilds prompt with previous blueprint + feedback context"
  - "AI unavailable (no API key) returns 503, AI errors return 502"

patterns-established:
  - "API endpoint error handling: 400 (bad input), 404 (not found), 422 (validation failed), 502 (AI error), 503 (AI unavailable)"
  - "Mock strategy for AI tests: patch BlueprintGenerator at module level, return make_test_blueprint() fixture"

# Metrics
duration: 7min
completed: 2026-02-04
---

# Phase 03 Plan 03: Blueprint API Summary

**Flask Blueprint with generate/accept/refine endpoints implementing review-before-commit workflow for AI-generated course structures**

## Performance

- **Duration:** 7 min
- **Started:** 2026-02-04T02:11:12Z
- **Completed:** 2026-02-04T02:19:02Z
- **Tasks:** 3
- **Files modified:** 3
- **Tests added:** 13
- **Total test count:** 180 (167 baseline + 13 new)

## Accomplishments

- Three API endpoints for blueprint workflow: POST /api/courses/<id>/blueprint/generate, /accept, /refine
- Review-before-commit pattern: blueprints are proposals until explicitly accepted by user
- Validation feedback provided at generation time, enforced at acceptance time
- 13 comprehensive integration tests covering success paths, error handling, and edge cases
- Zero regressions - all 167 existing tests still passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Blueprint API Flask Blueprint** - `8b000b6` (feat)
2. **Task 2: Register Blueprint API in app.py** - `769a53d` (feat)
3. **Task 3: Create integration tests for Blueprint API** - `6914b9a` (test)

## Files Created/Modified

- `src/api/blueprint.py` - Flask Blueprint with generate, accept, and refine endpoints
  - generate: Creates blueprint proposal with AI, returns validation feedback
  - accept: Validates and applies blueprint to course structure
  - refine: Regenerates blueprint with user feedback in prompt context
- `tests/test_blueprint_api.py` - 13 integration tests with AI mocking
- `app.py` - Blueprint registration following existing pattern

## Decisions Made

**1. Review-before-commit workflow**
- Blueprints are proposals, not immediately saved to course
- User sees validation feedback and can refine before accepting
- Accept endpoint enforces validation (422 if errors present)

**2. Validation runs twice**
- At generate: returns validation results (informational, non-blocking)
- At accept: enforces validation (blocks with 422 if errors present)
- Enables user to see issues and refine before committing

**3. Refine endpoint prompt strategy**
- Includes previous blueprint as JSON context
- Adds user feedback as refinement instructions
- Maintains original course description and outcomes
- Uses same structured output schema as generate

**4. Error handling strategy**
- 400: Bad request (missing/invalid input)
- 404: Course not found
- 422: Validation failed (blueprint has errors)
- 502: AI API error (anthropic exception)
- 503: AI not available (no API key)

**5. Test mocking strategy**
- Mock Config.ANTHROPIC_API_KEY for tests requiring AI unavailable
- Mock BlueprintGenerator class at src.api.blueprint module level
- Use make_test_blueprint() fixture for consistent test data
- Set target_duration_minutes on courses to match test blueprint (90 min)

## Deviations from Plan

None - plan executed exactly as written.

All endpoints implemented as specified:
- generate: AI generation with validation feedback
- accept: Validation enforcement and course structure application
- refine: Feedback-driven regeneration

All error handling, validation logic, and test coverage matches plan requirements.

## Issues Encountered

**1. Test fixture initialization**
- **Issue:** Initial tests missing learning_outcomes_bp initialization in fixture
- **Resolution:** Added init_learning_outcomes_bp to test fixture (followed existing pattern from other API tests)

**2. Mock timing**
- **Issue:** Config.ANTHROPIC_API_KEY check runs before mocks can be applied
- **Resolution:** Mock Config.ANTHROPIC_API_KEY at start of test functions (before creating course)

**3. Validation target_duration matching**
- **Issue:** Validator checks blueprint duration within 20% of course.target_duration_minutes
- **Resolution:** Set target_duration_minutes: 90 on test courses to match test blueprint (90.0 min)

All issues were standard test setup problems, resolved by following existing patterns.

## User Setup Required

None - no external service configuration required. API key configuration is handled by existing .env setup from Phase 2.

## Next Phase Readiness

**Ready for Phase 04 (Activity Generation):**
- Blueprint API provides course structure creation endpoint
- Accept endpoint creates modules/lessons/activities with BuildState.DRAFT
- Activity IDs are generated and saved to course
- Phase 04 can load courses and generate content for draft activities

**Integration points established:**
- Course structure in place with empty draft activities
- Activity IDs available for content generation targeting
- Validation ensures structure meets Coursera requirements

**No blockers.**

---
*Phase: 03-blueprint-generation*
*Completed: 2026-02-04*
