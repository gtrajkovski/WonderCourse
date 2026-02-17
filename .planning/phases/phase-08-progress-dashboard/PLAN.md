# Phase 8: Progress Dashboard

## Overview

Visualize course completion status and content generation progress. Provides authors with a comprehensive view of their course building progress, content metrics, and quality indicators.

**Key Features:**
- Build state progress tracking with visual indicators
- Content metrics (word count, duration vs. target)
- Module/lesson completion breakdown
- Quality score integration from audit system
- Content type distribution

## Implementation Plans

### Plan 1: Enhanced Progress API

**Modify `src/api/build_state.py`**

Enhance the existing `/api/courses/<id>/progress` endpoint with additional metrics:

```python
@build_state_bp.route('/api/courses/<course_id>/progress', methods=['GET'])
def get_course_progress(course_id):
    """Get comprehensive course progress metrics."""
    # Existing: by_state, total_activities, completion_percentage
    # Add:
    return {
        # ... existing fields ...
        "content_metrics": {
            "total_word_count": int,
            "total_duration_minutes": float,
            "target_duration_minutes": float,
            "duration_percentage": float,  # actual/target * 100
        },
        "structure": {
            "module_count": int,
            "lesson_count": int,
            "activity_count": int,
        },
        "by_content_type": {
            "video": {"count": int, "completed": int},
            "reading": {"count": int, "completed": int},
            "quiz": {"count": int, "completed": int},
            # ... etc
        },
        "by_module": [
            {
                "id": str,
                "title": str,
                "total": int,
                "completed": int,
                "percentage": float
            }
        ],
        "quality": {
            "audit_score": int or None,
            "open_issues": int,
            "last_audit": str or None  # ISO timestamp
        }
    }
```

---

### Plan 2: Dashboard Template

**Create `templates/progress.html`**

```html
{% extends "base.html" %}

{% block content %}
<div class="progress-dashboard" data-course-id="{{ course.id }}">
    <!-- Header -->
    <div class="dashboard-header">
        <h1>Progress Dashboard</h1>
        <p class="course-title">{{ course.title }}</p>
    </div>

    <!-- Summary Cards Row -->
    <div class="summary-cards">
        <div class="summary-card" id="card-completion">
            <div class="card-value" id="completion-percentage">0%</div>
            <div class="card-label">Complete</div>
            <div class="card-progress">
                <div class="progress-ring" id="completion-ring"></div>
            </div>
        </div>
        <div class="summary-card" id="card-activities">
            <div class="card-value" id="total-activities">0</div>
            <div class="card-label">Activities</div>
        </div>
        <div class="summary-card" id="card-duration">
            <div class="card-value" id="total-duration">0 min</div>
            <div class="card-label">Duration</div>
            <div class="card-sub" id="duration-target">Target: 0 min</div>
        </div>
        <div class="summary-card" id="card-quality">
            <div class="card-value" id="quality-score">--</div>
            <div class="card-label">Quality Score</div>
        </div>
    </div>

    <!-- Main Content Grid -->
    <div class="dashboard-grid">
        <!-- Build State Distribution -->
        <div class="dashboard-panel" id="panel-states">
            <h3>Build Status</h3>
            <div class="state-bars" id="state-bars">
                <!-- Rendered dynamically -->
            </div>
        </div>

        <!-- Module Progress -->
        <div class="dashboard-panel" id="panel-modules">
            <h3>Module Progress</h3>
            <div class="module-list" id="module-list">
                <!-- Rendered dynamically -->
            </div>
        </div>

        <!-- Content Type Breakdown -->
        <div class="dashboard-panel" id="panel-content-types">
            <h3>Content Types</h3>
            <div class="content-type-chart" id="content-type-chart">
                <!-- Rendered dynamically -->
            </div>
        </div>

        <!-- Activity List -->
        <div class="dashboard-panel panel-wide" id="panel-activities">
            <h3>Activities by Status</h3>
            <div class="activity-filters" id="activity-filters">
                <button class="filter-btn active" data-filter="all">All</button>
                <button class="filter-btn" data-filter="draft">Draft</button>
                <button class="filter-btn" data-filter="generated">Generated</button>
                <button class="filter-btn" data-filter="approved">Approved</button>
            </div>
            <div class="activity-table" id="activity-table">
                <!-- Rendered dynamically -->
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

---

### Plan 3: Dashboard JavaScript

**Create `static/js/pages/progress.js`**

```javascript
class ProgressDashboard {
    constructor(courseId) {
        this.courseId = courseId;
        this.progressData = null;
        this.currentFilter = 'all';
    }

