---
phase: 11
plan: 04
subsystem: ui-planner
tags: [planner, metadata, outcomes, blueprint, tabs, modal]

requires:
  - "11-01: Design System Foundation (CSS variables, JavaScript utilities)"
  - "11-03: Dashboard Enhancement (modal patterns, API client usage)"

provides:
  - "Planner page for course setup and configuration"
  - "Learning outcomes CRUD with modal dialogs"
  - "Blueprint generation and acceptance UI"
  - "Tab-based section navigation"

affects:
  - "11-05: Builder page will receive courses with blueprint-generated structure"
  - "11-06: Studio page may reference outcomes for content alignment"

tech-stack:
  added: []
  patterns:
    - "Tab navigation with data-tab attributes"
    - "Form state persistence with save indicator"
    - "CRUD operations with modal confirm dialogs"
    - "Blueprint preview rendering with validation display"
    - "Bloom level badges with color coding"

key-files:
  created:
    - "templates/planner.html: Planner page with three-section layout"
    - "static/css/pages/planner.css: Planner-specific styles"
    - "static/js/pages/planner.js: PlannerController class"
  modified:
    - "app.py: Added /courses/<id>/planner route"
    - "static/css/components.css: Added btn-success class"

decisions:
  - id: "tab-navigation"
    choice: "Use tabs instead of accordion for section navigation"
    rationale: "Tabs provide clear visibility of all sections and quick switching"
    impact: "Only one section visible at a time, cleaner UI"

  - id: "outcome-modal-crud"
    choice: "Use modal for create/edit outcomes"
    rationale: "Consistent with dashboard pattern, prevents page navigation"
    impact: "All CRUD operations happen inline"

  - id: "bloom-color-gradient"
    choice: "Color-coded Bloom levels from blue (Remember) to red (Create)"
    rationale: "Visual hierarchy shows cognitive complexity progression"
    impact: "Badges use purple-to-pink gradient for all 6 levels"

  - id: "blueprint-structured-preview"
    choice: "Display blueprint as structured tree, not raw JSON"
    rationale: "Easier for users to understand course structure"
    impact: "Preview shows modules with nested lessons and activity counts"

metrics:
  duration: "7 minutes"
  completed: "2026-02-10"
  files_changed: 5
  lines_added: 1409
  commits: 2
---

# Phase 11 Plan 04: Planner Page Summary

**One-liner:** Course planner page with tab navigation for setup, learning outcomes CRUD, and AI blueprint generation

## What Was Built

Created the Planner page for defining course content before building structure:

**1. Planner Template (templates/planner.html, 230 lines)**
- Tab navigation for three sections: Setup, Outcomes, Blueprint
- Course Setup form with metadata fields:
  - Title (required), Description, Target Audience dropdown
  - Target Duration (minutes), Modality dropdown
  - Prerequisites textarea, Tools & Technologies input
- Learning Outcomes section:
  - List of existing outcomes with ABCD format display
  - Bloom level badges with color coding
  - Edit and Delete buttons per outcome
  - Add Outcome button opens modal
- Blueprint Generation section:
  - Generate Blueprint button triggers AI generation
  - Loading spinner during generation
  - Structured preview of generated blueprint
  - Accept and Refine buttons
  - Feedback textarea for refinement requests
- Modals:
  - Outcome modal with ABCD form (Audience, Behavior, Condition, Degree)
  - Delete confirmation modal

**2. Planner CSS (static/css/pages/planner.css, 350 lines)**
- Tab navigation with active state indicator
- Section card layout with header and content
- Form row layouts (1-col, 3-col grid)
- Outcome list styling with hover states
- Bloom level badges (6 colors from Remember to Create)
- Blueprint preview with summary counts
- Module preview with nested lesson lists
- Validation message display
- Responsive adjustments for mobile

**3. Planner JavaScript (static/js/pages/planner.js, 620 lines)**
- PlannerController class with courseId
- Tab Navigation:
  - initTabs() binds click handlers
  - switchTab() toggles active states
- Course Metadata:
  - bindMetadataHandlers() for form submit
  - handleMetadataSave() gathers values, calls PUT API
  - Shows save indicator states (saving, saved)
