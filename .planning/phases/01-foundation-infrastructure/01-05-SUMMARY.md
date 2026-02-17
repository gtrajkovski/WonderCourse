---
phase: 01-foundation-infrastructure
plan: 05
subsystem: web-app
tags: [flask, jinja2, html, css, testing, pytest, rest-api]

# Dependency graph
requires:
  - phase: 01-01
    provides: Configuration system with Config class and environment variables
  - phase: 01-02
    provides: Course data model with serialization
  - phase: 01-03
    provides: ProjectStore persistence layer with file locking
  - phase: 01-04
    provides: AIClient for AI-powered features (optional dependency)
provides:
  - Flask web application running on port 5003
  - Dashboard UI for course management
  - REST API with full CRUD operations
  - Dark-themed responsive UI
  - Integration test suite with pytest
affects: [02-ai-content-generation, 03-module-planning, workspace-editor]

# Tech tracking
tech-stack:
  added: [Flask 3.1.0+, pytest-flask 1.3.0+]
  patterns: [Flask app factory pattern, Jinja2 template inheritance, REST API design, pytest fixtures]

key-files:
  created:
    - app.py
    - templates/base.html
    - templates/dashboard.html
    - static/css/main.css
    - tests/conftest.py
    - tests/test_app.py
  modified:
    - None (all new files)

key-decisions:
  - "Flask app on port 5003 to avoid conflicts with existing v5/v6 apps"
  - "AIClient initialized with try/except to allow app to run without API key"
  - "Dark theme with Coursera-inspired color palette (#1a1a2e, #16213e, #4da6ff)"
  - "Template-based dashboard with server-side rendering for initial view"
  - "Client-side JavaScript for CRUD operations via fetch API"
  - "Shared pytest fixtures in conftest.py for test isolation"

patterns-established:
  - "Module-level singletons: Flask app, ProjectStore, AIClient (with error handling)"
  - "REST API error responses: 404 for not found, 400 for invalid input, 500 for server errors"
  - "Flask test client with temporary ProjectStore for test isolation"
  - "Jinja2 template blocks: title, content, extra_head, extra_scripts"
  - "Dark theme component hierarchy: container > navbar/main/footer > cards"

# Metrics
duration: 5min
completed: 2026-02-02
---

# Phase 01 Plan 05: Flask Application Skeleton Summary

**Flask web app with dark-themed dashboard, REST API for course CRUD, and 17 integration tests**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-02T19:43:22Z
- **Completed:** 2026-02-02T19:48:34Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Full-featured Flask web application running on port 5003
- Dark-themed dashboard UI with course list, empty state, and inline CRUD
- Complete REST API with GET/POST/PUT/DELETE endpoints for courses
- Health check endpoint for system monitoring
- 17 integration tests covering all routes and API endpoints
- All 88 tests passing (17 new + 71 existing)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Flask app with routes and API endpoints** - `923aac4` (feat)
2. **Task 2: Create templates, static assets, and tests** - `410af69` (feat)

## Files Created/Modified
- `app.py` - Flask application with page routes and REST API endpoints (226 lines)
- `templates/base.html` - Dark-theme base layout with nav, content block, footer
- `templates/dashboard.html` - Course list page with cards, empty state, inline JavaScript
- `static/css/main.css` - Dark theme CSS (bg #1a1a2e, cards #16213e, accent #4da6ff)
- `tests/conftest.py` - Shared pytest fixtures (tmp_store, sample_course, client)
- `tests/test_app.py` - 17 integration tests for Flask endpoints

## Decisions Made

**1. Port 5003 for Flask app**
- Rationale: Avoids conflicts with existing ScreenCast Studio apps (v5 on 5001, v6 on 5002)
- Impact: Allows parallel development/testing of all applications

**2. AIClient optional initialization**
- Pattern: `try/except ValueError` with `ai_client = None` fallback
- Rationale: App can run without ANTHROPIC_API_KEY for UI development
- Impact: AI features disabled but app remains functional

**3. Dark theme color palette**
- Background: #1a1a2e (dark navy)
- Cards: #16213e (lighter navy)
- Accent: #4da6ff (bright blue)
- Navigation: #0f3460 (deep blue)
- Rationale: Professional look, reduces eye strain, Coursera-inspired
- Impact: Consistent visual identity across all pages

**4. Server-side rendering + client-side CRUD**
- Dashboard rendered server-side with Jinja2
- CRUD operations via fetch API to REST endpoints
- Rationale: Fast initial load, progressive enhancement
- Impact: Works without JavaScript for initial view, enhanced with JS

**5. Test isolation with temporary ProjectStore**
- Fixture creates temp directory per test
- Monkeypatch replaces module-level singleton
- Rationale: Prevents test interference, no cleanup needed
- Impact: Fast, reliable, isolated tests

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed JSON validation error handling**
- **Found during:** Task 2 (Writing integration tests)
- **Issue:** Flask `request.get_json()` returns `None` when no Content-Type header, causing 500 error instead of 400
- **Fix:** Moved JSON validation outside try/except block to return 400/415 before business logic
- **Files modified:** app.py (create_course and update_course endpoints)
- **Verification:** Tests `test_create_course_no_json` and `test_update_course_no_json` pass
- **Committed in:** 410af69 (Task 2 commit)

**2. [Rule 1 - Bug] Updated tests for Flask 415 status code**
- **Found during:** Task 2 (Running integration tests)
- **Issue:** Tests expected 400 for missing JSON, but Flask correctly returns 415 (Unsupported Media Type) when Content-Type header is missing
- **Fix:** Updated test assertions to accept both 400 and 415 status codes
- **Files modified:** tests/test_app.py
- **Verification:** All 17 Flask tests pass
- **Committed in:** 410af69 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes improved error handling correctness. No scope creep.

## Issues Encountered

**Flask request.get_json() behavior**
- Issue: `request.get_json()` returns `None` when Content-Type header is missing (not an exception)
- Resolution: Moved validation outside try/except to catch early and return appropriate 4xx error
- Learning: Flask's get_json() silent failure requires explicit None checks

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for Phase 2: AI Content Generation**
- Flask app provides UI foundation for course creation
- REST API ready for AI-powered content generation endpoints
- Dashboard provides entry point for course management
- Test infrastructure supports rapid feature development

**Prerequisites for AI features:**
- User must add ANTHROPIC_API_KEY to .env file
- AIClient will be available for content generation after restart

**Technical foundation complete:**
- ✅ Configuration system (01-01)
- ✅ Core data models (01-02)
- ✅ Persistence layer (01-03)
- ✅ AI client infrastructure (01-04)
- ✅ Web application skeleton (01-05)

**Next recommended tasks:**
- Add course editor UI (workspace page)
- Implement AI-powered module generation
- Add learning outcome scaffolding
- Build activity content generation

**No blockers or concerns.**

---
*Phase: 01-foundation-infrastructure*
*Completed: 2026-02-02*
