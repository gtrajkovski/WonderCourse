---
phase: 08-export-publishing
plan: 01
subsystem: export
tags: [export, validation, python-docx, infrastructure]
dependency-graph:
  requires:
    - phase-07 (ValidationResult pattern)
  provides:
    - BaseExporter ABC for all export formats
    - ExportValidator for pre-export content checking
    - python-docx dependency for DOCX export
  affects:
    - 08-02 (DocxExporter will extend BaseExporter)
    - 08-03 (Export API will use ExportValidator)
tech-stack:
  added:
    - python-docx>=1.1.0
  patterns:
    - ABC for export format abstraction
    - Validation-before-action pattern
file-tracking:
  key-files:
    created:
      - src/exporters/__init__.py
      - src/exporters/base_exporter.py
      - src/exporters/export_validator.py
      - tests/test_export_validator.py
    modified:
      - requirements.txt
decisions:
  - id: exportable-states
    choice: "APPROVED and PUBLISHED are exportable states"
    rationale: "Matches workflow where content must be reviewed before export"
  - id: require-approved-flag
    choice: "require_approved parameter allows relaxed validation"
    rationale: "Some exports may need draft content for preview purposes"
  - id: whitespace-is-missing
    choice: "Whitespace-only content treated as missing"
    rationale: "Prevents exporting activities with placeholder content"
metrics:
  duration: "3 minutes"
  completed: "2026-02-06"
  tests-added: 11
  tests-total: 419
---

# Phase 08 Plan 01: Export Infrastructure Summary

BaseExporter ABC and ExportValidator for pre-export content verification with python-docx dependency.

## One-Liner

Abstract exporter base class with content completeness validation before export.

## What Was Built

### BaseExporter (src/exporters/base_exporter.py)

Abstract base class for all export formats:

- `format_name` property: Human-readable format name (e.g., "Microsoft Word")
- `file_extension` property: File extension (e.g., ".docx")
- `export()` abstract method: Export course to file
- `get_output_path()`: Generate safe output file path from course title
- `get_metadata()`: Extract course metadata for export headers

### ExportValidator (src/exporters/export_validator.py)

Pre-export validation for content completeness:

- `validate_for_export(course, require_approved=True)`: Full validation
  - Checks all activities have content
  - Checks build state is APPROVED or PUBLISHED
  - Returns warnings for empty modules/lessons
  - Calculates completion and approval rates
- `get_missing_content(course)`: Quick list of activities without content
- `get_export_readiness(course)`: Summary dict for quick checks

### ExportValidationResult

Dataclass for validation results:
- `is_exportable`: Boolean ready-to-export flag
- `missing_content`: List of activities without content
- `incomplete_activities`: List of activities not approved
- `warnings`: Structural warnings
- `metrics`: Quantitative completion metrics

## Key Decisions

1. **Exportable States**: Only APPROVED and PUBLISHED activities are exportable by default. This enforces the review workflow before content goes out.

2. **Relaxed Mode**: The `require_approved=False` flag allows exporting GENERATED content for preview purposes, enabling draft exports when needed.

3. **Whitespace Detection**: Content that is only whitespace is treated as missing, preventing export of placeholder activities.

## Test Coverage

11 tests covering:
- Complete course export validation
- Missing content detection
- Unapproved activity detection
- Relaxed mode (require_approved=False)
- Empty course handling
- Empty module warnings
- get_missing_content convenience method
- get_export_readiness summary
- Result serialization
- Whitespace content detection
- PUBLISHED state handling

## Files Changed

| File | Change |
|------|--------|
| requirements.txt | Added python-docx>=1.1.0 |
| src/exporters/__init__.py | Created with BaseExporter, ExportValidator exports |
| src/exporters/base_exporter.py | Created with ABC for exporters |
| src/exporters/export_validator.py | Created with content validation |
| tests/test_export_validator.py | 11 tests for ExportValidator |

## Commits

| Hash | Type | Description |
|------|------|-------------|
| fd3bbf5 | feat | Add python-docx dependency and create exporter package |
| c0f71ab | feat | Implement ExportValidator with content completeness checking |

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

Ready for 08-02 (DocxExporter):
- BaseExporter provides the interface to implement
- python-docx is installed and importable
- ExportValidator can check content before DocxExporter runs
