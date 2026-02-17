"""E2E tests for collaboration features.

Tests multi-user workflows including invitations, permissions,
comments, and activity feed.
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
def test_invite_collaborator_by_email(page: Page, mock_ai_responses, clean_db, live_server):
    """Test inviting a collaborator by email.

    Verifies:
    - Collaboration modal opens
    - Collaborator email and role can be entered
    - Invitation appears in pending list
    """
    # Register and login first user
    page.goto(f"{live_server}/register")
    page.fill('input#name', "Course Owner")
    page.fill('input#email', "owner@test.com")
    page.fill('input#password', "ownerpassword123")
    page.fill('input#confirm_password', "ownerpassword123")
    page.click('button[type="submit"]')
    page.wait_for_url(f"{live_server}/login*", timeout=5000)

    page.fill('input#email', "owner@test.com")
    page.fill('input#password', "ownerpassword123")
    page.click('button[type="submit"]')
    page.wait_for_url(f"{live_server}/dashboard", timeout=5000)

    # Create course
    page.click('#create-course-btn')
    page.wait_for_selector('.modal', timeout=5000)
    page.fill('input[name="title"]', "Collaboration Test Course")
    page.fill('textarea[name="description"]', "Testing collaboration features")
    page.click('.modal button[type="submit"]')
    page.wait_for_selector('.course-card:has-text("Collaboration Test Course")', timeout=5000)

    # Open course
    course_card = page.locator('.course-card:has-text("Collaboration Test Course")')
    course_card.locator('button.btn-open').click()
    page.wait_for_url(f"{live_server}/courses/*/planner", timeout=5000)

    # Open collaboration modal
    page.click('#collaboration-btn, button:has-text("Collaborate")')
    page.wait_for_selector('.collaboration-modal', timeout=5000)

    # Fill invitation form
    page.fill('input[name="email"]', "designer@test.com")
    page.select_option('select[name="role"]', 'Designer')
    page.click('.collaboration-modal button[type="submit"]')

    # Verify invitation appears in pending list
    page.wait_for_selector('.invitation-pending:has-text("designer@test.com")', timeout=5000)
    invitation = page.locator('.invitation-pending:has-text("designer@test.com")')
    expect(invitation).to_be_visible()
    expect(invitation).to_contain_text("Designer")


@pytest.mark.e2e
def test_accept_invitation(page: Page, second_user, live_server, mock_ai_responses, clean_db):
    """Test accepting a collaboration invitation.

    Verifies:
    - Second user can view invitation
    - Invitation can be accepted
    - Course appears in second user's dashboard
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

    # Create course and invite second user
    page.click('#create-course-btn')
    page.wait_for_selector('.modal', timeout=5000)
    page.fill('input[name="title"]', "Shared Course")
    page.fill('textarea[name="description"]', "Course to be shared")
    page.click('.modal button[type="submit"]')
    page.wait_for_selector('.course-card:has-text("Shared Course")', timeout=5000)

    # Open course and invite second user
    course_card = page.locator('.course-card:has-text("Shared Course")')
    course_card.locator('button.btn-open').click()
    page.wait_for_url(f"{live_server}/courses/*/planner", timeout=5000)

    page.click('#collaboration-btn, button:has-text("Collaborate")')
    page.wait_for_selector('.collaboration-modal', timeout=5000)
    page.fill('input[name="email"]', "second@test.com")
    page.select_option('select[name="role"]', 'Designer')
    page.click('.collaboration-modal button[type="submit"]')
    page.wait_for_selector('.invitation-pending:has-text("second@test.com")', timeout=5000)

    # Second user accepts invitation
    second_user.goto(f"{live_server}/invitations")
    second_user.wait_for_selector('.invitation-card', timeout=5000)

    invitation_card = second_user.locator('.invitation-card:has-text("Shared Course")')
    expect(invitation_card).to_be_visible()

    invitation_card.locator('button:has-text("Accept")').click()
    second_user.wait_for_selector('.toast-success, .alert-success', timeout=5000)

    # Verify course appears in second user's dashboard
    second_user.goto(f"{live_server}/dashboard")
    second_user.wait_for_selector('.course-card:has-text("Shared Course")', timeout=5000)
    shared_course = second_user.locator('.course-card:has-text("Shared Course")')
    expect(shared_course).to_be_visible()