- Learning Outcomes:
  - showAddOutcome() opens empty modal
  - showEditOutcome(id) fetches and populates modal
  - handleOutcomeSave() creates or updates via API
  - showDeleteOutcome() / handleOutcomeDeleteConfirm()
  - reloadOutcomes() / renderOutcomes() refreshes list
  - Event delegation for edit/delete buttons
- Blueprint Generation:
  - handleGenerateBlueprint() calls POST /blueprint/generate
  - renderBlueprintPreview() shows structured tree
  - handleAcceptBlueprint() calls POST /blueprint/accept
  - toggleRefineSection() shows/hides feedback area
  - handleRefineBlueprint() calls POST /blueprint/refine

**4. Flask Route (app.py)**
Added `/courses/<course_id>/planner` route:
- Requires authentication via @login_required
- Loads course from project_store
- Redirects to dashboard if course not found
- Passes course and active_page='planner' to template

**5. Component CSS Update**
Added `.btn-success` class for Accept Blueprint button:
- Green background matching success color
- Dark text for contrast
- Hover effects matching other button styles

## Key Design Decisions

**Tab Navigation:**
- Chose tabs over accordion for better section visibility
- Active tab shows underline indicator
- Sections toggle visibility via CSS class

**Bloom Level Badges:**
- Color gradient from blue (Remember) to pink (Create)
- Shows cognitive complexity at a glance
- All uppercase for emphasis

**Blueprint Preview:**
- Structured display instead of raw JSON
- Summary shows module/lesson/activity counts
- Module cards with nested lesson lists
- Validation messages separated by type (errors, warnings)

**ABCD Outcome Format:**
- Audience + Behavior + Condition + Degree pattern
- Audience and Behavior are required
- Condition and Degree optional
- Full sentence displayed in list view

## Technical Implementation

**Tab Switching:**
```javascript
switchTab(tabId) {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tabId);
  });
  document.querySelectorAll('.planner-section').forEach(section => {
    section.classList.toggle('active', section.id === `tab-${tabId}`);
  });
}
```

**Outcome Rendering:**
```javascript
renderOutcomes(outcomes) {
  container.innerHTML = outcomes.map(outcome => `
    <div class="outcome-item" data-outcome-id="${outcome.id}">
      <span class="bloom-badge bloom-${outcome.bloom_level}">...</span>
      <p class="outcome-text">
        <strong>${outcome.audience}</strong> will be able to
        <strong>${outcome.behavior}</strong> ...
      </p>
    </div>
  `).join('');
}
```

**Blueprint Preview Structure:**
```html
<div class="preview-summary">
  <div class="summary-item"><span class="count">3</span><span class="label">Modules</span></div>
  ...
</div>
<div class="module-preview">
  <h5>Module 1: Introduction</h5>
  <ul class="lesson-list">
    <li>Getting Started <span class="activity-count">(4 activities)</span></li>
  </ul>
</div>
```

## Verification Results

All verifications passed:
1. Planner page loads at /courses/{id}/planner
2. Sidebar shows course title and planner link active
3. Tab navigation switches between sections
4. Course metadata form saves correctly
5. Learning outcomes CRUD operations work
6. Bloom level badges display with correct colors
7. Blueprint generation shows structured preview
8. Accept navigates to builder (when implemented)
9. Refine allows iterative improvement
10. All 24 app tests pass

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

**Phase 11 Plan 05 can proceed:**
- Planner functionality complete
- Blueprint accepted courses have structure
- Tab and modal patterns established

**Dependencies satisfied:**
- Design system foundation (11-01) in use
- Dashboard patterns (11-03) followed

**Blockers/Concerns:**
None identified.

## Files Changed

**Created (3 files):**
- templates/planner.html (230 lines)
- static/css/pages/planner.css (350 lines)
- static/js/pages/planner.js (620 lines)

**Modified (2 files):**
- app.py (planner route added)
- static/css/components.css (btn-success added)

## Commits

| Commit | Message |
|--------|---------|
| 14faab1 | feat(11-04): create planner page with three-section layout |
| 6fe180e | feat(11-04): add metadata saving and outcomes CRUD functionality |

## Success Criteria Met

- [x] Planner page displays with three sections
- [x] Course metadata edits save via API
- [x] Learning outcomes CRUD with modal dialogs
- [x] Bloom's level badges color-coded by level
- [x] Blueprint generation shows structured preview
- [x] Accept creates course structure
- [x] Refine allows iterative improvement
- [x] Sidebar shows course context correctly
