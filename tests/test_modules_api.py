"""Tests for module CRUD API endpoints."""

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
        'description': 'Test course for module API tests'
    })
    assert response.status_code == 201
    data = response.get_json()
    return data['id']


def test_create_module(client, course_id):
    """Test creating a module."""
    response = client.post(f'/api/courses/{course_id}/modules', json={
        'title': 'Module 1',
        'description': 'First module'
    })

    assert response.status_code == 201
    data = response.get_json()
    assert data['title'] == 'Module 1'
    assert data['description'] == 'First module'
    assert 'id' in data
    assert data['id'].startswith('mod_')
    assert data['order'] == 0


def test_create_module_course_not_found(client):
    """Test creating a module for non-existent course."""
    response = client.post('/api/courses/invalid_id/modules', json={
        'title': 'Module 1'
    })

    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data


def test_list_modules(client, course_id):
    """Test listing modules."""
    # Create two modules
    client.post(f'/api/courses/{course_id}/modules', json={
        'title': 'Module 1',
        'description': 'First module'
    })
    client.post(f'/api/courses/{course_id}/modules', json={
        'title': 'Module 2',
        'description': 'Second module'
    })

    # List modules
    response = client.get(f'/api/courses/{course_id}/modules')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2
    assert data[0]['title'] == 'Module 1'
    assert data[0]['order'] == 0
    assert data[1]['title'] == 'Module 2'
    assert data[1]['order'] == 1


def test_update_module(client, course_id):
    """Test updating a module."""
    # Create module
    create_response = client.post(f'/api/courses/{course_id}/modules', json={
        'title': 'Module 1',
        'description': 'First module'
    })
    module_id = create_response.get_json()['id']

    # Update module
    response = client.put(f'/api/courses/{course_id}/modules/{module_id}', json={
        'title': 'Updated Module 1',
        'description': 'Updated description'
    })

    assert response.status_code == 200
    data = response.get_json()
    assert data['title'] == 'Updated Module 1'
    assert data['description'] == 'Updated description'
    assert data['id'] == module_id


def test_update_module_not_found(client, course_id):
    """Test updating a non-existent module."""
    response = client.put(f'/api/courses/{course_id}/modules/invalid_id', json={
        'title': 'Updated Module'
    })

    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data


def test_delete_module(client, course_id):
    """Test deleting a module."""
    # Create module
    create_response = client.post(f'/api/courses/{course_id}/modules', json={
        'title': 'Module 1'
    })
    module_id = create_response.get_json()['id']

    # Delete module
    response = client.delete(f'/api/courses/{course_id}/modules/{module_id}')
    assert response.status_code == 200
    data = response.get_json()
    assert 'message' in data

    # Verify module is gone
    list_response = client.get(f'/api/courses/{course_id}/modules')
    modules = list_response.get_json()
    assert len(modules) == 0


def test_delete_module_cleans_outcome_mappings(client, course_id, tmp_path, monkeypatch):
    """Test that deleting a module cleans up learning outcome mappings."""
    # Get the project store from the app module
    import app as app_module
    store = app_module.project_store

    # User ID 1 is the authenticated test user from conftest.py
    user_id = 1

    # Create course with module containing activity
    course = store.load(user_id, course_id)

    # Add module with lesson and activity
    module = Module(title='Module 1', order=0)
    lesson = Lesson(title='Lesson 1', order=0)
    activity = Activity(title='Activity 1', order=0)
    lesson.activities.append(activity)
    module.lessons.append(lesson)
    course.modules.append(module)

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

    # Delete the module
    response = client.delete(f'/api/courses/{course_id}/modules/{module.id}')
    assert response.status_code == 200

    # Verify outcome's mapped_activity_ids is cleaned
    course = store.load(user_id, course_id)
    assert len(course.learning_outcomes) == 1
    assert activity.id not in course.learning_outcomes[0].mapped_activity_ids
    assert len(course.learning_outcomes[0].mapped_activity_ids) == 0


def test_reorder_modules(client, course_id):
    """Test reordering modules."""
    # Create three modules
    response1 = client.post(f'/api/courses/{course_id}/modules', json={'title': 'Module A'})
    response2 = client.post(f'/api/courses/{course_id}/modules', json={'title': 'Module B'})
    response3 = client.post(f'/api/courses/{course_id}/modules', json={'title': 'Module C'})

    # Verify initial order
    list_response = client.get(f'/api/courses/{course_id}/modules')
    modules = list_response.get_json()
    assert [m['title'] for m in modules] == ['Module A', 'Module B', 'Module C']
    assert [m['order'] for m in modules] == [0, 1, 2]

    # Move Module A (index 0) to position 2 (between B and C)
    # Result should be: B, C, A
    response = client.put(f'/api/courses/{course_id}/modules/reorder', json={
        'old_index': 0,
        'new_index': 2
    })

    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 3
    assert [m['title'] for m in data] == ['Module B', 'Module C', 'Module A']
    assert [m['order'] for m in data] == [0, 1, 2]


def test_reorder_modules_invalid_index(client, course_id):
    """Test reordering with invalid indices."""
    # Create two modules
    client.post(f'/api/courses/{course_id}/modules', json={'title': 'Module A'})
    client.post(f'/api/courses/{course_id}/modules', json={'title': 'Module B'})

    # Try to reorder with out-of-bounds index
    response = client.put(f'/api/courses/{course_id}/modules/reorder', json={
        'old_index': 0,
        'new_index': 5
    })

    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
