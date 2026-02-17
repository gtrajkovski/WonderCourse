# Phase 13: Integration & Polish - Research

**Researched:** 2026-02-11
**Domain:** E2E testing, error handling, performance optimization, help systems
**Confidence:** HIGH

## Summary

Phase 13 focuses on end-to-end workflow refinement, ensuring all 12 phases integrate smoothly without new features. Research covers five key domains: E2E testing with Playwright, error handling patterns with retry logic, performance optimization with lazy loading, help systems with onboarding tours, and integration testing strategies.

**Key findings:**
- Playwright with pytest provides robust E2E testing for Flask apps with parallel execution, auto-waiting, and API mocking capabilities
- Flask's built-in error handlers combined with Tenacity retry library enable sophisticated error recovery with exponential backoff
- Skeleton screens outperform progress bars for <10s loads; lazy loading critical for large course datasets
- Intro.js (10kB, zero dependencies) offers lightweight onboarding tours; Notyf provides minimal toast notifications
- Transaction rollback fixtures and HAR files enable fast, deterministic E2E tests with optional real AI calls

**Primary recommendation:** Use Playwright for E2E tests with mock-by-default API responses, implement Tenacity retry decorators for transient failures, skeleton screens for page transitions, Intro.js for onboarding, and Notyf for toast notifications.

## Standard Stack

### Core Testing

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| playwright | 1.42+ | E2E browser testing | Official Python support, auto-waiting, parallel execution, active maintenance |
| pytest-playwright | latest | pytest integration | Official pytest plugin with fixtures, session management |
| pytest-xdist | 3.5+ | Parallel test execution | Distributes tests across CPU cores for faster CI |
| pytest-randomly | 3.15+ | Test isolation | Randomizes test order, resets random seeds per test |

### Error Handling

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| tenacity | 8.2+ | Retry with backoff | Production-grade retry logic, exponential backoff with jitter |
| Flask built-in | - | Error handlers | @app.errorhandler decorator for custom error responses |

### Frontend Libraries

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Intro.js | 7.2+ | Onboarding tours | 10kB, zero dependencies, AGPL/commercial, enterprise adoption |
| Notyf | 3.10+ | Toast notifications | 3kB, responsive, A11Y compatible, vanilla JS |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-flask-sqlalchemy | latest | Transaction rollback | Database test isolation via nested transactions |
| Faker | 40.1+ | Test data generation | Seeded fixtures for repeatable test data |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Playwright | Selenium | Playwright has auto-wait, faster, modern API; Selenium has broader browser support |
| Intro.js | Shepherd.js | Shepherd more customizable but requires Popper.js dependency |
| Notyf | Toastify | Toastify slightly smaller (~2KB) but Notyf has better A11Y support |
| Tenacity | Built-in retry | Tenacity provides jitter, circuit breaker patterns, more sophisticated strategies |

**Installation:**
```bash
# E2E testing
pip install playwright pytest-playwright pytest-xdist pytest-randomly
playwright install chromium

# Error handling
pip install tenacity

# Database test fixtures (if needed)
pip install pytest-flask-sqlalchemy faker

# Frontend (via CDN or npm)
npm install intro.js notyf
```

## Architecture Patterns

### Recommended Project Structure

```
tests/
├── e2e/                      # End-to-end Playwright tests
│   ├── conftest.py           # E2E fixtures (live_server, browser)
│   ├── test_happy_path.py    # Registration → Export full workflow
│   ├── test_collaboration.py # Multi-user scenarios
│   ├── test_import_flows.py  # Content import workflows
│   └── fixtures/             # HAR files, mock data
├── integration/              # API integration tests (existing)
└── unit/                     # Unit tests (existing)

src/
├── utils/
│   ├── retry.py              # Retry decorators with Tenacity
│   └── error_handlers.py     # Centralized Flask error handlers
├── api/
│   └── errors.py             # Custom exception classes
└── static/
    ├── js/
    │   ├── error-recovery.js # Frontend retry logic
    │   └── onboarding.js     # Intro.js tour definitions
    └── css/
        └── help.css          # Help panel, tooltip styles
```

