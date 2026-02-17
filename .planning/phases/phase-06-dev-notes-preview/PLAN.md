# Phase 6: Developer Notes + Preview Mode

## Overview

Add internal documentation capabilities for content authors and learner-facing preview mode for content review.

**Developer Notes** are internal annotations that help authors track TODOs, reminders, and context that shouldn't appear in learner exports. Different from the existing Comment system (which is for team discussion), notes are personal author aids.

**Preview Mode** lets authors see content as learners would experience it, without author-only elements like dev notes, edit controls, or metadata.

## Implementation Plans

### Plan 1: Developer Note Model

**Create `DeveloperNote` dataclass in `src/core/models.py`**

```python
@dataclass
class DeveloperNote:
    """Internal note attached to a course element.

    Notes are visible to authors in the studio but excluded from
    learner exports. They serve as TODOs, reminders, or context.
    """
    id: str = field(default_factory=lambda: f"note_{uuid.uuid4().hex[:8]}")
    content: str = ""
    author_id: int = 0
    author_name: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    pinned: bool = False  # Pinned notes show first

    def to_dict(self) -> Dict[str, Any]: ...

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeveloperNote": ...
```

**Add `developer_notes` field to Activity, Lesson, Module, Course:**
```python
developer_notes: List[DeveloperNote] = field(default_factory=list)
```

**Update `to_dict()` and `from_dict()` for each model.**

---

### Plan 2: Developer Notes API

**Create `src/api/notes.py`**

```python
notes_bp = Blueprint('notes', __name__)

# GET /api/courses/<course_id>/notes
# Returns all notes in course (activities, lessons, modules, course-level)

# POST /api/courses/<course_id>/notes
# Create note at course level
# Body: { "content": "...", "pinned": false }

# POST /api/courses/<course_id>/modules/<module_id>/notes
# Create note on module

# POST /api/courses/<course_id>/lessons/<lesson_id>/notes
# Create note on lesson

# POST /api/courses/<course_id>/activities/<activity_id>/notes
# Create note on activity

# PUT /api/courses/<course_id>/notes/<note_id>
# Update note content or pinned status
# Body: { "content": "...", "pinned": true }

# DELETE /api/courses/<course_id>/notes/<note_id>
# Delete a note
```

**Register blueprint in `app.py`.**

---

### Plan 3: Studio Notes Panel

**Modify `templates/studio.html`**

Add collapsible notes panel below preview content:

```html
<!-- Notes Panel -->
<div class="notes-panel" id="notes-panel" style="display: none;">
    <div class="notes-header">
        <h4>Developer Notes</h4>
        <button class="btn btn-small" id="btn-add-note">+ Add Note</button>
    </div>
    <div class="notes-list" id="notes-list">
        <!-- Notes rendered here -->
    </div>
</div>
```

**Modify `static/js/pages/studio.js`**

Add methods:
- `loadActivityNotes()` - Fetch notes for selected activity
- `renderNotes()` - Display notes list
- `handleAddNote()` - Create new note
- `handleEditNote()` - Update note
- `handleDeleteNote()` - Delete note
- `handleTogglePin()` - Toggle pinned status

**Modify `static/css/pages/studio.css`**

Add styles for notes panel, note cards, pinned indicator.

---

### Plan 4: Preview Mode Toggle

**Modify `templates/studio.html`**

Add preview mode toggle in preview header:

```html
<div class="preview-header" id="preview-header">
    <h3 class="preview-title" id="preview-title">Select an Activity</h3>
    <div class="preview-mode-toggle">
        <button class="toggle-btn active" id="btn-author-view" title="Author view with notes and controls">
            Author
        </button>
        <button class="toggle-btn" id="btn-learner-preview" title="Preview as learner sees it">
            Learner
        </button>
    </div>
    <span class="preview-badge" id="preview-badge" style="display: none;"></span>
</div>
```

**Add viewport selector for learner preview:**

```html
<div class="viewport-selector" id="viewport-selector" style="display: none;">
    <button class="viewport-btn active" data-viewport="desktop" title="Desktop view">Desktop</button>
    <button class="viewport-btn" data-viewport="tablet" title="Tablet view">Tablet</button>
    <button class="viewport-btn" data-viewport="mobile" title="Mobile view">Mobile</button>
</div>
```

---

### Plan 5: Learner Preview Renderer

**Create `src/utils/preview_renderer.py`**

Transforms content into learner-facing HTML:

