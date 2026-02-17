"""Tests for learning outcome CRUD API endpoints."""

import pytest
from pathlib import Path

from src.core.project_store import ProjectStore
from src.core.models import Course, BloomLevel


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
        'description': 'Test course for learning outcome API tests'
    })
    assert response.status_code == 201
    data = response.get_json()
    return data['id']


def test_create_outcome(client, course_id):
    """Test creating a learning outcome with full ABCD components."""
    response = client.post(f'/api/courses/{course_id}/outcomes', json={
        'audience': 'Learners',
        'behavior': 'implement a REST API',
        'condition': 'Given Flask documentation',
        'degree': 'with proper error handling',
        'bloom_level': 'apply',
        'tags': ['flask', 'api']
    })

    assert response.status_code == 201
    data = response.get_json()
    assert data['audience'] == 'Learners'
    assert data['behavior'] == 'implement a REST API'
    assert data['condition'] == 'Given Flask documentation'
    assert data['degree'] == 'with proper error handling'
    assert data['bloom_level'] == 'apply'
    assert data['tags'] == ['flask', 'api']
    assert 'id' in data
    assert data['id'].startswith('lo_')
    assert data['mapped_activity_ids'] == []


def test_create_outcome_minimal(client, course_id):
    """Test creating a learning outcome with minimal fields."""
    response = client.post(f'/api/courses/{course_id}/outcomes', json={
        'behavior': 'write Python code'
    })

    assert response.status_code == 201
    data = response.get_json()
    assert data['behavior'] == 'write Python code'
    assert data['audience'] == ''
    assert data['condition'] == ''
    assert data['degree'] == ''
    assert data['bloom_level'] == 'apply'  # default
    assert data['tags'] == []  # default


def test_create_outcome_invalid_bloom(client, course_id):
    """Test creating a learning outcome with invalid bloom_level."""
    response = client.post(f'/api/courses/{course_id}/outcomes', json={
        'behavior': 'learn something',
        'bloom_level': 'invalid'
    })

    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    assert 'Invalid bloom_level' in data['error']
    assert 'remember' in data['error']
    assert 'understand' in data['error']
    assert 'apply' in data['error']
    assert 'analyze' in data['error']
    assert 'evaluate' in data['error']
    assert 'create' in data['error']


def test_list_outcomes(client, course_id):
    """Test listing learning outcomes."""
    # Create two outcomes
    client.post(f'/api/courses/{course_id}/outcomes', json={
        'audience': 'Students',
        'behavior': 'build web applications',
        'bloom_level': 'create',
        'tags': ['web', 'development']
    })
    client.post(f'/api/courses/{course_id}/outcomes', json={
        'audience': 'Developers',
        'behavior': 'debug code',
        'bloom_level': 'analyze',
        'tags': ['debugging']
    })

    # List outcomes
    response = client.get(f'/api/courses/{course_id}/outcomes')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2
    assert data[0]['behavior'] == 'build web applications'
    assert data[0]['bloom_level'] == 'create'
    assert data[1]['behavior'] == 'debug code'
    assert data[1]['bloom_level'] == 'analyze'


def test_update_outcome(client, course_id):
    """Test updating a learning outcome's behavior and bloom_level."""
    # Create outcome
    create_response = client.post(f'/api/courses/{course_id}/outcomes', json={
        'behavior': 'write code',
        'bloom_level': 'apply'
    })
    outcome_id = create_response.get_json()['id']

    # Update outcome
    response = client.put(f'/api/courses/{course_id}/outcomes/{outcome_id}', json={
        'behavior': 'architect systems',
        'bloom_level': 'create'
    })

    assert response.status_code == 200
    data = response.get_json()
    assert data['behavior'] == 'architect systems'
    assert data['bloom_level'] == 'create'
    assert data['id'] == outcome_id


def test_update_outcome_tags(client, course_id):
    """Test updating a learning outcome's tags."""
    # Create outcome
    create_response = client.post(f'/api/courses/{course_id}/outcomes', json={
        'behavior': 'use Python',
        'tags': ['python']
    })
    outcome_id = create_response.get_json()['id']

    # Update tags
    response = client.put(f'/api/courses/{course_id}/outcomes/{outcome_id}', json={
        'tags': ['python', 'flask', 'api']
    })

    assert response.status_code == 200
    data = response.get_json()
    assert data['tags'] == ['python', 'flask', 'api']
    assert data['id'] == outcome_id


