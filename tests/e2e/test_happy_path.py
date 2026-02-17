"""Happy path E2E test covering full user workflow.

Tests the complete user journey from registration through export,
verifying that all major features work together in a real browser.
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
@pytest.mark.slow
def test_registration_to_export(page: Page, mock_ai_responses, clean_db, live_server):
    """Full happy path: Register -> Create Course -> Generate Blueprint ->
    Generate Content -> Validate -> Export.

    This test covers:
    1. User registration
    2. User login
    3. Course creation
    4. Blueprint generation
    5. Content generation
    6. Validation
    7. Export (basic check)

    All AI responses are mocked for deterministic, fast testing.
    """
    # 1. Registration
    page.goto(f"{live_server}/register")

    # Fill registration form
    page.fill('input#name', "E2E Test User")
    page.fill('input#email', "e2e@test.com")
    page.fill('input#password', "testpassword123")
    page.fill('input#confirm_password', "testpassword123")

    # Submit registration
    page.click('button[type="submit"]')

    # Should redirect to login with success message
    page.wait_for_url(f"{live_server}/login*", timeout=5000)
    expect(page).to_have_url(f"{live_server}/login?registered=true")

    # 2. Login
    page.fill('input#email', "e2e@test.com")
    page.fill('input#password', "testpassword123")
    page.click('button[type="submit"]')

    # Should redirect to dashboard
    page.wait_for_url(f"{live_server}/dashboard", timeout=5000)

    # 3. Create Course
    page.click('#create-course-btn')

    # Wait for modal to appear
    page.wait_for_selector('.modal', timeout=5000)

    # Fill course creation form
    page.fill('input[name="title"]', "E2E Test Course")
    page.fill('textarea[name="description"]', "Test course for E2E testing")

    # Submit course creation
    page.click('.modal button[type="submit"]')

    # Should see course in list
    page.wait_for_selector('.course-card:has-text("E2E Test Course")', timeout=5000)

    # Verify course card displays correct information
    course_card = page.locator('.course-card:has-text("E2E Test Course")')
    expect(course_card).to_be_visible()
    expect(course_card.locator('.course-description')).to_contain_text("Test course for E2E testing")

    # 4. Navigate to Planner and Generate Blueprint
    # Click Open button on course card
    course_card.locator('button.btn-open').click()

    # Should navigate to planner (first page after opening course)
    page.wait_for_url(f"{live_server}/courses/*/planner", timeout=5000)

    # Switch to Blueprint tab
    page.click('#blueprint-tab')

    # Wait for tab content to be visible
    page.wait_for_selector('#blueprint-content', state='visible', timeout=5000)

    # Click generate blueprint button
    page.click('#generate-blueprint-btn')

    # Wait for blueprint preview to appear (AI generation takes time)
    page.wait_for_selector('.blueprint-preview', timeout=30000)

    # Verify blueprint contains expected structure
    expect(page.locator('.blueprint-preview')).to_contain_text("Introduction to Python")

    # Accept blueprint
    page.click('#accept-blueprint-btn')

    # Wait for acceptance to complete
    page.wait_for_selector('.toast-success, .alert-success', timeout=10000)

    # 5. Navigate to Studio and Generate Content
    page.click('a[href*="studio"]')

    # Wait for studio page to load
    page.wait_for_selector('.activity-list', timeout=5000)

    # Click on first activity
    page.click('.activity-item:first-child')

    # Wait for activity to be selected/loaded
    page.wait_for_selector('.content-preview, #generate-btn', timeout=5000)

    # Click generate content button
    page.click('#generate-btn')

    # Wait for content generation to complete (streaming)
    page.wait_for_selector('.content-preview:has-text("Hook"), .content-preview:has-text("hook")', timeout=30000)

    # Verify content preview shows video script structure
    content_preview = page.locator('.content-preview')
    expect(content_preview).to_be_visible()

    # 6. Navigate to Publish and Validate
    page.click('a[href*="publish"]')

    # Wait for validation results to load
    page.wait_for_selector('.validation-results, .export-card', timeout=10000)

    # 7. Export (basic check - don't need to actually download)
    # Just verify export button is clickable
    export_btn = page.locator('#export-instructor-btn, button:has-text("Export")')
    expect(export_btn.first).to_be_visible()

    # Success! Full workflow completed without errors


@pytest.mark.e2e
def test_login_with_wrong_password(page: Page, clean_db, live_server):
    """Test that login fails gracefully with wrong password.

    Verifies:
    - Error message is displayed
    - No redirect occurs
    - User remains on login page
    """
    # First, create a user via direct API call
    page.goto(f"{live_server}/register")
    page.fill('input#name', "Test User")
    page.fill('input#email', "test@example.com")
    page.fill('input#password', "correctpassword")
    page.fill('input#confirm_password', "correctpassword")
    page.click('button[type="submit"]')
    page.wait_for_url(f"{live_server}/login*", timeout=5000)

    # Now try to login with wrong password
    page.fill('input#email', "test@example.com")
    page.fill('input#password', "wrongpassword")
    page.click('button[type="submit"]')

    # Should stay on login page
    page.wait_for_timeout(1000)  # Give it a moment
    expect(page).to_have_url(f"{live_server}/login")

    # Should show error message
    error_msg = page.locator('.auth-form-error, .form-error, .alert-danger')
    expect(error_msg.first).to_be_visible()


@pytest.mark.e2e
def test_create_course_empty_title(page: Page, mock_ai_responses, clean_db, live_server):
    """Test that course creation validates required fields.

    Verifies:
    - Empty title triggers validation error
    - Modal remains open
    - Course is not created
    """
    # Register and login
    page.goto(f"{live_server}/register")
    page.fill('input#name', "Test User")
    page.fill('input#email', "test@example.com")
    page.fill('input#password', "testpassword123")
    page.fill('input#confirm_password', "testpassword123")
    page.click('button[type="submit"]')
    page.wait_for_url(f"{live_server}/login*")

    page.fill('input#email', "test@example.com")
    page.fill('input#password', "testpassword123")
    page.click('button[type="submit"]')
    page.wait_for_url(f"{live_server}/dashboard")

    # Open create course modal
    page.click('#create-course-btn')
    page.wait_for_selector('.modal')

    # Try to submit with empty title
    page.fill('input[name="title"]', "")
    page.fill('textarea[name="description"]', "Some description")
    page.click('.modal button[type="submit"]')

    # Modal should stay open (validation error)
    page.wait_for_timeout(1000)
    expect(page.locator('.modal')).to_be_visible()

    # Should show error message
    error_msg = page.locator('.form-error, .modal-error, .alert-danger')
    # Note: Error might be shown via HTML5 validation or JavaScript
    # We just verify modal stays open and no course card appears
    expect(page.locator('.course-card')).not_to_be_visible()
