---
phase: 03-blueprint-generation
plan: 01
subsystem: ai-generation
tags: [pydantic, anthropic, structured-outputs, claude, blueprint, curriculum-design]

# Dependency graph
requires:
  - phase: 01-foundation-infrastructure
    provides: Config with ANTHROPIC_API_KEY and MODEL
  - phase: 02-course-management
    provides: Core data models for conversion target
provides:
  - BlueprintGenerator class with AI-powered curriculum generation
  - Pydantic schemas for blueprint structure (ActivityBlueprint, LessonBlueprint, ModuleBlueprint, CourseBlueprint)
  - WWHAA pedagogy and Bloom's taxonomy prompt engineering
affects: [03-02-blueprint-validation, 03-03-blueprint-api, 03-04-planner-ui]

# Tech tracking
tech-stack:
  added: [pydantic>=2.10.0]
  patterns: [structured-outputs-with-output-config, educational-prompt-engineering, stateless-generator]

key-files:
  created:
    - src/generators/blueprint_generator.py
    - tests/test_blueprint_generator.py
  modified:
    - requirements.txt

key-decisions:
  - "Use output_config parameter (not response_format) for Claude structured outputs"
  - "BlueprintGenerator creates own Anthropic client (not using AIClient) to avoid history pollution"
  - "Keep existing Pydantic models from 03-02 to avoid breaking changes"
  - "MAX_TOKENS set to 8192 for large blueprint responses"

patterns-established:
  - "Educational prompt engineering with WWHAA pedagogy and Bloom's taxonomy"
  - "CONTEXT-TASK structured prompts for curriculum generation"
  - "Stateless generator pattern for one-shot AI generation"

# Metrics
duration: 5 min
completed: 2026-02-03
---

# Phase 3 Plan 1: Blueprint Generator with Structured Outputs Summary

**BlueprintGenerator class with Claude structured outputs API (output_config), WWHAA pedagogy, and Bloom's taxonomy for AI-powered curriculum design**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-03T23:49:57Z
- **Completed:** 2026-02-03T23:54:28Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Added BlueprintGenerator class with Claude structured outputs using output_config parameter
- Integrated WWHAA pedagogy (Why/What/How/Apply/Assess) and Bloom's taxonomy into system prompt
- Created 7 comprehensive tests with mocked Anthropic API
- Added content_distribution field to CourseBlueprint for tracking content type percentages
- Verified output_config parameter usage (NOT response_format) per Anthropic SDK v0.77.0+

## Task Commits

Each task was committed atomically:

1. **Task 1: Add Pydantic dependency and create generators package** - `c6699fc` (chore)
2. **Task 2: Create BlueprintGenerator with Pydantic schemas and prompt templates** - `0f02f48` (feat)
3. **Task 3: Create unit tests for BlueprintGenerator with mocked AI** - `dfa6d1c` (test)

## Files Created/Modified

- `requirements.txt` - Added pydantic>=2.10.0 dependency
- `src/generators/blueprint_generator.py` - BlueprintGenerator class with Pydantic schemas, SYSTEM_PROMPT, generate() method, and _build_prompt() helper
- `tests/test_blueprint_generator.py` - 7 tests covering schema validation, generation, prompt construction, and output_config usage

## Decisions Made

1. **Keep existing Pydantic models from 03-02** - Plan 03-02 (executed in parallel) already created ActivityBlueprint, LessonBlueprint, ModuleBlueprint, CourseBlueprint with slightly different field constraints. Kept those to avoid breaking what's working, only added content_distribution field.

2. **BlueprintGenerator creates own Anthropic client** - Does not use AIClient from src/ai/client.py. This avoids conversation history pollution and keeps the generator stateless. The existing AIClient is designed for conversational use; the generator needs one-shot structured outputs.

3. **Use output_config parameter** - Anthropic SDK v0.77.0+ uses `output_config.format` parameter (not `response_format` which is OpenAI's convention). Tests explicitly verify this to prevent future regressions.

4. **MAX_TOKENS set to 8192** - Blueprint generation produces large JSON responses (2+ modules, 3-5 lessons each, 2-4 activities per lesson). 8192 tokens ensures adequate space for complete blueprints.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Kept existing Pydantic models instead of replacing them**

- **Found during:** Task 2 (BlueprintGenerator implementation)
- **Issue:** Plan 03-01 specified different Pydantic field constraints (activity_type as Literal, title max_length=100) but plan 03-02 (executed in parallel) already created working models with activity_type as str and title max_length=200
- **Fix:** Kept existing models to avoid breaking what 03-02 created, only added content_distribution field to CourseBlueprint
- **Files modified:** src/generators/blueprint_generator.py (added field, not replaced models)
- **Verification:** All 167 tests pass including 03-02's converter tests
- **Committed in:** 0f02f48 (part of Task 2 commit)

---

**Total deviations:** 1 auto-fixed (blocking issue - preserved working code)
**Impact on plan:** Minimal - kept existing working models, only added missing field. No functional impact.

## Issues Encountered

None - execution was smooth with existing infrastructure from Phase 1 and Phase 2.

## Next Phase Readiness

- ✅ BlueprintGenerator ready for API integration (03-03)
- ✅ Pydantic models ready for validation (03-02 already complete)
- ✅ Tests verify correct output_config usage
- ⚠️  Note: Pydantic 2.12.5 has minor conflicts with global gradio/streamlit packages, but doesn't affect CourseBuilder
- ✅ All 167 tests passing (142 existing + 25 from Phase 3)

**Ready for plan 03-03 (Blueprint API Integration) and 03-04 (Planner UI).**

---
*Phase: 03-blueprint-generation*
*Completed: 2026-02-03*
