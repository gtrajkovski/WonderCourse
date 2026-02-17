---
phase: 08-export-publishing
plan: 02
subsystem: export
tags: [export, zip, instructor, syllabus, lesson-plans, rubrics, quizzes]
dependency-graph:
  requires:
    - 08-01 (BaseExporter ABC)
  provides:
    - InstructorPackageExporter for ZIP bundle generation
    - Syllabus, lesson plans, rubrics, quizzes, answer keys in ZIP
    - Textbook.docx inclusion when chapters exist
  affects:
    - 08-03 (Export API will use InstructorPackageExporter)
    - Future instructor download endpoints
tech-stack:
  added: []
  patterns:
    - In-memory ZIP generation with zipfile.ZIP_DEFLATED
    - Minimal inline DOCX generation (OOXML structure)
    - Filename sanitization for cross-platform compatibility
file-tracking:
  key-files:
    created:
      - src/exporters/instructor_package.py
      - tests/test_instructor_package.py
    modified:
      - src/exporters/__init__.py
decisions:
  - id: in-memory-zip
    choice: "Generate ZIP directly in BytesIO buffer"
    rationale: "Enables streaming download without temp files; cleaner API"
  - id: inline-docx-generator
    choice: "Simple inline DOCX generation rather than using DOCXTextbookExporter"
    rationale: "DOCXTextbookExporter writes to disk; inline approach works in-memory for ZIP"
  - id: sanitize-all-paths
    choice: "Remove all special characters from folder and file names"
    rationale: "Ensures cross-platform compatibility (Windows, macOS, Linux)"
  - id: quiz-student-instructor-split
    choice: "Separate quizzes/ (no answers) and answer_keys/ (with explanations)"
    rationale: "Supports instructor use case of distributing questions without revealing answers"
metrics:
  duration: "4 minutes"
  completed: "2026-02-06"
  tests-added: 18
  tests-total: 504
---

# Phase 08 Plan 02: Instructor Package Exporter Summary

InstructorPackageExporter creates ZIP bundles with syllabus, lesson plans, rubrics, quizzes, answer keys, and optional textbook.

## One-Liner

ZIP exporter for instructor materials with student-safe quizzes and instructor-only answer keys.

## What Was Built

### InstructorPackageExporter (src/exporters/instructor_package.py)

ZIP bundle exporter extending BaseExporter:

- `format_name`: "Instructor Package"
- `file_extension`: ".zip"
- `export(course, filename=None)`: Returns `(BytesIO, filename)` tuple

**ZIP Archive Structure:**
```
{course_title}_instructor.zip
├── syllabus.txt              # Course overview with modules/lessons
├── lesson_plans/
│   └── {module_title}/
│       └── {lesson_title}.txt  # Activities, timing, build state
├── rubrics/
│   └── {activity_title}.txt    # Rubric criteria for RUBRIC content types
├── quizzes/
│   └── {activity_title}_questions.txt  # Questions only (student version)
├── answer_keys/
│   └── {activity_title}_key.txt        # Answers with explanations
└── textbook.docx             # Only if course.textbook_chapters exists
```

**Syllabus Format:**
- Course title, duration, audience level
- Description
- Module/lesson list with activity counts
- Learning outcomes with Bloom's levels

**Lesson Plan Format:**
- Lesson title and parent module
- Description
- Activity list with content type, duration, build state

**Quiz/Answer Key Split:**
- `quizzes/` contains questions and options only (no correct answers)
- `answer_keys/` contains correct answer letters and explanations
- Both parsed from JSON content in QUIZ activities

**Textbook Generation:**
- Inline minimal DOCX generator (OOXML structure)
- Includes chapter titles, sections, glossary terms
- Only added when `course.textbook_chapters` is non-empty

### Filename Sanitization

`_sanitize_filename()` method:
- Removes special characters: `!@#$%^&*()[]{}|;:'",.<>?/\`
- Replaces spaces with underscores
- Collapses multiple underscores
- Falls back to "untitled" for empty results

## Key Decisions

1. **In-Memory ZIP**: Using `BytesIO` for ZIP creation enables direct streaming to HTTP response without temporary files on disk.

2. **Inline DOCX Generator**: Rather than using `DOCXTextbookExporter` (which writes to disk), implemented minimal inline DOCX generation that creates valid OOXML structure in memory.

3. **Strict Filename Sanitization**: Removes all characters that could cause issues on any operating system, ensuring ZIP extracts correctly everywhere.

4. **Quiz/Answer Split**: Separating questions from answers supports the instructor use case of distributing practice materials to students without revealing correct answers.

## Test Coverage

18 TDD tests covering:

**Basic Properties:**
- format_name is "Instructor Package"
- file_extension is ".zip"

**ZIP Structure:**
- Creates valid, readable ZIP file
- Contains syllabus.txt with course info
- Syllabus includes modules and lessons
- Syllabus includes learning outcomes

**Lesson Plans:**
- lesson_plans/ folder contains lesson files
- Lesson plan format includes title, module, activities, timing

**Rubrics:**
- rubrics/ folder contains RUBRIC activity files
- Rubric format includes criteria and score levels

**Quizzes and Answer Keys:**
- quizzes/ contains questions without answers
- answer_keys/ contains correct answers with explanations

**Textbook Integration:**
- textbook.docx included when chapters exist
- textbook.docx NOT included when no chapters

**Edge Cases:**
- Empty course produces valid ZIP with syllabus only
- Special characters sanitized from all paths
- Course without quizzes has no quiz/answer_key files
- Invalid JSON content handled gracefully (no crash)

## Files Changed

| File | Change |
|------|--------|
| src/exporters/instructor_package.py | Created with InstructorPackageExporter class (423 lines) |
| src/exporters/__init__.py | Added InstructorPackageExporter to exports |
| tests/test_instructor_package.py | Created with 18 TDD tests (449 lines) |

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 1bfc0b1 | test | Add failing tests for InstructorPackageExporter |
| 68175ec | feat | Implement InstructorPackageExporter with ZIP bundle generation |

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

Ready for 08-03 (Export API):
- InstructorPackageExporter provides downloadable ZIP bundles
- API endpoint can call `exporter.export(course)` and stream BytesIO response
- Filename returned for Content-Disposition header