def test_delete_outcome(client, course_id):
    """Test deleting a learning outcome."""
    # Create outcome
    create_response = client.post(f'/api/courses/{course_id}/outcomes', json={
        'behavior': 'test software'
    })
    outcome_id = create_response.get_json()['id']

    # Delete outcome
    response = client.delete(f'/api/courses/{course_id}/outcomes/{outcome_id}')
    assert response.status_code == 200
    data = response.get_json()
    assert 'message' in data

    # Verify outcome is gone
    list_response = client.get(f'/api/courses/{course_id}/outcomes')
    outcomes = list_response.get_json()
    assert len(outcomes) == 0


def test_delete_outcome_not_found(client, course_id):
    """Test deleting a non-existent learning outcome."""
    response = client.delete(f'/api/courses/{course_id}/outcomes/invalid_id')

    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data


def test_outcome_bloom_levels(client, course_id):
    """Test creating outcomes with each BloomLevel value."""
    bloom_levels = ['remember', 'understand', 'apply', 'analyze', 'evaluate', 'create']

    for level in bloom_levels:
        response = client.post(f'/api/courses/{course_id}/outcomes', json={
            'behavior': f'test {level}',
            'bloom_level': level
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data['bloom_level'] == level

    # Verify all outcomes created
    list_response = client.get(f'/api/courses/{course_id}/outcomes')
    outcomes = list_response.get_json()
    assert len(outcomes) == 6


# ===========================
# Bloom's Level Validation Tests
# ===========================

def test_analyze_text_detects_create_level(client):
    """Test that text with 'design' is detected as CREATE level."""
    response = client.post('/api/outcomes/analyze-text', json={
        'text': 'design a RESTful API architecture'
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['detected_level'] == 'create'
    assert 'design' in data['evidence']


def test_analyze_text_detects_understand_level(client):
    """Test that text with 'explain' is detected as UNDERSTAND level."""
    response = client.post('/api/outcomes/analyze-text', json={
        'text': 'explain the concept of REST'
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data['detected_level'] == 'understand'
    assert 'explain' in data['evidence']


def test_analyze_text_requires_text(client):
    """Test that text field is required."""
    response = client.post('/api/outcomes/analyze-text', json={})
    assert response.status_code == 400


def test_validate_outcome_aligned(client, course_id):
    """Test validation of properly aligned outcome."""
    # Create outcome with CREATE level and design verb
    create_response = client.post(f'/api/courses/{course_id}/outcomes', json={
        'behavior': 'design a database schema',
        'bloom_level': 'create'
    })
    outcome_id = create_response.get_json()['id']

    # Validate
    response = client.get(f'/api/courses/{course_id}/outcomes/{outcome_id}/validate')
    assert response.status_code == 200
    data = response.get_json()
    assert data['aligned'] is True
    assert data['severity'] == 'success'


def test_validate_outcome_misaligned(client, course_id):
    """Test validation of misaligned outcome (understand text, create claim)."""
    # Create outcome claiming CREATE but with understand verb
    create_response = client.post(f'/api/courses/{course_id}/outcomes', json={
        'behavior': 'explain how REST APIs work',
        'bloom_level': 'create'
    })
    outcome_id = create_response.get_json()['id']

    # Validate
    response = client.get(f'/api/courses/{course_id}/outcomes/{outcome_id}/validate')
    assert response.status_code == 200
    data = response.get_json()
    assert data['aligned'] is False
    assert data['detected_level'] == 'understand'
    assert data['claimed_level'] == 'create'
    assert data['severity'] in ['warning', 'error']


def test_validate_all_outcomes(client, course_id):
    """Test validation of all outcomes in a course."""
    # Create aligned outcome
    client.post(f'/api/courses/{course_id}/outcomes', json={
        'behavior': 'analyze system requirements',
        'bloom_level': 'analyze'
    })

    # Create misaligned outcome
    client.post(f'/api/courses/{course_id}/outcomes', json={
        'behavior': 'list the key features',
        'bloom_level': 'evaluate'
    })

    # Validate all
    response = client.get(f'/api/courses/{course_id}/outcomes/validate')
    assert response.status_code == 200
    data = response.get_json()
    assert data['total_outcomes'] == 2
    assert data['aligned_count'] == 1
    assert data['misaligned_count'] == 1
    assert len(data['outcomes']) == 2