### Pattern 1: E2E Test with Mock AI

**What:** Playwright tests that mock AI responses by default, with flag for real calls
**When to use:** Regression testing, CI pipelines
**Example:**
```python
# tests/e2e/conftest.py
import pytest
from playwright.sync_api import Page, Route

@pytest.fixture
def mock_ai_responses(page: Page, request):
    """Mock AI responses by default, unless --real-ai flag"""
    if request.config.getoption("--real-ai"):
        yield  # No mocking
        return

    def handle_route(route: Route):
        if "/api/courses/" in route.request.url and "/generate" in route.request.url:
            route.fulfill(
                json={
                    "content": {"hook": "Mocked content...", ...},
                    "metadata": {"word_count": 500, "estimated_duration": 3}
                }
            )
        else:
            route.continue_()

    page.route("**/api/**", handle_route)
    yield

# Test usage
def test_content_generation_workflow(page: Page, mock_ai_responses):
    page.goto("http://localhost:5003/studio")
    page.click("button:has-text('Generate')")
    page.wait_for_selector(".content-preview:has-text('Mocked content')")
```

### Pattern 2: Retry with Exponential Backoff

**What:** Tenacity decorator for transient failures with exponential backoff + jitter
**When to use:** AI API calls, file I/O, network requests
**Example:**
```python
# src/utils/retry.py
from tenacity import (
    retry, stop_after_attempt, wait_exponential,
    retry_if_exception_type, before_sleep_log
)
import logging

logger = logging.getLogger(__name__)

# Decorator for AI calls (max 3 attempts)
retry_ai = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((TimeoutError, ConnectionError)),
    before_sleep=before_sleep_log(logger, logging.WARNING)
)

# Usage in generator
@retry_ai
def call_anthropic_api(prompt):
    return client.messages.create(...)
```

**Frontend equivalent:**
```javascript
// static/js/error-recovery.js
async function fetchWithRetry(url, options, maxAttempts = 3) {
    let lastError;

    for (let attempt = 0; attempt < maxAttempts; attempt++) {
        try {
            const response = await fetch(url, options);
            if (response.ok) return response;

            // Don't retry 4xx errors (client errors)
            if (response.status >= 400 && response.status < 500) {
                throw new Error(`Client error: ${response.status}`);
            }

            // Retry 5xx errors with backoff
            if (attempt < maxAttempts - 1) {
                const delay = Math.min(1000 * 2 ** attempt, 10000);
                const jitter = Math.random() * 1000;
                await new Promise(resolve => setTimeout(resolve, delay + jitter));
            }
        } catch (error) {
            lastError = error;
            if (attempt === maxAttempts - 1) throw lastError;
        }
    }
}
```

### Pattern 3: Transaction Rollback Fixtures

**What:** Pytest fixtures that rollback database changes after each test
**When to use:** E2E tests that modify database state
**Example:**
```python
# tests/e2e/conftest.py
import pytest
from src.auth.db import get_db

@pytest.fixture(scope="function")
def db_session(app):
    """Provide a transactional scope for tests"""
    connection = get_db()
    transaction = connection.begin()

    yield connection

    transaction.rollback()
    connection.close()

@pytest.fixture
def seeded_course(db_session):
    """Create a course with known structure"""
    from src.core.models import Course, Module, Lesson
    course = Course(
        id="crs_test123",
        title="Test Course",
        ...
    )
    # Insert and commit within transaction
    # Will be rolled back after test
    return course
```

### Pattern 4: Lazy Loading with Pagination

**What:** Load course content on-demand as user navigates
**When to use:** Courses with 20+ activities, dashboard with many courses
**Example:**
```python
# src/api/courses.py
@courses_bp.route("/api/courses/<course_id>/modules/<module_id>/activities")
def get_activities(course_id, module_id):
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    course = project_store.load(course_id)
    module = next((m for m in course.modules if m.id == module_id), None)

    if not module:
        return jsonify({"error": "Module not found"}), 404

    # Paginate activities
    start = (page - 1) * per_page
    end = start + per_page
    activities = module.lessons[start:end] if module.lessons else []

    return jsonify({
        "activities": [a.to_dict() for a in activities],
        "page": page,
        "per_page": per_page,
        "total": len(module.lessons),
        "has_more": end < len(module.lessons)
    })
```

