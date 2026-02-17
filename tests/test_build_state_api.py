"""Tests for build state tracking API endpoints."""

import pytest
import json
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


def test_progress_empty_course(client):
    """Test progress endpoint with course containing no modules."""
    # Create empty course
    response = client.post('/api/courses',
                          data=json.dumps({"title": "Empty Course"}),
                          content_type='application/json')
    assert response.status_code == 201
    course_id = response.json['id']

    # Get progress
    response = client.get(f'/api/courses/{course_id}/progress')
    assert response.status_code == 200

    data = response.json
    assert data['total_activities'] == 0
    assert data['completion_percentage'] == 0.0
    assert len(data['activities']) == 0


def test_progress_counts_by_state(client):
    """Test progress endpoint counts activities by build state."""
    # Create course with activities in different states
    response = client.post('/api/courses',
                          data=json.dumps({"title": "Test Course"}),
                          content_type='application/json')
    assert response.status_code == 201
    course_id = response.json['id']

    # Create module with lesson
    response = client.post(f'/api/courses/{course_id}/modules',
                          data=json.dumps({"title": "Module 1", "order": 1}),
                          content_type='application/json')
    assert response.status_code == 201
    module_id = response.json['id']

    response = client.post(f'/api/courses/{course_id}/modules/{module_id}/lessons',
                          data=json.dumps({"title": "Lesson 1", "order": 1}),
                          content_type='application/json')
    assert response.status_code == 201
    lesson_id = response.json['id']

    # Create activities
    act_ids = []
    for i in range(5):
        response = client.post(
            f'/api/courses/{course_id}/lessons/{lesson_id}/activities',
            data=json.dumps({
                "title": f"Activity {i+1}",
                "content_type": "video",
                "order": i+1
            }),
            content_type='application/json'
        )
        assert response.status_code == 201
        act_ids.append(response.json['id'])

    # Set different build states
    course = _load_course(course_id)

    states = [BuildState.DRAFT, BuildState.GENERATED, BuildState.GENERATED,
              BuildState.REVIEWED, BuildState.APPROVED]
    for module in course.modules:
        for lesson in module.lessons:
            for i, activity in enumerate(lesson.activities):
                activity.build_state = states[i]

    _save_course(course_id, course)

    # Get progress
    response = client.get(f'/api/courses/{course_id}/progress')
    assert response.status_code == 200

    data = response.json
    assert data['total_activities'] == 5
    assert data['by_state']['draft'] == 1
    assert data['by_state']['generated'] == 2
    assert data['by_state']['reviewed'] == 1
    assert data['by_state']['approved'] == 1
    assert data['by_state']['generating'] == 0
    assert data['by_state']['published'] == 0


def test_progress_completion_percentage(client):
    """Test progress calculates completion percentage correctly."""
    # Create course
    response = client.post('/api/courses',
                          data=json.dumps({"title": "Test Course"}),
                          content_type='application/json')
    assert response.status_code == 201
    course_id = response.json['id']

    # Create structure
    response = client.post(f'/api/courses/{course_id}/modules',
                          data=json.dumps({"title": "Module 1", "order": 1}),
                          content_type='application/json')
    module_id = response.json['id']

    response = client.post(f'/api/courses/{course_id}/modules/{module_id}/lessons',
                          data=json.dumps({"title": "Lesson 1", "order": 1}),
                          content_type='application/json')
    lesson_id = response.json['id']

    # Create 10 activities
    for i in range(10):
        client.post(
            f'/api/courses/{course_id}/lessons/{lesson_id}/activities',
            data=json.dumps({
                "title": f"Activity {i+1}",
                "content_type": "video",
                "order": i+1
            }),
            content_type='application/json'
        )

    # Set 3 to approved
    course = _load_course(course_id)

    count = 0
    for module in course.modules:
        for lesson in module.lessons:
            for activity in lesson.activities:
                if count < 3:
                    activity.build_state = BuildState.APPROVED
                count += 1

    _save_course(course_id, course)

    # Get progress
    response = client.get(f'/api/courses/{course_id}/progress')
    assert response.status_code == 200

    data = response.json
    assert data['total_activities'] == 10
    assert data['completion_percentage'] == 30.0


