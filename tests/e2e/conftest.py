"""Playwright fixtures for E2E tests."""

import os
import tempfile
import threading
import time
import pytest
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright

from app import app as flask_app
from src.core.project_store import ProjectStore


def pytest_addoption(parser):
    """Add custom pytest command line options."""
    parser.addoption(
        "--real-ai",
        action="store_true",
        default=False,
        help="Use real AI API instead of mocks (requires ANTHROPIC_API_KEY)"
    )


@pytest.fixture(scope="session")
def app(tmp_path_factory):
    """Create Flask app configured for E2E testing.

    Sets up isolated database and project store.

    Returns:
        Configured Flask app instance.
    """
    from src.auth.db import init_db
    from src.auth.routes import init_auth_bp

    # Create temporary database
    db_fd, db_path = tempfile.mkstemp()

    # Create temporary projects directory
    tmp_path = tmp_path_factory.mktemp("e2e_projects")
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir(parents=True, exist_ok=True)

    # Patch the project_store
    import app as app_module
    app_module.project_store = ProjectStore(projects_dir)

    # Re-initialize all blueprints with the test project_store
    from src.api.modules import init_modules_bp
    from src.api.lessons import init_lessons_bp
    from src.api.activities import init_activities_bp
    from src.api.learning_outcomes import init_learning_outcomes_bp
    from src.api.blueprint import init_blueprint_bp
    from src.api.content import init_content_bp
    from src.api.build_state import init_build_state_bp
    from src.api.textbook import init_textbook_bp
    from src.api.validation import init_validation_bp
    from src.api.export import init_export_bp
    from src.api.collab import init_collab_bp
    from src.api.import_bp import init_import_bp
    from src.api.coach_bp import init_coach_bp

    init_modules_bp(app_module.project_store)
    init_lessons_bp(app_module.project_store)
    init_activities_bp(app_module.project_store)
    init_learning_outcomes_bp(app_module.project_store)
    init_blueprint_bp(app_module.project_store)
    init_content_bp(app_module.project_store)
    init_build_state_bp(app_module.project_store)
    init_textbook_bp(app_module.project_store)
    init_validation_bp(app_module.project_store)
    init_export_bp(app_module.project_store)
    init_collab_bp(app_module.project_store)
    init_import_bp(app_module.project_store)
    init_coach_bp(app_module.project_store)

    # Configure Flask app for testing
    flask_app.config.update({
        'TESTING': True,
        'DATABASE': db_path,
        'SECRET_KEY': 'e2e-test-secret-key',
        'WTF_CSRF_ENABLED': False,
    })

    # Re-init auth blueprint AFTER setting TESTING=True to disable rate limiter
    init_auth_bp(flask_app)

    # Initialize database
    with flask_app.app_context():
        init_db()
        # Seed collaboration permissions for tests
        from src.collab.permissions import seed_permissions
        from src.auth.db import get_db
        seed_permissions(get_db())

    yield flask_app

    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture(scope="session")
def live_server(app):
    """Start Flask app in background thread.

    Uses werkzeug.serving.make_server to run Flask in a thread.

    Args:
        app: Flask app instance from app fixture

    Yields:
        Base URL of the live server (e.g., http://localhost:5003)
    """
    # Create server
    server = make_server('localhost', 5003, app, threaded=True)

    # Start server in background thread
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    # Give server time to start
    time.sleep(1)

    yield "http://localhost:5003"

    # Shutdown server
    server.shutdown()


@pytest.fixture(scope="session")
def browser():
    """Launch Playwright browser.

    Launches chromium in headless mode by default.
    Set HEADED=1 environment variable to see browser.

    Yields:
        Playwright browser instance
    """
    headed = os.environ.get('HEADED', '0') == '1'

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed)
        yield browser
        browser.close()


@pytest.fixture
def page(browser, live_server):
    """Create new browser page with isolated context.

    Args:
        browser: Playwright browser instance from browser fixture
        live_server: Base URL from live_server fixture

    Yields:
        Playwright page instance
    """
    context = browser.new_context(base_url=live_server)
    page = context.new_page()

    yield page

    page.close()
    context.close()


@pytest.fixture
def mock_ai_responses(page, request):
    """Mock AI API responses for deterministic tests.

    Routes all /api/.*/generate requests to return mock data.
    Skipped if --real-ai flag is set.

    Args:
        page: Playwright page instance from page fixture
        request: pytest request object for accessing command line options
    """
    # Skip mocking if --real-ai flag is set
    if request.config.getoption("--real-ai"):
        yield
        return

    # Import mock responses
    from tests.e2e.fixtures.mock_responses import route_handler

    # Route API calls to mock handler
    def handle_route(route):
        # Check if this is a generate endpoint
        if '/generate' in route.request.url or '/blueprint' in route.request.url:
            response = route_handler(route)
            if response:
                route.fulfill(**response)
                return

        # Continue with real request if not a generate endpoint
        route.continue_()

    page.route("**/api/**", handle_route)

    yield


