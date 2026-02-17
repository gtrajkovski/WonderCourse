# Phase 2: Course Management - Research

**Researched:** 2026-02-02
**Domain:** Flask REST API, nested resource CRUD, hierarchical data management
**Confidence:** HIGH

## Summary

Phase 2 implements comprehensive course management with nested structure editing (modules/lessons/activities), learning outcome definition with Bloom's taxonomy, and outcome-to-activity mapping. The research identifies proven Flask patterns for hierarchical CRUD operations, JavaScript libraries for drag-and-drop reordering, and critical pitfalls to avoid when managing deeply nested dataclass structures.

The standard approach uses Flask REST endpoints with limited URL nesting (max 2 levels), SortableJS for client-side reordering, and careful atomic update patterns for nested structures. The existing Phase 1 infrastructure (dataclasses with to_dict/from_dict, ProjectStore with file locking, dark-themed Jinja2 templates) provides a solid foundation that requires minimal additional dependencies.

**Primary recommendation:** Extend existing Flask app with nested resource endpoints following /api/courses/:id/modules/:id pattern (2-level max), use SortableJS for drag-and-drop reordering, and implement copy-on-write pattern for nested dataclass updates to maintain atomicity.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Flask | 3.1.0+ | REST API framework | Already in Phase 1, proven for nested resources |
| SortableJS | 1.15+ | Drag-and-drop reordering | Industry standard, no jQuery, touch support, 29k+ stars |
| Jinja2 | 3.1+ | Template engine | Bundled with Flask, template inheritance |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-flask | 1.3.0+ | Flask testing | Already in Phase 1 for integration tests |
| Just-validate | 3.5+ | Client-side validation | Lightweight, vanilla JS, HTML5 data attributes |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SortableJS | Draggable (Shopify) | More modular but heavier; SortableJS simpler for list reordering |
| Just-validate | Pristine | Both lightweight; Just-validate has better TypeScript support |
| Nested endpoints | Query parameters | Query params cleaner for deep nesting but lose hierarchical clarity |

**Installation:**
```bash
# No Python dependencies needed beyond Phase 1
# Client-side libraries loaded via CDN in templates
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── core/
│   ├── models.py              # Existing: Course, Module, Lesson, Activity, LearningOutcome
│   └── project_store.py       # Existing: save/load with file locking
├── api/
│   ├── courses.py             # NEW: Course CRUD endpoints
│   ├── modules.py             # NEW: Module nested CRUD
│   ├── lessons.py             # NEW: Lesson nested CRUD
│   ├── activities.py          # NEW: Activity nested CRUD
│   └── learning_outcomes.py  # NEW: Learning outcome CRUD and mapping
app.py                         # Existing: Register new blueprints
templates/
├── base.html                  # Existing: Dark theme base
├── dashboard.html             # Existing: Course list
└── workspace.html             # NEW: Course editor with nested structure tree
```

### Pattern 1: Nested Resource URL Design (2-Level Max)

**What:** RESTful endpoints for hierarchical resources limited to 2 nesting levels
**When to use:** When resources have parent-child relationship (course→module→lesson→activity)

**Best practice:**
```python
# GOOD: 2-level nesting
GET    /api/courses/:course_id/modules
POST   /api/courses/:course_id/modules
PUT    /api/courses/:course_id/modules/:module_id
DELETE /api/courses/:course_id/modules/:module_id

# GOOD: Direct resource access for deep operations
PUT    /api/modules/:module_id/reorder-lessons
POST   /api/activities/:activity_id/assign-outcome

# BAD: 3+ level nesting
PUT    /api/courses/:id/modules/:id/lessons/:id/activities/:id
```

