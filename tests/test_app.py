"""Integration tests for Flask application endpoints."""

import json
import pytest


# ===========================
# Page Route Tests
# ===========================

def test_index_redirects_to_dashboard(client):
    """Test that root route redirects to dashboard."""
    response = client.get('/')
    assert response.status_code == 302
    assert '/dashboard' in response.location


def test_dashboard_renders(client):
    """Test that dashboard page renders successfully."""
    response = client.get('/dashboard')
    assert response.status_code == 200
    assert b'Course Builder Studio' in response.data
    assert b'My Courses' in response.data


def test_dashboard_shows_empty_state(client):
    """Test that dashboard shows empty state when no courses exist."""
    response = client.get('/dashboard')
    assert response.status_code == 200
    assert b'No courses yet' in response.data


def test_dashboard_shows_courses(client):
    """Test that dashboard displays courses when they exist."""
    # Create a course
    client.post('/api/courses',
                json={'title': 'Test Course', 'description': 'Test description'})

    # Check dashboard displays it
    response = client.get('/dashboard')
    assert response.status_code == 200
    assert b'Test Course' in response.data
    assert b'Test description' in response.data


# ===========================
# GET /api/courses Tests
# ===========================

def test_get_courses_empty(client):
    """Test getting courses when none exist."""
    response = client.get('/api/courses')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['courses'] == []
    assert data['page'] == 1
    assert data['total'] == 0
    assert data['has_more'] is False


def test_get_courses_list(client):
    """Test getting list of courses."""
    # Create two courses
    client.post('/api/courses', json={'title': 'Course 1'})
    client.post('/api/courses', json={'title': 'Course 2'})

    response = client.get('/api/courses')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data['courses']) == 2
    assert data['total'] == 2
    assert any(c['title'] == 'Course 1' for c in data['courses'])
    assert any(c['title'] == 'Course 2' for c in data['courses'])


# ===========================
# POST /api/courses Tests
# ===========================

def test_create_course_minimal(client):
    """Test creating course with minimal data."""
    response = client.post('/api/courses', json={'title': 'New Course'})
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['title'] == 'New Course'
    assert 'id' in data
    assert data['id'].startswith('course_')


def test_create_course_full(client):
    """Test creating course with all fields."""
    course_data = {
        'title': 'Python Basics',
        'description': 'Learn Python fundamentals',
        'audience_level': 'beginner',
        'target_duration_minutes': 120,
        'modality': 'online'
    }

    response = client.post('/api/courses', json=course_data)
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['title'] == 'Python Basics'
    assert data['description'] == 'Learn Python fundamentals'
    assert data['audience_level'] == 'beginner'
    assert data['target_duration_minutes'] == 120
    assert data['modality'] == 'online'


def test_create_course_no_json(client):
    """Test creating course without JSON body returns 4xx error."""
    response = client.post('/api/courses')
    # Flask returns 415 when Content-Type is missing, or 400 if JSON is None
    assert response.status_code in [400, 415]


# ===========================
# GET /api/courses/<id> Tests
# ===========================

