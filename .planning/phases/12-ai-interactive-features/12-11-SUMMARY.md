---
phase: 12-ai-interactive-features
plan: 11
subsystem: ui-editing
tags: [floating-toolbar, ai-editing, diff-preview, undo-redo, keyboard-shortcuts]
requires: [12-05-suggestion-engine, 12-06-autocomplete-bloom, 12-07-history]
provides: [floating-ai-toolbar, inline-editing-ui, suggestion-preview]
affects: []
tech-stack:
  added: []
  patterns: [floating-ui, selection-detection, inline-diff-rendering]
key-files:
  created:
    - templates/partials/ai-toolbar.html
    - static/css/components/ai-toolbar.css
    - static/js/components/ai-toolbar.js
  modified:
    - templates/studio.html
    - static/js/pages/studio.js
decisions:
  - choice: "Always-visible custom prompt input"
    rationale: "Per CONTEXT.md, custom prompt should be immediately accessible without expanding menu"
    impact: "Users can quickly type custom instructions without extra clicks"
  - choice: "Unicode icons instead of icon library"
    rationale: "Follows Phase 11 pattern of zero dependencies, works immediately"
    impact: "No external dependency, but may have rendering differences across systems"
  - choice: "Inline diff with <ins>/<del> tags"
    rationale: "Simple HTML-based diff for preview, no external diff library"
    impact: "Clear visual representation, works with existing CSS"
  - choice: "Position toolbar above selection"
    rationale: "Standard pattern for selection-based toolbars (Medium, Google Docs)"
    impact: "Familiar UX, though may require adjustment if near top of viewport"
metrics:
  duration: "~45 minutes"
  completed: "2026-02-11"
---

# Phase 12 Plan 11: Floating AI Toolbar Summary

**One-liner:** Floating toolbar with 10+ AI actions, inline diff preview, and undo/redo integration for inline text editing

## What Was Built

### Components

**1. Toolbar HTML Partial** (`templates/partials/ai-toolbar.html`)
- Floating container with `ai-toolbar` ID
- Quick action buttons: Improve, Expand, Simplify, Rewrite
- Extended actions dropdown: Fix Grammar, Make Academic, Make Conversational, Add Examples, Summarize
- Change Tone submenu: Formal, Friendly, Professional
- Always-visible custom prompt input field
- Inline diff preview area with Accept/Reject/Regenerate buttons
- Undo/Redo history controls
- Bloom's taxonomy level indicator badge
- Loading spinner for async operations

**2. Toolbar CSS** (`static/css/components/ai-toolbar.css`)
- Floating positioning with z-index 1000
- Dark theme styling: `#16213e` background, white text
- Box shadow for floating effect: `0 4px 12px rgba(0,0,0,0.3)`
- Button hover states with accent color transition
- Dropdown menu with submenu support
- Diff highlighting: green for `<ins>`, red for `<del>`
- Fade-in/fade-out animations for show/hide
- Responsive design: min 300px, max 500px width
- Mobile adjustments: hide labels, show icons only
- Bloom badge color gradients (blue → pink for Remember → Create)

**3. Toolbar JavaScript Controller** (`static/js/components/ai-toolbar.js`)
- `AIToolbar` class with attach/detach lifecycle
- Selection detection via `selectionchange` event
- Dynamic positioning using `getBoundingClientRect()`
- API integration:
  - `POST /api/edit/suggest` for AI suggestions
  - `POST /api/edit/history/push` for history tracking
  - `POST /api/edit/history/undo` for undo
  - `POST /api/edit/history/redo` for redo
- Inline diff generation (word-level comparison)
- Context-aware prompting (content type, Bloom level, learning outcomes)
- Keyboard shortcuts:
  - `Ctrl+Shift+I`: Improve
  - `Ctrl+Shift+E`: Expand
  - `Ctrl+Shift+S`: Simplify
  - `Ctrl+Z`: Undo
  - `Ctrl+Shift+Z`: Redo
- Session-scoped history with unique session IDs

**4. Studio Integration**
- Updated `templates/studio.html` to include toolbar partial and CSS
- Updated `static/js/pages/studio.js` to initialize AIToolbar
- Toolbar attaches to preview content area on activity selection
- Context passed from activity (content type, Bloom level, learning outcomes)
- `onContentChange` callback reloads course data after edits

## Architecture

### Selection Detection Flow
```
User selects text
  → selectionchange event fires
  → Check if selection within containerEl
  → Calculate position with getBoundingClientRect()
  → Position toolbar above selection (with viewport boundary check)
  → Show toolbar with fade-in animation
```

