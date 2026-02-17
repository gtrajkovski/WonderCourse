"""Tests for Export API endpoints.

Tests for previewing and downloading course content in various export formats:
- Instructor Package (ZIP)
- LMS Manifest (JSON)
- DOCX Textbook
- SCORM 1.2 Package (ZIP)
"""

import json
import zipfile
from io import BytesIO

import pytest

from src.core.models import Course, Module, Lesson, Activity, ContentType, BuildState
from src.collab.models import Collaborator
from app import app as flask_app


def _load_course(course_id):
    """Helper to load course with owner_id lookup."""
    import app as app_module
    with flask_app.app_context():
        owner_id = Collaborator.get_course_owner_id(course_id)
    return app_module.project_store.load(owner_id, course_id)


def _save_course(course_id, course):
    """Helper to save course with owner_id lookup."""
    import app as app_module
    with flask_app.app_context():
        owner_id = Collaborator.get_course_owner_id(course_id)
    app_module.project_store.save(owner_id, course)


def _create_course_with_content(client):
    """Helper to create a course with approved content for export tests.

    Returns:
        tuple: (course_id, module_id, lesson_id, activity_id)
    """
    # Create course
    response = client.post('/api/courses',
                          data=json.dumps({"title": "Test Export Course"}),
                          content_type='application/json')
    course_id = response.json['id']

    # Create module
    response = client.post(f'/api/courses/{course_id}/modules',
                          data=json.dumps({"title": "Module 1", "order": 1}),
                          content_type='application/json')
    module_id = response.json['id']

    # Create lesson
    response = client.post(f'/api/courses/{course_id}/modules/{module_id}/lessons',
                          data=json.dumps({"title": "Lesson 1", "order": 1}),
                          content_type='application/json')
    lesson_id = response.json['id']

    # Create video activity with content
    response = client.post(
        f'/api/courses/{course_id}/lessons/{lesson_id}/activities',
        data=json.dumps({
            "title": "Test Video",
            "content_type": "video",
            "order": 1
        }),
        content_type='application/json'
    )
    activity_id = response.json['id']

    # Set activity to approved state with content
    course = _load_course(course_id)
    for module in course.modules:
        for lesson in module.lessons:
            for activity in lesson.activities:
                activity.content = "Test video script content for export."
                activity.build_state = BuildState.APPROVED
    _save_course(course_id, course)

    return course_id, module_id, lesson_id, activity_id


# ===========================
# Preview Endpoint Tests
# ===========================

def test_preview_instructor_format(client):
    """Test preview endpoint returns file list for instructor format."""
    course_id, _, _, _ = _create_course_with_content(client)

    response = client.get(f'/api/courses/{course_id}/export/preview?format=instructor')
    assert response.status_code == 200

    data = response.json
    assert data['format'] == 'instructor'
    assert data['course_id'] == course_id
    assert data['course_title'] == 'Test Export Course'
    assert 'files' in data
    assert 'syllabus.txt' in data['files']
    assert any('lesson_plans' in f for f in data['files'])


def test_preview_lms_format(client):
    """Test preview endpoint returns file list for LMS format."""
    course_id, _, _, _ = _create_course_with_content(client)

    response = client.get(f'/api/courses/{course_id}/export/preview?format=lms')
    assert response.status_code == 200

    data = response.json
    assert data['format'] == 'lms'
    assert 'course_manifest.json' in data['files']


def test_preview_docx_format(client):
    """Test preview endpoint returns file list for DOCX format."""
    course_id, _, _, _ = _create_course_with_content(client)

    response = client.get(f'/api/courses/{course_id}/export/preview?format=docx')
    assert response.status_code == 200

    data = response.json
    assert data['format'] == 'docx'
    assert any('.docx' in f for f in data['files'])


def test_preview_scorm_format(client):
    """Test preview endpoint returns file list for SCORM format."""
    course_id, _, _, _ = _create_course_with_content(client)

    response = client.get(f'/api/courses/{course_id}/export/preview?format=scorm')
    assert response.status_code == 200

    data = response.json
    assert data['format'] == 'scorm'
    assert 'imsmanifest.xml' in data['files']
    assert 'shared/style.css' in data['files']


def test_preview_invalid_format(client):
    """Test preview endpoint returns 400 for invalid format."""
    course_id, _, _, _ = _create_course_with_content(client)

    response = client.get(f'/api/courses/{course_id}/export/preview?format=invalid')
    assert response.status_code == 400
    assert 'error' in response.json
    assert 'valid_formats' in response.json


def test_preview_missing_format(client):
    """Test preview endpoint returns 400 when format is missing."""
    course_id, _, _, _ = _create_course_with_content(client)

    response = client.get(f'/api/courses/{course_id}/export/preview')
    assert response.status_code == 400
    assert 'error' in response.json
    assert 'format' in response.json['error'].lower()


