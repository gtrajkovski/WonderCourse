---
phase: 11
title: UI Implementation
created: 2026-02-10
status: decisions-locked
---

# Phase 11: UI Implementation Context

User decisions gathered via `/gsd:discuss-phase 11`. These guide research and planning.

## Decisions

### Page Layout & Navigation

**Left Navigation**
- Collapsible sidebar: expanded by default (240px), collapse to icons-only (60px)
- Collapse button at bottom of nav
- State persisted in localStorage
- Current course title pinned at top (above page links)
- Click course title returns to that course's view

**Header Bar**
- Left: App logo (clickable → main dashboard)
- Center: Breadcrumb trail (Course Name › Module › Lesson › Activity)
- Right: Save indicator (synced/saving/error) + user avatar dropdown

**Page Transitions**
- Full page loads (Jinja2 templates)
- Preserve scroll position when returning to pages
- Loading skeleton shows instantly, content fills in
- Current nav item highlighted immediately on click

### Content Generation UX

**Generation Trigger**
- Primary: Button in activity detail panel
- Secondary: Bulk "generate all" option in toolbar for multiple activities

**Progress Feedback**
- Streaming text appearing in real-time (shows progress naturally)
- No artificial progress stages

**Result Presentation**
- Generated content appears in preview pane
- Side-by-side diff view when regenerating existing content

**Edit Flow**
- Inline quick edits directly in preview
- Full editor modal available for major changes
- Both options always accessible

### Builder Tree Interactions

**Tree Structure**
- Hierarchical: Course → Modules → Lessons → Activities
- All levels collapsible with expand/collapse toggles
- Expand/collapse state persisted

**Drag & Drop**
- Full reordering within levels (reorder modules, lessons, activities)
- Cross-level moves where valid (move lesson between modules)
- Visual drop indicators (line between items, highlight valid targets)

**Selection & Editing**
- Single-click: select item, show details in right panel
- Double-click: inline rename
- Keyboard: Delete key with confirmation dialog

**Add/Delete**
- "+" buttons visible at each tree level
- Right-click context menu for all actions
- Delete requires confirmation modal

### Dark Theme Specifics

**Color Palette**
- Background: #1a1a2e (base), #16213e (panels/cards), #0f0f1a (inputs)
- Accent: #4361ee (electric blue) for primary actions
- Success: Green tint for "generated" and "approved" states
- Error: Red for validation issues and delete actions

**Text Hierarchy**
- Primary text: #ffffff
- Secondary text: #a0a0a0
- Disabled/placeholder: #606060

**Borders & Dividers**
- Subtle borders: #2a2a4a
- Avoid harsh contrasts
- Consistent 1px borders on cards and inputs

**Component Styling**
- Buttons: Filled primary (#4361ee), ghost secondary
- Inputs: Dark background (#0f0f1a) with subtle border
- Cards: #16213e with subtle border, slight shadow

## Claude's Discretion

Implementation details Claude can decide:
- Specific CSS framework or vanilla CSS approach
- Animation timing and easing functions
- Exact icon set (Font Awesome, Heroicons, etc.)
- Form validation UX details
- Toast/notification positioning and timing
- Modal backdrop opacity

## Deferred Ideas

Not in scope for Phase 11:
- Real-time collaboration indicators
- Keyboard shortcut overlay/help
- Customizable theme colors
- Mobile responsive layout (desktop-focused tool)
- Undo/redo UI (backend support only)