**Frontend:**
```javascript
// static/js/lazy-load.js
class LazyModuleLoader {
    constructor(courseId) {
        this.courseId = courseId;
        this.loadedModules = new Set();
    }

    async loadModule(moduleId) {
        if (this.loadedModules.has(moduleId)) {
            return; // Already loaded
        }

        const response = await fetch(
            `/api/courses/${this.courseId}/modules/${moduleId}/activities?per_page=20`
        );
        const data = await response.json();

        this.renderActivities(moduleId, data.activities);
        this.loadedModules.add(moduleId);
    }

    renderActivities(moduleId, activities) {
        const container = document.querySelector(`[data-module="${moduleId}"] .activities`);
        container.innerHTML = activities.map(a =>
            `<div class="activity-item">${a.title}</div>`
        ).join('');
    }
}
```

### Pattern 5: Skeleton Screens for Loading

**What:** Show page layout wireframe while content loads
**When to use:** Page transitions <10s, heavy content pages (textbook, studio)
**Example:**
```html
<!-- templates/studio.html -->
<div class="studio-layout" data-loading="true">
    <!-- Skeleton shown by default -->
    <div class="skeleton-sidebar">
        <div class="skeleton-item"></div>
        <div class="skeleton-item"></div>
        <div class="skeleton-item"></div>
    </div>

    <!-- Real content hidden until loaded -->
    <div class="activity-sidebar" style="display: none;">
        <!-- Real activity list -->
    </div>
</div>

<script>
async function loadStudio() {
    const layout = document.querySelector('.studio-layout');
    const skeleton = document.querySelector('.skeleton-sidebar');
    const real = document.querySelector('.activity-sidebar');

    const activities = await fetchActivities();

    // Hide skeleton, show real content
    skeleton.style.display = 'none';
    real.style.display = 'block';
    layout.dataset.loading = 'false';
}
</script>
```

**CSS:**
```css
/* static/css/main.css */
.skeleton-item {
    height: 40px;
    margin: 8px 0;
    background: linear-gradient(90deg, #2a2a3e 25%, #3a3a4e 50%, #2a2a3e 75%);
    background-size: 200% 100%;
    animation: skeleton-loading 1.5s infinite;
    border-radius: 4px;
}

@keyframes skeleton-loading {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}
```

### Pattern 6: Contextual Error Display

**What:** Inline errors for field validation, toast for system errors
**When to use:** All form submissions, AI generation, file operations
**Example:**
```javascript
// static/js/error-handling.js
class ErrorHandler {
    // Field-level inline error
    showFieldError(fieldName, message) {
        const field = document.querySelector(`[name="${fieldName}"]`);
        const errorDiv = document.createElement('div');
        errorDiv.className = 'field-error';
        errorDiv.textContent = message;
        field.parentNode.appendChild(errorDiv);
        field.classList.add('error');
    }

    // System-level toast notification
    showToast(message, type = 'error') {
        const toast = new Notyf();
        if (type === 'error') {
            toast.error({
                message,
                duration: 5000,
                dismissible: true
            });
        } else {
            toast.success(message);
        }

        // Log technical details to console
        console.error('[ErrorHandler]', { message, type, timestamp: new Date() });
    }

    // Smart retry handler
    async handleApiError(error, retryFn, context) {
        if (error.status === 502 || error.status === 503) {
            // Transient failure - offer retry
            const retry = confirm(
                'The server is temporarily unavailable. Would you like to retry?'
            );
            if (retry) {
                return await retryFn();
            }
        } else if (error.status === 400) {
            // Validation error - show inline
            if (error.field) {
                this.showFieldError(error.field, error.message);
            } else {
                this.showToast(error.message, 'error');
            }
        } else {
            // Unknown error - toast with technical details in console
            this.showToast('An unexpected error occurred. Please try again.');
            console.error('[API Error]', error);
        }
    }
}
```