def test_preview_missing_course(client):
    """Test preview endpoint returns 404 for non-existent course."""
    response = client.get('/api/courses/nonexistent/export/preview?format=instructor')
    assert response.status_code == 404
    assert 'error' in response.json


def test_preview_shows_missing_content(client):
    """Test preview shows missing content when activities have no content."""
    # Create course
    response = client.post('/api/courses',
                          data=json.dumps({"title": "Incomplete Course"}),
                          content_type='application/json')
    course_id = response.json['id']

    # Create module and lesson
    response = client.post(f'/api/courses/{course_id}/modules',
                          data=json.dumps({"title": "Module 1", "order": 1}),
                          content_type='application/json')
    module_id = response.json['id']

    response = client.post(f'/api/courses/{course_id}/modules/{module_id}/lessons',
                          data=json.dumps({"title": "Lesson 1", "order": 1}),
                          content_type='application/json')
    lesson_id = response.json['id']

    # Create activity without content
    client.post(
        f'/api/courses/{course_id}/lessons/{lesson_id}/activities',
        data=json.dumps({
            "title": "Empty Activity",
            "content_type": "video",
            "order": 1
        }),
        content_type='application/json'
    )

    # Preview should show missing content
    response = client.get(f'/api/courses/{course_id}/export/preview?format=instructor')
    assert response.status_code == 200

    data = response.json
    assert data['ready'] is False
    assert len(data['missing_content']) > 0
    assert data['missing_content'][0]['title'] == 'Empty Activity'


def test_preview_shows_ready_when_complete(client):
    """Test preview shows ready=true when course is complete."""
    course_id, _, _, _ = _create_course_with_content(client)

    response = client.get(f'/api/courses/{course_id}/export/preview?format=instructor')
    assert response.status_code == 200

    data = response.json
    assert data['ready'] is True
    assert len(data['missing_content']) == 0


# ===========================
# Download Endpoint Tests
# ===========================

def test_download_instructor_package(client):
    """Test downloading instructor package as ZIP."""
    course_id, _, _, _ = _create_course_with_content(client)

    response = client.get(f'/api/courses/{course_id}/export/instructor')
    assert response.status_code == 200
    assert response.content_type == 'application/zip'

    # Verify it's a valid ZIP
    buffer = BytesIO(response.data)
    with zipfile.ZipFile(buffer) as zf:
        names = zf.namelist()
        assert 'syllabus.txt' in names


def test_download_lms_manifest(client):
    """Test downloading LMS manifest as JSON."""
    course_id, _, _, _ = _create_course_with_content(client)

    response = client.get(f'/api/courses/{course_id}/export/lms')
    assert response.status_code == 200
    assert response.content_type == 'application/json'

    # Verify it's valid JSON with expected structure
    data = json.loads(response.data)
    assert 'version' in data
    assert 'course' in data
    assert data['course']['title'] == 'Test Export Course'


def test_download_docx_textbook(client):
    """Test downloading DOCX textbook."""
    course_id, _, _, _ = _create_course_with_content(client)

    response = client.get(f'/api/courses/{course_id}/export/docx')
    assert response.status_code == 200
    assert 'openxmlformats-officedocument.wordprocessingml.document' in response.content_type

    # DOCX files are actually ZIP files
    buffer = BytesIO(response.data)
    with zipfile.ZipFile(buffer) as zf:
        names = zf.namelist()
        assert 'word/document.xml' in names


def test_download_scorm_package(client):
    """Test downloading SCORM package as ZIP."""
    course_id, _, _, _ = _create_course_with_content(client)

    response = client.get(f'/api/courses/{course_id}/export/scorm')
    assert response.status_code == 200
    assert response.content_type == 'application/zip'

    # Verify it's a valid SCORM package
    buffer = BytesIO(response.data)
    with zipfile.ZipFile(buffer) as zf:
        names = zf.namelist()
        assert 'imsmanifest.xml' in names
        assert 'shared/style.css' in names


def test_download_missing_course(client):
    """Test download returns 404 for non-existent course."""
    response = client.get('/api/courses/nonexistent/export/instructor')
    assert response.status_code == 404
    assert 'error' in response.json


