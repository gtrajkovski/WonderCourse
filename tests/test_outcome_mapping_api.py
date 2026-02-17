"""Tests for learning outcome-activity mapping and alignment API endpoints."""

import pytest
from pathlib import Path

from src.core.project_store import ProjectStore
from src.core.models import Course, BloomLevel


# Uses client fixture from conftest.py which includes authentication


@pytest.fixture
def seeded_course(client):
    """Create course with modules, lessons, activities, and outcomes.

    Structure:
    - 1 course
    - 1 module
    - 2 lessons (each with 2 activities, 4 activities total)
    - 2 learning outcomes

    Args:
        client: Flask test client fixture.

    Returns:
        Tuple of (course_id, module_id, [lesson_id1, lesson_id2],
                  [act_id1, act_id2, act_id3, act_id4], [outcome_id1, outcome_id2])
    """
    # Create course
    resp = client.post('/api/courses', json={"title": "Test Course"})
    course_id = resp.get_json()['id']

    # Create module
    resp = client.post(f'/api/courses/{course_id}/modules', json={"title": "Module 1"})
    module_id = resp.get_json()['id']

    # Create lesson 1
    resp = client.post(f'/api/courses/{course_id}/modules/{module_id}/lessons', json={
        "title": "Lesson 1"
    })
    lesson_id1 = resp.get_json()['id']

    # Create 2 activities in lesson 1
    resp = client.post(f'/api/courses/{course_id}/lessons/{lesson_id1}/activities', json={
        "title": "Video Lecture 1"
    })
    activity_id1 = resp.get_json()['id']

    resp = client.post(f'/api/courses/{course_id}/lessons/{lesson_id1}/activities', json={
        "title": "Lab Exercise 1"
    })
    activity_id2 = resp.get_json()['id']

    # Create lesson 2
    resp = client.post(f'/api/courses/{course_id}/modules/{module_id}/lessons', json={
        "title": "Lesson 2"
    })
    lesson_id2 = resp.get_json()['id']

    # Create 2 activities in lesson 2
    resp = client.post(f'/api/courses/{course_id}/lessons/{lesson_id2}/activities', json={
        "title": "Video Lecture 2"
    })
    activity_id3 = resp.get_json()['id']

    resp = client.post(f'/api/courses/{course_id}/lessons/{lesson_id2}/activities', json={
        "title": "Quiz 1"
    })
    activity_id4 = resp.get_json()['id']

    # Create 2 learning outcomes
    resp = client.post(f'/api/courses/{course_id}/outcomes', json={
        "behavior": "implement a REST API",
        "bloom_level": "apply"
    })
    outcome_id1 = resp.get_json()['id']

    resp = client.post(f'/api/courses/{course_id}/outcomes', json={
        "behavior": "debug code",
        "bloom_level": "analyze"
    })
    outcome_id2 = resp.get_json()['id']

    return (
        course_id,
        module_id,
        [lesson_id1, lesson_id2],
        [activity_id1, activity_id2, activity_id3, activity_id4],
        [outcome_id1, outcome_id2]
    )


def test_map_outcome_to_activity(client, seeded_course):
    """Test mapping an outcome to an activity."""
    course_id, _, _, activity_ids, outcome_ids = seeded_course
    outcome_id = outcome_ids[0]
    activity_id = activity_ids[0]

    response = client.post(
        f'/api/courses/{course_id}/outcomes/{outcome_id}/map',
        json={"activity_id": activity_id}
    )

    assert response.status_code == 200
    data = response.get_json()
    assert activity_id in data['mapped_activity_ids']
    assert len(data['mapped_activity_ids']) == 1


