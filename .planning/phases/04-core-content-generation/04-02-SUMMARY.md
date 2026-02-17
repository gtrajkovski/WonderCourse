---
phase: 04-core-content-generation
plan: 02
subsystem: content-generation
tags: [video-scripts, wwhaa, anthropic, pydantic, tdd, pytest]

# Dependency graph
requires:
  - phase: 04-01
    provides: BaseGenerator ABC, ContentMetadata utility, VideoScriptSchema
provides:
  - VideoScriptGenerator with WWHAA structure (Hook/Objective/Content/IVQ/Summary/CTA)
  - 6 WWHAA sections with percentage guidelines (10%/10%/60%/5%/10%/5%)
  - Per-section word count metadata tracking
  - 150 WPM video duration estimation
  - generate_script() convenience method
affects: [04-06-content-generation-api, future-video-content-features]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TDD with RED-GREEN cycle (test → implementation)"
    - "Mock Anthropic API in base_generator module for BaseGenerator tests"
    - "Per-section metadata extraction for structured content"

key-files:
  created:
    - src/generators/video_script_generator.py
    - tests/test_video_script_generator.py
  modified: []

key-decisions:
  - "Patch Anthropic in base_generator module (not video_script_generator) since BaseGenerator.__init__ instantiates client"
  - "Per-section word counts in metadata for proportionality validation"
  - "generate_script() convenience method for cleaner API than generate(schema=...)"

patterns-established:
  - "WWHAA percentage guidelines in system prompt (Hook 10%, Objective 10%, Content 60%, IVQ 5%, Summary 10%, CTA 5%)"
  - "Target word count calculation: duration_minutes * 150 WPM in user prompt"
  - "section_word_counts dict in metadata for section-level analysis"

# Metrics
duration: 8min
completed: 2026-02-04
---

# Phase 04 Plan 02: VideoScriptGenerator with WWHAA Structure Summary

**VideoScriptGenerator producing 6-section WWHAA video scripts with 150 WPM duration estimates and per-section word count tracking**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-04T03:48:27Z
- **Completed:** 2026-02-04T03:56:16Z
- **Tasks:** 1 (TDD task with RED-GREEN cycle)
- **Files modified:** 2

## Accomplishments
- VideoScriptGenerator extends BaseGenerator[VideoScriptSchema]
- System prompt with WWHAA structure and percentage guidelines
- extract_metadata() returns word_count, estimated_duration_minutes (150 WPM), section_word_counts
- All 6 tests passing with mocked Anthropic API
- No regressions (225 total tests passing)

## Task Commits

Each TDD phase was committed atomically:

1. **RED: Write failing tests** - `047b061` (test)
2. **GREEN: Implement VideoScriptGenerator** - `b2cfbdb` (feat)

_Note: No REFACTOR phase - code was clean after GREEN implementation_

## Files Created/Modified
- `src/generators/video_script_generator.py` - VideoScriptGenerator with WWHAA structure, system prompt with percentages, build_user_prompt with duration calculation, extract_metadata with section word counts
- `tests/test_video_script_generator.py` - 6 tests covering schema validation, system prompt WWHAA content, user prompt parameters, metadata calculations, section word counts, output_config API usage

## Decisions Made

**Mock placement for BaseGenerator tests:**
- Patch 'src.generators.base_generator.Anthropic' not 'src.generators.video_script_generator.Anthropic'
- Rationale: BaseGenerator.__init__ instantiates Anthropic client, so mock must be applied before subclass constructor runs

**Per-section word counts:**
- Return section_word_counts dict with hook/objective/content/ivq/summary/cta counts
- Rationale: Enables validation of WWHAA proportions (are sections actually 10%/10%/60%/5%/10%/5%?)

**generate_script() convenience method:**
- Wrapper around generate(schema=VideoScriptSchema, ...) with same parameters
- Rationale: Cleaner API for video script generation without schema boilerplate

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

**Mock not being applied (resolved):**
- Initial attempt patched 'src.generators.video_script_generator.Anthropic'
- Tests still hit real API with authentication errors
- Root cause: BaseGenerator.__init__ instantiates Anthropic before mock applied
- Solution: Patch 'src.generators.base_generator.Anthropic' where client is actually created
- Verification: All 6 tests pass with mock, no real API calls

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- VideoScriptGenerator ready for integration in 04-06 (content generation API)
- Pattern established for remaining generators (ReadingGenerator, QuizGenerator, RubricGenerator)
- Test infrastructure proven with BaseGenerator mock pattern
- Ready to proceed with 04-03 (ReadingGenerator)

---
*Phase: 04-core-content-generation*
*Completed: 2026-02-04*
