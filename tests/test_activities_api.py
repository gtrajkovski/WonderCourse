"""Tests for activity CRUD API endpoints."""

import pytest
from pathlib import Path

from src.core.project_store import ProjectStore
from src.core.models import Course, Module, Lesson, Activity, LearningOutcome, BloomLevel


# Uses client fixture from conftest.py which includes authentication


@pytest.fixture
def course_id(client):
    """Create a test course and return its ID.

    Args:
        client: Flask test client fixture.

    Returns:
        Course ID string.
    """
    response = client.post('/api/courses', json={
        'title': 'Test Course',
        'description': 'Test course for activity API tests'
    })
    assert response.status_code == 201
    data = response.get_json()
    return data['id']


@pytest.fixture
def module_id(client, course_id):
    """Create a test module and return its ID.

    Args:
        client: Flask test client fixture.
        course_id: Course ID from fixture.

    Returns:
        Module ID string.
    """
    response = client.post(f'/api/courses/{course_id}/modules', json={
        'title': 'Test Module',
        'description': 'Test module for activity API tests'
    })
    assert response.status_code == 201
    data = response.get_json()
    return data['id']


@pytest.fixture
def lesson_id(client, course_id, module_id):
    """Create a test lesson and return its ID.

    Args:
        client: Flask test client fixture.
        course_id: Course ID from fixture.
        module_id: Module ID from fixture.

    Returns:
        Lesson ID string.
    """
    response = client.post(f'/api/courses/{course_id}/modules/{module_id}/lessons', json={
        'title': 'Test Lesson',
        'description': 'Test lesson for activity API tests'
    })
    assert response.status_code == 201
    data = response.get_json()
    return data['id']


def test_create_activity(client, course_id, lesson_id):
    """Test creating an activity."""
    response = client.post(f'/api/courses/{course_id}/lessons/{lesson_id}/activities', json={
        'title': 'Activity 1'
    })

    assert response.status_code == 201
    data = response.get_json()
    assert data['title'] == 'Activity 1'
    assert 'id' in data
    assert data['id'].startswith('act_')
    assert data['order'] == 0
    assert data['content_type'] == 'video'
    assert data['activity_type'] == 'video_lecture'


def test_create_activity_with_types(client, course_id, lesson_id):
    """Test creating an activity with specific content and activity types."""
    response = client.post(f'/api/courses/{course_id}/lessons/{lesson_id}/activities', json={
        'title': 'Reading Activity',
        'content_type': 'reading',
        'activity_type': 'reading_material'
    })

    assert response.status_code == 201
    data = response.get_json()
    assert data['title'] == 'Reading Activity'
    assert data['content_type'] == 'reading'
    assert data['activity_type'] == 'reading_material'


def test_list_activities(client, course_id, lesson_id):
    """Test listing activities."""
    # Create two activities
    client.post(f'/api/courses/{course_id}/lessons/{lesson_id}/activities', json={
        'title': 'Activity 1'
    })
    client.post(f'/api/courses/{course_id}/lessons/{lesson_id}/activities', json={
        'title': 'Activity 2'
    })

    # List activities
    response = client.get(f'/api/courses/{course_id}/lessons/{lesson_id}/activities')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2
    assert data[0]['title'] == 'Activity 1'
    assert data[0]['order'] == 0
    assert data[1]['title'] == 'Activity 2'
    assert data[1]['order'] == 1


def test_update_activity(client, course_id, lesson_id):
    """Test updating an activity."""
    # Create activity
    create_response = client.post(f'/api/courses/{course_id}/lessons/{lesson_id}/activities', json={
        'title': 'Activity 1'
    })
    activity_id = create_response.get_json()['id']

    # Update activity
    response = client.put(f'/api/courses/{course_id}/activities/{activity_id}', json={
        'title': 'Updated Activity 1',
        'content_type': 'quiz'
    })

    assert response.status_code == 200
    data = response.get_json()
    assert data['title'] == 'Updated Activity 1'
    assert data['content_type'] == 'quiz'
    assert data['id'] == activity_id


