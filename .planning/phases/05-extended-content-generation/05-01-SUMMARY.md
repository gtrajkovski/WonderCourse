---
phase: 05-extended-content-generation
plan: 01
subsystem: content-generation
tags: [pydantic, schemas, validation, structured-outputs]

# Dependency graph
requires:
  - phase: 04-core-content-generation
    provides: BaseGenerator ABC, existing schema patterns (quiz.py, rubric.py)
provides:
  - 7 new Pydantic schemas for extended content types
  - HOL schema with Advanced/Intermediate/Beginner scoring (5/4/2 points)
  - Coach schema with 8-section dialogue structure
  - PracticeQuiz schema separate from Quiz with hint fields
  - Lab, Discussion, Assignment, and Project schemas
affects: [05-02, 05-03, 05-04, 05-05, 05-06, 05-07, 05-08]

# Tech tracking
tech-stack:
  added: []
  patterns: [Skill-based rubric scoring (Advanced/Intermediate/Beginner), Formative vs summative quiz separation, Multi-section dialogue structure, Project milestone staging]

key-files:
  created:
    - src/generators/schemas/hol.py
    - src/generators/schemas/coach.py
    - src/generators/schemas/practice_quiz.py
    - src/generators/schemas/lab.py
    - src/generators/schemas/discussion.py
    - src/generators/schemas/assignment.py
    - src/generators/schemas/project.py
  modified:
    - src/generators/schemas/__init__.py

key-decisions:
  - "HOL uses Advanced/Intermediate/Beginner scoring model (5/4/2 points) instead of Below/Meets/Exceeds to emphasize skill progression"
  - "PracticeQuizSchema separate from QuizSchema to distinguish formative (with hints) from summative (graded) assessment"
  - "CoachSchema requires exactly 8 sections for complete conversational learning experience"
  - "ProjectMilestoneSchema uses A1/A2/A3 literal types to enforce standard milestone staging"

patterns-established:
  - "Skill-based rubrics for performance-oriented assessments (HOL)"
  - "Formative vs summative content type separation (PracticeQuiz vs Quiz)"
  - "Multi-section dialogue structures with conversation starters and sample responses"
  - "Milestone-based project staging with typed progression (A1/A2/A3)"

# Metrics
duration: 3min
completed: 2026-02-04
---

# Phase 5 Plan 1: Extended Content Schemas Summary

**7 Pydantic v2 schemas for HOL, Coach, PracticeQuiz, Lab, Discussion, Assignment, and Project with skill-based HOL rubrics and 8-section coach dialogues**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-04T16:06:54Z
- **Completed:** 2026-02-04T16:09:41Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Created 7 new Pydantic schemas following quiz.py/rubric.py patterns
- HOL schema uses Advanced/Intermediate/Beginner scoring (5/4/2 points) instead of Below/Meets/Exceeds
- PracticeQuiz schema separated from Quiz with hint fields for formative assessment
- Coach schema includes all 8 required sections for complete dialogue experience
- All schemas produce valid JSON schemas via model_json_schema()
- All 250 existing tests pass with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Create all 7 Pydantic schemas** - `14a3f65` (feat)
2. **Task 2: Update schemas __init__.py with all new exports** - `970fcda` (feat)

## Files Created/Modified
- `src/generators/schemas/hol.py` - HOLSchema with HOLPart and HOLRubricCriterion (Advanced/Intermediate/Beginner scoring)
- `src/generators/schemas/coach.py` - CoachSchema with ConversationStarter and SampleResponse (8 sections)
- `src/generators/schemas/practice_quiz.py` - PracticeQuizSchema with hint fields (separate from QuizSchema)
- `src/generators/schemas/lab.py` - LabSchema with SetupStep for environment preparation
- `src/generators/schemas/discussion.py` - DiscussionSchema with facilitation questions and engagement hooks
- `src/generators/schemas/assignment.py` - AssignmentSchema with AssignmentDeliverable and ChecklistItem
- `src/generators/schemas/project.py` - ProjectMilestoneSchema with MilestoneDeliverable and A1/A2/A3 typing
- `src/generators/schemas/__init__.py` - Updated to export all 7 new schemas (now 11 total content types)

## Decisions Made

1. **HOL scoring model:** Used Advanced/Intermediate/Beginner (5/4/2 points) instead of Below/Meets/Exceeds to emphasize skill progression over pass/fail, appropriate for hands-on technical assessment
2. **PracticeQuiz separation:** Created separate schema from QuizSchema to distinguish formative (with hints, no passing score) from summative (graded, passing threshold) assessment purposes
3. **Coach dialogue structure:** Enforced all 8 sections at schema level to ensure complete conversational learning experience (learning_objectives, scenario, tasks, conversation_starters, sample_responses, evaluation_criteria, wrap_up, reflection_prompts)
4. **Project milestone typing:** Used Literal["A1","A2","A3"] to enforce standard milestone progression and prevent invalid staging

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 7 schemas validated and importable
- Ready for Phase 5 generator implementation (plans 05-02 through 05-08)
- Schema patterns established for consistent API usage with BaseGenerator
- HOL rubric correctly uses 5/4/2 point model as specified in research

---
*Phase: 05-extended-content-generation*
*Completed: 2026-02-04*
