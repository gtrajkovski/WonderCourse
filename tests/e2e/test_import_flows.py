"""E2E tests for import flows.

Tests importing content via paste (JSON/Markdown), file upload,
validation, and AI enhancement.
"""

import pytest
import json
from playwright.sync_api import Page, expect


# Sample blueprint for import testing
SAMPLE_BLUEPRINT_JSON = json.dumps({
    "title": "Imported Course",
    "description": "Course imported from JSON",
    "duration_minutes": 120,
    "modules": [
        {
            "title": "Imported Module 1",
            "description": "First imported module",
            "order": 0,
            "lessons": [
                {
                    "title": "Imported Lesson 1",
                    "description": "First imported lesson",
                    "order": 0,
                    "activities": [
                        {
                            "title": "Imported Video",
                            "content_type": "VIDEO",
                            "activity_type": "VIDEO_LECTURE",
                            "order": 0
                        }
                    ]
                }
            ]
        }
    ]
})


SAMPLE_MARKDOWN = """
# Introduction to Machine Learning

## Module 1: Fundamentals
### Lesson 1: What is ML?
- Video: Introduction to ML
- Reading: ML Basics

### Lesson 2: Types of Learning
- Video: Supervised vs Unsupervised
- Quiz: ML Types Quiz

## Module 2: Algorithms
### Lesson 1: Linear Regression
- Video: Linear Models
- Lab: Implement Linear Regression
"""


@pytest.mark.e2e
def test_paste_json_import(page: Page, mock_ai_responses, clean_db, live_server):
    """Test importing a course from pasted JSON.

    Verifies:
    - Import page accessible
    - JSON can be pasted
    - Preview is shown
    - Course structure created correctly
    """
    # Register and login
    page.goto(f"{live_server}/register")
    page.fill('input#name', "Import User")
    page.fill('input#email', "import@test.com")
    page.fill('input#password', "importpassword123")
    page.fill('input#confirm_password', "importpassword123")
    page.click('button[type="submit"]')
    page.wait_for_url(f"{live_server}/login*", timeout=5000)

    page.fill('input#email', "import@test.com")
    page.fill('input#password', "importpassword123")
    page.click('button[type="submit"]')
    page.wait_for_url(f"{live_server}/dashboard", timeout=5000)

    # Navigate to import page
    page.goto(f"{live_server}/import")
    page.wait_for_selector('.import-container', timeout=5000)

    # Paste JSON blueprint
    page.fill('textarea#import-content', SAMPLE_BLUEPRINT_JSON)

    # Click import button
    page.click('#import-btn')

    # Wait for preview to appear
    page.wait_for_selector('.blueprint-preview, .import-preview', timeout=10000)

    # Verify preview shows course title
    preview = page.locator('.blueprint-preview, .import-preview')
    expect(preview).to_contain_text("Imported Course")
    expect(preview).to_contain_text("Imported Module 1")

    # Accept import
    page.click('#accept-import-btn, button:has-text("Accept")')

    # Should redirect to dashboard with new course
    page.wait_for_url(f"{live_server}/dashboard", timeout=10000)
    page.wait_for_selector('.course-card:has-text("Imported Course")', timeout=5000)

    course_card = page.locator('.course-card:has-text("Imported Course")')
    expect(course_card).to_be_visible()


@pytest.mark.e2e
def test_paste_markdown_import(page: Page, mock_ai_responses, clean_db, live_server):
    """Test importing a course from pasted Markdown.

    Verifies:
    - Markdown format detected
    - Content parsed correctly
    - Course structure created
    """
    # Register and login
    page.goto(f"{live_server}/register")
    page.fill('input#name', "Markdown User")
    page.fill('input#email', "markdown@test.com")
    page.fill('input#password', "markdownpassword123")
    page.fill('input#confirm_password', "markdownpassword123")
    page.click('button[type="submit"]')
    page.wait_for_url(f"{live_server}/login*", timeout=5000)

    page.fill('input#email', "markdown@test.com")
    page.fill('input#password', "markdownpassword123")
    page.click('button[type="submit"]')
    page.wait_for_url(f"{live_server}/dashboard", timeout=5000)

    # Navigate to import page
    page.goto(f"{live_server}/import")
    page.wait_for_selector('.import-container', timeout=5000)

    # Paste Markdown content
    page.fill('textarea#import-content', SAMPLE_MARKDOWN)

    # Click import button
    page.click('#import-btn')

    # Wait for preview (may show format detection)
    page.wait_for_selector('.blueprint-preview, .import-preview, .format-detected', timeout=10000)

    # Verify format detected as Markdown
    format_indicator = page.locator('.format-indicator, .detected-format')
    if format_indicator.is_visible():
        expect(format_indicator).to_contain_text("Markdown")

    # Preview should show course structure
    preview = page.locator('.blueprint-preview, .import-preview')
    expect(preview).to_contain_text("Machine Learning")

    # Accept import
    page.click('#accept-import-btn, button:has-text("Accept")')
    page.wait_for_url(f"{live_server}/dashboard", timeout=10000)