def test_download_not_ready_without_force(client):
    """Test download returns 400 when validation fails and force not set."""
    # Create course with activity in draft state (not approved)
    response = client.post('/api/courses',
                          data=json.dumps({"title": "Incomplete Course"}),
                          content_type='application/json')
    course_id = response.json['id']

    response = client.post(f'/api/courses/{course_id}/modules',
                          data=json.dumps({"title": "Module 1", "order": 1}),
                          content_type='application/json')
    module_id = response.json['id']

    response = client.post(f'/api/courses/{course_id}/modules/{module_id}/lessons',
                          data=json.dumps({"title": "Lesson 1", "order": 1}),
                          content_type='application/json')
    lesson_id = response.json['id']

    # Create activity without content (stays in draft)
    client.post(
        f'/api/courses/{course_id}/lessons/{lesson_id}/activities',
        data=json.dumps({
            "title": "Draft Activity",
            "content_type": "video",
            "order": 1
        }),
        content_type='application/json'
    )

    # Download should fail
    response = client.get(f'/api/courses/{course_id}/export/instructor')
    assert response.status_code == 400
    assert 'error' in response.json
    assert 'not ready' in response.json['error'].lower()


def test_download_with_force_flag(client):
    """Test download with force=true bypasses validation."""
    # Create course with activity in draft state
    response = client.post('/api/courses',
                          data=json.dumps({"title": "Force Export Course"}),
                          content_type='application/json')
    course_id = response.json['id']

    response = client.post(f'/api/courses/{course_id}/modules',
                          data=json.dumps({"title": "Module 1", "order": 1}),
                          content_type='application/json')
    module_id = response.json['id']

    response = client.post(f'/api/courses/{course_id}/modules/{module_id}/lessons',
                          data=json.dumps({"title": "Lesson 1", "order": 1}),
                          content_type='application/json')
    lesson_id = response.json['id']

    client.post(
        f'/api/courses/{course_id}/lessons/{lesson_id}/activities',
        data=json.dumps({
            "title": "Draft Activity",
            "content_type": "video",
            "order": 1
        }),
        content_type='application/json'
    )

    # Download with force=true should succeed
    response = client.get(f'/api/courses/{course_id}/export/instructor?force=true')
    assert response.status_code == 200
    assert response.content_type == 'application/zip'


# ===========================
# Content-Type Verification Tests
# ===========================

def test_instructor_content_type(client):
    """Test instructor package returns application/zip content type."""
    course_id, _, _, _ = _create_course_with_content(client)

    response = client.get(f'/api/courses/{course_id}/export/instructor')
    assert response.content_type == 'application/zip'


def test_lms_content_type(client):
    """Test LMS manifest returns application/json content type."""
    course_id, _, _, _ = _create_course_with_content(client)

    response = client.get(f'/api/courses/{course_id}/export/lms')
    assert response.content_type == 'application/json'


def test_docx_content_type(client):
    """Test DOCX textbook returns correct Word content type."""
    course_id, _, _, _ = _create_course_with_content(client)

    response = client.get(f'/api/courses/{course_id}/export/docx')
    expected_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    assert expected_type in response.content_type


def test_scorm_content_type(client):
    """Test SCORM package returns application/zip content type."""
    course_id, _, _, _ = _create_course_with_content(client)

    response = client.get(f'/api/courses/{course_id}/export/scorm')
    assert response.content_type == 'application/zip'


# ===========================
# Additional Edge Cases
# ===========================

def test_preview_includes_metrics(client):
    """Test preview includes validation metrics."""
    course_id, _, _, _ = _create_course_with_content(client)

    response = client.get(f'/api/courses/{course_id}/export/preview?format=instructor')
    assert response.status_code == 200

    data = response.json
    assert 'metrics' in data
    assert 'total_activities' in data['metrics']
    assert 'content_completion_rate' in data['metrics']


def test_download_with_quiz_activity(client):
    """Test export includes quiz content when course has quiz activities."""
    course_id, module_id, lesson_id, _ = _create_course_with_content(client)

    # Add a quiz activity
    response = client.post(
        f'/api/courses/{course_id}/lessons/{lesson_id}/activities',
        data=json.dumps({
            "title": "Chapter Quiz",
            "content_type": "quiz",
            "order": 2
        }),
        content_type='application/json'
    )
    quiz_id = response.json['id']

    # Set quiz content and approve
    course = _load_course(course_id)
    for module in course.modules:
        for lesson in module.lessons:
            for activity in lesson.activities:
                if activity.id == quiz_id:
                    activity.content = json.dumps({
                        "title": "Chapter Quiz",
                        "questions": [{
                            "question_text": "What is 2+2?",
                            "options": [
                                {"label": "A", "text": "3"},
                                {"label": "B", "text": "4"}
                            ],
                            "correct_answer": "B",
                            "feedback_correct": "Correct!"
                        }]
                    })
                    activity.build_state = BuildState.APPROVED
    _save_course(course_id, course)

    # Export instructor package
    response = client.get(f'/api/courses/{course_id}/export/instructor')
    assert response.status_code == 200

    # Verify quiz files are included
    buffer = BytesIO(response.data)
    with zipfile.ZipFile(buffer) as zf:
        names = zf.namelist()
        assert any('quizzes/' in n for n in names)
        assert any('answer_keys/' in n for n in names)