### AI Action Flow
```
User clicks action button
  → Close dropdown if open
  → Show loading state
  → POST to /api/edit/suggest with:
    - text: selected text
    - action: action type
    - context: {content_type, bloom_level, learning_outcomes}
  → Receive suggestion JSON
  → Generate inline diff HTML
  → Show preview with Accept/Reject/Regenerate buttons
  → On Accept:
    - Replace selected text in DOM
    - POST to /api/edit/history/push with EditCommand
    - Update undo/redo button states
    - Trigger onContentChange callback
```

### History Integration
```
On toolbar init:
  → Generate unique session ID
  → GET /api/edit/history/state to check can_undo/can_redo
  → Enable/disable buttons based on state

On Accept:
  → Push EditCommand to history:
    {
      type: 'ai_edit',
      action: action_type,
      original_text: selected_text,
      new_text: suggestion,
      position: character_offset
    }

On Undo:
  → POST /api/edit/history/undo
  → Receive command to revert
  → Trigger content reload
  → Update button states

On Redo:
  → POST /api/edit/history/redo
  → Receive command to reapply
  → Trigger content reload
  → Update button states
```

## UI/UX Patterns

### Toolbar Visibility
- Shows on text selection (length > 0)
- Hides on:
  - Click outside toolbar
  - Empty selection
  - Escape key press
  - Selection outside container

### Positioning
- Default: above selection, centered
- Boundary check: adjusts left position if would overflow viewport
- Maintains 8px minimum margin from edges

### Visual Feedback
- Loading spinner replaces toolbar content during API call
- Button hover: background changes to accent color
- Disabled buttons: 50% opacity, no pointer events
- Preview diff: green additions, red deletions
- Bloom badge: color-coded by cognitive level

### Accessibility
- All buttons have `title` attributes for tooltips
- Focus-visible outlines (2px solid accent color, 2px offset)
- ARIA labels on input fields
- Keyboard navigation supported
- Escape key closes toolbar

## Integration Points

### With Studio Page
- `StudioController.initAIToolbar()` creates new toolbar instance
- Attaches to `#preview-content` element
- Passes activity context (ID, content type, Bloom level)
- Passes course learning outcomes for context-aware suggestions
- `onContentChange` callback reloads course data

### With Edit API
- `POST /api/edit/suggest`: Get AI suggestion
- `POST /api/edit/history/push`: Record edit in history
- `POST /api/edit/history/undo`: Undo last edit
- `POST /api/edit/history/redo`: Redo last undone edit
- `GET /api/edit/history/state`: Check undo/redo availability

### With Toast Notifications
- Uses `window.toast.success()` for accepted suggestions
- Uses `window.toast.error()` for API failures
- Uses `window.toast.info()` for rejected suggestions

## Key Decisions

### 1. Always-Visible Custom Prompt
**Decision:** Custom prompt input is always visible in toolbar, not hidden behind dropdown

**Rationale:**
- CONTEXT.md specified custom prompt should be immediately accessible
- Users need quick access to custom instructions without extra clicks
- Follows modern AI tool patterns (ChatGPT, Claude, Notion AI)

**Alternatives Considered:**
- Hide behind dropdown: Would require extra click, less discoverable
- Separate modal: Would break inline editing flow

**Impact:**
- Toolbar is slightly taller (adds ~40px)
- Custom instructions more discoverable
- Faster workflow for power users

### 2. Unicode Icons
**Decision:** Use Unicode characters for action icons instead of icon library

**Rationale:**
- Follows Phase 11 pattern of zero external dependencies
- Works immediately without loading external resources
- Consistent with existing UI components

**Alternatives Considered:**
- Font Awesome: Would add external dependency, increase bundle size
- SVG icons: Would require separate icon files, more complex

**Impact:**
- No external dependency
- Potential rendering differences across platforms/fonts
- Can be replaced with icon library later if needed

### 3. Inline Diff with HTML Tags
**Decision:** Use `<ins>` and `<del>` HTML tags for diff preview

**Rationale:**
- Semantic HTML for insertions and deletions
- Works with simple CSS (green background for ins, red for del)
- No external diff library needed
- Clear visual representation

**Alternatives Considered:**
- External diff library (diff-match-patch): Would add dependency
- Side-by-side diff: Would require more complex layout
- Line-based diff: Less useful for inline text editing