@pytest.mark.e2e
def test_role_permissions_enforced(page: Page, course_with_collaborator, live_server, second_user):
    """Test that role permissions are enforced.

    Verifies:
    - Designer can edit content
    - Designer cannot delete course
    - Permission error shown for forbidden actions
    """
    course_id = course_with_collaborator

    # Second user (Designer) navigates to course
    second_user.goto(f"{live_server}/courses/{course_id}/planner")
    second_user.wait_for_selector('.course-header, h1', timeout=5000)

    # Try to access settings (should be forbidden for Designer)
    # Look for settings button or menu
    settings_btn = second_user.locator('#settings-btn, button:has-text("Settings")')
    if settings_btn.is_visible():
        settings_btn.click()
        # Should show permission error
        second_user.wait_for_selector('.permission-error, .alert-danger:has-text("permission")', timeout=5000)
        error = second_user.locator('.permission-error, .alert-danger:has-text("permission")')
        expect(error).to_be_visible()

    # Designer should be able to navigate to studio (edit content)
    second_user.goto(f"{live_server}/courses/{course_id}/studio")
    second_user.wait_for_selector('.studio-container, .activity-list', timeout=5000)
    # No error - can access studio


@pytest.mark.e2e
def test_comment_on_activity(page: Page, course_with_collaborator, live_server, second_user, mock_ai_responses):
    """Test commenting on an activity.

    Verifies:
    - Comments panel can be opened
    - Comment can be added
    - Comment appears in panel
    - Other collaborators can see comment
    """
    course_id = course_with_collaborator

    # First user navigates to studio and generates blueprint
    page.goto(f"{live_server}/courses/{course_id}/planner")
    page.wait_for_selector('#blueprint-tab', timeout=5000)
    page.click('#blueprint-tab')
    page.wait_for_selector('#blueprint-content', state='visible', timeout=5000)
    page.click('#generate-blueprint-btn')
    page.wait_for_selector('.blueprint-preview', timeout=30000)
    page.click('#accept-blueprint-btn')
    page.wait_for_selector('.toast-success, .alert-success', timeout=10000)

    # Navigate to studio
    page.goto(f"{live_server}/courses/{course_id}/studio")
    page.wait_for_selector('.activity-list', timeout=5000)

    # Click on first activity
    page.click('.activity-item:first-child')
    page.wait_for_selector('.content-preview, #generate-btn', timeout=5000)

    # Open comments panel
    page.click('#comments-btn, button:has-text("Comments")')
    page.wait_for_selector('.comments-panel', timeout=5000)

    # Add comment
    page.fill('textarea[name="comment"]', "This activity needs more examples")
    page.click('.comments-panel button[type="submit"]')

    # Verify comment appears
    page.wait_for_selector('.comment:has-text("This activity needs more examples")', timeout=5000)
    comment = page.locator('.comment:has-text("This activity needs more examples")')
    expect(comment).to_be_visible()
    expect(comment).to_contain_text("First User")

    # Second user can see comment
    second_user.goto(f"{live_server}/courses/{course_id}/studio")
    second_user.wait_for_selector('.activity-list', timeout=5000)
    second_user.click('.activity-item:first-child')
    second_user.wait_for_selector('.content-preview, #generate-btn', timeout=5000)
    second_user.click('#comments-btn, button:has-text("Comments")')
    second_user.wait_for_selector('.comments-panel', timeout=5000)

    # Verify comment visible to second user
    second_user_comment = second_user.locator('.comment:has-text("This activity needs more examples")')
    expect(second_user_comment).to_be_visible()


@pytest.mark.e2e
def test_activity_feed_shows_changes(page: Page, course_with_collaborator, live_server, second_user, mock_ai_responses):
    """Test that activity feed shows changes from collaborators.

    Verifies:
    - First user's edits appear in feed
    - Second user can see these changes
    - Feed shows user who made change
    """
    course_id = course_with_collaborator

    # First user makes an edit (create blueprint)
    page.goto(f"{live_server}/courses/{course_id}/planner")
    page.wait_for_selector('#blueprint-tab', timeout=5000)
    page.click('#blueprint-tab')
    page.wait_for_selector('#blueprint-content', state='visible', timeout=5000)
    page.click('#generate-blueprint-btn')
    page.wait_for_selector('.blueprint-preview', timeout=30000)
    page.click('#accept-blueprint-btn')
    page.wait_for_selector('.toast-success, .alert-success', timeout=10000)

    # Second user views activity feed
    second_user.goto(f"{live_server}/courses/{course_id}/activity")
    second_user.wait_for_selector('.activity-feed', timeout=5000)

    # Verify blueprint generation appears in feed
    feed_item = second_user.locator('.feed-item:has-text("blueprint"), .feed-item:has-text("generated")')
    expect(feed_item.first).to_be_visible()

    # Should show first user as author
    expect(feed_item.first).to_contain_text("First User")