def test_map_idempotent(client, seeded_course):
    """Test mapping same pair twice produces no duplicates."""
    course_id, _, _, activity_ids, outcome_ids = seeded_course
    outcome_id = outcome_ids[0]
    activity_id = activity_ids[0]

    # Map once
    client.post(
        f'/api/courses/{course_id}/outcomes/{outcome_id}/map',
        json={"activity_id": activity_id}
    )

    # Map again
    response = client.post(
        f'/api/courses/{course_id}/outcomes/{outcome_id}/map',
        json={"activity_id": activity_id}
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data['mapped_activity_ids'] == [activity_id]  # No duplicates


def test_map_invalid_outcome(client, seeded_course):
    """Test mapping with nonexistent outcome returns 404."""
    course_id, _, _, activity_ids, _ = seeded_course
    activity_id = activity_ids[0]

    response = client.post(
        f'/api/courses/{course_id}/outcomes/invalid_outcome_id/map',
        json={"activity_id": activity_id}
    )

    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data


def test_map_invalid_activity(client, seeded_course):
    """Test mapping with nonexistent activity returns 404."""
    course_id, _, _, _, outcome_ids = seeded_course
    outcome_id = outcome_ids[0]

    response = client.post(
        f'/api/courses/{course_id}/outcomes/{outcome_id}/map',
        json={"activity_id": "invalid_activity_id"}
    )

    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data


def test_unmap_outcome_from_activity(client, seeded_course):
    """Test unmapping an outcome from an activity."""
    course_id, _, _, activity_ids, outcome_ids = seeded_course
    outcome_id = outcome_ids[0]
    activity_id = activity_ids[0]

    # Map first
    client.post(
        f'/api/courses/{course_id}/outcomes/{outcome_id}/map',
        json={"activity_id": activity_id}
    )

    # Unmap
    response = client.delete(
        f'/api/courses/{course_id}/outcomes/{outcome_id}/map/{activity_id}'
    )

    assert response.status_code == 200
    data = response.get_json()
    assert 'message' in data

    # Verify removed
    outcome_response = client.get(f'/api/courses/{course_id}/outcomes')
    outcomes = outcome_response.get_json()
    outcome = next((o for o in outcomes if o['id'] == outcome_id), None)
    assert outcome is not None
    assert activity_id not in outcome['mapped_activity_ids']


def test_unmap_nonexistent_mapping(client, seeded_course):
    """Test unmapping activity that wasn't mapped returns 200 (idempotent)."""
    course_id, _, _, activity_ids, outcome_ids = seeded_course
    outcome_id = outcome_ids[0]
    activity_id = activity_ids[0]

    # Unmap without mapping first
    response = client.delete(
        f'/api/courses/{course_id}/outcomes/{outcome_id}/map/{activity_id}'
    )

    assert response.status_code == 200  # Idempotent


def test_alignment_matrix(client, seeded_course):
    """Test alignment matrix with mixed mappings."""
    course_id, _, _, activity_ids, outcome_ids = seeded_course
    outcome_id1 = outcome_ids[0]
    outcome_id2 = outcome_ids[1]
    activity_id1 = activity_ids[0]
    activity_id2 = activity_ids[1]
    activity_id3 = activity_ids[2]
    activity_id4 = activity_ids[3]

    # Map outcome 1 to activities 1 and 2
    client.post(
        f'/api/courses/{course_id}/outcomes/{outcome_id1}/map',
        json={"activity_id": activity_id1}
    )
    client.post(
        f'/api/courses/{course_id}/outcomes/{outcome_id1}/map',
        json={"activity_id": activity_id2}
    )

    # Leave outcome 2 unmapped

    # Get alignment
    response = client.get(f'/api/courses/{course_id}/alignment')
    assert response.status_code == 200
    data = response.get_json()

    # Verify structure
    assert 'outcomes' in data
    assert 'unmapped_outcomes' in data
    assert 'unmapped_activities' in data
    assert 'coverage_score' in data

    # Verify outcomes
    assert len(data['outcomes']) == 2

    # Verify outcome 1 has 2 mapped activities
    outcome1_data = next((o for o in data['outcomes'] if o['id'] == outcome_id1), None)
    assert outcome1_data is not None
    assert len(outcome1_data['mapped_activities']) == 2
    assert outcome1_data['behavior'] == 'implement a REST API'
    assert outcome1_data['bloom_level'] == 'apply'

    # Verify unmapped outcomes (outcome 2)
    assert outcome_id2 in data['unmapped_outcomes']
    assert len(data['unmapped_outcomes']) == 1

    # Verify unmapped activities (activities 3 and 4)
    assert activity_id3 in data['unmapped_activities']
    assert activity_id4 in data['unmapped_activities']
    assert len(data['unmapped_activities']) == 2

    # Verify coverage score (1 out of 2 outcomes mapped = 0.5)
    assert data['coverage_score'] == 0.5


def test_alignment_empty_course(client):
    """Test alignment for course with no outcomes."""
    # Create course with no outcomes
    resp = client.post('/api/courses', json={"title": "Empty Course"})
    course_id = resp.get_json()['id']

    response = client.get(f'/api/courses/{course_id}/alignment')
    assert response.status_code == 200
    data = response.get_json()

    assert data['outcomes'] == []
    assert data['unmapped_outcomes'] == []
    assert data['unmapped_activities'] == []
    assert data['coverage_score'] == 0.0


def test_reverse_lookup(client, seeded_course):
    """Test reverse lookup: get outcomes mapped to an activity."""
    course_id, _, _, activity_ids, outcome_ids = seeded_course
    outcome_id1 = outcome_ids[0]
    outcome_id2 = outcome_ids[1]
    activity_id = activity_ids[0]

    # Map both outcomes to same activity
    client.post(
        f'/api/courses/{course_id}/outcomes/{outcome_id1}/map',
        json={"activity_id": activity_id}
    )
    client.post(
        f'/api/courses/{course_id}/outcomes/{outcome_id2}/map',
        json={"activity_id": activity_id}
    )

    # Reverse lookup
    response = client.get(f'/api/courses/{course_id}/activities/{activity_id}/outcomes')
    assert response.status_code == 200
    data = response.get_json()

    assert len(data) == 2
    outcome_ids_in_response = [o['id'] for o in data]
    assert outcome_id1 in outcome_ids_in_response
    assert outcome_id2 in outcome_ids_in_response


def test_reverse_lookup_no_mappings(client, seeded_course):
    """Test reverse lookup for unmapped activity returns empty list."""
    course_id, _, _, activity_ids, _ = seeded_course
    activity_id = activity_ids[0]

    # No mappings created

    response = client.get(f'/api/courses/{course_id}/activities/{activity_id}/outcomes')
    assert response.status_code == 200
    data = response.get_json()

    assert data == []
