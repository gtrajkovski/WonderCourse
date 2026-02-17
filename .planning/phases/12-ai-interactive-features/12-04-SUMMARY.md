---
phase: 12-ai-interactive-features
plan: 04
subsystem: import
tags: [ai, content-conversion, claude, structured-output, wwhaa, import]

# Dependency graph
requires:
  - phase: 12-01
    provides: Import parsers and format detection
  - phase: 12-03
    provides: ImportPipeline and ContentAnalyzer
provides:
  - AI-powered content conversion (plain text to structured formats)
  - ContentConverter with convert() and suggest_type() methods
  - Conversion endpoints in import blueprint
  - Support for VIDEO (WWHAA), READING, QUIZ formats
affects: [12-frontend, export, content-generation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Claude structured outputs for format conversion
    - Tool-based structured output pattern
    - Keyword-based content type detection
    - Confidence scoring for AI conversions

key-files:
  created:
    - src/import/converter.py
    - tests/test_import_converter.py
  modified:
    - src/import/__init__.py
    - src/api/import_bp.py

key-decisions:
  - "Keyword-based suggest_type() for quick content type detection without AI call"
  - "Confidence scoring based on content length and structure completeness"
  - "Support only VIDEO, READING, QUIZ for conversion (not all 11 content types)"
  - "Activity-specific conversion saves directly to course structure"

patterns-established:
  - "ContentConverter follows BaseGenerator pattern with structured outputs"
  - "ConversionResult dataclass tracks original, structured, confidence, changes"
  - "Change documentation provides transparency into AI transformations"

# Metrics
duration: 10min
completed: 2026-02-11
---

# Phase 12 Plan 04: AI Content Converter Summary

**AI-powered plain text conversion to WWHAA video scripts, structured readings, and MCQ quizzes using Claude structured outputs**

## Performance

- **Duration:** 10 min
- **Started:** 2026-02-11T04:33:07Z
- **Completed:** 2026-02-11T04:42:27Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- ContentConverter with AI-powered format conversion for VIDEO, READING, QUIZ
- Keyword-based suggest_type() for instant content type detection
- Three conversion endpoints added to import blueprint
- Comprehensive test suite with 17 tests (all passing)
- Confidence scoring and change documentation for transparency

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ContentConverter with structured output** - `94ff972` (feat)
   - ContentConverter class with convert(), suggest_type() methods
   - to_video_script(), to_reading(), to_quiz() conversion methods
   - ConversionResult dataclass with confidence and changes tracking
   - Keyword-based content type detection

2. **Task 2: Add conversion endpoints to import blueprint** - `df25bca` (feat)
   - POST /api/import/convert endpoint
   - GET/POST /api/import/suggest-type endpoint
   - POST /api/courses/<id>/activities/<id>/convert endpoint
   - 17 comprehensive tests with mocked Anthropic API

## Files Created/Modified

- `src/import/converter.py` - ContentConverter with AI-powered format conversion
- `src/import/__init__.py` - Export ContentConverter and ConversionResult
- `src/api/import_bp.py` - Added conversion endpoints to existing import blueprint
- `tests/test_import_converter.py` - 17 tests covering all conversion types

## Decisions Made

**1. Keyword-based suggest_type() for quick detection**
- Rationale: Avoids unnecessary AI API calls for obvious content patterns
- Pattern detection: MCQ questions (? + A/B/C/D), WWHAA keywords, long paragraphs
- Fallback: Length-based heuristic (short=VIDEO, long=READING)

**2. Confidence scoring based on content characteristics**
- Base confidence 0.9, reduced for short content (<50 words: -0.2, <100 words: -0.1)
- Bonus for structure completeness (all WWHAA sections, 2-6 reading sections, 3-10 quiz questions)
- Provides transparency into AI conversion quality

**3. Limited to VIDEO, READING, QUIZ conversion**
- Rationale: These three are most common for imported content
- Other content types (HOL, Coach, Lab, etc.) require more specialized structure
- Raises ValueError for unsupported types

**4. Activity-specific conversion saves directly**
- /api/courses/<id>/activities/<id>/convert endpoint
- Reads activity's content_type to determine target format
- Updates activity.content and build_state automatically
- Logs audit entry for tracking

## Deviations from Plan

**Auto-fixed Issues:**

**1. [Rule 3 - Blocking] Import keyword conflict in test file**
- **Found during:** Task 2 (running tests)
- **Issue:** `from src.import.converter` syntax error - `import` is Python keyword
- **Fix:** Used `importlib.import_module('src.import')` pattern in test imports
- **Files modified:** tests/test_import_converter.py
- **Verification:** All 17 tests pass
- **Committed in:** df25bca (part of Task 2 commit)

**2. [Rule 3 - Blocking] Import keyword conflict in import_bp.py initialization**
- **Found during:** Task 2 (linter auto-fix)
- **Issue:** Direct import of ContentConverter would cause syntax error
- **Fix:** Linter applied importlib pattern in init_import_bp()
- **Files modified:** src/api/import_bp.py
- **Verification:** Import blueprint initializes correctly
- **Committed in:** df25bca (part of Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both fixes necessary to work around Python's `import` keyword in package name. No functional changes to planned features.

## Issues Encountered

None - plan executed smoothly with only keyword-related import fixes.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for:**
- Frontend integration to show conversion UI
- Export functionality to include converted content
- Content editing with converted structures

**Delivered capabilities:**
- Plain text → WWHAA video script conversion
- Plain text → structured reading conversion
- Plain text → MCQ quiz conversion
- Content type suggestion for ambiguous inputs
- Activity-targeted conversion with automatic saving

**Quality assurance:**
- 17 tests cover all conversion types and edge cases
- Mocked Anthropic API prevents flaky tests
- Confidence scoring provides quality transparency
- Change documentation shows what AI modified

---
*Phase: 12-ai-interactive-features*
*Completed: 2026-02-11*