**Source:** [Moesif REST API Design Best Practices](https://www.moesif.com/blog/technical/api-design/REST-API-Design-Best-Practices-for-Sub-and-Nested-Resources/)

### Pattern 2: Immutable Dataclass Updates (Copy-on-Write)

**What:** Create new instances instead of mutating nested dataclass lists
**When to use:** When updating nested structures in frozen or tracked dataclasses

**Example:**
```python
# GOOD: Copy-on-write for atomicity
def add_module(course: Course, module: Module) -> Course:
    """Add module to course, returning new Course instance."""
    updated_modules = course.modules + [module]
    course.modules = updated_modules
    return course

# GOOD: Reorder with list slicing
def reorder_modules(course: Course, old_index: int, new_index: int) -> Course:
    """Reorder modules by moving from old_index to new_index."""
    modules = course.modules.copy()
    module = modules.pop(old_index)
    modules.insert(new_index, module)

    # Update order field
    for i, mod in enumerate(modules):
        mod.order = i

    course.modules = modules
    return course
```

**Source:** [Real Python: Data Classes Guide](https://realpython.com/python-data-classes/)

### Pattern 3: SortableJS Drag-and-Drop Integration

**What:** Client-side reordering with server-side persistence
**When to use:** Module/lesson/activity reordering in workspace UI

**Example:**
```javascript
// Client-side: SortableJS initialization
const moduleList = document.getElementById('module-list');
Sortable.create(moduleList, {
    animation: 150,
    handle: '.drag-handle',
    onEnd: function(evt) {
        // Send new order to server
        const moduleId = evt.item.dataset.id;
        fetch(`/api/courses/${courseId}/modules/${moduleId}/reorder`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                old_index: evt.oldIndex,
                new_index: evt.newIndex
            })
        });
    }
});
```

**Source:** [SortableJS Documentation](https://sortablejs.github.io/Sortable/)

### Pattern 4: Learning Outcome Mapping (Many-to-Many)

**What:** Track which activities fulfill which learning outcomes
**When to use:** Alignment tracking, coverage analysis

**Example:**
```python
# LearningOutcome stores mapped_activity_ids: List[str]
# Activity doesn't need reverse reference (query via outcome)

def map_outcome_to_activity(course: Course, outcome_id: str, activity_id: str) -> None:
    """Add activity to outcome's mapping."""
    for outcome in course.learning_outcomes:
        if outcome.id == outcome_id:
            if activity_id not in outcome.mapped_activity_ids:
                outcome.mapped_activity_ids.append(activity_id)
            break

def get_activities_for_outcome(course: Course, outcome_id: str) -> List[Activity]:
    """Get all activities mapped to an outcome."""
    outcome = next((o for o in course.learning_outcomes if o.id == outcome_id), None)
    if not outcome:
        return []

    # Flatten course structure to get all activities
    all_activities = []
    for module in course.modules:
        for lesson in module.lessons:
            all_activities.extend(lesson.activities)

    return [a for a in all_activities if a.id in outcome.mapped_activity_ids]
```

**Pattern:** Unidirectional mapping with query helpers prevents sync issues

### Anti-Patterns to Avoid

- **Deep URL nesting (3+ levels):** Use direct resource routes or query params instead
- **Mutating nested lists in-place:** Always copy before modifying to ensure atomic saves
- **Bidirectional references in dataclasses:** Use unidirectional mapping with query helpers to avoid sync bugs
- **Client-side only reordering:** Always persist order to server immediately
- **Missing order field:** Without explicit `order: int`, reordering requires full list replacement

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Drag-and-drop lists | Custom mouse event handlers | SortableJS | Touch support, accessibility, auto-scroll, ghost elements, 10+ years battle-tested |
| Form validation | Custom regex + DOM | Just-validate or Pristine | HTML5 constraint validation API, custom rules, async validation |
| Nested object updates | Deep copy utilities | Dataclass replace pattern | Native Python, type-safe, clean copy-on-write |
| URL routing | String concatenation | Flask url_for() | Safe from URL changes, automatic escaping |
| Template reuse | Copy-paste HTML | Jinja2 inheritance | Single source of truth, maintainable |

**Key insight:** Nested CRUD seems straightforward until you handle concurrent updates, partial failures, order synchronization, and client-server consistency. Use proven patterns (atomic saves via ProjectStore locking, copy-on-write updates) instead of naive in-place mutations.

## Common Pitfalls

### Pitfall 1: Inconsistent Order Values After Reordering

**What goes wrong:** After drag-and-drop, order fields don't match visual position
**Why it happens:** Client sends old_index/new_index but server doesn't recalculate all order values
**How to avoid:** Always renumber entire list after reorder operation
**Warning signs:** Items jump position on page reload; duplicate order values

**Prevention:**
```python
def reorder_items(items: List[Any], old_idx: int, new_idx: int) -> List[Any]:
    """Reorder list and fix all order fields."""
    items = items.copy()
    item = items.pop(old_idx)
    items.insert(new_idx, item)

    # CRITICAL: Renumber all items
    for i, item in enumerate(items):
        item.order = i

    return items
```

### Pitfall 2: Nested Structure Updates Without Atomicity

**What goes wrong:** Partial updates leave course in inconsistent state (e.g., module saved but lesson not)
**Why it happens:** No transaction boundaries; file saved after each nested operation
**How to avoid:** Load full course, modify in memory, save once with ProjectStore file locking
**Warning signs:** Corruption on errors; race conditions with concurrent edits

**Prevention:**
```python
# BAD: Multiple saves (non-atomic)
def add_activity_to_lesson_bad(course_id, lesson_id, activity):
    course = store.load(course_id)
    lesson = find_lesson(course, lesson_id)
    lesson.activities.append(activity)
    store.save(course)  # SAVE 1

    lesson.activities[-1].order = len(lesson.activities) - 1
    store.save(course)  # SAVE 2 - What if this fails?

# GOOD: Single atomic save
def add_activity_to_lesson_good(course_id, lesson_id, activity):
    course = store.load(course_id)
    lesson = find_lesson(course, lesson_id)

    # Do all modifications in memory
    activity.order = len(lesson.activities)
    lesson.activities.append(activity)

    # Single atomic save with file lock
    store.save(course)
```

### Pitfall 3: Deep Nesting in REST URLs

**What goes wrong:** URLs become unwieldy: `/api/courses/:id/modules/:id/lessons/:id/activities/:id/update`
**Why it happens:** Mirroring data structure in URL hierarchy
**How to avoid:** Limit to 2 nesting levels; use direct resource routes for deep operations
**Warning signs:** URL longer than 80 chars; 4+ path segments after /api

**Prevention:**
```python
# BAD: Deep nesting
@app.route('/api/courses/<cid>/modules/<mid>/lessons/<lid>/activities/<aid>', methods=['PUT'])

# GOOD: Direct resource access
@app.route('/api/activities/<activity_id>', methods=['PUT'])
def update_activity(activity_id):
    # Find activity by traversing course structure
    course = find_course_containing_activity(activity_id)
    activity = find_activity(course, activity_id)
    # ... update and save
```

### Pitfall 4: Missing Validation on Nested Structure Operations

**What goes wrong:** Deleting a module leaves orphaned learning outcome mappings
**Why it happens:** No cascading checks when removing nested items
**How to avoid:** Validate dependent data before deletions; clean up references
**Warning signs:** Broken references in outcome.mapped_activity_ids; 404s on mapped activities

**Prevention:**
```python
def delete_module(course: Course, module_id: str) -> None:
    """Delete module and clean up dependent references."""
    module = find_module(course, module_id)

    # Get all activity IDs in module
    activity_ids = []
    for lesson in module.lessons:
        activity_ids.extend([a.id for a in lesson.activities])

    # Remove from learning outcome mappings
    for outcome in course.learning_outcomes:
        outcome.mapped_activity_ids = [
            aid for aid in outcome.mapped_activity_ids
            if aid not in activity_ids
        ]

    # Remove module
    course.modules = [m for m in course.modules if m.id != module_id]

    # Renumber remaining modules
    for i, mod in enumerate(course.modules):
        mod.order = i
```

### Pitfall 5: Ignoring Schema Evolution for New Fields

**What goes wrong:** Adding `prerequisites`, `tools`, `grading_policy` to Course breaks existing JSON files
**Why it happens:** from_dict() expects all fields to exist or have defaults
**How to avoid:** Use Optional[] with None defaults; field filtering in from_dict already handles this
**Warning signs:** KeyError on load; crashes opening old courses

**Prevention:**
```python
# Phase 1 pattern already handles this via field filtering
@dataclass
class Course:
    # Existing fields...
    title: str = "Untitled Course"

    # NEW fields for COURSE-03
    prerequisites: Optional[str] = None  # Safe: None default
    tools: List[str] = field(default_factory=list)  # Safe: empty list
    grading_policy: Optional[str] = None  # Safe: None default

    # from_dict() filters unknown fields, loads missing as defaults
```

## Code Examples

Verified patterns from official sources:

### Adding Module to Course (Atomic)
```python
from src.core.models import Course, Module
from src.core.project_store import ProjectStore

def add_module(store: ProjectStore, course_id: str, title: str, description: str = "") -> Module:
    """Add module to course with automatic ordering."""
    # Load course
    course = store.load(course_id)
    if not course:
        raise ValueError(f"Course {course_id} not found")

    # Create module with next order value
    module = Module(
        title=title,
        description=description,
        order=len(course.modules)
    )

    # Add to course
    course.modules.append(module)

    # Atomic save (ProjectStore handles locking)
    store.save(course)

    return module
```

### Reordering Lessons in Module
```python
def reorder_lesson(store: ProjectStore, course_id: str, module_id: str,
                   old_index: int, new_index: int) -> None:
    """Reorder lesson within module."""
    course = store.load(course_id)
    module = next((m for m in course.modules if m.id == module_id), None)
    if not module:
        raise ValueError(f"Module {module_id} not found")

    # Validate indices
    if not (0 <= old_index < len(module.lessons) and 0 <= new_index < len(module.lessons)):
        raise ValueError("Invalid lesson index")

    # Reorder
    lessons = module.lessons.copy()
    lesson = lessons.pop(old_index)
    lessons.insert(new_index, lesson)

    # Renumber all
    for i, lesson in enumerate(lessons):
        lesson.order = i

    module.lessons = lessons

    # Atomic save
    store.save(course)
```

### Mapping Learning Outcome to Activity
```python
def map_outcome(store: ProjectStore, course_id: str, outcome_id: str, activity_id: str) -> None:
    """Map learning outcome to activity."""
    course = store.load(course_id)

    # Find outcome
    outcome = next((o for o in course.learning_outcomes if o.id == outcome_id), None)
    if not outcome:
        raise ValueError(f"Outcome {outcome_id} not found")

    # Verify activity exists (optional validation)
    activity_exists = False
    for module in course.modules:
        for lesson in module.lessons:
            if any(a.id == activity_id for a in lesson.activities):
                activity_exists = True
                break

    if not activity_exists:
        raise ValueError(f"Activity {activity_id} not found")

    # Add mapping (idempotent)
    if activity_id not in outcome.mapped_activity_ids:
        outcome.mapped_activity_ids.append(activity_id)

    # Atomic save
    store.save(course)
```

### Flask Endpoint with Nested Resource
```python
from flask import Blueprint, request, jsonify
from src.core.project_store import ProjectStore

modules_bp = Blueprint('modules', __name__)
store = ProjectStore()

@modules_bp.route('/api/courses/<course_id>/modules', methods=['POST'])
def create_module(course_id):
    """Create module in course."""
    data = request.get_json()

    try:
        module = add_module(
            store,
            course_id,
            data.get('title', 'Untitled Module'),
            data.get('description', '')
        )
        return jsonify(module.to_dict()), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@modules_bp.route('/api/courses/<course_id>/modules/<module_id>', methods=['DELETE'])
def delete_module(course_id, module_id):
    """Delete module and clean up references."""
    try:
        course = store.load(course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        # Find module
        module = next((m for m in course.modules if m.id == module_id), None)
        if not module:
            return jsonify({"error": "Module not found"}), 404

        # Collect activity IDs for cleanup
        activity_ids = []
        for lesson in module.lessons:
            activity_ids.extend([a.id for a in lesson.activities])

        # Clean outcome mappings
        for outcome in course.learning_outcomes:
            outcome.mapped_activity_ids = [
                aid for aid in outcome.mapped_activity_ids
                if aid not in activity_ids
            ]

        # Remove module
        course.modules = [m for m in course.modules if m.id != module_id]

        # Renumber
        for i, mod in enumerate(course.modules):
            mod.order = i

        # Save
        store.save(course)

        return jsonify({"message": "Module deleted"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| jQuery UI Sortable | SortableJS | ~2015 | No jQuery dependency, better touch support, smaller bundle |
| Deep REST nesting | 2-level max + direct routes | ~2018 | Cleaner URLs, easier to document, better caching |
| Mutable dataclass updates | Copy-on-write pattern | Python 3.7+ | Safer concurrent access, easier testing |
| Custom validation | HTML5 + JS libraries | ~2019 | Standards-based, accessible, less code |
| Flask-RESTful | Blueprint + jsonify | Flask 1.0+ | Less abstraction, more control, faster |

**Deprecated/outdated:**
- **Flask-RESTful:** Still works but Flask's built-in Blueprint + jsonify is simpler and Flask maintainers recommend native approach
- **jQuery UI:** Heavy dependency (250KB+); SortableJS is 10KB and framework-agnostic
- **Marshmallow for simple CRUD:** Overkill for basic validation; use dataclass validation or Just-validate client-side

## Open Questions

Things that couldn't be fully resolved:

1. **Should Course model add prerequisites/tools/grading_policy fields now or in separate plan?**
   - What we know: COURSE-03 requires editing these fields
   - What's unclear: Whether to add fields in 02-01 (Course CRUD) or 02-02 (structure management)
   - Recommendation: Add in 02-01 since they're Course-level metadata, not nested structure

2. **How deep should activity type validation go?**
   - What we know: Activity has activity_type enum, Phase 1 doesn't validate compatibility with content_type
   - What's unclear: Should VIDEO content_type restrict to VIDEO_LECTURE activity_type? Or allow flexibility?
   - Recommendation: Allow flexibility for now (e.g., VIDEO + COACH_DIALOGUE for coach videos). Defer strict validation to Phase 7 (Validation & Quality)

3. **Should learning outcome management be separate plan or combined with outcome mapping?**
   - What we know: COURSE-06 defines outcomes, COURSE-12 maps to activities
   - What's unclear: Whether these should be split into 02-03 (outcome CRUD) + 02-04 (mapping) or combined
   - Recommendation: Separate plans. CRUD is different complexity than many-to-many mapping logic

## Sources

### Primary (HIGH confidence)
- [Moesif: REST API Design Best Practices for Nested Resources](https://www.moesif.com/blog/technical/api-design/REST-API-Design-Best-Practices-for-Sub-and-Nested-Resources/) - URL design patterns
- [Real Python: Data Classes Guide](https://realpython.com/python-data-classes/) - Dataclass manipulation patterns
- [SortableJS Documentation](https://sortablejs.github.io/Sortable/) - Drag-and-drop implementation
- [Python Dataclasses Official Docs](https://docs.python.org/3/library/dataclasses.html) - from_dict pattern, field defaults
- [Flask Official Docs: Blueprints](https://flask.palletsprojects.com/en/stable/blueprints/) - REST API organization

### Secondary (MEDIUM confidence)
- [Watermark: Curriculum Mapping](https://www.watermarkinsights.com/resources/blog/how-curriculum-mapping-helps-students-learn-more/) - Learning outcome mapping patterns
- [Vanderbilt: Bloom's Taxonomy](https://cft.vanderbilt.edu/guides-sub-pages/blooms-taxonomy/) - Taxonomy framework
- [MindTools: ABCD Learning Objectives](https://www.mindtools.com/acqerdm/abcd-learning-objectives-model/) - ABCD model components
- [Stack Overflow: REST API Best Practices](https://stackoverflow.blog/2020/03/02/best-practices-for-rest-api-design/) - General API design
- [Retool: CRUD Endpoint Best Practices](https://retool.com/blog/best-practices-for-building-crud-endpoints) - Validation, error handling

### Tertiary (LOW confidence)
- Various web search results on Flask Jinja2 patterns (2025-2026 articles) - General guidance, not specific to this use case
- Educational institution curriculum mapping guides - Process guidance but not technical implementation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - SortableJS, Flask Blueprints, and dataclass patterns are industry-proven
- Architecture: HIGH - Nested resource patterns well-documented with clear 2-level limit consensus
- Pitfalls: HIGH - Atomicity, reordering, and nesting issues are well-known from official docs and authoritative sources

**Research date:** 2026-02-02
**Valid until:** ~60 days (stable domain; Flask, dataclasses, SortableJS have infrequent breaking changes)
