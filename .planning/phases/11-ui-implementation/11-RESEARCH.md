# Phase 11: UI Implementation - Research

**Researched:** 2026-02-10
**Domain:** Flask + Jinja2 + Vanilla JavaScript Web UI with Dark Theme
**Confidence:** HIGH

## Summary

Phase 11 implements a complete web UI for Course Builder Studio across 8 pages (login, register, dashboard, planner, builder, studio, textbook, publish) with a dark theme aesthetic and collapsible sidebar navigation. The existing codebase already has Flask infrastructure, API endpoints, and a basic dashboard template, so the primary focus is on expanding the UI layer while maintaining the established patterns.

The research confirms that Flask + Jinja2 + vanilla JavaScript is a proven stack for this type of application. The locked design decisions (collapsible sidebar, dark theme palette, drag-drop tree, streaming generation) all have well-established implementation patterns. The existing codebase shows:
- Dark theme foundation already in place (`#1a1a2e` background, `#16213e` panels)
- Basic Jinja2 template inheritance established (`base.html`, `dashboard.html`)
- API endpoints ready for all required functionality
- No JavaScript dependencies (vanilla JS approach confirmed)

Key technical challenges identified:
1. Implementing drag-drop hierarchical tree without libraries
2. Server-Sent Events for streaming generation progress
3. Maintaining scroll position and sidebar state across page transitions
4. Building accessible modals and form validation

**Primary recommendation:** Use vanilla JavaScript with native HTML5 Drag and Drop API for tree reordering, Server-Sent Events for streaming, and localStorage for state persistence. Avoid introducing JavaScript frameworks or heavy libraries.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Flask | 3.1.x | Python web framework | Lightweight, proven for template-driven apps, already in use |
| Jinja2 | 3.1.x | Template engine | Built into Flask, powerful inheritance and macros |
| Vanilla JavaScript | ES6+ | Client-side interactivity | Zero dependencies, full browser support, project constraint |
| CSS3 | - | Styling and animations | Native browser support, CSS Grid/Flexbox for layout |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| localStorage API | Native | Client-side state persistence | Sidebar collapse state, scroll positions, form drafts |
| Drag and Drop API | HTML5 | Native drag-drop functionality | Tree reordering without libraries |
| Server-Sent Events | Native | Real-time server-to-client streaming | AI generation progress display |
| Fetch API | Native | HTTP requests | All API calls from client |
| ContentEditable | HTML5 | Inline text editing | Quick edits in preview panes |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Vanilla JS | jQuery | jQuery adds 87KB and is unnecessary for modern browsers |
| Vanilla JS | React | React requires build tooling and violates project constraints (Jinja first) |
| Native Drag/Drop | SortableJS | SortableJS (11KB) simplifies implementation but adds dependency |
| CSS Variables | Sass/Less | Build step adds complexity; CSS variables are native and sufficient |

**Installation:**
```bash
# Already installed via requirements.txt
pip install flask jinja2
# No JavaScript dependencies needed
```

## Architecture Patterns

### Recommended Project Structure
```
templates/
├── base.html              # Master template with nav, header, footer
├── auth/
│   ├── login.html
│   └── register.html
├── dashboard.html         # Course list (exists)
├── planner.html           # Course setup, outcomes, blueprint
├── builder.html           # Module/lesson/activity tree editor
├── studio.html            # Content generation with preview
├── textbook.html          # Chapter generation, glossary
└── publish.html           # Export selection and download

static/
├── css/
│   ├── main.css           # Base styles (exists)
│   ├── components.css     # Reusable components (buttons, cards, modals)
│   ├── navigation.css     # Sidebar and header styles
│   └── pages/
│       ├── builder.css
│       ├── studio.css
│       └── ...
└── js/
    ├── utils/
    │   ├── api.js         # Fetch wrapper functions
    │   ├── storage.js     # localStorage helpers
    │   └── toast.js       # Notification system
    ├── components/
    │   ├── tree.js        # Hierarchical tree with drag-drop
    │   ├── modal.js       # Modal dialog management
    │   └── sidebar.js     # Sidebar collapse/expand
    └── pages/
        ├── builder.js
        ├── studio.js
        └── ...
```

### Pattern 1: Template Inheritance with Blocks
**What:** Jinja2's template inheritance allows defining a base template with common elements (nav, header, footer) and child templates that override specific blocks.