@pytest.fixture
def clean_db(app):
    """Reset database before each E2E test.

    Truncates users and courses tables, re-seeds permissions.

    Args:
        app: Flask app instance from app fixture
    """
    from src.auth.db import get_db
    from src.collab.permissions import seed_permissions

    with app.app_context():
        db = get_db()

        # Truncate tables (cascade will handle related records)
        db.execute("DELETE FROM user")
        db.execute("DELETE FROM collaborator")
        db.execute("DELETE FROM role")
        db.execute("DELETE FROM invitation")
        db.execute("DELETE FROM comment")
        db.execute("DELETE FROM audit_log")
        db.commit()

        # Re-seed permissions
        seed_permissions(db)

    yield


@pytest.fixture
def second_user(browser, live_server, clean_db):
    """Create and login a second user in a separate browser context.

    Returns:
        Playwright page with second user session
    """
    # Create new browser context (isolated cookies/session)
    context = browser.new_context(base_url=live_server)
    page = context.new_page()

    # Register second user
    page.goto(f"{live_server}/register")
    page.fill('input#name', "Second User")
    page.fill('input#email', "second@test.com")
    page.fill('input#password', "secondpassword123")
    page.fill('input#confirm_password', "secondpassword123")
    page.click('button[type="submit"]')

    # Wait for redirect to login
    page.wait_for_url(f"{live_server}/login*", timeout=5000)

    # Login as second user
    page.fill('input#email', "second@test.com")
    page.fill('input#password', "secondpassword123")
    page.click('button[type="submit"]')

    # Wait for dashboard
    page.wait_for_url(f"{live_server}/dashboard", timeout=5000)

    yield page

    # Cleanup
    page.close()
    context.close()


@pytest.fixture
def course_with_collaborator(page, second_user, live_server, mock_ai_responses):
    """Create course and add second user as collaborator.

    Args:
        page: First user's page
        second_user: Second user's page
        live_server: Server URL
        mock_ai_responses: Mock AI fixture

    Returns:
        Course ID with collaborator added
    """
    # First user registers and logs in
    page.goto(f"{live_server}/register")
    page.fill('input#name', "First User")
    page.fill('input#email', "first@test.com")
    page.fill('input#password', "firstpassword123")
    page.fill('input#confirm_password', "firstpassword123")
    page.click('button[type="submit"]')
    page.wait_for_url(f"{live_server}/login*", timeout=5000)

    page.fill('input#email', "first@test.com")
    page.fill('input#password', "firstpassword123")
    page.click('button[type="submit"]')
    page.wait_for_url(f"{live_server}/dashboard", timeout=5000)

    # Create course
    page.click('#create-course-btn')
    page.wait_for_selector('.modal', timeout=5000)
    page.fill('input[name="title"]', "Collaboration Test Course")
    page.fill('textarea[name="description"]', "Course for testing collaboration")
    page.click('.modal button[type="submit"]')
    page.wait_for_selector('.course-card:has-text("Collaboration Test Course")', timeout=5000)

    # Extract course ID from URL after opening course
    course_card = page.locator('.course-card:has-text("Collaboration Test Course")')
    course_card.locator('button.btn-open').click()
    page.wait_for_url(f"{live_server}/courses/*/planner", timeout=5000)

    # Extract course_id from URL (format: /courses/{course_id}/planner)
    current_url = page.url
    course_id = current_url.split('/courses/')[1].split('/')[0]

    # Open collaboration modal
    page.click('#collaboration-btn, button:has-text("Collaborate")')
    page.wait_for_selector('.collaboration-modal', timeout=5000)

    # Invite second user
    page.fill('input[name="email"]', "second@test.com")
    page.select_option('select[name="role"]', 'Designer')
    page.click('.collaboration-modal button[type="submit"]')

    # Wait for invitation to appear
    page.wait_for_selector('.invitation-pending:has-text("second@test.com")', timeout=5000)

    # Switch to second user and accept invitation
    second_user.goto(f"{live_server}/invitations")
    second_user.wait_for_selector('.invitation-card', timeout=5000)
    second_user.click('.invitation-card button:has-text("Accept")')
    second_user.wait_for_selector('.toast-success, .alert-success', timeout=5000)

    yield course_id
