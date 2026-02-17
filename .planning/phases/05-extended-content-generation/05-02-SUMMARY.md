---
phase: 05-extended-content-generation
plan: 02
subsystem: content-generation
completed: 2026-02-04
duration: 2m 23s

tags:
  - hol-generator
  - skill-based-rubrics
  - tdd
  - content-generation
  - scaffolded-learning

requires:
  - 04-01  # BaseGenerator ABC
  - 05-01  # HOLSchema

provides:
  - HOLGenerator class for hands-on lab generation
  - Advanced/Intermediate/Beginner rubric scoring (5/4/2)
  - 3-part scaffolded structure

affects:
  - 05-08  # ProjectMilestoneGenerator (similar complex structure)
  - content-api  # Will need HOL generation support

tech-stack:
  added: []
  patterns:
    - TDD RED-GREEN-REFACTOR cycle
    - Skill-based rubric scoring model
    - Duration calculation from part estimates

key-files:
  created:
    - src/generators/hol_generator.py
    - tests/test_hol_generator.py
  modified: []

decisions:
  - decision: "HOL rubric uses Advanced/Intermediate/Beginner (5/4/2) instead of Below/Meets/Exceeds"
    rationale: "Emphasizes skill progression over pass/fail for hands-on technical work"
    impact: "Different scoring model from other content types (Quiz/Rubric use Below/Meets/Exceeds)"
  - decision: "Duration calculated as sum of part.estimated_minutes"
    rationale: "HOL parts have explicit time estimates for pacing"
    impact: "More accurate than word-count-based estimation for hands-on activities"
  - decision: "Total points fixed at 15 (3 criteria × 5 max)"
    rationale: "Standard Coursera HOL rubric structure"
    impact: "Consistent scoring across all HOL activities"
---

# Phase 5 Plan 2: HOLGenerator with Skill-Based Rubrics Summary

**One-liner:** TDD implementation of HOLGenerator with Advanced/Intermediate/Beginner scoring (5/4/2 points) and 3-part scaffolded structure

## What Was Built

Created HOLGenerator following TDD methodology with RED-GREEN-REFACTOR cycle. Generator produces hands-on lab activities with:

- **Scenario-based framing**: Real-world context for authentic learning
- **3-part scaffolding**: Foundation → Development → Integration structure
- **Submission criteria**: Clear deliverable specifications
- **Skill-based rubric**: Advanced/Intermediate/Beginner levels with 5/4/2 point distribution

### Key Components

**HOLGenerator Class** (`src/generators/hol_generator.py`, 178 lines)
- Extends `BaseGenerator[HOLSchema]`
- System prompt with detailed guidelines for scenario design, scaffolding, and skill-based rubrics
- User prompt builder incorporating learning objective, topic, and difficulty
- Metadata extraction: word_count, duration (sum of part minutes), total_points (15), content_type
- Convenience method `generate_hol()`

**Test Suite** (`tests/test_hol_generator.py`, 205 lines)
- 6 test cases with mocked Anthropic API
- Tests for valid schema generation
- Tests for correct rubric scoring model (5/4/2, not Below/Meets/Exceeds)
- Tests for system/user prompt content
- Tests for metadata calculation (duration as sum of parts)
- Tests for output_config parameter usage

### Technical Implementation

**TDD Execution:**
1. **RED Phase**: Wrote 6 failing tests (commit 7c66de6)
2. **GREEN Phase**: Implemented HOLGenerator to pass all tests (commit e19fbd1)
3. **REFACTOR Phase**: No refactoring needed - implementation clean on first pass

**Scoring Model:**
- Advanced: 5 points (best practices, comprehensive implementation)
- Intermediate: 4 points (functional, minor issues)
- Beginner: 2 points (partial completion, needs improvement)
- Total: 15 points (3 criteria × 5 max points)

**Duration Calculation:**
Unlike other content types that use word count, HOL duration is sum of `part.estimated_minutes` from the 3 scaffolded parts. This provides more accurate estimates for hands-on technical work.

## Deviations from Plan

None - plan executed exactly as written.

## Test Results

```
tests/test_hol_generator.py::test_generate_returns_valid_schema PASSED
tests/test_hol_generator.py::test_rubric_uses_correct_scoring PASSED
tests/test_hol_generator.py::test_system_prompt_mentions_scoring PASSED
tests/test_hol_generator.py::test_build_user_prompt_includes_params PASSED
tests/test_hol_generator.py::test_extract_metadata_calculates_duration PASSED
tests/test_hol_generator.py::test_api_called_with_output_config PASSED

6 passed in 0.92s
```

All tests passing with mocked Anthropic API.

## Integration Points

**Upstream Dependencies:**
- `BaseGenerator[T]` - Abstract base class with generic type safety
- `HOLSchema` - Pydantic schema with 3 parts and 3 rubric criteria
- `ContentMetadata` - Word counting utility

**Downstream Impact:**
- Content API will need HOL generation endpoint (`POST /api/courses/<id>/activities/<aid>/generate` with type="hol")
- Build state tracking will handle HOL activities in progress calculations
- Future generators (ProjectMilestoneGenerator) can follow this pattern for complex multi-part content

## Known Issues

None.

## Next Phase Readiness

**Phase 5 progress:** 2/8 plans complete (Extended Content Generation)

**Ready for Plan 05-03:** CoachGenerator with 8-section dialogue
- HOLGenerator establishes pattern for complex content types
- Can follow same TDD approach for Coach dialogue structure
- Different content complexity but similar implementation pattern

**Blockers:** None

**Prerequisites for next plan:**
- CoachSchema already exists from 05-01
- BaseGenerator pattern proven with HOLGenerator
- Test patterns established

## Decisions Made

1. **HOL rubric uses Advanced/Intermediate/Beginner scoring**
   - Rationale: Emphasizes skill progression over pass/fail
   - Impact: Different from Quiz/Rubric (Below/Meets/Exceeds)
   - Alternative considered: Use same Below/Meets/Exceeds as other rubrics
   - Why rejected: HOL activities assess skill development, not just task completion

2. **Duration calculated from part estimates, not word count**
   - Rationale: HOL parts have explicit time estimates
   - Impact: More accurate for hands-on activities
   - Supports pacing and time management for students

3. **Fixed total points at 15 (3 criteria × 5 max)**
   - Rationale: Standard Coursera HOL structure
   - Impact: Consistent scoring across all HOLs
   - Simplifies grade calculations

## Lessons Learned

1. **TDD cycle highly effective for generators**: RED-GREEN-REFACTOR forced clear thinking about HOL-specific requirements before implementation

2. **System prompt critical for scoring model**: Explicit mention of "Advanced/Intermediate/Beginner" and "5/4/2 points" prevents Claude from using wrong rubric model

3. **Duration calculation varies by content type**: HOL uses sum of part minutes (hands-on work), while Reading/Video use word count. Each content type needs appropriate estimation strategy.

4. **Pattern established for complex content**: HOLGenerator proves that multi-part content types (HOL, Coach, Project) can follow same BaseGenerator pattern with custom metadata extraction.

## Files Changed

**Created:**
- `src/generators/hol_generator.py` (178 lines)
- `tests/test_hol_generator.py` (205 lines)

**Modified:**
- None

## Metrics

- **Test Coverage**: 6 tests, all passing
- **Code Quality**: Follows established QuizGenerator pattern
- **Duration**: 2 minutes 23 seconds
- **Commits**: 2 (RED + GREEN phases)
- **Lines Added**: 383 lines (178 implementation + 205 tests)
