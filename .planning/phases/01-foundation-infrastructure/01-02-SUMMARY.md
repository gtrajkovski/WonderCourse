---
phase: 01-foundation-infrastructure
plan: 02
subsystem: data-models
tags: [python, dataclasses, serialization, schema-evolution, tdd]

# Dependency graph
requires:
  - phase: 01-01
    provides: Project directory structure and configuration foundation
provides:
  - Core data models (Course, Module, Lesson, Activity, LearningOutcome, TextbookChapter)
  - Complete serialization support with to_dict/from_dict
  - Schema evolution tolerance via unknown field filtering
  - 5 enums for content type, build state, Bloom's taxonomy
affects: [01-03-ai-client, 01-04-flask-app, all-future-phases]

# Tech tracking
tech-stack:
  added: [dataclasses, uuid, datetime, enum]
  patterns:
    - "Recursive serialization for nested object trees"
    - "Schema evolution via __dataclass_fields__ filtering"
    - "Default ID generation with typed prefixes"
    - "TDD with RED-GREEN-REFACTOR cycle"

key-files:
  created:
    - src/core/models.py
    - tests/test_models.py
  modified: []

key-decisions:
  - "Use uuid4 hex prefix pattern for default IDs (act_, les_, mod_, lo_, ch_, course_)"
  - "Store timestamps as ISO format strings for JSON compatibility"
  - "Enum deserialization falls back to first enum value for invalid inputs"
  - "Defensive dict copying in from_dict to prevent mutation side effects"

patterns-established:
  - "to_dict: Convert enums to .value strings, recursively serialize nested lists"
  - "from_dict: Pop nested lists, filter to known fields, reconstruct nested objects"
  - "All dataclasses have created_at/updated_at ISO timestamps"
  - "Optional fields use None default, lists use field(default_factory=list)"

# Metrics
duration: 4min
completed: 2026-02-02
---

# Phase 01 Plan 02: Core Data Models Summary

**6 dataclasses with recursive serialization supporting full course hierarchy from Activity through Lesson/Module to Course**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-02T14:21:37Z
- **Completed:** 2026-02-02T14:25:20Z
- **Tasks:** 1 (TDD task with 2 commits)
- **Files modified:** 2
- **Tests:** 28 passing

## Accomplishments

- Implemented complete data model hierarchy: Course → Module → Lesson → Activity
- Full round-trip serialization with schema evolution support (unknown fields ignored)
- 5 enums: ContentType (10 values), ActivityType (11 values), BuildState (6 values), BloomLevel (6 values), WWHAAPhase (6 values)
- TDD approach with comprehensive test coverage (28 tests covering all edge cases)
- LearningOutcome with ABCD model and Bloom's taxonomy integration
- TextbookChapter with sections and glossary support

## Task Commits

TDD cycle with 2 atomic commits:

1. **RED Phase: Failing tests** - `6ce4040` (test)
   - 28 comprehensive tests covering all dataclasses, enums, serialization, schema evolution
   - Tests for default ID generation patterns, timestamp formats, nested object round-trips
   - Edge cases: unknown fields, missing optional fields, invalid enum values

2. **GREEN Phase: Implementation** - `4645163` (feat)
   - All 6 dataclasses with complete to_dict/from_dict methods
   - All 5 enums with correct values
   - Recursive serialization for nested object trees
   - Schema evolution support via __dataclass_fields__ filtering
   - Default ID generation with uuid4 hex patterns
   - ISO timestamp generation with datetime.now().isoformat()

**No REFACTOR phase needed** - code was clean on first implementation following ScreenCast Studio pattern exactly.

## Files Created/Modified

- `src/core/models.py` - Core data models with 6 dataclasses and 5 enums (420 lines)
  - Activity: Atomic content unit with WWHAA phase, content type, build state
  - Lesson: Container for activities with order tracking
  - Module: Container for lessons forming course units
  - LearningOutcome: ABCD model with Bloom's taxonomy and activity mapping
  - TextbookChapter: Sections and glossary for supplemental reading
  - Course: Root container with modules, learning outcomes, textbook chapters

- `tests/test_models.py` - Comprehensive test suite (495 lines)
  - 5 test classes for enums (verify all values exist)
  - 6 test classes for dataclasses (default creation, round-trip serialization)
  - Schema evolution tests (unknown fields, missing optional fields)
  - Enum deserialization tests (string to enum, invalid value fallback)
  - ID generation pattern tests (prefix and length verification)
  - Timestamp format tests (ISO format validation)

## Decisions Made

**1. ID Generation Pattern**
- Rationale: Typed prefixes (act_, les_, mod_, etc.) make IDs self-documenting and enable type identification from ID alone
- Implementation: field(default_factory=lambda: f"prefix_{uuid.uuid4().hex[:8]}")
- Impact: All future code can identify object type from ID prefix

**2. Timestamp Storage as Strings**
- Rationale: ISO format strings serialize to JSON without conversion, cross-language compatible
- Implementation: field(default_factory=lambda: datetime.now().isoformat())
- Impact: Direct JSON serialization without custom encoders

**3. Enum Deserialization Fallback**
- Rationale: Schema evolution tolerance - old data with removed enum values won't crash
- Implementation: try/except ValueError with fallback to first enum value
- Impact: Backward compatibility when enum values change

**4. Known Field Filtering**
- Rationale: Forward compatibility - adding new fields won't break older code reading data
- Implementation: filtered = {k: v for k, v in data.items() if k in known}
- Impact: Seamless schema evolution without migration scripts

## Deviations from Plan

None - plan executed exactly as written.

TDD approach followed perfectly:
- RED phase: Wrote 28 comprehensive tests, all failed (ModuleNotFoundError)
- GREEN phase: Implemented all models, all 28 tests passed
- REFACTOR phase: Not needed - code was clean on first implementation

Pattern matched ScreenCast Studio models.py exactly as specified in plan.

## Issues Encountered

None - implementation was straightforward following the reference pattern.

## User Setup Required

None - no external service configuration required.

Data models are pure Python with standard library dependencies only.

## Next Phase Readiness

**Ready for 01-03 (AI Client Wrapper):**
- All data models available for import
- Course, Module, Lesson, Activity ready for AI content generation
- to_dict/from_dict methods ready for JSON serialization in API responses
- LearningOutcome ready for curriculum planning features
- TextbookChapter ready for supplemental content generation

**Ready for 01-04 (Flask Application):**
- All models ready for API endpoint responses
- Serialization methods ready for JSON API payloads
- BuildState enum ready for workflow management
- ActivityType and ContentType enums ready for content filtering

**Blockers:** None

**Prerequisites for next plan:**
- Anthropic API key needed in .env for AI client (already documented in 01-01)

---
*Phase: 01-foundation-infrastructure*
*Completed: 2026-02-02*
