---
phase: 04-core-content-generation
plan: 01
subsystem: api
tags: [pydantic, anthropic, structured-outputs, content-generation, abc]

# Dependency graph
requires:
  - phase: 03-blueprint-generation
    provides: BlueprintGenerator pattern with structured outputs API
provides:
  - BaseGenerator abstract class defining interface for all content generators
  - ContentMetadata utility with deterministic duration calculations (238 WPM reading, 150 WPM video, 1.5 min/quiz)
  - VideoScriptSchema enforcing WWHAA structure (hook, objective, content, ivq, summary, cta)
  - ReadingSchema with sections and APA 7 references
  - QuizSchema with Bloom's taxonomy levels and option-level feedback
  - RubricSchema with 3-level scoring (Below/Meets/Exceeds Expectations)
affects: [04-02, 04-03, 04-04, 04-05, video-generation, reading-generation, quiz-generation, rubric-generation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ABC pattern with Generic[T] for typed schema validation"
    - "Deterministic metadata extraction from generated content"
    - "Pydantic schemas as Claude structured output contracts"
    - "3-level rubric scoring model (Below/Meets/Exceeds)"

key-files:
  created:
    - src/generators/base_generator.py
    - src/utils/content_metadata.py
    - src/generators/schemas/__init__.py
    - src/generators/schemas/video_script.py
    - src/generators/schemas/reading.py
    - src/generators/schemas/quiz.py
    - src/generators/schemas/rubric.py
    - tests/test_content_metadata.py
  modified: []

key-decisions:
  - "BaseGenerator as ABC with Generic[T] for type-safe schema validation"
  - "ContentMetadata uses industry-standard rates (238 WPM reading, 150 WPM speaking, 1.5 min/quiz)"
  - "VideoScriptSchema enforces WWHAA structure with 6 distinct section fields (not list)"
  - "QuizOption with is_correct field enables natural answer position variation"
  - "RubricSchema uses 3-level scoring (research shows clearer than 5+ levels)"

patterns-established:
  - "BaseGenerator.generate() orchestrates prompt building, API call, validation, metadata extraction"
  - "Concrete generators implement system_prompt, build_user_prompt, extract_metadata"
  - "All schemas include learning_objective field for traceability"
  - "Duration estimation rounded to 1 decimal place for consistency"

# Metrics
duration: 10min
completed: 2026-02-04
---

# Phase 4 Plan 01: Foundation Infrastructure Summary

**BaseGenerator ABC with typed schema validation, ContentMetadata utility with deterministic calculations, and 4 Pydantic schemas enforcing WWHAA structure and pedagogical best practices**

## Performance

- **Duration:** 10 min
- **Started:** 2026-02-04T03:37:38Z
- **Completed:** 2026-02-04T03:47:38Z (estimated)
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments

- BaseGenerator abstract class provides unified interface for all content generators with typed schema validation via Generic[T]
- ContentMetadata utility delivers deterministic duration calculations using industry-standard rates (238 WPM reading, 150 WPM video, 1.5 min per quiz question)
- All 4 Pydantic schemas enforce pedagogical best practices: WWHAA structure for videos, APA 7 for readings, Bloom's taxonomy for quizzes, 3-level rubric scoring
- 16 comprehensive tests for ContentMetadata covering all edge cases
- All 196 tests passing (180 existing + 16 new)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create BaseGenerator ABC and ContentMetadata utility** - `e95f80a` (feat)
   - BaseGenerator abstract class with generate(), system_prompt, build_user_prompt, extract_metadata
   - ContentMetadata with count_words, estimate_reading_duration, estimate_video_duration, estimate_quiz_duration
   - 16 tests covering all ContentMetadata methods

2. **Task 2: Create Pydantic schema models for all 4 content types** - `93b5198` (feat)
   - VideoScriptSchema with 6 WWHAA section fields (hook, objective, content, ivq, summary, cta)
   - ReadingSchema with introduction, sections, conclusion, APA 7 references
   - QuizSchema with Bloom's taxonomy levels and option-level feedback
   - RubricSchema with 3-level scoring criteria (Below/Meets/Exceeds Expectations)

## Files Created/Modified

**Created:**
- `src/generators/base_generator.py` - Abstract base class for all content generators with Generic[T] type safety
- `src/utils/content_metadata.py` - Utility for word counts and duration estimation with industry-standard rates
- `src/generators/schemas/__init__.py` - Package exports for all 4 schema types
- `src/generators/schemas/video_script.py` - VideoScriptSchema enforcing WWHAA structure with 6 distinct sections
- `src/generators/schemas/reading.py` - ReadingSchema with sections (2-6) and APA 7 references (1-5)
- `src/generators/schemas/quiz.py` - QuizSchema with Bloom's levels and QuizOption with is_correct field
- `src/generators/schemas/rubric.py` - RubricSchema with 3-level RubricCriterion and weight percentages
- `tests/test_content_metadata.py` - 16 tests covering all ContentMetadata methods and edge cases

## Decisions Made

**1. BaseGenerator as ABC with Generic[T]**
- Rationale: Type-safe schema validation via Generic[T] bound to BaseModel ensures all generators work with validated Pydantic schemas
- Pattern follows BlueprintGenerator but abstracts to support multiple content types

**2. ContentMetadata uses industry-standard rates**
- 238 WPM for reading (adult non-fiction average from research)
- 150 WPM for video (instructional speaking rate)
- 1.5 minutes per quiz question (Coursera best practice)
- Rationale: Deterministic calculations enable accurate course duration estimates

**3. VideoScriptSchema with 6 distinct fields (not list)**
- Each WWHAA phase is a separate field (hook, objective, content, ivq, summary, cta)
- Rationale: Enforces WWHAA structure at schema level - impossible to generate video without all sections

**4. QuizOption with is_correct field**
- Alternative was separate correct_answer + distractors fields
- Rationale: Natural answer position variation (correct answer not always first), simpler validation

**5. RubricSchema uses 3-level scoring**
- Below/Meets/Exceeds Expectations instead of 5-point scale
- Rationale: Research shows 3-level rubrics are clearer and more reliable than 5+ levels

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all tasks completed without blocking issues.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for Phase 4 Plans 02-05:**
- BaseGenerator ABC provides unified interface for all content generators
- ContentMetadata utility ready for metadata extraction in all generators
- All 4 Pydantic schemas validated and producing correct JSON schemas for Claude API
- Industry-standard duration calculations enable accurate course planning
- WWHAA structure, Bloom's taxonomy, and 3-level rubric scoring patterns established

**No blockers** - Wave 2 (Plans 02-05) can execute in parallel, each implementing a concrete generator using this foundation.

---
*Phase: 04-core-content-generation*
*Completed: 2026-02-04*