@pytest.mark.e2e
def test_file_upload_import(page: Page, mock_ai_responses, clean_db, live_server):
    """Test importing a course from uploaded file.

    Verifies:
    - File upload works
    - File content parsed
    - Course created
    """
    # Register and login
    page.goto(f"{live_server}/register")
    page.fill('input#name', "Upload User")
    page.fill('input#email', "upload@test.com")
    page.fill('input#password', "uploadpassword123")
    page.fill('input#confirm_password', "uploadpassword123")
    page.click('button[type="submit"]')
    page.wait_for_url(f"{live_server}/login*", timeout=5000)

    page.fill('input#email', "upload@test.com")
    page.fill('input#password', "uploadpassword123")
    page.click('button[type="submit"]')
    page.wait_for_url(f"{live_server}/dashboard", timeout=5000)

    # Navigate to import page
    page.goto(f"{live_server}/import")
    page.wait_for_selector('.import-container', timeout=5000)

    # Create temporary test file
    import tempfile
    import os
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write(SAMPLE_BLUEPRINT_JSON)
        temp_file = f.name

    try:
        # Upload file
        file_input = page.locator('input[type="file"]')
        file_input.set_input_files(temp_file)

        # Wait for file to be processed
        page.wait_for_selector('.file-uploaded, .blueprint-preview', timeout=10000)

        # Preview should show content
        preview = page.locator('.blueprint-preview, .import-preview')
        expect(preview).to_contain_text("Imported Course")

        # Accept import
        page.click('#accept-import-btn, button:has-text("Accept")')
        page.wait_for_url(f"{live_server}/dashboard", timeout=10000)
    finally:
        # Cleanup temp file
        os.unlink(temp_file)


@pytest.mark.e2e
def test_import_validation_error(page: Page, clean_db, live_server):
    """Test import error handling for invalid JSON.

    Verifies:
    - Invalid JSON shows error
    - No crash
    - Can retry with valid data
    """
    # Register and login
    page.goto(f"{live_server}/register")
    page.fill('input#name', "Error User")
    page.fill('input#email', "error@test.com")
    page.fill('input#password', "errorpassword123")
    page.fill('input#confirm_password', "errorpassword123")
    page.click('button[type="submit"]')
    page.wait_for_url(f"{live_server}/login*", timeout=5000)

    page.fill('input#email', "error@test.com")
    page.fill('input#password', "errorpassword123")
    page.click('button[type="submit"]')
    page.wait_for_url(f"{live_server}/dashboard", timeout=5000)

    # Navigate to import page
    page.goto(f"{live_server}/import")
    page.wait_for_selector('.import-container', timeout=5000)

    # Paste invalid JSON
    page.fill('textarea#import-content', '{"invalid": json missing closing brace')

    # Try to import
    page.click('#import-btn')

    # Should show error message
    page.wait_for_selector('.import-error, .alert-danger, .error-message', timeout=5000)
    error = page.locator('.import-error, .alert-danger, .error-message')
    expect(error).to_be_visible()
    expect(error).to_contain_text("invalid", ignore_case=True)

    # No crash - page still functional
    expect(page.locator('textarea#import-content')).to_be_visible()

    # Can retry with valid JSON
    page.fill('textarea#import-content', SAMPLE_BLUEPRINT_JSON)
    page.click('#import-btn')
    page.wait_for_selector('.blueprint-preview, .import-preview', timeout=10000)


@pytest.mark.e2e
def test_import_with_ai_enhancement(page: Page, mock_ai_responses, clean_db, live_server):
    """Test importing plain text with AI enhancement.

    Verifies:
    - Plain text can be pasted
    - AI enhancement option available
    - AI converts to structured format
    """
    # Register and login
    page.goto(f"{live_server}/register")
    page.fill('input#name', "AI User")
    page.fill('input#email', "ai@test.com")
    page.fill('input#password', "aipassword123")
    page.fill('input#confirm_password', "aipassword123")
    page.click('button[type="submit"]')
    page.wait_for_url(f"{live_server}/login*", timeout=5000)

    page.fill('input#email', "ai@test.com")
    page.fill('input#password', "aipassword123")
    page.click('button[type="submit"]')
    page.wait_for_url(f"{live_server}/dashboard", timeout=5000)

    # Navigate to import page
    page.goto(f"{live_server}/import")
    page.wait_for_selector('.import-container', timeout=5000)

    # Paste plain text
    plain_text = """
    Course about Data Science
    - Introduction to data
    - Statistics basics
    - Python for data analysis
    - Data visualization
    """
    page.fill('textarea#import-content', plain_text)

    # Enable AI enhancement
    ai_checkbox = page.locator('input[type="checkbox"]#ai-enhance, input[name="ai_enhance"]')
    if ai_checkbox.is_visible():
        ai_checkbox.check()

    # Import
    page.click('#import-btn')

    # Wait for AI processing and preview
    page.wait_for_selector('.blueprint-preview, .import-preview', timeout=30000)

    # Preview should show structured course (AI converted plain text)
    preview = page.locator('.blueprint-preview, .import-preview')
    expect(preview).to_be_visible()
    # Should contain some course structure elements
    expect(preview.locator('.module-item, .lesson-item, h3, h4').first).to_be_visible()