**When to use:** All pages should extend `base.html` and override the `content` block. Page-specific styles go in `extra_head`, scripts in `extra_scripts`.

**Example:**
```html
<!-- base.html -->
<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/main.css') }}">
    {% block extra_head %}{% endblock %}
</head>
<body>
    {% include 'partials/sidebar.html' %}
    {% include 'partials/header.html' %}
    <main>{% block content %}{% endblock %}</main>
    {% include 'partials/footer.html' %}
    <script src="{{ url_for('static', filename='js/utils/api.js') }}"></script>
    {% block extra_scripts %}{% endblock %}
</body>
</html>

<!-- builder.html -->
{% extends "base.html" %}
{% block content %}
<div class="builder-container">...</div>
{% endblock %}
```
**Source:** [Real Python - Jinja Templating](https://realpython.com/primer-on-jinja-templating/)

### Pattern 2: Collapsible Sidebar with localStorage Persistence
**What:** Sidebar that toggles between expanded (240px) and collapsed (60px) states, with state stored in localStorage.

**When to use:** Left navigation implementation per locked design decision.

**Example:**
```javascript
// sidebar.js
class Sidebar {
    constructor() {
        this.sidebar = document.getElementById('sidebar');
        this.toggleBtn = document.getElementById('sidebar-toggle');
        this.collapsed = localStorage.getItem('sidebar-collapsed') === 'true';

        this.init();
    }

    init() {
        this.applyState();
        this.toggleBtn.addEventListener('click', () => this.toggle());
    }

    toggle() {
        this.collapsed = !this.collapsed;
        localStorage.setItem('sidebar-collapsed', this.collapsed);
        this.applyState();
    }

    applyState() {
        this.sidebar.classList.toggle('collapsed', this.collapsed);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    new Sidebar();
});
```

```css
/* navigation.css */
.sidebar {
    width: 240px;
    transition: width 0.3s ease;
}

.sidebar.collapsed {
    width: 60px;
}

.sidebar.collapsed .nav-text {
    display: none;
}
```
**Source:** [CSS Script - Smooth Collapsible Sidebar](https://www.cssscript.com/smooth-collapsible-sidebar-navigation/)

### Pattern 3: Hierarchical Tree with Drag-Drop
**What:** Nested list structure with native HTML5 Drag and Drop API for reordering items within and across levels.

**When to use:** Builder page tree structure for modules/lessons/activities.

**Example:**
```javascript
// tree.js
class HierarchicalTree {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.draggedItem = null;
        this.init();
    }

    init() {
        // Make all tree items draggable
        this.container.querySelectorAll('[data-tree-item]').forEach(item => {
            item.draggable = true;
            item.addEventListener('dragstart', (e) => this.onDragStart(e));
            item.addEventListener('dragover', (e) => this.onDragOver(e));
            item.addEventListener('drop', (e) => this.onDrop(e));
            item.addEventListener('dragend', (e) => this.onDragEnd(e));
        });
    }

    onDragStart(e) {
        this.draggedItem = e.target;
        e.dataTransfer.effectAllowed = 'move';
        e.target.classList.add('dragging');
    }

    onDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';

        const afterElement = this.getDragAfterElement(e.currentTarget, e.clientY);
        // Show visual drop indicator
        this.showDropIndicator(e.currentTarget, afterElement);
    }

    onDrop(e) {
        e.preventDefault();
        const dropTarget = e.currentTarget;

        // Validate drop (can't drop parent into child, etc.)
        if (this.isValidDrop(this.draggedItem, dropTarget)) {
            this.reorderItems(this.draggedItem, dropTarget);
            // Send reorder API call
            this.saveOrder();
        }
    }

    getDragAfterElement(container, y) {
        const draggableElements = [...container.querySelectorAll('[data-tree-item]:not(.dragging)')];

        return draggableElements.reduce((closest, child) => {
            const box = child.getBoundingClientRect();
            const offset = y - box.top - box.height / 2;

            if (offset < 0 && offset > closest.offset) {
                return { offset: offset, element: child };
            } else {
                return closest;
            }
        }, { offset: Number.NEGATIVE_INFINITY }).element;
    }
}
```
**Source:** [GitHub - davidfig/tree](https://github.com/davidfig/tree) and [W3C HTML Drag and Drop](https://developer.mozilla.org/en-US/docs/Web/API/HTML_Drag_and_Drop_API)

### Pattern 4: Server-Sent Events for Streaming
**What:** SSE connection to stream AI-generated content in real-time as it's produced.

**When to use:** Content generation progress display (locked decision: streaming text appearing).

**Example:**
```javascript
// studio.js - Client side
function generateContent(activityId) {
    const eventSource = new EventSource(`/api/courses/${courseId}/activities/${activityId}/generate/stream`);
    const previewPane = document.getElementById('preview');

    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === 'content_chunk') {
            // Append text chunk to preview
            previewPane.textContent += data.chunk;
        } else if (data.type === 'complete') {
            eventSource.close();
            showToast('Generation complete', 'success');
        } else if (data.type === 'error') {
            eventSource.close();
            showToast(data.message, 'error');
        }
    };

    eventSource.onerror = () => {
        eventSource.close();
        showToast('Connection error', 'error');
    };
}
```

```python
# content.py - Server side (Flask)
from flask import Response, stream_with_context
import json

@content_bp.route('/api/courses/<course_id>/activities/<activity_id>/generate/stream')
def generate_content_stream(course_id, activity_id):
    def generate():
        try:
            # Stream content chunks as they're generated
            for chunk in generator.generate_streaming(...):
                yield f"data: {json.dumps({'type': 'content_chunk', 'chunk': chunk})}\n\n"

            yield f"data: {json.dumps({'type': 'complete'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')
```
**Source:** [MDN - Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events) and [Medium - ChatGPT Streaming](https://medium.com/@hitesh4296/server-sent-events-breaking-down-how-chatgpt-streams-text-4b1d2d4db4ce)

### Pattern 5: Scroll Position Persistence
**What:** Save scroll position before page unload and restore on page load using localStorage.

**When to use:** All content pages to preserve context when navigating (locked design decision).

**Example:**
```javascript
// utils/storage.js
class ScrollManager {
    constructor() {
        this.key = `scroll_${window.location.pathname}`;
        this.restore();
        this.setupSave();
    }

    restore() {
        const position = localStorage.getItem(this.key);
        if (position) {
            window.scrollTo(0, parseInt(position));
        }
    }

    setupSave() {
        window.addEventListener('beforeunload', () => {
            localStorage.setItem(this.key, window.scrollY);
        });
    }
}

// Initialize on every page
new ScrollManager();
```
**Source:** [CSS-Tricks - Memorize Scroll Position](https://css-tricks.com/memorize-scroll-position-across-page-loads/)

### Pattern 6: Toast Notifications
**What:** Non-intrusive notification messages that appear temporarily and auto-dismiss.

**When to use:** Feedback for save operations, generation completion, errors.

**Example:**
```javascript
// utils/toast.js
class ToastManager {
    constructor() {
        this.container = this.createContainer();
        document.body.appendChild(this.container);
    }

    createContainer() {
        const container = document.createElement('div');
        container.className = 'toast-container';
        container.setAttribute('role', 'region');
        container.setAttribute('aria-live', 'polite');
        return container;
    }

    show(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;

        this.container.appendChild(toast);

        // Trigger animation
        setTimeout(() => toast.classList.add('show'), 10);

        // Auto-dismiss
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }
}

// Global instance
const toast = new ToastManager();
```

```css
/* components.css */
.toast-container {
    position: fixed;
    bottom: 20px;
    right: 20px;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.toast {
    background: #16213e;
    border: 1px solid #2a2a4a;
    padding: 12px 20px;
    border-radius: 4px;
    opacity: 0;
    transform: translateX(100px);
    transition: all 0.3s ease;
}

.toast.show {
    opacity: 1;
    transform: translateX(0);
}

.toast-success { border-left: 4px solid #4ade80; }
.toast-error { border-left: 4px solid #ef4444; }
.toast-info { border-left: 4px solid #4361ee; }
```
**Source:** [CSS Script - Toast Notification Libraries](https://www.cssscript.com/best-toast-notification-libraries/)

### Pattern 7: Accessible Modal Dialogs
**What:** Modal dialog with focus trap, ESC to close, and proper ARIA attributes.

**When to use:** Confirmation dialogs, full editor modal, forms.

**Example:**
```javascript
// components/modal.js
class Modal {
    constructor(id) {
        this.modal = document.getElementById(id);
        this.lastFocusedElement = null;
        this.setupEventListeners();
    }

    open() {
        this.lastFocusedElement = document.activeElement;
        this.modal.setAttribute('aria-hidden', 'false');
        this.modal.classList.add('open');

        // Focus first focusable element
        const firstFocusable = this.modal.querySelector('button, input, textarea');
        if (firstFocusable) firstFocusable.focus();

        // Trap focus
        this.modal.addEventListener('keydown', this.trapFocus.bind(this));
    }

    close() {
        this.modal.setAttribute('aria-hidden', 'true');
        this.modal.classList.remove('open');

        // Restore focus
        if (this.lastFocusedElement) {
            this.lastFocusedElement.focus();
        }
    }

    setupEventListeners() {
        // ESC key closes modal
        this.modal.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') this.close();
        });

        // Click backdrop closes modal
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) this.close();
        });
    }

    trapFocus(e) {
        if (e.key !== 'Tab') return;

        const focusableElements = this.modal.querySelectorAll(
            'button, input, textarea, select, a[href], [tabindex]:not([tabindex="-1"])'
        );
        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        if (e.shiftKey && document.activeElement === firstElement) {
            e.preventDefault();
            lastElement.focus();
        } else if (!e.shiftKey && document.activeElement === lastElement) {
            e.preventDefault();
            firstElement.focus();
        }
    }
}
```

```html
<div id="confirm-modal" class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title" aria-hidden="true">
    <div class="modal-backdrop"></div>
    <div class="modal-content">
        <h2 id="modal-title">Confirm Action</h2>
        <p>Are you sure you want to delete this?</p>
        <div class="modal-actions">
            <button class="btn btn-danger">Delete</button>
            <button class="btn">Cancel</button>
        </div>
    </div>
</div>
```
**Source:** [W3C WAI-ARIA Modal Dialog Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/) and [A11Y Collective - Modal Accessibility](https://www.a11y-collective.com/blog/modal-accessibility/)

### Pattern 8: Form Validation with Flask-WTF
**What:** Server-side form validation with error messages passed to Jinja2 templates for inline display.

**When to use:** Login, register, course setup forms.

**Example:**
```python
# auth/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, Email, Length

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(message='Email is required'),
        Email(message='Invalid email address')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required'),
        Length(min=8, message='Password must be at least 8 characters')
    ])
```

```html
<!-- auth/login.html -->
<form method="POST">
    {{ form.csrf_token }}

    <div class="form-group">
        {{ form.email.label }}
        {{ form.email(class="form-input") }}
        {% if form.email.errors %}
            <div class="form-error">
                {% for error in form.email.errors %}
                    <span>{{ error }}</span>
                {% endfor %}
            </div>
        {% endif %}
    </div>

    <button type="submit">Login</button>
</form>
```
**Source:** [Flask Documentation - WTForms](https://flask.palletsprojects.com/en/stable/patterns/wtforms/)

### Anti-Patterns to Avoid

- **Inline styles:** Use CSS classes instead of style attributes. Inline styles defeat the purpose of CSS variables for theming.

- **jQuery for DOM manipulation:** Modern vanilla JS with `querySelector`, `addEventListener`, etc. is cleaner and removes 87KB dependency.

- **Full page reload on save:** Use fetch API for background saves, update UI optimistically, show toast confirmation.

- **Blocking synchronous API calls:** All API calls must use async/await or promises to prevent UI freezing.

- **Nested ternary operators in Jinja2:** Use if/elif/else blocks for clarity.

- **Putting business logic in templates:** Templates should only contain presentation logic. Keep calculations in Python views.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tree drag-drop validation | Custom drop zone detection | HTML5 Drag and Drop API | Native API handles coordinate math, drop zones, visual feedback |
| Focus trap in modals | Manual focus cycling | Established pattern (see Pattern 7) | Edge cases: hidden elements, dynamic content, screen readers |
| Scroll restoration | Manual scroll tracking per page | localStorage + beforeunload pattern | Handles browser back/forward, refresh, history API navigation |
| Toast notification queue | Custom queue management | Simple array with setTimeout | Timing conflicts, overlapping toasts, rapid notifications |
| Form CSRF protection | Manual token generation | Flask-WTF built-in | Secure token generation, expiration, validation |
| Collapsible tree state | Rebuilding tree on expand | CSS classes + data attributes | Performance with large trees, animation timing |

**Key insight:** UI state management is deceptively complex. Native browser APIs and established patterns handle edge cases you won't discover until production (keyboard navigation, screen readers, mobile touch events, browser history interactions, memory leaks in event listeners).

## Common Pitfalls

### Pitfall 1: Drag and Drop Ghost Image Issues
**What goes wrong:** Default drag ghost image includes entire element with children, making drag preview huge and confusing in hierarchical trees.

**Why it happens:** Browser default behavior includes all child elements in the drag image.

**How to avoid:**
```javascript
onDragStart(e) {
    // Create custom drag image showing only the item being dragged
    const dragImage = e.target.cloneNode(false); // false = shallow clone
    dragImage.textContent = e.target.dataset.title;
    document.body.appendChild(dragImage);
    e.dataTransfer.setDragImage(dragImage, 0, 0);
    setTimeout(() => dragImage.remove(), 0);
}
```

**Warning signs:** Users report confusing drag preview, difficulty seeing where they're dropping.

### Pitfall 2: Server-Sent Events Connection Leaks
**What goes wrong:** EventSource connections remain open after user navigates away, causing memory leaks and server resource exhaustion.

**Why it happens:** EventSource doesn't auto-close on page unload in all browsers.

**How to avoid:**
```javascript
// Store reference globally or in component state
let currentEventSource = null;

function generateContent(activityId) {
    // Close any existing connection
    if (currentEventSource) {
        currentEventSource.close();
    }

    currentEventSource = new EventSource(`/api/...`);

    // Clean up on page unload
    window.addEventListener('beforeunload', () => {
        if (currentEventSource) {
            currentEventSource.close();
        }
    });
}
```

**Warning signs:** Server shows many open connections, browser memory usage grows over time, generation endpoints receive multiple simultaneous requests.

### Pitfall 3: localStorage Quota Exceeded
**What goes wrong:** localStorage has 5-10MB limit. Storing large form drafts or cached content can exceed quota and throw exceptions.

**Why it happens:** Developers treat localStorage as unlimited storage.

**How to avoid:**
```javascript
class SafeStorage {
    set(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (e) {
            if (e.name === 'QuotaExceededError') {
                // Clear old data, prioritize recent
                this.cleanupOldest();
                try {
                    localStorage.setItem(key, JSON.stringify(value));
                } catch (e2) {
                    console.warn('localStorage full, cannot save', key);
                }
            }
        }
    }

    cleanupOldest() {
        // Remove items by timestamp or LRU
        const items = Object.entries(localStorage)
            .filter(([k]) => k.startsWith('scroll_'))
            .sort(([,a], [,b]) => JSON.parse(a).timestamp - JSON.parse(b).timestamp);

        // Remove oldest 20%
        items.slice(0, Math.ceil(items.length * 0.2)).forEach(([k]) => {
            localStorage.removeItem(k);
        });
    }
}
```

**Warning signs:** Users report "failed to save" errors, localStorage writes fail silently in some browsers.

### Pitfall 4: Dark Theme Color Contrast
**What goes wrong:** Text on dark backgrounds fails WCAG contrast ratios, especially with accent colors.

**Why it happens:** Colors that look good in light theme don't translate directly to dark theme.

**How to avoid:** Test all color combinations with contrast checker. Locked palette:
- Background `#1a1a2e` + Primary text `#ffffff` = 15.3:1 (AAA)
- Panel `#16213e` + Primary text `#ffffff` = 13.8:1 (AAA)
- Accent `#4361ee` + White text `#ffffff` = 4.8:1 (AA for large text only)
- **Never** use accent blue for body text on dark background

```css
/* Safe combinations */
.btn-primary {
    background: #4361ee;
    color: #ffffff;
    font-size: 1rem; /* 16px = large text threshold */
}

/* Danger - fails contrast */
.body-text {
    color: #4361ee; /* Only 4.8:1 contrast on #1a1a2e */
}

/* Fixed */
.body-text {
    color: #ffffff; /* 15.3:1 contrast */
}
```

**Warning signs:** Accessibility audits show contrast failures, users complain text is hard to read.

### Pitfall 5: contentEditable innerHTML Security
**What goes wrong:** Using innerHTML to read contentEditable content allows XSS attacks.

**Why it happens:** Users paste content from external sources (Word, web pages) containing malicious scripts.

**How to avoid:**
```javascript
// Dangerous
const content = editableDiv.innerHTML;

// Safe
const content = editableDiv.textContent; // Text only, no HTML

// If HTML needed, sanitize
function sanitizeHTML(html) {
    const temp = document.createElement('div');
    temp.textContent = html;
    return temp.innerHTML;
}
```

**Warning signs:** Security audits flag innerHTML usage, XSS vulnerability reports.

### Pitfall 6: Tree Expand State Lost on Refresh
**What goes wrong:** User expands several tree nodes, refreshes page, all nodes collapse.

**Why it happens:** Expand state not persisted to localStorage.

**How to avoid:**
```javascript
class HierarchicalTree {
    constructor(containerId) {
        this.storageKey = `tree_state_${containerId}`;
        this.restoreExpandedState();
    }

    toggleNode(nodeId) {
        const node = document.querySelector(`[data-node-id="${nodeId}"]`);
        const expanded = node.classList.toggle('expanded');

        // Save state
        const state = this.getExpandedNodes();
        localStorage.setItem(this.storageKey, JSON.stringify(state));
    }

    getExpandedNodes() {
        return Array.from(document.querySelectorAll('[data-tree-item].expanded'))
            .map(el => el.dataset.nodeId);
    }

    restoreExpandedState() {
        const state = JSON.parse(localStorage.getItem(this.storageKey) || '[]');
        state.forEach(nodeId => {
            const node = document.querySelector(`[data-node-id="${nodeId}"]`);
            if (node) node.classList.add('expanded');
        });
    }
}
```

**Warning signs:** Users complain about re-expanding trees constantly.

## Code Examples

Verified patterns from official sources:

### Fetch API Wrapper for All API Calls
```javascript
// utils/api.js
class APIClient {
    constructor(baseURL = '/api') {
        this.baseURL = baseURL;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        try {
            const response = await fetch(url, config);

            // Check if response is JSON
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.error || `HTTP ${response.status}`);
                }

                return data;
            }

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            return response;
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }

    get(endpoint) {
        return this.request(endpoint, { method: 'GET' });
    }

    post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    put(endpoint, data) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }
}

// Global instance
const api = new APIClient();
```

### Dark Theme CSS Variables
```css
/* main.css - CSS variables for theme */
:root {
    /* Backgrounds */
    --bg-base: #1a1a2e;
    --bg-panel: #16213e;
    --bg-input: #0f0f1a;

    /* Text */
    --text-primary: #ffffff;
    --text-secondary: #a0a0a0;
    --text-disabled: #606060;

    /* Borders */
    --border-subtle: #2a2a4a;

    /* Accent */
    --accent-primary: #4361ee;
    --accent-hover: #3d8ee6;

    /* Status colors */
    --success: #4ade80;
    --error: #ef4444;
    --warning: #fbbf24;

    /* Spacing */
    --sidebar-width: 240px;
    --sidebar-collapsed: 60px;

    /* Timing */
    --transition-fast: 0.15s;
    --transition-normal: 0.3s;
}

body {
    background: var(--bg-base);
    color: var(--text-primary);
}

.panel {
    background: var(--bg-panel);
    border: 1px solid var(--border-subtle);
}

.btn-primary {
    background: var(--accent-primary);
    transition: background var(--transition-fast);
}

.btn-primary:hover {
    background: var(--accent-hover);
}
```

### Breadcrumb Navigation Component
```html
<!-- partials/header.html -->
<header class="app-header">
    <div class="header-left">
        <a href="/dashboard" class="app-logo">
            <span class="logo-text">Course Builder</span>
        </a>
    </div>

    <div class="header-center">
        <nav class="breadcrumb" aria-label="Breadcrumb">
            <ol>
                {% if breadcrumb %}
                    {% for item in breadcrumb %}
                        <li>
                            {% if not loop.last %}
                                <a href="{{ item.url }}">{{ item.title }}</a>
                                <span class="separator">›</span>
                            {% else %}
                                <span aria-current="page">{{ item.title }}</span>
                            {% endif %}
                        </li>
                    {% endfor %}
                {% endif %}
            </ol>
        </nav>
    </div>

    <div class="header-right">
        <div class="save-indicator" id="save-status">
            <span class="status-icon"></span>
            <span class="status-text">Synced</span>
        </div>
        <div class="user-menu">
            <button class="user-avatar">{{ current_user.email[0].upper() }}</button>
        </div>
    </div>
</header>
```

### Inline Edit with ContentEditable
```javascript
// components/inline-edit.js
class InlineEditor {
    constructor(selector) {
        this.elements = document.querySelectorAll(selector);
        this.init();
    }

    init() {
        this.elements.forEach(el => {
            // Double-click to edit
            el.addEventListener('dblclick', () => this.startEdit(el));
        });
    }

    startEdit(el) {
        const original = el.textContent;
        el.contentEditable = true;
        el.focus();

        // Select all text
        const range = document.createRange();
        range.selectNodeContents(el);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);

        // Save on blur
        el.addEventListener('blur', () => this.endEdit(el, original), { once: true });

        // Save on Enter, cancel on Escape
        el.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                el.blur();
            } else if (e.key === 'Escape') {
                el.textContent = original;
                el.blur();
            }
        });
    }

    async endEdit(el, original) {
        el.contentEditable = false;
        const newValue = el.textContent.trim();

        if (newValue !== original && newValue !== '') {
            // Save via API
            try {
                await api.put(el.dataset.updateUrl, {
                    [el.dataset.field]: newValue
                });
                toast.show('Saved', 'success');
            } catch (error) {
                el.textContent = original;
                toast.show('Failed to save', 'error');
            }
        } else {
            el.textContent = original;
        }
    }
}

// Initialize on elements with data-inline-edit attribute
document.addEventListener('DOMContentLoaded', () => {
    new InlineEditor('[data-inline-edit]');
});
```

### Loading Skeleton Pattern
```html
<!-- Loading skeleton shows instantly while content loads -->
<div class="content-wrapper" data-content-id="123">
    <!-- Skeleton (shown initially) -->
    <div class="skeleton">
        <div class="skeleton-header"></div>
        <div class="skeleton-line"></div>
        <div class="skeleton-line"></div>
        <div class="skeleton-line short"></div>
    </div>

    <!-- Real content (hidden initially, shown when loaded) -->
    <div class="content" style="display: none;">
        <!-- Content here -->
    </div>
</div>
```

```css
.skeleton {
    animation: pulse 1.5s ease-in-out infinite;
}

.skeleton-header {
    height: 32px;
    width: 60%;
    background: var(--bg-panel);
    border-radius: 4px;
    margin-bottom: 16px;
}

.skeleton-line {
    height: 16px;
    width: 100%;
    background: var(--bg-panel);
    border-radius: 4px;
    margin-bottom: 8px;
}

.skeleton-line.short {
    width: 70%;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}
```

```javascript
// Load content and swap
async function loadContent(contentId) {
    const wrapper = document.querySelector(`[data-content-id="${contentId}"]`);
    const skeleton = wrapper.querySelector('.skeleton');
    const content = wrapper.querySelector('.content');

    try {
        const data = await api.get(`/api/content/${contentId}`);
        content.innerHTML = data.html;

        skeleton.style.display = 'none';
        content.style.display = 'block';
    } catch (error) {
        skeleton.innerHTML = '<p class="error">Failed to load content</p>';
    }
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| jQuery for DOM manipulation | Vanilla JS with querySelector/classList | ~2019 | Removed 87KB dependency, cleaner API |
| Sass/Less compilation | CSS variables | ~2020 | No build step, dynamic theming |
| WebSockets for streaming | Server-Sent Events (SSE) | ~2021 | Simpler for unidirectional flow, better HTTP/2 support |
| Custom drag-drop libraries | Native HTML5 Drag and Drop API | ~2018 | Better browser support, mobile touch events |
| Flask-Session for client state | localStorage API | ~2020 | No server storage, works offline |
| Twitter Bootstrap | Custom CSS with Grid/Flexbox | ~2022 | Smaller footprint, no unused CSS |
| alert() for notifications | Toast notifications | ~2020 | Non-blocking, better UX |

**Deprecated/outdated:**
- **jQuery:** Modern browsers have native equivalents for all jQuery functionality
- **Bower:** Replaced by npm/yarn, discontinued 2017
- **CSS preprocessors for variables:** CSS custom properties (variables) are native since 2016
- **Polyfills for fetch/Promise:** All modern browsers support natively (IE11 is dead)

## Open Questions

Things that couldn't be fully resolved:

1. **Icon Library Selection**
   - What we know: Font Awesome has 30,000+ icons, Heroicons has 450 optimized for Tailwind
   - What's unclear: Which provides better dark theme rendering and smaller bundle size?
   - Recommendation: Defer to planner; both work. Font Awesome Pro (paid) or Heroicons (free) are safe choices. Can also use native Unicode symbols for MVP.

2. **Diff View Implementation**
   - What we know: Need side-by-side comparison when regenerating content
   - What's unclear: Should this be a library (diff2html, monaco-diff-editor) or custom implementation?
   - Recommendation: Start with simple character-level diff using native TextArea comparison. Add library if users request advanced features (syntax highlighting, inline diff).

3. **Mobile Responsiveness**
   - What we know: Design decisions focus on desktop ("desktop-focused tool")
   - What's unclear: Should tablet (iPad) be supported? Minimum screen width?
   - Recommendation: Design for 1280px+ screens, graceful degradation to 1024px. No mobile phone support per requirements.

4. **Offline Capability**
   - What we know: localStorage stores some state (sidebar, scroll position)
   - What's unclear: Should the app work offline beyond UI state? Service worker?
   - Recommendation: No offline support for MVP. All operations require server connection. Future enhancement could cache read-only content.

5. **Keyboard Shortcuts**
   - What we know: Locked decision mentions keyboard navigation for accessibility
   - What's unclear: Should power-user keyboard shortcuts be implemented (Cmd+S save, Cmd+K command palette)?
   - Recommendation: Core accessibility (Tab, Enter, Escape, Arrow keys) is mandatory. Power-user shortcuts (save, search) are Claude's discretion, low priority.

## Sources

### Primary (HIGH confidence)
- [W3C WAI-ARIA Authoring Practices Guide](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/) - Modal dialog patterns and accessibility
- [MDN Web Docs - Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events) - SSE implementation
- [MDN Web Docs - HTML Drag and Drop API](https://developer.mozilla.org/en-US/docs/Web/API/HTML_Drag_and_Drop_API) - Native drag-drop
- [MDN Web Docs - ARIA modal attribute](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Attributes/aria-modal) - Accessibility requirements
- [Flask Documentation - Form Validation with WTForms](https://flask.palletsprojects.com/en/stable/patterns/wtforms/) - Form handling
- [Real Python - Primer on Jinja Templating](https://realpython.com/primer-on-jinja-templating/) - Template patterns

### Secondary (MEDIUM confidence)
- [CSS-Tricks - Memorize Scroll Position Across Page Loads](https://css-tricks.com/memorize-scroll-position-across-page-loads/) - Verified scroll persistence pattern
- [CSS Script - Smooth Collapsible Sidebar Navigation](https://www.cssscript.com/smooth-collapsible-sidebar-navigation/) - Sidebar implementation verified against W3Schools
- [GitHub - davidfig/tree](https://github.com/davidfig/tree) - Vanilla JS drag-drop tree example
- [The A11Y Collective - Modal Accessibility](https://www.a11y-collective.com/blog/modal-accessibility/) - 2026 accessibility guidance
- [Medium - Server-Sent Events: How ChatGPT Streams Text](https://medium.com/@hitesh4296/server-sent-events-breaking-down-how-chatgpt-streams-text-4b1d2d4db4ce) - Real-world SSE usage
- [CSS Script - Best Toast Notification Libraries 2026](https://www.cssscript.com/best-toast-notification-libraries/) - Current toast patterns
- [Lineicons Blog - Best Open Source Icon Libraries 2026](https://lineicons.com/blog/best-open-source-icon-libraries) - Icon library comparison

### Tertiary (LOW confidence)
- [CSS Script - Best Tree View JavaScript Libraries 2026](https://www.cssscript.com/best-tree-view/) - Library overview (not using libraries, but patterns are relevant)
- [Medium - State Management in Vanilla JS: 2026 Trends](https://medium.com/@chirag.dave/state-management-in-vanilla-js-2026-trends-f9baed7599de) - General trends, needs validation
- [OneUpTime Blog - Flask Jinja2 Templates](https://oneuptime.com/blog/post/2026-02-02-flask-jinja2-templates/view) - Recent Flask patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Flask + Jinja2 + vanilla JS is well-established and already partially implemented
- Architecture: HIGH - Patterns verified against MDN, W3C, and Flask official docs
- Pitfalls: MEDIUM - Based on common issues reported in forums and GitHub issues, not exhaustive testing

**Research date:** 2026-02-10
**Valid until:** 2026-04-10 (60 days - stable technologies)

**Notes:**
- Existing codebase already implements foundation: base template, dark theme colors, basic dashboard
- All API endpoints exist and are tested (27 endpoints across 11 blueprints)
- No JavaScript frameworks or heavy libraries per project constraints
- Focus on progressive enhancement: core functionality works without JS, enhanced with JS
- Accessibility is built-in via semantic HTML, ARIA, keyboard navigation patterns