### Pattern 7: Onboarding Tour with Intro.js

**What:** Interactive step-by-step tour for first-time users
**When to use:** First login, new feature rollout
**Example:**
```javascript
// static/js/onboarding.js
const tourSteps = [
    {
        element: '#create-course-btn',
        intro: 'Start by creating your first course. Click here to begin.',
        position: 'right'
    },
    {
        element: '#planner-tab',
        intro: 'The Planner helps you define learning outcomes and generate a course blueprint.',
        position: 'bottom'
    },
    {
        element: '#builder-tab',
        intro: 'Use the Builder to structure your course with modules, lessons, and activities.',
        position: 'bottom'
    },
    {
        element: '#studio-tab',
        intro: 'The Studio is where you generate and edit all your course content.',
        position: 'bottom'
    }
];

function startOnboardingTour() {
    introJs()
        .setOptions({
            steps: tourSteps,
            showProgress: true,
            showBullets: false,
            exitOnOverlayClick: false,
            dontShowAgain: true,
            dontShowAgainLabel: "Don't show this again"
        })
        .oncomplete(() => {
            localStorage.setItem('onboarding_completed', 'true');
        })
        .onexit(() => {
            localStorage.setItem('onboarding_skipped', 'true');
        })
        .start();
}

// Auto-start for first-time users
document.addEventListener('DOMContentLoaded', () => {
    const hasCompletedOnboarding = localStorage.getItem('onboarding_completed');
    const hasSkippedOnboarding = localStorage.getItem('onboarding_skipped');

    if (!hasCompletedOnboarding && !hasSkippedOnboarding) {
        startOnboardingTour();
    }
});

// Menu option to replay tour
document.querySelector('#replay-tour-btn').addEventListener('click', () => {
    startOnboardingTour();
});
```

### Anti-Patterns to Avoid

- **Blocking UI during AI generation:** Use SSE streaming or stage indicators; never freeze the page
- **Global retry on all errors:** Don't retry 4xx errors (client mistakes); only retry transient failures
- **Counting total rows for pagination:** For large datasets, use cursor-based pagination or skip total count
- **Progress bars for <10s loads:** Use skeleton screens instead; progress bars increase perceived wait time
- **Dense help text everywhere:** Progressive disclosure; show help when needed, not all at once
- **Single timeout value:** Different operations need different thresholds (30s save, 90s generation, 120s export)

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Retry with backoff | Custom setTimeout loop | Tenacity library | Handles jitter, circuit breakers, idempotency, edge cases (connection reset, partial response) |
| Browser automation | Selenium with manual waits | Playwright | Auto-waits for elements, parallel execution, modern async API, better error messages |
| Toast notifications | DIV + setTimeout | Notyf or Toastify | Accessibility (ARIA, screen readers), mobile responsive, queue management, dismissal logic |
| Onboarding tours | Custom overlays | Intro.js or Shepherd | Step sequencing, progress tracking, mobile support, keyboard navigation, position calculation |
| Test data fixtures | Manual JSON files | Faker + pytest fixtures | Seeded randomness, realistic data (names, dates), repeatable tests, locale support |
| Database rollback | Manual DELETE queries | pytest-flask-sqlalchemy | Nested transactions (savepoints), handles foreign keys, faster than DELETE, no orphaned data |

**Key insight:** Integration and polish work involves many small UX details that seem simple (toasts, tours, retries) but have subtle edge cases around accessibility, mobile, keyboard navigation, and error states. Mature libraries have solved these; custom implementations miss edge cases.

## Common Pitfalls

### Pitfall 1: Flaky E2E Tests from Race Conditions

**What goes wrong:** Tests intermittently fail because elements aren't ready when assertions run
**Why it happens:** Async operations (SSE streaming, API calls) complete at unpredictable times
**How to avoid:** Use Playwright's auto-wait and explicit wait_for_selector with state checks
**Warning signs:** Tests pass locally but fail in CI, "Element not found" errors, timeouts

