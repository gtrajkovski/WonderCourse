---
phase: 08-export-publishing
plan: 06
status: complete
started: 2026-02-06T19:30:23Z
completed: 2026-02-06T19:34:36Z
duration: ~4 minutes
subsystem: export-api
tags: [flask, api, export, download, preview]

depends_on:
  - 08-01  # BaseExporter and ExportValidator
  - 08-02  # InstructorPackageExporter
  - 08-03  # LMSManifestExporter
  - 08-04  # DOCXTextbookExporter
  - 08-05  # SCORMPackageExporter

provides:
  - Export API Blueprint with preview and download endpoints
  - REST API for all 4 export formats
  - Preview before download functionality
  - force=true validation bypass

affects:
  - Phase 09 (if UI for export downloads needed)
  - Any future export format additions

files:
  created:
    - src/api/export.py (341 lines)
    - tests/test_export_api.py (447 lines)
  modified:
    - app.py (added export_bp registration)
    - tests/conftest.py (added init_export_bp)

decisions:
  - id: export-api-pattern
    choice: Flask Blueprint with init_*_bp dependency injection
    rationale: Consistent with other API blueprints in codebase

metrics:
  tests_added: 22
  test_file_lines: 447
  api_endpoints: 5
  export_formats: 4
---

# Phase 08 Plan 06: Export API Blueprint Summary

Complete REST API for exporting course content with preview and download functionality.

## One-Liner

Export API Blueprint with 5 endpoints: preview for all formats plus download for instructor, LMS, DOCX, SCORM.

## What Was Built

### Export API Blueprint (`src/api/export.py`)

Created Flask Blueprint with init_export_bp pattern matching codebase conventions.

**Endpoints implemented:**

| Endpoint | Method | Returns | Content-Type |
|----------|--------|---------|--------------|
| `/api/courses/<id>/export/preview?format=...` | GET | JSON preview | application/json |
| `/api/courses/<id>/export/instructor` | GET | ZIP file | application/zip |
| `/api/courses/<id>/export/lms` | GET | JSON file | application/json |
| `/api/courses/<id>/export/docx` | GET | DOCX file | application/vnd.openxmlformats... |
| `/api/courses/<id>/export/scorm` | GET | ZIP file | application/zip |

**Preview response structure:**
```json
{
  "format": "instructor",
  "course_id": "...",
  "course_title": "...",
  "ready": true,
  "files": ["syllabus.txt", ...],
  "missing_content": [],
  "validation_errors": [],
  "warnings": [],
  "metrics": {...}
}
```

**Features:**
- Uses ExportValidator to check export readiness
- Returns 400 if not ready (unless `?force=true`)
- Handles both BytesIO (instructor) and file-based (others) exporters
- Proper Content-Type headers for each format
- Temporary directory cleanup for file-based exports

### API Integration Tests (`tests/test_export_api.py`)

22 comprehensive tests covering:

**Preview tests (10):**
- All 4 format previews
- Invalid/missing format errors
- Missing course 404
- Missing content detection
- Ready state verification
- Metrics inclusion

**Download tests (8):**
- All 4 format downloads
- Missing course 404
- Validation failure without force
- force=true bypass
- Quiz content in instructor package

**Content-Type tests (4):**
- Correct MIME types for each format

## Technical Implementation

### Exporter Handling

Different exporters have different return types:
- `InstructorPackageExporter.export()` returns `Tuple[BytesIO, str]`
- Others return `Path` (write to disk)

API handles both patterns:
```python
if format_name == 'instructor':
    buffer, filename = exporter.export(course)
    return send_file(buffer, ...)
else:
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = exporter.export(course)
        buffer = BytesIO(open(output_path, 'rb').read())
        return send_file(buffer, ...)
```

### Preview File Lists

Preview generates expected file lists without actually exporting:
- Instructor: syllabus.txt, lesson_plans/, rubrics/, quizzes/, answer_keys/
- LMS: course_manifest.json
- DOCX: {title}.docx
- SCORM: imsmanifest.xml, shared/style.css, content/module_*/lesson_*.html

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 7e2f35c | feat | Add Export API Blueprint with preview and download endpoints |
| e2fb94b | feat | Register Export API Blueprint in app.py |
| 40913fb | test | Add 22 API integration tests for export endpoints |

## Verification Results

```
Export routes: [
  '/api/courses/<course_id>/export/preview',
  '/api/courses/<course_id>/export/instructor',
  '/api/courses/<course_id>/export/lms',
  '/api/courses/<course_id>/export/docx',
  '/api/courses/<course_id>/export/scorm'
]

Tests: 526 passed (22 new export API tests)
```

## Deviations from Plan

None - plan executed exactly as written.

## Success Criteria Verification

- [x] Export API Blueprint with init_export_bp(project_store)
- [x] Preview endpoint returns file list and validation status
- [x] 4 download endpoints (instructor, lms, docx, scorm)
- [x] force=true query param bypasses validation
- [x] Blueprint registered in app.py
- [x] All exporters in __init__.py (already complete from prior plans)
- [x] 22 API tests passing (exceeds 15+ requirement)
- [x] Full test suite passing (526 tests)

## Phase 08 Completion

This plan (08-06) completes Phase 08 (Export & Publishing):

| Plan | Component | Status |
|------|-----------|--------|
| 08-01 | BaseExporter + ExportValidator | Complete |
| 08-02 | InstructorPackageExporter | Complete |
| 08-03 | LMSManifestExporter | Complete |
| 08-04 | DOCXTextbookExporter | Complete |
| 08-05 | SCORMPackageExporter | Complete |
| 08-06 | Export API | Complete |

## Next Phase Readiness

Phase 08 deliverables ready for Phase 09 (Analytics & Reporting):
- Complete export pipeline (validator, 4 exporters, API)
- 5 REST endpoints for UI integration
- Preview before download pattern established
