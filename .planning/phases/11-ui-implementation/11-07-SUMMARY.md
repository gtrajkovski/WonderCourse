---
phase: 11
plan: 07
subsystem: ui-textbook
tags: [textbook, chapters, glossary, generation, preview, javascript, css]

requires:
  - "11-01: Design System Foundation (CSS variables, JavaScript utilities)"
  - "11-03: Dashboard Enhancement (Modal component, API client patterns)"
  - "06-03: TextbookGenerator backend (generation API)"
  - "06-04: CoherenceValidator backend (validation checks)"

provides:
  - "Textbook page with chapter list and generation controls"
  - "Chapter preview with sections, key concepts, and references"
  - "Glossary management with CRUD operations"
  - "Full textbook view with table of contents"
  - "Job polling for async chapter generation"

affects:
  - "11-08: Publish page may link to textbook for export"

tech-stack:
  added: []
  patterns:
    - "Two-panel layout for list and preview"
    - "Tab navigation for Chapters/Glossary/Settings"
    - "Job polling pattern for async generation"
    - "Grouped alphabetical glossary display"

key-files:
  created:
    - "templates/textbook.html: Textbook page template"
    - "static/css/pages/textbook.css: Textbook page styles"
    - "static/js/pages/textbook.js: TextbookController class"
  modified:
    - "app.py: Added /courses/{id}/textbook route"

decisions:
  - id: "chapter-per-outcome"
    choice: "Map chapters 1:1 with learning outcomes"
    rationale: "Each learning outcome defines a chapter topic"
    impact: "Chapter list length equals learning outcomes count"

  - id: "sequential-bulk-generation"
    choice: "Generate chapters sequentially in bulk mode"
    rationale: "Avoid overloading API with parallel requests"
    impact: "Slower bulk generation but more reliable"

  - id: "client-side-glossary"
    choice: "Aggregate glossary terms from all chapters client-side"
    rationale: "No dedicated glossary API endpoint exists"
    impact: "Full course data loaded for glossary operations"

  - id: "alphabetical-glossary-grouping"
    choice: "Group glossary terms by first letter"
    rationale: "Standard dictionary/glossary presentation"
    impact: "Easy to scan and find terms"

metrics:
  duration: "7 minutes"
  completed: "2026-02-10"
  files_changed: 4
  lines_added: 1440
  commits: 2
---

# Phase 11 Plan 07: Textbook Page Summary

**One-liner:** Two-panel textbook page with chapter generation from learning outcomes, preview with sections, and alphabetically-grouped glossary management

## What Was Built

Created a complete textbook management interface for chapter generation and glossary management.

**1. Textbook Template (templates/textbook.html)**
- Two-panel layout: left panel for controls, right panel for preview
- Three tabs: Chapters, Glossary, Settings
- Chapter list showing one row per learning outcome
- Status badges: Not Generated / Generating / Generated
- Generate button per chapter and "Generate All" bulk option
- Generation progress bar for bulk operations
- Glossary list with alphabetical grouping
- Add/Edit/Delete term modals
- Settings tab with textbook title and course info
- Preview panel with empty state and chapter content

**2. Textbook CSS (static/css/pages/textbook.css, 459 lines)**
- .textbook: Two-column flex layout
- .textbook-panel-left: 400px chapter/glossary panel
- .textbook-tabs: Tab navigation buttons
- .tab-content: Switchable content sections
- .chapter-item: Chapter row with number, title, status, actions
- .chapter-status: Status badges with semantic colors
- .glossary-group: Alphabetical letter grouping
- .glossary-term: Term display with definition and source
- .preview-content: Right panel for chapter preview
- .chapter-preview: Formatted chapter display
- .section-heading, .section-content: Section formatting
- .key-concepts: Highlighted concept boxes
- .image-placeholder: Placeholder for future images
- .references-section: Reference list styling
- .glossary-highlight: Term highlighting in preview