**Prevention:**
```python
# Bad: Assumes element is immediately present
def test_generate_content(page):
    page.click("#generate-btn")
    assert "Generated content" in page.inner_text(".preview")  # Flaky!

# Good: Wait for element with expected state
def test_generate_content(page):
    page.click("#generate-btn")
    page.wait_for_selector(".preview:has-text('Generated content')", state="visible", timeout=90000)
    preview = page.locator(".preview")
    expect(preview).to_contain_text("Generated content")
```

### Pitfall 2: Retry Storm on System Failure

**What goes wrong:** When AI API is down, all clients retry simultaneously, overwhelming the service when it recovers
**Why it happens:** Synchronized retry timing without jitter creates thundering herd
**How to avoid:** Always add random jitter to exponential backoff delays
**Warning signs:** API recovers briefly then crashes again, spiky traffic patterns

**Prevention:**
```python
# Bad: Fixed exponential backoff
wait=wait_exponential(multiplier=1, min=4, max=10)

# Good: Exponential backoff with jitter
wait=wait_random_exponential(multiplier=1, min=4, max=10)
```

### Pitfall 3: Loading Entire Course in Dashboard

**What goes wrong:** Dashboard becomes slow with 10+ courses, especially with large courses
**Why it happens:** Loading full course JSON (including all content) when only titles/counts needed
**How to avoid:** Create lightweight summary endpoint that returns only metadata, lazy-load full course on demand
**Warning signs:** Dashboard load time >2s, 500KB+ JSON responses, browser memory spikes

**Prevention:**
```python
# Bad: Load full course for dashboard
courses = [project_store.load(id) for id in ids]  # Loads all content!

# Good: Load summary only
def load_summary(course_id):
    """Load course metadata without full content"""
    course = project_store.load(course_id)
    return {
        "id": course.id,
        "title": course.title,
        "module_count": len(course.modules),
        "activity_count": sum(len(m.lessons) for m in course.modules),
        "updated_at": course.updated_at
    }
```

### Pitfall 4: HAR File Brittleness in Tests

**What goes wrong:** HAR-recorded API mocks break when API changes, causing false test failures
**Why it happens:** HAR files capture exact responses, including fields that may change
**How to avoid:** Use route mocking with flexible matchers instead of HAR for frequently-changing APIs; reserve HAR for stable external APIs
**Warning signs:** Tests fail after API changes even though functionality works

**Prevention:**
```python
# Bad: HAR file for internal API (brittle)
page.route_from_har("recordings/api.har")

# Good: Flexible route mock for internal API
def handle_route(route):
    if "/generate" in route.request.url:
        route.fulfill(json={"content": {...}, "metadata": {...}})  # Only mock what test needs
    else:
        route.continue_()

page.route("**/api/**", handle_route)
```

### Pitfall 5: No Timeout Differentiation

**What goes wrong:** Quick operations timeout too late, long operations timeout too early
**Why it happens:** Single global timeout value for all operations
**How to avoid:** Set operation-specific timeouts based on expected duration
**Warning signs:** Users wait 30s for save to fail, textbook generation times out prematurely

**Prevention:**
```javascript
// Good: Operation-specific timeouts
const TIMEOUTS = {
    SAVE: 30000,        // 30s for quick saves
    GENERATE: 90000,    // 90s for content generation
    TEXTBOOK: 120000,   // 2min for textbook/export
    STREAM: 0           // No timeout for SSE streams
};

async function generateContent(activityId) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), TIMEOUTS.GENERATE);

    try {
        const response = await fetch(`/api/activities/${activityId}/generate`, {
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        return response;
    } catch (error) {
        if (error.name === 'AbortError') {
            // Show timeout-specific message with option to retry or cancel
            showTimeoutDialog(activityId);
        }
        throw error;
    }
}
```

### Pitfall 6: Error Logging Without Context

**What goes wrong:** Error logs lack context for debugging (which user, which course, what action)
**Why it happens:** Logging only exception message without request/session context
**How to avoid:** Include user ID, course ID, request path, timestamp in all error logs
**Warning signs:** Cannot reproduce bugs from production logs, ambiguous error reports

