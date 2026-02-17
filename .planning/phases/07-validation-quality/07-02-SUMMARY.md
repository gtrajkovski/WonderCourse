---
phase: 07-validation-quality
plan: 02
subsystem: validation
tags: [learning-outcomes, coverage-scoring, gap-detection, alignment, quality-assurance]

# Dependency graph
requires:
  - phase: 07-01
    provides: ValidationResult dataclass with three-tier severity model

provides:
  - OutcomeValidator with coverage scoring and gap detection
  - Unmapped outcome detection (0 activities)
  - Low coverage warnings (< 2 activities per outcome)
  - Unmapped activity detection
  - Stale activity ID filtering

affects: [07-04-validation-api, future-quality-dashboard]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "MIN_ACTIVITIES_PER_OUTCOME constant for coverage threshold"
    - "Stale reference filtering pattern for deleted entities"
    - "Text truncation for user-friendly error messages"

key-files:
  created:
    - src/validators/outcome_validator.py
    - tests/test_outcome_validator.py
  modified: []

key-decisions:
  - "MIN_ACTIVITIES_PER_OUTCOME = 2 for recommended coverage"
  - "Unmapped outcomes are errors (blockers)"
  - "Low coverage outcomes are warnings (concerns)"
  - "Stale activity IDs filtered out (not counted as errors)"
  - "Coverage score = outcomes with 1+ activities / total outcomes"

patterns-established:
  - "Coverage scoring: percentage of outcomes with at least one mapped activity"
  - "Gap detection: identify both unmapped outcomes and unmapped activities"
  - "Graceful handling of no outcomes (valid with warning)"

# Metrics
duration: 4min
completed: 2026-02-06
---

# Phase 07 Plan 02: OutcomeValidator Summary

**Outcome-activity alignment validator with coverage scoring, unmapped outcome detection, and stale reference filtering**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-06T17:03:42Z
- **Completed:** 2026-02-06T17:07:55Z
- **Tasks:** 3 (RED → GREEN → REFACTOR)
- **Files modified:** 2

## Accomplishments

- OutcomeValidator detects unmapped outcomes (0 activities) as errors
- Low coverage outcomes (< 2 activities) generate warnings
- Unmapped activities (not linked to any outcome) identified
- Stale activity IDs from deleted activities filtered automatically
- Coverage score calculated as percentage of outcomes with 1+ activities
- 11 comprehensive tests covering all validation cases

## Task Commits

Each TDD phase was committed atomically:

1. **RED: Write failing tests** - `6859c2c` (test)
   - 11 test cases for all coverage scenarios
   - Tests fail (module doesn't exist)

2. **GREEN: Implement OutcomeValidator** - `f71cfd9` (feat)
   - Full implementation with coverage scoring
   - All 11 tests pass
   - Fixed test assertion to handle multiple warnings

3. **REFACTOR: Clean up imports** - `6d4c02c` (refactor)
   - Removed unused Tuple and LearningOutcome imports
   - Tests still pass (397 total)

## Files Created/Modified

- `src/validators/outcome_validator.py` - OutcomeValidator with validate() method
  - Detects unmapped outcomes (errors)
  - Warns about low coverage (< 2 activities)
  - Identifies unmapped activities
  - Filters stale activity references
  - Calculates 7 metrics (coverage_score, counts, averages)

- `tests/test_outcome_validator.py` - 11 comprehensive tests
  - No outcomes scenario
  - Unmapped/low coverage/good coverage outcomes
  - Stale activity ID filtering
  - Mixed coverage scenarios
  - Metrics validation

## Decisions Made

**MIN_ACTIVITIES_PER_OUTCOME = 2**
- Rationale: Single activity is fragile; 2+ activities provide robust coverage
- Impact: Low coverage warnings at 1 activity encourage better alignment

**Unmapped outcomes as errors**
- Rationale: Outcomes with 0 activities are publishing blockers
- Impact: Forces explicit outcome-activity alignment before approval

**Stale activity filtering**
- Rationale: Deleted activities shouldn't cause false errors
- Impact: Validator automatically handles orphaned references

**Coverage score calculation**
- Formula: (outcomes with 1+ activities) / total outcomes
- Rationale: Simple percentage metric for dashboard visualization
- Range: 0.0 to 1.0, rounded to 2 decimal places

## Deviations from Plan

**1. [Rule 1 - Bug] Fixed test assertion for multiple warnings**
- **Found during:** GREEN phase (test execution)
- **Issue:** Test expected exactly 1 warning but got 2 (low coverage + unmapped activities)
- **Fix:** Changed assertion to check for presence of low coverage warning using `any()`
- **Files modified:** tests/test_outcome_validator.py
- **Verification:** All 11 tests pass
- **Committed in:** f71cfd9 (GREEN phase commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor test assertion fix for correctness. No scope changes.

## Issues Encountered

None - TDD flow executed smoothly.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for Phase 7 Plan 3 (Structure Validators):**
- ValidationResult pattern established and proven
- OutcomeValidator demonstrates gap detection pattern
- 397 tests passing (11 new from this plan)

**Pattern established:**
- Three-tier severity (errors/warnings/suggestions)
- Metrics dictionary for quantitative data
- Helper methods for code reuse (_flatten_activities, _truncate_text)

**No blockers or concerns**

---
*Phase: 07-validation-quality*
*Completed: 2026-02-06*
