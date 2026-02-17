---
phase: 06-textbook-generation
plan: 03
subsystem: generators
tags: [textbook, hierarchical-expansion, tdd, claude-api, pydantic]

# Dependency graph
requires:
  - phase: 06-01
    provides: TextbookChapterSchema, TextbookOutlineSchema, TextbookSectionSchema, SectionOutline schemas
  - phase: 04-01
    provides: BaseGenerator ABC with generate() method and output_config pattern
provides:
  - TextbookGenerator with hierarchical expansion (outline -> sections -> assembly)
  - generate_outline() for chapter structure planning
  - generate_section() for individual section generation with context
  - generate_chapter() orchestrating full pipeline with progress_callback support
affects: [06-04-textbook-api, 06-05-textbook-export]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Hierarchical content expansion: outline -> sections -> assembly"
    - "Progress callback pattern for async progress tracking"
    - "Sequential section generation with accumulated context"

key-files:
  created:
    - src/generators/textbook_generator.py
    - tests/test_textbook_generator.py
  modified: []

key-decisions:
  - "Three-phase generation: outline -> sections -> assembly for coherent long-form content"
  - "progress_callback as Optional[Callable[[float, str], None]] for API layer integration"
  - "Covered concepts passed to generate_section to prevent redundancy"
  - "Final assembly prompt includes all section content for context-aware conclusion/references/glossary"

patterns-established:
  - "Hierarchical expansion pattern: Plan structure first, then generate parts, then assemble"
  - "Progress callback integration: Generator accepts callback without knowing about job tracking"

# Metrics
duration: 12min
completed: 2026-02-05
---

# Phase 6 Plan 03: TextbookGenerator with Hierarchical Expansion Summary

**TextbookGenerator with three-phase hierarchical expansion (outline -> sections -> assembly), progress_callback support for async tracking, and ~3000 word target with APA 7 citations**

## Performance

- **Duration:** 12 min
- **Started:** 2026-02-05
- **Completed:** 2026-02-05
- **Tasks:** 2 (TDD: RED -> GREEN)
- **Files created:** 2

## Accomplishments

- TextbookGenerator extending BaseGenerator[TextbookChapterSchema] with hierarchical generation
- generate_outline() produces structured outline with 5-8 sections from learning outcome
- generate_section() generates individual sections with context from previous sections to prevent redundancy
- generate_chapter() orchestrates the full pipeline with optional progress_callback at each step
- System prompt with academic writing guidelines, ~3000 word target, APA 7 citation examples
- Metadata with all 7 fields: word_count, estimated_duration_minutes, section_count, reference_count, glossary_count, image_count
- 11 comprehensive tests with mocked Anthropic API

## Task Commits

Each task was committed atomically:

1. **Task 1: RED - Write failing tests** - `f1fab76` (test)
2. **Task 2: GREEN - Implement TextbookGenerator** - `491f69c` (feat)

_Note: TDD plan - no refactor phase needed as implementation was clean_

## Files Created/Modified

- `src/generators/textbook_generator.py` (359 lines) - TextbookGenerator with hierarchical expansion
- `tests/test_textbook_generator.py` (364 lines) - 11 tests with mocked Anthropic API

## Decisions Made

1. **Three-phase generation approach** - Outline first, then sections sequentially, then final assembly
   - Rationale: Ensures coherent long-form content by maintaining context throughout

2. **progress_callback as Optional[Callable[[float, str], None]]**
   - Rationale: Allows API layer to wire in JobTracker updates without generator knowing about jobs

3. **Covered concepts passed between sections**
   - Rationale: Prevents redundancy by telling each section what concepts are already covered

4. **Final assembly includes all section content in prompt**
   - Rationale: Claude can write contextually-aware introduction, conclusion, references, and glossary

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - TDD cycle executed smoothly.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- TextbookGenerator ready for integration into content API (06-04)
- JobTracker from 06-02 can be wired to progress_callback for async progress updates
- All 344 tests passing including new 11 textbook generator tests

---
*Phase: 06-textbook-generation*
*Completed: 2026-02-05*