def test_update_activity_wwhaa_phase(client, course_id, lesson_id):
    """Test updating an activity's WWHAA phase."""
    # Create activity
    create_response = client.post(f'/api/courses/{course_id}/lessons/{lesson_id}/activities', json={
        'title': 'Activity 1'
    })
    activity_id = create_response.get_json()['id']

    # Update wwhaa_phase
    response = client.put(f'/api/courses/{course_id}/activities/{activity_id}', json={
        'wwhaa_phase': 'hook'
    })

    assert response.status_code == 200
    data = response.get_json()
    assert data['wwhaa_phase'] == 'hook'


def test_delete_activity(client, course_id, lesson_id):
    """Test deleting an activity."""
    # Create activity
    create_response = client.post(f'/api/courses/{course_id}/lessons/{lesson_id}/activities', json={
        'title': 'Activity 1'
    })
    activity_id = create_response.get_json()['id']

    # Delete activity
    response = client.delete(f'/api/courses/{course_id}/activities/{activity_id}')
    assert response.status_code == 200
    data = response.get_json()
    assert 'message' in data

    # Verify activity is gone
    list_response = client.get(f'/api/courses/{course_id}/lessons/{lesson_id}/activities')
    activities = list_response.get_json()
    assert len(activities) == 0


def test_delete_activity_cleans_outcome_mappings(client, course_id, lesson_id):
    """Test that deleting an activity cleans up learning outcome mappings."""
    # Get the project store from the app module
    import app as app_module
    store = app_module.project_store

    # User ID 1 is the authenticated test user from conftest.py
    user_id = 1

    # Load course
    course = store.load(user_id, course_id)

    # Find the lesson we created
    lesson = None
    for module in course.modules:
        for les in module.lessons:
            if les.id == lesson_id:
                lesson = les
                break
        if lesson:
            break
    assert lesson is not None

    # Add activity
    activity = Activity(title='Activity 1', order=0)
    lesson.activities.append(activity)

    # Add learning outcome with mapped activity
    outcome = LearningOutcome(
        audience='Students',
        behavior='Learn Python',
        condition='After this course',
        degree='Proficiently',
        bloom_level=BloomLevel.APPLY,
        mapped_activity_ids=[activity.id]
    )
    course.learning_outcomes.append(outcome)

    # Save course
    store.save(user_id, course)

    # Delete the activity
    response = client.delete(f'/api/courses/{course_id}/activities/{activity.id}')
    assert response.status_code == 200

    # Verify outcome's mapped_activity_ids is cleaned
    course = store.load(user_id, course_id)
    assert len(course.learning_outcomes) == 1
    assert activity.id not in course.learning_outcomes[0].mapped_activity_ids
    assert len(course.learning_outcomes[0].mapped_activity_ids) == 0


def test_reorder_activities(client, course_id, lesson_id):
    """Test reordering activities."""
    # Create three activities
    response1 = client.post(f'/api/courses/{course_id}/lessons/{lesson_id}/activities', json={'title': 'Activity A'})
    response2 = client.post(f'/api/courses/{course_id}/lessons/{lesson_id}/activities', json={'title': 'Activity B'})
    response3 = client.post(f'/api/courses/{course_id}/lessons/{lesson_id}/activities', json={'title': 'Activity C'})

    # Verify initial order
    list_response = client.get(f'/api/courses/{course_id}/lessons/{lesson_id}/activities')
    activities = list_response.get_json()
    assert [a['title'] for a in activities] == ['Activity A', 'Activity B', 'Activity C']
    assert [a['order'] for a in activities] == [0, 1, 2]

    # Move Activity A (index 0) to position 2
    # Result should be: B, C, A
    response = client.put(f'/api/courses/{course_id}/lessons/{lesson_id}/activities/reorder', json={
        'old_index': 0,
        'new_index': 2
    })

    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 3
    assert [a['title'] for a in data] == ['Activity B', 'Activity C', 'Activity A']
    assert [a['order'] for a in data] == [0, 1, 2]