**Prevention:**
```python
# Bad: Minimal logging
except Exception as e:
    logger.error(f"Generation failed: {e}")

# Good: Contextual logging
except Exception as e:
    logger.error(
        "Content generation failed",
        extra={
            "user_id": current_user.id,
            "course_id": course_id,
            "activity_id": activity_id,
            "content_type": activity.content_type,
            "error": str(e),
            "traceback": traceback.format_exc()
        }
    )
```

## Code Examples

Verified patterns from official sources:

### E2E Test with Live Server

```python
# tests/e2e/conftest.py
# Source: https://playwright.dev/python/docs/test-runners
import pytest
from playwright.sync_api import sync_playwright
from app import create_app
from threading import Thread
from werkzeug.serving import make_server

@pytest.fixture(scope="session")
def app():
    """Create Flask app for testing"""
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SERVER_NAME": "localhost:5003"
    })
    return app

@pytest.fixture(scope="session")
def live_server(app):
    """Start Flask server in background thread"""
    server = make_server("localhost", 5003, app)
    thread = Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    yield "http://localhost:5003"

    server.shutdown()

@pytest.fixture(scope="session")
def browser():
    """Launch browser for E2E tests"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()

@pytest.fixture
def page(browser):
    """Create new page for each test"""
    context = browser.new_context()
    page = context.new_page()
    yield page
    context.close()
```

### Flask Error Handler with JSON Response

```python
# src/utils/error_handlers.py
# Source: https://flask.palletsprojects.com/en/stable/errorhandling/
from flask import jsonify
from werkzeug.exceptions import HTTPException

def register_error_handlers(app):
    """Register all error handlers for the app"""

    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        """Return JSON for all HTTP errors"""
        response = e.get_response()
        response.data = jsonify({
            "code": e.code,
            "name": e.name,
            "description": e.description
        }).data
        response.content_type = "application/json"
        return response

    @app.errorhandler(Exception)
    def handle_exception(e):
        """Handle unexpected exceptions"""
        # Pass through HTTP exceptions
        if isinstance(e, HTTPException):
            return e

        # Log unexpected error
        app.logger.error(f"Unhandled exception: {e}", exc_info=True)

        # Return generic 500
        return jsonify({
            "code": 500,
            "name": "Internal Server Error",
            "description": "An unexpected error occurred"
        }), 500
```

### Tenacity Retry Decorator

```python
# src/utils/retry.py
# Source: https://tenacity.readthedocs.io/
from tenacity import (
    retry, stop_after_attempt, wait_random_exponential,
    retry_if_exception_type, before_sleep_log
)
import logging

logger = logging.getLogger(__name__)

# AI API calls: 3 attempts with exponential backoff + jitter
ai_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_random_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((TimeoutError, ConnectionError, APIError)),
    before_sleep=before_sleep_log(logger, logging.WARNING)
)

# File operations: 5 attempts with shorter backoff
file_retry = retry(
    stop=stop_after_attempt(5),
    wait=wait_random_exponential(multiplier=0.5, min=1, max=5),
    retry=retry_if_exception_type((IOError, OSError)),
    before_sleep=before_sleep_log(logger, logging.INFO)
)

# Usage:
@ai_retry
def generate_content(prompt):
    return client.messages.create(...)

@file_retry
def save_course(course):
    project_store.save(course)
```

### Playwright API Mocking

```python
# tests/e2e/test_content_generation.py
# Source: https://playwright.dev/python/docs/mock
import pytest
from playwright.sync_api import Page, Route

def test_content_generation_with_mock(page: Page):
    """Test content generation with mocked AI response"""

    # Mock AI generation endpoint
    def handle_generate(route: Route):
        if "/generate" in route.request.url:
            route.fulfill(
                status=200,
                content_type="application/json",
                body='{"content": {"hook": "Test hook"}, "metadata": {"word_count": 500}}'
            )
        else:
            route.continue_()

    page.route("**/api/courses/*/activities/*/generate", handle_generate)

    # Navigate and trigger generation
    page.goto("http://localhost:5003/studio?activity=act_123")
    page.click("button:has-text('Generate')")

    # Wait for mocked response to appear
    page.wait_for_selector(".preview:has-text('Test hook')", state="visible")

    # Assert generation completed
    assert page.inner_text(".status") == "Generated"
```