**Impact:**
- Simple, lightweight implementation
- Works immediately without additional libraries
- May not show all diff nuances (word reordering, etc.)
- Good enough for inline editing use case

### 4. Position Above Selection
**Decision:** Toolbar appears above selected text by default

**Rationale:**
- Standard pattern for selection-based toolbars (Medium, Google Docs)
- Familiar UX for users
- Less likely to obscure content below selection

**Alternatives Considered:**
- Below selection: Would obscure content user is likely to edit next
- Fixed position: Would require users to look away from selection
- Inline with selection: Would break text flow

**Impact:**
- Familiar UX
- May require adjustment if selection near top of viewport
- Boundary checking ensures toolbar stays in viewport

## Testing Notes

### Manual Verification (Human Checkpoint)
- ✅ Toolbar appears on text selection in Studio preview
- ✅ All action buttons trigger API calls
- ✅ Suggestion preview shows diff with green/red highlighting
- ✅ Accept button replaces selected text
- ✅ Undo button reverts changes
- ✅ Redo button reapplies changes
- ✅ Custom prompt input works
- ✅ Keyboard shortcuts (Ctrl+Shift+I, Ctrl+Z) trigger actions
- ✅ Dropdown menu shows extended actions
- ✅ Toolbar hides on escape key and outside click

### Edge Cases Handled
- Empty selection: Toolbar hides
- Selection outside container: Toolbar doesn't show
- Toolbar near viewport edge: Position adjusted to stay in bounds
- API error: Loading state clears, error toast shown
- No history available: Undo/redo buttons disabled
- Custom prompt without text: Error toast shown

### Known Limitations
- Undo/redo applies to content area, not precise selection position
- Word-level diff may not catch all nuances (character-level changes)
- Unicode icons may render differently across systems
- Mobile view hides button labels (icon-only)

## Next Phase Readiness

### Blocks Future Plans
None - this is a self-contained UI component

### Enables Future Plans
- **12-12 Coach Chat UI**: Can use similar floating toolbar pattern
- **Future inline annotations**: Toolbar pattern reusable for comments
- **Future collaborative editing**: Toolbar could show co-editor actions

### Dependencies Satisfied
- ✅ Requires 12-05 (Suggestion Engine): API endpoints available
- ✅ Requires 12-06 (Autocomplete): Bloom analyzer for badge
- ✅ Requires 12-07 (History): Undo/redo API available

### Open Questions
None - all functionality verified during checkpoint

## Deviations from Plan

None - plan executed exactly as written.

## Files Modified

### Created
- `templates/partials/ai-toolbar.html` (93 lines)
- `static/css/components/ai-toolbar.css` (359 lines)
- `static/js/components/ai-toolbar.js` (663 lines)

### Modified
- `templates/studio.html` (+6 lines): Include toolbar partial, CSS, JS
- `static/js/pages/studio.js` (+29 lines): Initialize AIToolbar on activity selection

### Total Changes
- 3 files created
- 2 files modified
- ~1150 lines added

## Commit History

1. **1b0ddc4** - `feat(12-11): create floating toolbar partial and styles`
   - AI toolbar HTML partial with quick actions, dropdown, custom prompt
   - Toolbar CSS with floating positioning, z-index 1000
   - Dark theme styling with accent colors and shadows
   - Diff preview with green additions, red deletions
   - Animation for show/hide transitions
   - Responsive design for mobile
   - Bloom's level indicator badge
   - History controls (undo/redo buttons)

2. **6c267b4** - `feat(12-11): create toolbar JavaScript controller`
   - AIToolbar class with selection detection and positioning
   - API integration with /api/edit/suggest endpoint
   - Inline diff preview with accept/reject/regenerate
   - History integration with undo/redo via /api/edit/history
   - Keyboard shortcuts (Ctrl+Shift+I/E/S, Ctrl+Z, Ctrl+Shift+Z)
   - Custom prompt input with always-visible pattern
   - Dropdown menu for extended actions
   - Studio integration: attach toolbar to preview content
   - Context-aware prompting with learning outcomes, bloom level

## Success Metrics

- ✅ Floating toolbar positions correctly above selection
- ✅ All 10+ action types work (Improve, Expand, Simplify, Rewrite, Fix Grammar, Make Academic, Make Conversational, Add Examples, Summarize, Change Tone)
- ✅ Diff preview clearly shows changes with color coding
- ✅ History integration enables undo/redo
- ✅ Keyboard shortcuts trigger actions
- ✅ Human verification passed

**Plan completed successfully.**
