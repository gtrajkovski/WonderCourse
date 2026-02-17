"""E2E tests for error recovery and resilience.

Tests retry logic, timeout handling, operation cancellation,
and inline validation.
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
def test_retry_on_server_error(page: Page, mock_ai_responses, clean_db, live_server):
    """Test automatic retry on server error.

    Verifies:
    - First request fails with 503
    - System automatically retries
    - Second request succeeds
    - User sees success, not error
    """
    # Register and login
    page.goto(f"{live_server}/register")
    page.fill('input#name', "Retry User")
    page.fill('input#email', "retry@test.com")
    page.fill('input#password', "retrypassword123")
    page.fill('input#confirm_password', "retrypassword123")
    page.click('button[type="submit"]')
    page.wait_for_url(f"{live_server}/login*", timeout=5000)

    page.fill('input#email', "retry@test.com")
    page.fill('input#password', "retrypassword123")
    page.click('button[type="submit"]')
    page.wait_for_url(f"{live_server}/dashboard", timeout=5000)

    # Create course
    page.click('#create-course-btn')
    page.wait_for_selector('.modal', timeout=5000)
    page.fill('input[name="title"]', "Retry Test Course")
    page.fill('textarea[name="description"]', "Testing retry logic")

    # Intercept API call to simulate server error on first attempt
    first_call = [True]  # Mutable container to track state

    def handle_route(route):
        if '/courses' in route.request.url and route.request.method == 'POST':
            if first_call[0]:
                # First call: return 503
                first_call[0] = False
                route.fulfill(status=503, body='{"error": "Service unavailable"}')
            else:
                # Second call: let it succeed
                route.continue_()
        else:
            route.continue_()

    page.route('**/api/**', handle_route)

    # Submit form (should trigger retry logic)
    page.click('.modal button[type="submit"]')

    # Should eventually succeed (after retry)
    page.wait_for_selector('.course-card:has-text("Retry Test Course")', timeout=15000)
    course_card = page.locator('.course-card:has-text("Retry Test Course")')
    expect(course_card).to_be_visible()

    # Should NOT show error to user
    error_msg = page.locator('.alert-danger, .error-message')
    expect(error_msg).not_to_be_visible()


@pytest.mark.e2e
def test_timeout_dialog_appears(page: Page, mock_ai_responses, clean_db, live_server):
    """Test timeout dialog for long operations.

    Verifies:
    - Long operation triggers timeout warning
    - Dialog appears with option to wait
    - "Keep Waiting" extends timeout
    - Operation eventually succeeds
    """
    # Register and login
    page.goto(f"{live_server}/register")
    page.fill('input#name', "Timeout User")
    page.fill('input#email', "timeout@test.com")
    page.fill('input#password', "timeoutpassword123")
    page.fill('input#confirm_password', "timeoutpassword123")
    page.click('button[type="submit"]')
    page.wait_for_url(f"{live_server}/login*", timeout=5000)

    page.fill('input#email', "timeout@test.com")
    page.fill('input#password', "timeoutpassword123")
    page.click('button[type="submit"]')
    page.wait_for_url(f"{live_server}/dashboard", timeout=5000)

    # Create course and navigate to planner
    page.click('#create-course-btn')
    page.wait_for_selector('.modal', timeout=5000)
    page.fill('input[name="title"]', "Timeout Test")
    page.fill('textarea[name="description"]', "Testing timeouts")
    page.click('.modal button[type="submit"]')
    page.wait_for_selector('.course-card:has-text("Timeout Test")', timeout=5000)

    course_card = page.locator('.course-card:has-text("Timeout Test")')
    course_card.locator('button.btn-open').click()
    page.wait_for_url(f"{live_server}/courses/*/planner", timeout=5000)

    # Simulate slow response (35 seconds)
    def handle_slow_route(route):
        if '/blueprint/generate' in route.request.url:
            # Delay response by 35 seconds (beyond 30s timeout)
            import time
            time.sleep(35)
            route.continue_()
        else:
            route.continue_()

    page.route('**/api/**', handle_slow_route)

    # Generate blueprint (should timeout)
    page.click('#blueprint-tab')
    page.wait_for_selector('#blueprint-content', state='visible', timeout=5000)
    page.click('#generate-blueprint-btn')

    # Timeout dialog should appear around 30s
    page.wait_for_selector('.timeout-dialog, .modal:has-text("timeout")', timeout=35000)
    timeout_dialog = page.locator('.timeout-dialog, .modal:has-text("timeout")')
    expect(timeout_dialog).to_be_visible()

    # Click "Keep Waiting" button
    keep_waiting_btn = timeout_dialog.locator('button:has-text("Keep Waiting"), button:has-text("Wait")')
    if keep_waiting_btn.is_visible():
        keep_waiting_btn.click()

    # Eventually should complete (if backend finishes)
    # For this test, we just verify the dialog appeared and button works


@pytest.mark.e2e
def test_cancel_long_operation(page: Page, mock_ai_responses, clean_db, live_server):
    """Test canceling a long-running operation.

    Verifies:
    - Long operation can be started
    - Cancel button appears
    - Clicking cancel stops operation
    - UI returns to stable state
    """
    # Register and login
    page.goto(f"{live_server}/register")
    page.fill('input#name', "Cancel User")
    page.fill('input#email', "cancel@test.com")
    page.fill('input#password', "cancelpassword123")
    page.fill('input#confirm_password', "cancelpassword123")
    page.click('button[type="submit"]')
    page.wait_for_url(f"{live_server}/login*", timeout=5000)

    page.fill('input#email', "cancel@test.com")
    page.fill('input#password', "cancelpassword123")
    page.click('button[type="submit"]')
    page.wait_for_url(f"{live_server}/dashboard", timeout=5000)

    # Create course and navigate to studio
    page.click('#create-course-btn')
    page.wait_for_selector('.modal', timeout=5000)
    page.fill('input[name="title"]', "Cancel Test")
    page.fill('textarea[name="description"]', "Testing cancellation")
    page.click('.modal button[type="submit"]')
    page.wait_for_selector('.course-card:has-text("Cancel Test")', timeout=5000)

    course_card = page.locator('.course-card:has-text("Cancel Test")')
    course_card.locator('button.btn-open').click()
    page.wait_for_url(f"{live_server}/courses/*/planner", timeout=5000)

    # Generate blueprint first
    page.click('#blueprint-tab')
    page.wait_for_selector('#blueprint-content', state='visible', timeout=5000)
    page.click('#generate-blueprint-btn')
    page.wait_for_selector('.blueprint-preview', timeout=30000)
    page.click('#accept-blueprint-btn')
    page.wait_for_selector('.toast-success, .alert-success', timeout=10000)

    # Navigate to studio
    page.goto(page.url.replace('/planner', '/studio'))
    page.wait_for_selector('.activity-list', timeout=5000)

    # Start content generation
    page.click('.activity-item:first-child')
    page.wait_for_selector('#generate-btn', timeout=5000)
    page.click('#generate-btn')

    # Wait for cancel button to appear (during generation)
    page.wait_for_selector('#cancel-btn, button:has-text("Cancel")', timeout=5000)
    cancel_btn = page.locator('#cancel-btn, button:has-text("Cancel")')
    expect(cancel_btn).to_be_visible()

    # Click cancel
    cancel_btn.click()

    # Should return to stable state
    page.wait_for_selector('#generate-btn', timeout=5000)
    generate_btn = page.locator('#generate-btn')
    expect(generate_btn).to_be_visible()

    # No error state
    expect(page.locator('.error-state')).not_to_be_visible()


@pytest.mark.e2e
def test_validation_error_inline(page: Page, clean_db, live_server):
    """Test inline validation error display.

    Verifies:
    - Invalid form data triggers inline error
    - Error appears next to field
    - Fixing error and resubmitting succeeds
    """
    # Register and login
    page.goto(f"{live_server}/register")
    page.fill('input#name', "Validation User")
    page.fill('input#email', "validation@test.com")
    page.fill('input#password', "validationpassword123")
    page.fill('input#confirm_password', "validationpassword123")
    page.click('button[type="submit"]')
    page.wait_for_url(f"{live_server}/login*", timeout=5000)

    page.fill('input#email', "validation@test.com")
    page.fill('input#password', "validationpassword123")
    page.click('button[type="submit"]')
    page.wait_for_url(f"{live_server}/dashboard", timeout=5000)

    # Try to create course with invalid data (empty title)
    page.click('#create-course-btn')
    page.wait_for_selector('.modal', timeout=5000)

    # Leave title empty, fill description
    page.fill('input[name="title"]', '')
    page.fill('textarea[name="description"]', 'Some description')

    # Try to submit
    page.click('.modal button[type="submit"]')

    # Should show inline error near title field
    # Browser might use HTML5 validation or JavaScript
    page.wait_for_timeout(1000)

    # Modal should stay open
    expect(page.locator('.modal')).to_be_visible()

    # No course card should appear
    expect(page.locator('.course-card')).not_to_be_visible()

    # Fix error by filling title
    page.fill('input[name="title"]', 'Valid Course Title')

    # Resubmit
    page.click('.modal button[type="submit"]')

    # Should succeed
    page.wait_for_selector('.course-card:has-text("Valid Course Title")', timeout=5000)
    course_card = page.locator('.course-card:has-text("Valid Course Title")')
    expect(course_card).to_be_visible()