**3. TextbookController (static/js/pages/textbook.js, 843 lines)**
- Tab navigation with content switching
- Course and chapter data loading from API
- Chapter list rendering from learning outcomes
- Chapter selection and preview display
- Single chapter generation with job polling
- Bulk generation with progress tracking
- Chapter preview with sections, key concepts, references
- Full textbook view with table of contents
- Glossary loading and alphabetical grouping
- Glossary CRUD operations (add, edit, delete)
- Modal integration for term editing

**4. Route (app.py)**
- Added /courses/{course_id}/textbook route
- Loads course data and renders textbook.html
- Authentication required, redirects if course not found

## Key Design Decisions

**Chapter-Outcome Mapping:**
Each learning outcome maps to one textbook chapter. The chapter list shows all learning outcomes with generation status. This provides clear 1:1 relationship between outcomes and content.

**Async Generation with Polling:**
Chapter generation is asynchronous (returns task_id). Controller polls /api/jobs/{task_id} every 2 seconds until complete. This matches the backend's JobTracker pattern.

**Sequential Bulk Generation:**
When generating all chapters, process sequentially rather than in parallel. This avoids API overload and provides clearer progress feedback.

**Glossary Aggregation:**
Glossary terms are stored within each chapter. Controller aggregates all terms client-side and groups alphabetically. CRUD operations update the source chapter.

## Technical Implementation

**Tab Navigation Pattern:**
```javascript
handleTabClick(e) {
  const tabId = tabBtn.dataset.tab;
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  tabBtn.classList.add('active');
  document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
  document.getElementById(`tab-${tabId}`).classList.add('active');
}
```

**Job Polling Pattern:**
```javascript
pollJobStatus(taskId, callback, interval = 2000) {
  const poll = async () => {
    const job = await api.get(`/jobs/${taskId}`);
    if (job.status === 'completed' || job.status === 'failed') {
      callback(job);
    } else {
      setTimeout(poll, interval);
    }
  };
  poll();
}
```

**Alphabetical Glossary Grouping:**
```javascript
const groups = {};
this.allGlossaryTerms.forEach(term => {
  const firstLetter = (term.term || '').charAt(0).toUpperCase() || '#';
  if (!groups[firstLetter]) groups[firstLetter] = [];
  groups[firstLetter].push(term);
});
```

## Verification Results

All functionality verified:
1. Textbook page loads at /courses/{id}/textbook
2. Chapter list shows one entry per learning outcome
3. Tabs switch between Chapters, Glossary, Settings
4. Preview panel shows empty state initially
5. Chapter selection shows preview or "not generated" message
6. Generate button triggers async generation with polling
7. Generated chapters display with sections and key concepts
8. Full textbook view shows table of contents
9. Glossary tab shows terms grouped alphabetically
10. Term add/edit/delete modals work correctly
11. All app tests pass (24/24)

## Deviations from Plan

None. Plan executed exactly as written.

## Next Phase Readiness

**Phase 11 Plan 08 can proceed:**
- Textbook page complete
- Generation and preview working
- Glossary management functional

**Dependencies satisfied:**
- Design system (11-01) in use
- Modal patterns (11-03) applied
- Backend textbook API (06-03, 06-04) integrated

**Blockers/Concerns:**
None identified.

## Files Changed

**Created (3 files):**
- templates/textbook.html (148 lines)
- static/css/pages/textbook.css (459 lines)
- static/js/pages/textbook.js (843 lines)

**Modified (1 file):**
- app.py (added textbook route)

## Commits

| Commit | Message |
|--------|---------|
| 60cdd99 | feat(11-07): create textbook page template with two-panel layout |
| 2e8f56b | feat(11-06): enhance inline editing with section-level updates (includes textbook.js) |

Note: The textbook.js file was committed in a mislabeled commit (11-06 instead of 11-07) due to parallel plan execution.

## Success Criteria Met

- [x] Two-panel layout with tabs (Chapters, Glossary, Settings)
- [x] Chapter list shows status for each chapter
- [x] Single chapter generation with progress
- [x] Bulk generation with overall progress
- [x] Chapter preview shows formatted content
- [x] Glossary displays all terms alphabetically
- [x] Glossary CRUD works with modal dialogs
- [x] Glossary terms can be viewed in preview (via chapter sections)