    async init() {
        await this.loadProgress();
        this.renderSummaryCards();
        this.renderStateBars();
        this.renderModuleProgress();
        this.renderContentTypes();
        this.renderActivityTable();
        this.bindEventHandlers();
    }

    async loadProgress() {
        this.progressData = await api.get(`/courses/${this.courseId}/progress`);
    }

    renderSummaryCards() {
        // Update completion percentage with ring
        // Update activity count
        // Update duration vs target
        // Update quality score
    }

    renderStateBars() {
        // Horizontal bars for each build state
        // Draft, Generating, Generated, Reviewed, Approved, Published
    }

    renderModuleProgress() {
        // List modules with progress bars
    }

    renderContentTypes() {
        // Simple bar chart showing video, reading, quiz, etc.
    }

    renderActivityTable() {
        // Filterable table of activities with status
    }

    handleFilterChange(filter) {
        this.currentFilter = filter;
        this.renderActivityTable();
    }
}
```

---

### Plan 4: Dashboard CSS

**Create `static/css/pages/progress.css`**

```css
.progress-dashboard {
    padding: var(--spacing-lg);
    max-width: 1400px;
    margin: 0 auto;
}

/* Summary Cards */
.summary-cards {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: var(--spacing-lg);
    margin-bottom: var(--spacing-xl);
}

.summary-card {
    background: var(--bg-panel);
    border-radius: var(--radius-lg);
    padding: var(--spacing-lg);
    text-align: center;
}

.card-value {
    font-size: 2.5rem;
    font-weight: 700;
    color: var(--accent-primary);
}

/* Dashboard Grid */
.dashboard-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: var(--spacing-lg);
}

.dashboard-panel {
    background: var(--bg-panel);
    border-radius: var(--radius-lg);
    padding: var(--spacing-lg);
}

.panel-wide {
    grid-column: span 2;
}

/* State Bars */
.state-bar {
    display: flex;
    align-items: center;
    margin-bottom: var(--spacing-sm);
}

.state-bar-fill {
    height: 24px;
    border-radius: var(--radius-sm);
    transition: width 0.5s ease;
}

/* Module Progress */
.module-item {
    margin-bottom: var(--spacing-md);
}

.module-progress-bar {
    height: 8px;
    background: var(--bg-hover);
    border-radius: var(--radius-full);
    overflow: hidden;
}

/* Activity Table */
.activity-table {
    max-height: 400px;
    overflow-y: auto;
}
```

---

### Plan 5: Flask Route

**Modify `app.py`**

Add route for progress dashboard page:

```python
@app.route('/courses/<course_id>/progress')
@login_required
def progress_page(course_id):
    """Render progress dashboard page."""
    owner_id = Collaborator.get_course_owner_id(course_id)
    if not owner_id:
        abort(404)
    course = project_store.load(owner_id, course_id)
    if not course:
        abort(404)
    return render_template('progress.html', course=course)
```

---

### Plan 6: Navigation Integration

**Modify `templates/partials/sidebar.html`** (or equivalent nav)

Add Progress Dashboard link in course navigation.

---

## Files to Create

| File | Description |
|------|-------------|
| `templates/progress.html` | Progress dashboard page |
| `static/js/pages/progress.js` | Dashboard controller |
| `static/css/pages/progress.css` | Dashboard styles |

## Files to Modify

| File | Changes |
|------|---------|
| `src/api/build_state.py` | Enhance /progress endpoint with more metrics |
| `app.py` | Add /courses/<id>/progress route |
| `templates/partials/sidebar.html` | Add dashboard nav link |

## Verification

1. **Manual testing:**
   - Navigate to Progress Dashboard for a course
   - Verify completion percentage is accurate
   - Verify module progress shows correctly
   - Verify activity list filters work
   - Verify quality score from audit shows
   - Test with course at various stages (empty, partial, complete)

2. **Edge cases:**
   - Empty course (no modules/activities)
   - Course with no generated content
   - Course with all content approved

## Dependencies

- Uses existing `/api/courses/<id>/progress` endpoint
- Can integrate with audit score from `/api/courses/<id>/audit`
- Builds on existing BuildState tracking

## Notes

- Dashboard is read-only (no state changes)
- All calculations done server-side in progress endpoint
- Quality score shows "--" if no audit has been run