### Intro.js Onboarding Tour

```javascript
// static/js/onboarding.js
// Source: https://introjs.com/
function initializeOnboarding() {
    const tour = introJs();

    tour.setOptions({
        steps: [
            {
                element: document.querySelector('#create-course-btn'),
                intro: 'Start by creating your first course here.',
                position: 'right'
            },
            {
                element: document.querySelector('#planner-tab'),
                intro: 'Define learning outcomes and generate your course blueprint.',
                position: 'bottom'
            },
            {
                element: document.querySelector('#studio-tab'),
                intro: 'Generate and edit all your course content in the Studio.',
                position: 'bottom'
            }
        ],
        showProgress: true,
        showBullets: false,
        exitOnOverlayClick: false,
        dontShowAgain: true,
        dontShowAgainCookie: 'onboarding_completed'
    });

    // Auto-start for new users
    if (!localStorage.getItem('onboarding_completed')) {
        tour.start();
    }

    // Add replay option to menu
    document.querySelector('#replay-tour').addEventListener('click', () => {
        tour.start();
    });
}

document.addEventListener('DOMContentLoaded', initializeOnboarding);
```

### Notyf Toast Notification

```javascript
// static/js/toast.js
// Source: https://carlosroso.com/notyf/
const notyf = new Notyf({
    duration: 5000,
    position: { x: 'right', y: 'top' },
    dismissible: true,
    ripple: true
});

// Success notification
function showSuccess(message) {
    notyf.success({
        message,
        duration: 3000
    });
}

// Error notification with longer duration
function showError(message) {
    notyf.error({
        message,
        duration: 5000,
        dismissible: true
    });

    // Log technical details to console
    console.error('[Toast Error]', { message, timestamp: new Date() });
}

// Warning notification (custom type)
function showWarning(message) {
    notyf.open({
        type: 'warning',
        message,
        duration: 4000,
        background: '#FFA500',
        icon: {
            className: 'notyf-icon-warning',
            tagName: 'span',
            text: '⚠️'
        }
    });
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Selenium WebDriver | Playwright | 2020 | Auto-wait eliminates flaky tests, parallel execution 3x faster |
| Manual retry loops | Tenacity library | Ongoing | Exponential backoff with jitter prevents retry storms, circuit breakers |
| Flask-Testing fixtures | pytest-playwright | 2021+ | Live server in background thread, browser automation for full E2E |
| Progress spinners | Skeleton screens | 2019+ | 20-30% faster perceived load time, maintains visual context |
| Custom tour overlays | Intro.js/Shepherd | Mature | Accessibility (A11Y), keyboard navigation, mobile support built-in |
| Alert/confirm dialogs | Toast notifications | Mature | Non-blocking, queue management, better UX |
| Manual seed data | Faker fixtures | Mature | Repeatable random data, locale support, realistic test data |

**Deprecated/outdated:**
- **Selenium with time.sleep()**: Replaced by Playwright's auto-wait; explicit waits are more reliable
- **Global try/except for retry**: Use Tenacity decorators for sophisticated retry strategies
- **Bootstrap modals for errors**: Use lightweight toast libraries (Notyf, Toastify) for system notifications
- **Static help text**: Use Intro.js tours for progressive disclosure, contextual help panels
- **unittest**: pytest is standard for Python testing (fixtures, parametrize, plugins)

## Open Questions

Things that couldn't be fully resolved:

1. **SSE timeout handling on slow connections**
   - What we know: SSE streams are infinite, browsers handle reconnection automatically
   - What's unclear: Best practice for detecting "stuck" SSE streams vs legitimately slow generation
   - Recommendation: Implement heartbeat messages every 15s during generation; frontend detects missing heartbeat as timeout

2. **E2E test data reset strategy**
   - What we know: Transaction rollback works for SQLite (users), JSON files need manual cleanup
   - What's unclear: Whether to reset projects/ directory between E2E tests or use unique IDs per test
   - Recommendation: Use unique course IDs per test (crs_test_{uuid}) and clean up in fixture teardown; avoids shared state

3. **Help content maintenance workflow**
   - What we know: Intro.js tours defined in JavaScript, glossary terms could be in JSON/database
   - What's unclear: Whether help content should be editable through admin UI or maintained in code
   - Recommendation: Keep tours in code (rarely change), store glossary in JSON file for easier updates without deployment

4. **Playwright CI resource requirements**
   - What we know: Browser tests use more memory/CPU than unit tests
   - What's unclear: Optimal number of parallel workers for CI environment
   - Recommendation: Start with 2 workers in CI, monitor resource usage, adjust up to 4 if stable

## Sources

### Primary (HIGH confidence)

- [Playwright Python Docs - Test Runners](https://playwright.dev/python/docs/test-runners) - pytest integration, fixtures
- [Flask Error Handling](https://flask.palletsprojects.com/en/stable/errorhandling/) - @errorhandler decorator, custom errors
- [Tenacity Documentation](https://tenacity.readthedocs.io/) - Retry patterns, exponential backoff
- [Intro.js Official Site](https://introjs.com/) - Onboarding tours (10kB, zero dependencies)
- [Playwright Python Docs - Mock APIs](https://playwright.dev/python/docs/mock) - API mocking patterns

### Secondary (MEDIUM confidence)

- [Playwright Best Practices](https://playwright.dev/docs/best-practices) - Test isolation, auto-waiting
- [BrowserStack - Playwright Best Practices 2026](https://www.browserstack.com/guide/playwright-best-practices) - Parallel execution, CI integration
- [Testomat.io - Flask Testing with Playwright](https://testomat.io/blog/automation-testing-flask-application-with-playwright-pytest-examples/) - Flask-specific E2E patterns
- [Better Stack - Flask Error Handling Patterns](https://betterstack.com/community/guides/scaling-python/flask-error-handling/) - Structured logging, custom exceptions
- [EasyParser - API Error Handling & Retry Strategies](https://easyparser.com/blog/api-error-handling-retry-strategies-python-guide) - Exponential backoff with jitter, circuit breakers
- [Notyf Official](https://carlosroso.com/notyf/) - Toast notifications (3kB, A11Y)
- [Medium - Flask API Optimization with Pagination and Lazy Loading](https://medium.com/@iragantiganesh555/flask-api-optimization-with-pagination-and-lazy-loading-64f9879469f6) - Lazy loading patterns
- [NN/g - Skeleton Screens](https://www.nngroup.com/articles/skeleton-screens/) - UX research on loading indicators
- [DataMade - Transactional Testing with Flask-SQLAlchemy](https://datamade.us/blog/transactional-testing/) - Transaction rollback fixtures
- [Advanced Web Machinery - Exponential Backoff in JavaScript](https://advancedweb.hu/how-to-implement-an-exponential-backoff-retry-strategy-in-javascript/) - Frontend retry patterns
- [Flask-SSE Quickstart](https://flask-sse.readthedocs.io/en/latest/quickstart.html) - SSE timeout handling

### Tertiary (LOW confidence)

- [Chameleon - 10 Best JavaScript Onboarding Libraries](https://www.chameleon.io/blog/javascript-product-tours) - Tour library comparison
- [Whatfix - 22 Best Software Documentation Tools 2026](https://whatfix.com/blog/software-documentation-tools/) - In-app help systems
- [CSS Script - Best Toast Notification Libraries 2026](https://www.cssscript.com/best-toast-notification-libraries/) - Toast library comparison

## Metadata

**Confidence breakdown:**
- E2E testing stack: HIGH - Official Playwright docs, verified Flask integration patterns
- Error handling: HIGH - Official Flask docs, Tenacity library documentation
- Performance (lazy loading, skeleton screens): MEDIUM - Multiple sources agree, no official Flask guidance
- Help systems: MEDIUM - WebSearch-based comparison, Intro.js official docs verified
- Integration patterns: HIGH - Playwright, pytest, Tenacity all have official Python docs

**Research date:** 2026-02-11
**Valid until:** ~30 days (stable ecosystem, minimal churn expected in testing/error handling tools)
