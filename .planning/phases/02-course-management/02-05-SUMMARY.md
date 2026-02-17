# Phase 2 Plan 5: Outcome-Activity Mapping API Summary

**One-liner:** Bidirectional outcome-activity mapping with alignment coverage tracking and reverse lookups

---

## What Was Built

Added four new endpoints to `src/api/learning_outcomes.py` that enable mapping learning outcomes to activities and querying the alignment:

### Mapping Endpoints

1. **POST `/api/courses/<id>/outcomes/<oid>/map`** - Map outcome to activity
   - Validates both outcome and activity exist
   - Adds activity_id to outcome.mapped_activity_ids
   - Idempotent (no duplicates on repeated calls)
   - Returns updated outcome object

2. **DELETE `/api/courses/<id>/outcomes/<oid>/map/<aid>`** - Unmap outcome from activity
   - Removes activity_id from outcome.mapped_activity_ids
   - Idempotent (no error if mapping doesn't exist)
   - Returns success message

### Query Endpoints

3. **GET `/api/courses/<id>/alignment`** - Get alignment matrix with coverage analysis
   - Returns full alignment data structure:
     - `outcomes`: Array of outcomes with mapped activity details
     - `unmapped_outcomes`: Array of outcome IDs with no mappings
     - `unmapped_activities`: Array of activity IDs not in any mapping
     - `coverage_score`: Ratio of mapped to total outcomes (0.0-1.0)
   - Useful for curriculum gap analysis and quality checks

4. **GET `/api/courses/<id>/activities/<aid>/outcomes`** - Reverse lookup outcomes by activity
   - Returns array of outcome objects that include the activity in their mappings
   - Enables activity-centric views of learning objectives

### Helper Function

Added `_get_all_activities(course)` helper that traverses the nested course structure (modules → lessons → activities) to collect all activities in a flat list. This is used by mapping validation and alignment queries.

---

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Store mappings unidirectionally in LearningOutcome.mapped_activity_ids | Simpler data model, single source of truth | Reverse lookups require O(n) scan but acceptable given typical course sizes |
| Validate activity existence on mapping | Prevent orphaned mappings | Catches typos/deletions early, maintains data integrity |
| Make mapping/unmapping idempotent | Safe for retries, simpler client code | Can call mapping endpoint multiple times without side effects |
| Include activity details in alignment matrix | Reduce follow-up API calls | Richer response but slightly larger payload |
| Calculate coverage score dynamically | Always accurate, no caching complexity | Negligible performance impact for typical course sizes |
| Add reverse lookup endpoint on learning_outcomes_bp | Keeps all mapping logic in one blueprint | URL pattern works across blueprints, logical cohesion |

---

## Technical Implementation

### Data Flow

```
Map Operation:
1. Load course from ProjectStore
2. Validate outcome exists (404 if not)
3. Traverse course structure to find activity (404 if not)
4. Add activity_id to outcome.mapped_activity_ids (if not present)
5. Save course to ProjectStore
6. Return updated outcome

Alignment Query:
1. Load course from ProjectStore
2. Get all activities via _get_all_activities()
3. Build activity lookup dict for fast access
4. For each outcome, resolve mapped activity IDs to activity objects
5. Calculate unmapped outcomes (empty mapped_activity_ids)
6. Calculate unmapped activities (not in any outcome's mappings)
7. Calculate coverage score (mapped / total outcomes)
8. Return alignment structure
```

### Idempotency

- **Map endpoint**: Checks if activity_id already in list before appending
- **Unmap endpoint**: List comprehension filters out activity_id (no error if not present)

### Cascading Cleanup

Activities API already handles mapping cleanup on activity deletion (from plan 02-03):
- When deleting an activity, removes its ID from all outcome.mapped_activity_ids

---

## Test Coverage

Created `tests/test_outcome_mapping_api.py` with 10 comprehensive tests:

1. **test_map_outcome_to_activity** - Basic mapping adds activity to list
2. **test_map_idempotent** - Mapping twice produces no duplicates
3. **test_map_invalid_outcome** - 404 for nonexistent outcome
4. **test_map_invalid_activity** - 404 for nonexistent activity
5. **test_unmap_outcome_from_activity** - Unmapping removes from list
6. **test_unmap_nonexistent_mapping** - Unmapping non-mapped pair returns 200 (idempotent)
7. **test_alignment_matrix** - Full alignment query with mixed mappings validates structure and coverage score
8. **test_alignment_empty_course** - Empty course returns empty alignment with 0.0 coverage
9. **test_reverse_lookup** - Activity with multiple outcome mappings returns all
10. **test_reverse_lookup_no_mappings** - Unmapped activity returns empty array

All tests use `seeded_course` fixture that creates:
- 1 course with 1 module
- 2 lessons (2 activities each, 4 total)
- 2 learning outcomes

**Total test suite: 142 tests passing** (132 existing + 10 new)

---

## Files Changed

### Modified
- **src/api/learning_outcomes.py** (+251 lines)
  - Added 4 new route handlers
  - Added `_get_all_activities()` helper
  - Now 8 endpoints total (4 CRUD + 4 mapping/alignment)

### Created
- **tests/test_outcome_mapping_api.py** (352 lines)
  - 10 comprehensive tests covering mapping, unmapping, alignment, and reverse lookup
  - `seeded_course` fixture for consistent test data

---

## Integration Points

### Existing APIs
- Works with activities from plans 02-02 and 02-03
- Activities API already handles mapping cleanup on deletion
- Modules/lessons APIs handle cascading cleanup that removes activities (which triggers mapping cleanup)

### Data Model
- Uses `LearningOutcome.mapped_activity_ids: List[str]` from 01-02
- Traverses `Course.modules[].lessons[].activities[]` hierarchy

### Future Use
- Alignment matrix endpoint will be used by dashboard/analytics features
- Reverse lookup enables activity-centric curriculum design views
- Coverage score can drive quality gates and curriculum completeness checks

---

## Known Limitations

1. **No validation that deleted activities are cleaned from mappings** - Relies on activities API to do this during deletion. If activities deleted via direct database access, orphaned IDs could remain.

2. **Reverse lookup is O(n) over outcomes** - Acceptable for typical course sizes (10-50 outcomes) but could be slow for extremely large courses (1000+ outcomes).

3. **No bulk mapping endpoint** - To map one outcome to 10 activities requires 10 API calls. Future enhancement could add bulk operation.

4. **No mapping metadata** - Don't track who/when mapping was created or rationale. Future enhancement could add mapping justification field.

5. **Coverage score is simple ratio** - Doesn't account for outcome importance weighting or Bloom's level distribution. Future enhancement could add weighted coverage.

---

## Success Metrics

- ✅ All 4 mapping/alignment endpoints implemented and registered
- ✅ Mapping validates both outcome and activity exist
- ✅ Mapping and unmapping are idempotent
- ✅ Alignment matrix returns coverage score
- ✅ Reverse lookup returns outcomes by activity
- ✅ 10 comprehensive tests covering all endpoints and edge cases
- ✅ All 142 tests passing (100% compatibility with existing features)
- ✅ Zero deviations from plan

---

## Next Phase Readiness

**Phase 2 Complete** - All course structure CRUD APIs are now complete:
- ✅ 02-01: Enhanced course metadata
- ✅ 02-02: Module CRUD
- ✅ 02-03: Lesson CRUD
- ✅ 02-03: Activity CRUD
- ✅ 02-04: Learning Outcome CRUD
- ✅ 02-05: Outcome-Activity Mapping (this plan)

**Ready for Phase 3: AI Content Generation**

The mapping API enables:
- **Curriculum alignment verification** - Ensure all outcomes have supporting activities
- **Gap analysis** - Identify unmapped outcomes needing content
- **Activity justification** - Show which outcomes an activity addresses
- **Coverage tracking** - Monitor curriculum completeness

Phase 3 AI generators can use alignment data to:
- Prioritize content generation for unmapped outcomes
- Suggest activity types based on Bloom's level
- Generate activities that fill curriculum gaps
- Validate generated content aligns with declared outcomes

---

## Deployment Notes

No migrations required - uses existing `mapped_activity_ids` field in LearningOutcome model.

Blueprint already registered in app.py (learning_outcomes_bp) - new endpoints automatically available.

No new dependencies.

---

## Metadata

**Phase:** 02-course-management
**Plan:** 05
**Type:** execute
**Status:** Complete
**Duration:** ~3 minutes
**Completed:** 2026-02-02

**Commits:**
- `a938a28` - feat(02-05): add outcome-activity mapping and alignment endpoints
- `d677b36` - test(02-05): add comprehensive outcome mapping and alignment tests

**Test Results:**
```
142 passed in 1.97s
```