def test_get_course_exists(client):
    """Test getting a specific course that exists."""
    # Create course
    create_response = client.post('/api/courses', json={'title': 'Test Course'})
    course_id = json.loads(create_response.data)['id']

    # Get course
    response = client.get(f'/api/courses/{course_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['id'] == course_id
    assert data['title'] == 'Test Course'


def test_get_course_not_found(client):
    """Test getting non-existent course returns 404."""
    response = client.get('/api/courses/nonexistent_id')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert 'error' in data


# ===========================
# PUT /api/courses/<id> Tests
# ===========================

def test_update_course(client):
    """Test updating course fields."""
    # Create course
    create_response = client.post('/api/courses', json={'title': 'Original Title'})
    course_id = json.loads(create_response.data)['id']

    # Update course
    update_data = {
        'title': 'Updated Title',
        'description': 'New description'
    }
    response = client.put(f'/api/courses/{course_id}', json=update_data)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == 'Updated Title'
    assert data['description'] == 'New description'


def test_update_course_not_found(client):
    """Test updating non-existent course returns 404."""
    response = client.put('/api/courses/nonexistent_id', json={'title': 'New'})
    assert response.status_code == 404
    data = json.loads(response.data)
    assert 'error' in data


def test_update_course_no_json(client):
    """Test updating course without JSON body returns 4xx error."""
    # Create course
    create_response = client.post('/api/courses', json={'title': 'Test'})
    course_id = json.loads(create_response.data)['id']

    # Try update without JSON
    response = client.put(f'/api/courses/{course_id}')
    # Flask returns 415 when Content-Type is missing, or 400 if JSON is None
    assert response.status_code in [400, 415]


# ===========================
# DELETE /api/courses/<id> Tests
# ===========================

def test_delete_course(client):
    """Test deleting an existing course."""
    # Create course
    create_response = client.post('/api/courses', json={'title': 'To Delete'})
    course_id = json.loads(create_response.data)['id']

    # Delete course
    response = client.delete(f'/api/courses/{course_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'message' in data

    # Verify course is gone
    get_response = client.get(f'/api/courses/{course_id}')
    assert get_response.status_code == 404


def test_delete_course_not_found(client):
    """Test deleting non-existent course returns 404."""
    response = client.delete('/api/courses/nonexistent_id')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert 'error' in data


# ===========================
# System Health Tests
# ===========================

def test_health_check(client):
    """Test health check endpoint."""
    response = client.get('/api/system/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'ok'
    assert data['version'] == '1.0.0'
    assert 'ai_enabled' in data


# ===========================
# Extended Course Fields Tests
# ===========================

def test_create_course_with_prerequisites(client):
    """Test creating course with prerequisites field."""
    course_data = {
        'title': 'Advanced Machine Learning',
        'prerequisites': 'Python programming, linear algebra, basic statistics'
    }

    response = client.post('/api/courses', json=course_data)
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['title'] == 'Advanced Machine Learning'
    assert data['prerequisites'] == 'Python programming, linear algebra, basic statistics'


def test_create_course_with_tools(client):
    """Test creating course with tools list."""
    course_data = {
        'title': 'Web Development Bootcamp',
        'tools': ['Node.js', 'React', 'PostgreSQL', 'Docker']
    }

    response = client.post('/api/courses', json=course_data)
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['title'] == 'Web Development Bootcamp'
    assert data['tools'] == ['Node.js', 'React', 'PostgreSQL', 'Docker']
    assert len(data['tools']) == 4


def test_create_course_with_grading_policy(client):
    """Test creating course with grading_policy field."""
    course_data = {
        'title': 'Data Science Fundamentals',
        'grading_policy': '40% projects, 30% quizzes, 20% final exam, 10% participation'
    }

    response = client.post('/api/courses', json=course_data)
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['title'] == 'Data Science Fundamentals'
    assert data['grading_policy'] == '40% projects, 30% quizzes, 20% final exam, 10% participation'


def test_create_course_with_all_new_fields(client):
    """Test creating course with prerequisites, tools, and grading_policy."""
    course_data = {
        'title': 'Full Stack Development',
        'description': 'Comprehensive full stack course',
        'prerequisites': 'Basic HTML, CSS, JavaScript',
        'tools': ['VS Code', 'Git', 'Node.js', 'MongoDB'],
        'grading_policy': '50% projects, 30% labs, 20% quizzes'
    }

    response = client.post('/api/courses', json=course_data)
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['prerequisites'] == 'Basic HTML, CSS, JavaScript'
    assert data['tools'] == ['VS Code', 'Git', 'Node.js', 'MongoDB']
    assert data['grading_policy'] == '50% projects, 30% labs, 20% quizzes'


def test_create_course_without_new_fields(client):
    """Test creating course without new fields still works (backward compat)."""
    course_data = {
        'title': 'Old Style Course',
        'description': 'Created without new fields'
    }

    response = client.post('/api/courses', json=course_data)
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['title'] == 'Old Style Course'
    assert data['prerequisites'] is None
    assert data['tools'] == []
    assert data['grading_policy'] is None


def test_update_course_with_new_fields(client):
    """Test updating course with prerequisites, tools, grading_policy."""
    # Create course
    create_response = client.post('/api/courses', json={'title': 'Test Course'})
    course_id = json.loads(create_response.data)['id']

    # Update with new fields
    update_data = {
        'prerequisites': 'Updated prerequisites',
        'tools': ['Tool1', 'Tool2'],
        'grading_policy': 'Updated grading policy'
    }
    response = client.put(f'/api/courses/{course_id}', json=update_data)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['prerequisites'] == 'Updated prerequisites'
    assert data['tools'] == ['Tool1', 'Tool2']
    assert data['grading_policy'] == 'Updated grading policy'


def test_list_courses_includes_status_fields(client):
    """Test that list courses includes audience_level, modality, lesson_count, activity_count."""
    # Create a course
    course_data = {
        'title': 'Test Course',
        'audience_level': 'advanced',
        'modality': 'blended',
        'target_duration_minutes': 180
    }
    client.post('/api/courses', json=course_data)

    # Get courses list with summary_only=false to get full fields
    response = client.get('/api/courses?summary_only=false')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data['courses']) == 1

    course = data['courses'][0]
    assert 'audience_level' in course
    assert course['audience_level'] == 'advanced'
    assert 'modality' in course
    assert course['modality'] == 'blended'
    assert 'target_duration_minutes' in course
    assert course['target_duration_minutes'] == 180
    assert 'lesson_count' in course
    assert 'activity_count' in course
    assert 'build_state' in course


# ===========================
# Course-Level Audience Tests
# ===========================

def test_course_default_audience(client):
    """Test course default_audience field."""
    # Create course with custom default_audience
    response = client.post('/api/courses', json={
        'title': 'Test Course',
        'default_audience': 'Data Scientists'
    })
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['default_audience'] == 'Data Scientists'


def test_update_course_default_audience(client):
    """Test updating course default_audience field."""
    # Create course
    create_response = client.post('/api/courses', json={'title': 'Test Course'})
    course_id = json.loads(create_response.data)['id']

    # Update default_audience
    response = client.put(f'/api/courses/{course_id}', json={
        'default_audience': 'Software Engineers'
    })
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['default_audience'] == 'Software Engineers'


def test_outcome_effective_audience_inherits_from_course(client):
    """Test that learning outcomes inherit effective_audience from course."""
    # Create course with custom default_audience
    create_response = client.post('/api/courses', json={
        'title': 'Test Course',
        'default_audience': 'Product Managers'
    })
    course_id = json.loads(create_response.data)['id']

    # Create learning outcome without explicit audience
    outcome_response = client.post(f'/api/courses/{course_id}/outcomes', json={
        'behavior': 'identify key metrics',
        'bloom_level': 'understand'
    })
    assert outcome_response.status_code == 201
    outcome_data = json.loads(outcome_response.data)

    # effective_audience should inherit from course
    assert outcome_data['effective_audience'] == 'Product Managers'
    assert outcome_data['audience'] == ''  # Raw audience is empty


def test_outcome_explicit_audience_overrides_course(client):
    """Test that explicit audience on outcome overrides course default."""
    # Create course with default_audience
    create_response = client.post('/api/courses', json={
        'title': 'Test Course',
        'default_audience': 'Developers'
    })
    course_id = json.loads(create_response.data)['id']

    # Create learning outcome with explicit audience
    outcome_response = client.post(f'/api/courses/{course_id}/outcomes', json={
        'audience': 'Senior Developers',
        'behavior': 'design system architectures',
        'bloom_level': 'create'
    })
    assert outcome_response.status_code == 201
    outcome_data = json.loads(outcome_response.data)

    # effective_audience should use explicit audience
    assert outcome_data['effective_audience'] == 'Senior Developers'
    assert outcome_data['audience'] == 'Senior Developers'