```python
class PreviewRenderer:
    """Renders content as learners would see it."""

    def render_video_script(self, content: dict) -> str:
        """Render video script as formatted HTML."""
        # Title, learning objective, sections
        # No speaker notes (author-only)

    def render_reading(self, content: dict) -> str:
        """Render reading as formatted HTML."""
        # Title, intro, sections, conclusion, references

    def render_quiz(self, content: dict) -> str:
        """Render quiz as learner would see."""
        # Questions, options (no correct answer indicators)
        # No explanations until after answer

    def render_content(self, content_type: str, content: dict) -> str:
        """Dispatch to appropriate renderer."""
```

**Add API endpoint in `src/api/content.py`:**

```python
@content_bp.route('/api/courses/<course_id>/activities/<activity_id>/preview', methods=['GET'])
def get_learner_preview(course_id, activity_id):
    """Get learner-facing preview HTML for activity content."""
    # Returns { "html": "...", "viewport_css": "..." }
```

---

### Plan 6: Preview Mode JS Implementation

**Modify `static/js/pages/studio.js`**

Add preview mode state and methods:

```javascript
class StudioController {
    constructor() {
        // ...
        this.previewMode = 'author';  // 'author' | 'learner'
        this.viewport = 'desktop';     // 'desktop' | 'tablet' | 'mobile'
    }

    handleTogglePreviewMode(mode) {
        this.previewMode = mode;
        // Update UI buttons
        // Re-render preview
        // Show/hide notes panel
        // Show/hide viewport selector
    }

    handleViewportChange(viewport) {
        this.viewport = viewport;
        // Apply viewport width constraints
        // Re-render preview
    }

    async fetchLearnerPreview() {
        // Call /api/.../preview endpoint
        // Render HTML in preview pane
    }
}
```

---

### Plan 7: CSS and Styling

**Modify `static/css/pages/studio.css`**

```css
/* Preview Mode Toggle */
.preview-mode-toggle {
    display: flex;
    gap: 4px;
    background: var(--bg-hover);
    border-radius: var(--radius-sm);
    padding: 2px;
}

.toggle-btn {
    padding: 4px 12px;
    border: none;
    background: transparent;
    cursor: pointer;
    border-radius: var(--radius-sm);
}

.toggle-btn.active {
    background: var(--accent-primary);
    color: white;
}

/* Viewport Selector */
.viewport-selector { ... }

/* Viewport Constraints */
.preview-content.viewport-tablet {
    max-width: 768px;
    margin: 0 auto;
}

.preview-content.viewport-mobile {
    max-width: 375px;
    margin: 0 auto;
}

/* Notes Panel */
.notes-panel { ... }
.note-card { ... }
.note-card.pinned { ... }
```

---

### Plan 8: Export Integration

**Modify export functions to respect notes visibility**

Notes should NOT appear in:
- SCORM exports
- LMS manifest exports
- Instructor packages (unless toggled)

**Add export option in `src/api/export.py`:**

```python
# Option to include dev notes in instructor package only
include_dev_notes: bool = False
```

---

## Files to Create

| File | Description |
|------|-------------|
| `src/api/notes.py` | Developer notes API endpoints |
| `src/utils/preview_renderer.py` | Learner-facing content renderer |
| `tests/test_notes_api.py` | API tests for notes |
| `tests/test_preview_renderer.py` | Preview rendering tests |

## Files to Modify

| File | Changes |
|------|---------|
| `src/core/models.py` | Add DeveloperNote dataclass, add developer_notes to Activity/Lesson/Module/Course |
| `app.py` | Register notes blueprint |
| `templates/studio.html` | Add notes panel, preview mode toggle, viewport selector |
| `static/js/pages/studio.js` | Add notes and preview mode handlers |
| `static/css/pages/studio.css` | Add notes panel and preview mode styles |
| `src/api/content.py` | Add /preview endpoint |
| `src/api/export.py` | Add dev notes export option |

## Verification

1. **Notes API tests:** `pytest tests/test_notes_api.py`
2. **Preview tests:** `pytest tests/test_preview_renderer.py`
3. **Manual testing:**
   - Create notes on activity, verify they appear in studio
   - Toggle to Learner Preview, verify notes hidden
   - Change viewport, verify content reflows
   - Export course, verify notes not included
   - Pin a note, verify it sorts to top

## Dependencies

- Requires authentication (uses current_user for author tracking)
- Builds on existing studio infrastructure

## Notes

- Developer Notes are simpler than Comments (no threading, mentions, resolution)
- Preview Mode reuses existing content rendering but strips author-only elements
- Viewport preview is client-side CSS only (no server rendering)
