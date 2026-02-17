---
phase: 11
plan: 05
subsystem: ui-builder
tags: [tree, drag-drop, crud, javascript]
completed: 2026-02-10
duration: ~6 minutes

dependency-graph:
  requires: [11-01, 11-03]
  provides: [builder-page, tree-component, course-structure-ui]
  affects: [11-06, 11-07]

tech-stack:
  added: []
  patterns: [hierarchical-tree, drag-drop-reorder, inline-edit, modal-crud]

key-files:
  created:
    - static/js/components/tree.js
    - static/js/pages/builder.js
    - static/css/pages/builder.css
    - templates/builder.html
  modified:
    - app.py

decisions:
  - id: tree-expand-state-localstorage
    choice: Persist expand/collapse state in localStorage per course
    rationale: Maintains user preferences across page refreshes
  - id: drag-drop-same-level-only
    choice: Only allow reordering within same level and parent
    rationale: Prevents structural confusion, matches API capabilities
  - id: inline-edit-blur-save
    choice: Save inline edits on blur event
    rationale: Natural UX pattern, immediate feedback without explicit save button

metrics:
  tasks-completed: 3/3
  files-created: 4
  files-modified: 1
  lines-added: ~1950
---

# Phase 11 Plan 05: Builder Page Summary

**One-liner:** Hierarchical tree editor with drag-drop reordering for course modules, lessons, and activities.

## What Was Built

### 1. HierarchicalTree Component (static/js/components/tree.js)

A reusable tree component providing:

- **Expand/Collapse**: Toggle visibility of nested children with localStorage persistence
- **Node Selection**: Click to select, callback for detail panel updates
- **Drag and Drop**: Reorder items within same level (modules with modules, lessons within module, activities within lesson)
- **Visual Feedback**: Drop indicator line, dragging opacity, hover states
- **Content Icons**: Different icons for content types (video, reading, quiz, etc.)
- **Build State Display**: Color-coded badges showing draft/generated/approved/published

Key methods:
- `render(course)` - Build tree from course data
- `toggleNode(nodeId)` - Expand/collapse with state persistence
- `selectNode(nodeId, nodeType)` - Set selection with callback
- `onDragStart/Over/Drop/End` - Full drag-drop lifecycle

### 2. Builder Page Template (templates/builder.html)

Two-column layout:
- **Left Panel (60%)**: Tree container with add module button, expand/collapse all
- **Right Panel (40%)**: Detail panel showing selected item properties

Detail Views:
- **Module**: Title (editable), description (editable), lesson count, order, add lesson button
- **Lesson**: Title (editable), activity count, parent module, add activity button
- **Activity**: Title (editable), content type, activity type dropdown, WWHAA phase dropdown, build state badge, generate content button

Modal Dialogs:
- Add Module: Title and description fields
- Add Lesson: Title field, shows parent module
- Add Activity: Title, content type, activity type dropdowns
- Delete Confirmation: Warning text with cascade notice for items with children

### 3. Builder Page CSS (static/css/pages/builder.css)

Styling for:
- Two-column flex layout with responsive breakpoints
- Tree structure with indentation and icons
- Expand/collapse animations
- Drag-drop visual states (dragging, drop indicator, drag-over)
- Detail panel form layouts
- Build state color coding
- Responsive design for tablet/mobile

### 4. BuilderController (static/js/pages/builder.js)

Controller connecting tree and detail panel:

- **Tree Integration**: Instantiates HierarchicalTree with callbacks
- **Selection Handling**: Updates detail panel when tree node selected
- **Inline Editing**: Blur save for title, description, dropdowns
- **CRUD Operations**:
  - Add module via POST /api/courses/{id}/modules
  - Add lesson via POST /api/courses/{id}/modules/{mid}/lessons
  - Add activity via POST /api/courses/{id}/lessons/{lid}/activities
  - Delete via DELETE endpoints with confirmation
- **Reorder**: Calls PUT /api/courses/{id}/[modules|lessons|activities]/reorder
- **Navigation**: Generate Content button links to Studio page

### 5. Builder Route (app.py)

New route at `/courses/<course_id>/builder`:
- Requires authentication
- Loads course data
- Renders builder.html with course and active_page context

## Verification Results

All success criteria met:
- [x] Hierarchical tree displays modules > lessons > activities
- [x] Expand/collapse state persists in localStorage
- [x] Drag-drop reordering works within same level
- [x] Selection shows details in right panel
- [x] Inline editing updates item title on blur
- [x] Add operations use modal dialogs
- [x] Delete requires confirmation
- [x] "Generate Content" links to Studio page
- [x] All operations show toast feedback (via global toast utility)

## API Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| /api/courses/{id} | GET | Load course with full structure |
| /api/courses/{id}/modules | POST | Create module |
| /api/courses/{id}/modules/{mid} | PUT | Update module |
| /api/courses/{id}/modules/{mid} | DELETE | Delete module |
| /api/courses/{id}/modules/reorder | PUT | Reorder modules |
| /api/courses/{id}/modules/{mid}/lessons | POST | Create lesson |
| /api/courses/{id}/lessons/{lid} | PUT | Update lesson |
| /api/courses/{id}/lessons/{lid} | DELETE | Delete lesson |
| /api/courses/{id}/modules/{mid}/lessons/reorder | PUT | Reorder lessons |
| /api/courses/{id}/lessons/{lid}/activities | POST | Create activity |
| /api/courses/{id}/activities/{aid} | PUT | Update activity |
| /api/courses/{id}/activities/{aid} | DELETE | Delete activity |
| /api/courses/{id}/lessons/{lid}/activities/reorder | PUT | Reorder activities |

## Deviations from Plan

None - plan executed exactly as written.

## Next Phase Readiness

Builder page is complete. Ready for:
- 11-06: Studio Page (content generation interface)
- 11-07: Textbook Page (chapter generation interface)
