---
phase: 12-ai-interactive-features
plan: 02
subsystem: import
tags: [docx, html, scorm, qti, lxml, beautifulsoup4, bleach, mammoth, content-import]

# Dependency graph
requires:
  - phase: none
    provides: foundational parser infrastructure was created in parallel with plan 12-01
provides:
  - Advanced content import parsers for DOCX, HTML, SCORM, and QTI formats
  - Format detection and sanitization for external content
  - Course structure extraction from SCORM packages
  - Quiz question extraction from QTI files
affects: [12-03, 12-04, import-api, content-migration]

# Tech tracking
tech-stack:
  added:
    - mammoth>=1.9.0 (DOCX to semantic HTML conversion)
    - lxml>=5.0.0 (XML parsing for SCORM/QTI)
    - beautifulsoup4>=4.12.0 (HTML parsing)
    - bleach>=6.0.0 (HTML sanitization)
  patterns:
    - BaseParser ABC with can_parse/parse interface
    - ParseResult dataclass with content/metadata/warnings/provenance
    - Format detection via magic bytes and content patterns
    - Sanitization defense-in-depth (server-side)

key-files:
  created:
    - src/import/parsers/base_parser.py (ABC and result dataclass)
    - src/import/parsers/docx_parser.py (python-docx + mammoth)
    - src/import/parsers/html_parser.py (BeautifulSoup + bleach)
    - src/import/parsers/scorm_parser.py (lxml with SCORM namespaces)
    - src/import/parsers/qti_parser.py (QTI 2.1/2.2 quiz parsing)
    - tests/test_import_parsers_advanced.py (28 comprehensive tests)
  modified:
    - requirements.txt (added 4 import libraries)
    - src/import/parsers/__init__.py (export all parsers)
    - src/import/parsers/*.py (fixed relative imports in 5 base parsers)

key-decisions:
  - "Use python-docx for structured extraction + mammoth for semantic HTML conversion from DOCX"
  - "Sanitize HTML with bleach server-side to prevent XSS attacks"
  - "Search for imsmanifest.xml at any depth in SCORM ZIPs to handle non-standard packaging"
  - "Handle both namespaced and non-namespaced QTI XML for maximum compatibility"
  - "Use relative imports (from .base_parser) to avoid Python keyword conflicts with 'import'"

patterns-established:
  - "Format detection: filename extension + magic bytes + content patterns"
  - "Sanitization defense-in-depth: bleach (server) + DOMPurify (client planned)"
  - "Provenance tracking: filename, import_time, original_format, parser name"
  - "Content type detection: heuristics from document structure (headings, numbered lists)"

# Metrics
duration: 12min
completed: 2026-02-10
---

# Phase 12 Plan 02: Advanced Content Import Parsers Summary

**DOCX, HTML, SCORM, and QTI parsers with XSS sanitization, SCORM manifest search at any depth, and comprehensive test coverage**

## Performance

- **Duration:** 12 minutes
- **Started:** 2026-02-10T23:13:53Z
- **Completed:** 2026-02-10T23:26:41Z
- **Tasks:** 2
- **Files modified:** 15
- **Tests:** 28 tests passing

## Accomplishments

- Four advanced parsers handle complex document and package formats
- DOCX parser extracts structured content + converts to semantic HTML with mammoth
- HTML parser sanitizes with bleach to prevent XSS attacks
- SCORM parser finds imsmanifest.xml at any depth (handles non-root packaging)
- QTI parser extracts quiz questions from QTI 2.1/2.2 XML
- 28 comprehensive tests cover format detection, parsing, sanitization, and edge cases

## Task Commits

Each task was committed atomically:

1. **Task 1: Add dependencies and create DOCX and HTML parsers** - `0707a6e` (feat)
   - Added mammoth, lxml, beautifulsoup4, bleach to requirements.txt
   - Created BaseParser ABC and ParseResult dataclass
   - Implemented DOCXParser with python-docx + mammoth
   - Implemented HTMLParser with BeautifulSoup + bleach

2. **Task 2: Create SCORM and QTI parsers with tests** - `07e7809` (feat)
   - Implemented SCORMParser with lxml and SCORM namespaces
   - Implemented QTIParser for QTI 2.1/2.2 quiz parsing
   - Fixed relative imports in all parser files (avoiding Python keyword conflict)
   - Created 28 comprehensive tests covering all 4 parsers

## Files Created/Modified

**Created:**
- `src/import/parsers/base_parser.py` - Abstract BaseParser class and ParseResult dataclass
- `src/import/parsers/docx_parser.py` - DOCX parsing with python-docx and mammoth
- `src/import/parsers/html_parser.py` - HTML parsing with BeautifulSoup and bleach sanitization
- `src/import/parsers/scorm_parser.py` - SCORM package parsing with lxml
- `src/import/parsers/qti_parser.py` - QTI quiz question extraction
- `tests/test_import_parsers_advanced.py` - 28 tests for all parsers

**Modified:**
- `requirements.txt` - Added mammoth, lxml, beautifulsoup4, bleach
- `src/import/parsers/__init__.py` - Export all parsers
- `src/import/parsers/*.py` (5 files) - Fixed imports from absolute to relative (avoiding `import` keyword)

## Decisions Made

**1. DOCX dual-library approach:**
- Use python-docx for structured extraction (paragraphs, tables, styles, metadata)
- Use mammoth for semantic HTML conversion
- Rationale: python-docx gives structure, mammoth gives clean HTML for rendering

**2. Server-side HTML sanitization with bleach:**
- Remove scripts, styles, comments
- Allow only safe tags: p, h1-h6, ul, ol, li, strong, em, a, br, table
- Rationale: Defense-in-depth security, prevents XSS attacks from imported content

**3. SCORM manifest search at any depth:**
- Search for imsmanifest.xml anywhere in ZIP, not just root
- Adjust resource paths relative to manifest location
- Warn user about non-standard structure
- Rationale: Real-world SCORM authoring tools export with wrapper folders (per RESEARCH.md pitfall)

**4. QTI namespace flexibility:**
- Try QTI 2.1 and 2.2 namespaces
- Fall back to non-namespaced xpath queries
- Handle root element being assessmentItem directly
- Rationale: Maximizes compatibility with QTI exports from various LMS platforms

**5. Relative imports to avoid keyword conflict:**
- Changed `from src.import.parsers.base_parser` to `from .base_parser`
- Rationale: Python treats `import` as a keyword, causing syntax errors in absolute imports

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed import keyword conflict in parser files**
- **Found during:** Task 2 (test execution)
- **Issue:** Plan 12-01 created parser files with absolute imports `from src.import.parsers.base_parser` which failed because `import` is a Python keyword
- **Fix:** Changed all imports to relative `from .base_parser` in 5 parser files (text, json, markdown, csv, zip)
- **Files modified:** text_parser.py, json_parser.py, markdown_parser.py, csv_parser.py, zip_parser.py
- **Verification:** All parsers import successfully, tests pass
- **Committed in:** 07e7809 (part of Task 2 commit)

**2. [Rule 1 - Bug] Fixed QTI parser to handle root assessmentItem element**
- **Found during:** Task 2 (test debugging)
- **Issue:** XPath `.//assessmentItem` doesn't match root element itself, only descendants. Tests failed because parser couldn't extract identifier/title from single-question QTI files.
- **Fix:** Added check for root element being assessmentItem before searching descendants. Fixed namespace handling to avoid empty xpath prefix errors.
- **Files modified:** src/import/parsers/qti_parser.py
- **Verification:** QTI parser test passes, extracts all fields correctly
- **Committed in:** 07e7809 (part of Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both auto-fixes necessary for functionality. The import keyword conflict was inherited from plan 12-01's parallel execution. No scope creep.

## Issues Encountered

**1. Python library installation required for testing:**
- **Issue:** Tests failed initially because mammoth, lxml, beautifulsoup4, bleach not installed
- **Resolution:** Ran `pip install mammoth lxml beautifulsoup4 bleach` to install dependencies
- **Outcome:** All 28 tests passing

**2. Python module caching during debugging:**
- **Issue:** QTI parser fixes didn't take effect immediately due to Python's `__pycache__`
- **Resolution:** Cleared pycache directories and used `py -B` flag to bypass caching
- **Outcome:** Changes properly reflected, tests passed

## User Setup Required

None - no external service configuration required. Libraries will be installed via `pip install -r requirements.txt`.

## Next Phase Readiness

**Ready for:**
- Import API endpoints (plan 12-03) can use these parsers
- Import UI (plan 12-04) can trigger parsing workflows
- Content migration tools can leverage advanced format support

**Capabilities enabled:**
- Import existing course content from DOCX documents
- Import course packages from SCORM LMS exports
- Import quiz questions from QTI interchange files
- Sanitize and clean HTML from external sources

**No blockers.** All parsers functional and tested with comprehensive coverage.

---
*Phase: 12-ai-interactive-features*
*Plan: 02*
*Completed: 2026-02-10*
