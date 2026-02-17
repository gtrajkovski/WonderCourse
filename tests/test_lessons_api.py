"""Tests for lesson CRUD API endpoints."""

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
        'description': 'Test course for lesson API tests'
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
        'description': 'Test module for lesson API tests'
    })
    assert response.status_code == 201
    data = response.get_json()
    return data['id']


def test_create_lesson(client, course_id, module_id):
    """Test creating a lesson."""
    response = client.post(f'/api/courses/{course_id}/modules/{module_id}/lessons', json={
        'title': 'Lesson 1',
        'description': 'First lesson'
    })

    assert response.status_code == 201
    data = response.get_json()
    assert data['title'] == 'Lesson 1'
    assert data['description'] == 'First lesson'
    assert 'id' in data
    assert data['id'].startswith('les_')
    assert data['order'] == 0


def test_create_lesson_module_not_found(client, course_id):
    """Test creating a lesson for non-existent module."""
    response = client.post(f'/api/courses/{course_id}/modules/invalid_id/lessons', json={
        'title': 'Lesson 1'
    })

    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data


def test_list_lessons(client, course_id, module_id):
    """Test listing lessons."""
    # Create two lessons
    client.post(f'/api/courses/{course_id}/modules/{module_id}/lessons', json={
        'title': 'Lesson 1',
        'description': 'First lesson'
    })
    client.post(f'/api/courses/{course_id}/modules/{module_id}/lessons', json={
        'title': 'Lesson 2',
        'description': 'Second lesson'
    })

    # List lessons
    response = client.get(f'/api/courses/{course_id}/modules/{module_id}/lessons')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2
    assert data[0]['title'] == 'Lesson 1'
    assert data[0]['order'] == 0
    assert data[1]['title'] == 'Lesson 2'
    assert data[1]['order'] == 1


def test_update_lesson(client, course_id, module_id):
    """Test updating a lesson."""
    # Create lesson
    create_response = client.post(f'/api/courses/{course_id}/modules/{module_id}/lessons', json={
        'title': 'Lesson 1',
        'description': 'First lesson'
    })
    lesson_id = create_response.get_json()['id']

    # Update lesson
    response = client.put(f'/api/courses/{course_id}/lessons/{lesson_id}', json={
        'title': 'Updated Lesson 1',
        'description': 'Updated description'
    })

    assert response.status_code == 200
    data = response.get_json()
    assert data['title'] == 'Updated Lesson 1'
    assert data['description'] == 'Updated description'
    assert data['id'] == lesson_id


def test_delete_lesson(client, course_id, module_id):
    """Test deleting a lesson."""
    # Create lesson
    create_response = client.post(f'/api/courses/{course_id}/modules/{module_id}/lessons', json={
        'title': 'Lesson 1'
    })
    lesson_id = create_response.get_json()['id']

    # Delete lesson
    response = client.delete(f'/api/courses/{course_id}/lessons/{lesson_id}')
    assert response.status_code == 200
    data = response.get_json()
    assert 'message' in data

    # Verify lesson is gone
    list_response = client.get(f'/api/courses/{course_id}/modules/{module_id}/lessons')
    lessons = list_response.get_json()
    assert len(lessons) == 0


def test_delete_lesson_cleans_outcome_mappings(client, course_id, module_id):
    """Test that deleting a lesson cleans up learning outcome mappings."""
    # Get the project store from the app module
    import app as app_module
    store = app_module.project_store

    # User ID 1 is the authenticated test user from conftest.py
    user_id = 1

    # Load course
    course = store.load(user_id, course_id)

    # Find the module we created
    module = next((m for m in course.modules if m.id == module_id), None)
    assert module is not None

    # Add lesson with activity
    lesson = Lesson(title='Lesson 1', order=0)
    activity = Activity(title='Activity 1', order=0)
    lesson.activities.append(activity)
    module.lessons.append(lesson)

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

    # Delete the lesson
    response = client.delete(f'/api/courses/{course_id}/lessons/{lesson.id}')
    assert response.status_code == 200

    # Verify outcome's mapped_activity_ids is cleaned
    course = store.load(user_id, course_id)
    assert len(course.learning_outcomes) == 1
    assert activity.id not in course.learning_outcomes[0].mapped_activity_ids
    assert len(course.learning_outcomes[0].mapped_activity_ids) == 0


def test_reorder_lessons(client, course_id, module_id):
    """Test reordering lessons."""
    # Create three lessons
    response1 = client.post(f'/api/courses/{course_id}/modules/{module_id}/lessons', json={'title': 'Lesson A'})
    response2 = client.post(f'/api/courses/{course_id}/modules/{module_id}/lessons', json={'title': 'Lesson B'})
    response3 = client.post(f'/api/courses/{course_id}/modules/{module_id}/lessons', json={'title': 'Lesson C'})

    # Verify initial order
    list_response = client.get(f'/api/courses/{course_id}/modules/{module_id}/lessons')
    lessons = list_response.get_json()
    assert [l['title'] for l in lessons] == ['Lesson A', 'Lesson B', 'Lesson C']
    assert [l['order'] for l in lessons] == [0, 1, 2]

    # Move Lesson A (index 0) to position 2
    # Result should be: B, C, A
    response = client.put(f'/api/courses/{course_id}/modules/{module_id}/lessons/reorder', json={
        'old_index': 0,
        'new_index': 2
    })

    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 3
    assert [l['title'] for l in data] == ['Lesson B', 'Lesson C', 'Lesson A']
    assert [l['order'] for l in data] == [0, 1, 2]