def test_progress_includes_activity_list(client):
    """Test progress includes per-activity details."""
    # Create course
    response = client.post('/api/courses',
                          data=json.dumps({"title": "Test Course"}),
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

    # Create activity
    response = client.post(
        f'/api/courses/{course_id}/lessons/{lesson_id}/activities',
        data=json.dumps({
            "title": "Test Activity",
            "content_type": "reading",
            "order": 1
        }),
        content_type='application/json'
    )
    activity_id = response.json['id']

    # Set build state
    course = _load_course(course_id)
    for module in course.modules:
        for lesson in module.lessons:
            for activity in lesson.activities:
                activity.build_state = BuildState.GENERATED
                activity.word_count = 450
    _save_course(course_id, course)

    # Get progress
    response = client.get(f'/api/courses/{course_id}/progress')
    assert response.status_code == 200

    data = response.json
    assert len(data['activities']) == 1

    act_detail = data['activities'][0]
    assert act_detail['id'] == activity_id
    assert act_detail['title'] == "Test Activity"
    assert act_detail['content_type'] == "reading"
    assert act_detail['build_state'] == "generated"
    assert act_detail['word_count'] == 450


def test_progress_404_course_not_found(client):
    """Test progress endpoint returns 404 for non-existent course."""
    response = client.get('/api/courses/bad_course_id/progress')
    assert response.status_code == 404
    assert 'error' in response.json


def test_update_state_generated_to_reviewed(client):
    """Test valid state transition from GENERATED to REVIEWED."""
    # Create course with activity
    response = client.post('/api/courses',
                          data=json.dumps({"title": "Test Course"}),
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

    response = client.post(
        f'/api/courses/{course_id}/lessons/{lesson_id}/activities',
        data=json.dumps({"title": "Test Activity", "content_type": "video", "order": 1}),
        content_type='application/json'
    )
    activity_id = response.json['id']

    # Set to GENERATED state
    course = _load_course(course_id)
    for module in course.modules:
        for lesson in module.lessons:
            for activity in lesson.activities:
                activity.build_state = BuildState.GENERATED
    _save_course(course_id, course)

    # Update state to REVIEWED
    response = client.put(
        f'/api/courses/{course_id}/activities/{activity_id}/state',
        data=json.dumps({"build_state": "reviewed"}),
        content_type='application/json'
    )
    assert response.status_code == 200
    assert response.json['build_state'] == 'reviewed'


def test_update_state_reviewed_to_approved(client):
    """Test valid state transition from REVIEWED to APPROVED."""
    # Create course with activity
    response = client.post('/api/courses',
                          data=json.dumps({"title": "Test Course"}),
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

    response = client.post(
        f'/api/courses/{course_id}/lessons/{lesson_id}/activities',
        data=json.dumps({"title": "Test Activity", "content_type": "video", "order": 1}),
        content_type='application/json'
    )
    activity_id = response.json['id']

    # Set to REVIEWED state
    course = _load_course(course_id)
    for module in course.modules:
        for lesson in module.lessons:
            for activity in lesson.activities:
                activity.build_state = BuildState.REVIEWED
    _save_course(course_id, course)

    # Update state to APPROVED
    response = client.put(
        f'/api/courses/{course_id}/activities/{activity_id}/state',
        data=json.dumps({"build_state": "approved"}),
        content_type='application/json'
    )
    assert response.status_code == 200
    assert response.json['build_state'] == 'approved'


def test_update_state_invalid_transition(client):
    """Test invalid state transition returns 400 with error."""
    # Create course with activity
    response = client.post('/api/courses',
                          data=json.dumps({"title": "Test Course"}),
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

    response = client.post(
        f'/api/courses/{course_id}/lessons/{lesson_id}/activities',
        data=json.dumps({"title": "Test Activity", "content_type": "video", "order": 1}),
        content_type='application/json'
    )
    activity_id = response.json['id']

    # Activity starts in DRAFT state
    # Try to transition directly to APPROVED (not allowed)
    response = client.put(
        f'/api/courses/{course_id}/activities/{activity_id}/state',
        data=json.dumps({"build_state": "approved"}),
        content_type='application/json'
    )
    assert response.status_code == 400
    assert 'error' in response.json
    assert 'Invalid state transition' in response.json['error']


def test_update_state_revert_generated_to_draft(client):
    """Test revert path from GENERATED to DRAFT."""
    # Create course with activity
    response = client.post('/api/courses',
                          data=json.dumps({"title": "Test Course"}),
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

    response = client.post(
        f'/api/courses/{course_id}/lessons/{lesson_id}/activities',
        data=json.dumps({"title": "Test Activity", "content_type": "video", "order": 1}),
        content_type='application/json'
    )
    activity_id = response.json['id']

    # Set to GENERATED state
    course = _load_course(course_id)
    for module in course.modules:
        for lesson in module.lessons:
            for activity in lesson.activities:
                activity.build_state = BuildState.GENERATED
    _save_course(course_id, course)

    # Revert to DRAFT
    response = client.put(
        f'/api/courses/{course_id}/activities/{activity_id}/state',
        data=json.dumps({"build_state": "draft"}),
        content_type='application/json'
    )
    assert response.status_code == 200
    assert response.json['build_state'] == 'draft'


def test_approve_endpoint_from_reviewed(client):
    """Test approve endpoint successfully approves REVIEWED activity."""
    # Create course with activity
    response = client.post('/api/courses',
                          data=json.dumps({"title": "Test Course"}),
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

    response = client.post(
        f'/api/courses/{course_id}/lessons/{lesson_id}/activities',
        data=json.dumps({"title": "Test Activity", "content_type": "video", "order": 1}),
        content_type='application/json'
    )
    activity_id = response.json['id']

    # Set to REVIEWED state
    course = _load_course(course_id)
    for module in course.modules:
        for lesson in module.lessons:
            for activity in lesson.activities:
                activity.build_state = BuildState.REVIEWED
    _save_course(course_id, course)

    # Approve
    response = client.post(f'/api/courses/{course_id}/activities/{activity_id}/approve')
    assert response.status_code == 200
    assert response.json['build_state'] == 'approved'


def test_approve_endpoint_from_wrong_state(client):
    """Test approve endpoint returns 400 when activity not in REVIEWED state."""
    # Create course with activity
    response = client.post('/api/courses',
                          data=json.dumps({"title": "Test Course"}),
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

    response = client.post(
        f'/api/courses/{course_id}/lessons/{lesson_id}/activities',
        data=json.dumps({"title": "Test Activity", "content_type": "video", "order": 1}),
        content_type='application/json'
    )
    activity_id = response.json['id']

    # Activity is in DRAFT state, try to approve
    response = client.post(f'/api/courses/{course_id}/activities/{activity_id}/approve')
    assert response.status_code == 400
    assert 'error' in response.json
    assert 'Cannot approve activity' in response.json['error']


def test_update_state_404_activity(client):
    """Test update state returns 404 for non-existent activity."""
    # Create course
    response = client.post('/api/courses',
                          data=json.dumps({"title": "Test Course"}),
                          content_type='application/json')
    course_id = response.json['id']

    # Try to update non-existent activity
    response = client.put(
        f'/api/courses/{course_id}/activities/bad_activity_id/state',
        data=json.dumps({"build_state": "reviewed"}),
        content_type='application/json'
    )
    assert response.status_code == 404
    assert 'error' in response.json
