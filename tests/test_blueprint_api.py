"""Integration tests for blueprint API endpoints."""

import pytest
from pathlib import Path

from src.core.project_store import ProjectStore
from src.core.models import Course, LearningOutcome, BloomLevel
from src.generators.blueprint_generator import (
    CourseBlueprint,
    ModuleBlueprint,
    LessonBlueprint,
    ActivityBlueprint,
    ContentDistribution
)


# Uses client fixture from conftest.py which includes authentication


def make_test_blueprint():
    """Create a valid CourseBlueprint for testing.

    Creates a 2-module blueprint with realistic structure:
    - 2 modules, 3 lessons each, 2 activities per lesson = 12 activities
    - ~90 min total
    - Realistic content type distribution
    """
    # Module 1: Introduction
    module1 = ModuleBlueprint(
        title="Introduction to Python Basics",
        description="Learn fundamental Python concepts and syntax",
        lessons=[
            LessonBlueprint(
                title="Python Setup and First Program",
                description="Install Python and run your first program",
                activities=[
                    ActivityBlueprint(
                        title="Welcome to Python",
                        content_type="video",
                        activity_type="video_lecture",
                        wwhaa_phase="hook",
                        bloom_level="remember",
                        estimated_duration_minutes=7.0,
                        description="Introduction to Python and its applications"
                    ),
                    ActivityBlueprint(
                        title="Python Installation Guide",
                        content_type="reading",
                        activity_type="reading",
                        bloom_level="understand",
                        estimated_duration_minutes=10.0,
                        description="Step-by-step installation guide"
                    )
                ]
            ),
            LessonBlueprint(
                title="Variables and Data Types",
                description="Understanding variables, strings, numbers, and booleans",
                activities=[
                    ActivityBlueprint(
                        title="Variables Explained",
                        content_type="video",
                        activity_type="video_lecture",
                        wwhaa_phase="content",
                        bloom_level="understand",
                        estimated_duration_minutes=8.0,
                        description="How to create and use variables"
                    ),
                    ActivityBlueprint(
                        title="Data Types Practice",
                        content_type="quiz",
                        activity_type="practice_quiz",
                        bloom_level="apply",
                        estimated_duration_minutes=5.0,
                        description="Practice identifying data types"
                    )
                ]
            ),
            LessonBlueprint(
                title="Basic Operations",
                description="Arithmetic and string operations",
                activities=[
                    ActivityBlueprint(
                        title="Python Operators",
                        content_type="video",
                        activity_type="video_lecture",
                        wwhaa_phase="content",
                        bloom_level="apply",
                        estimated_duration_minutes=6.0,
                        description="Arithmetic and comparison operators"
                    ),
                    ActivityBlueprint(
                        title="Operations Lab",
                        content_type="hol",
                        activity_type="hands_on_lab",
                        bloom_level="apply",
                        estimated_duration_minutes=15.0,
                        description="Practice using operators in code"
                    )
                ]
            )
        ]
    )

    # Module 2: Control Flow
    module2 = ModuleBlueprint(
        title="Control Flow and Functions",
        description="Learn conditionals, loops, and functions",
        lessons=[
            LessonBlueprint(
                title="If Statements",
                description="Conditional logic with if/elif/else",
                activities=[
                    ActivityBlueprint(
                        title="Conditional Logic",
                        content_type="video",
                        activity_type="video_lecture",
                        wwhaa_phase="content",
                        bloom_level="understand",
                        estimated_duration_minutes=7.0,
                        description="How to write conditional statements"
                    ),
                    ActivityBlueprint(
                        title="Conditionals Quiz",
                        content_type="quiz",
                        activity_type="graded_quiz",
                        bloom_level="apply",
                        estimated_duration_minutes=8.0,
                        description="Test your understanding of conditionals"
                    )
                ]
            ),
            LessonBlueprint(
                title="Loops",
                description="For and while loops",
                activities=[
                    ActivityBlueprint(
                        title="Iteration Basics",
                        content_type="video",
                        activity_type="video_lecture",
                        wwhaa_phase="content",
                        bloom_level="apply",
                        estimated_duration_minutes=8.0,
                        description="Using for and while loops"
                    ),
                    ActivityBlueprint(
                        title="Loop Practice Lab",
                        content_type="hol",
                        activity_type="hands_on_lab",
                        bloom_level="apply",
                        estimated_duration_minutes=12.0,
                        description="Write loops to solve problems"
                    )
                ]
            ),
            LessonBlueprint(
                title="Functions",
                description="Defining and calling functions",
                activities=[
                    ActivityBlueprint(
                        title="Function Fundamentals",
                        content_type="reading",
                        activity_type="reading",
                        bloom_level="understand",
                        estimated_duration_minutes=9.0,
                        description="Function syntax and parameters"
                    ),
                    ActivityBlueprint(
                        title="Final Assessment",
                        content_type="quiz",
                        activity_type="graded_quiz",
                        bloom_level="analyze",
                        estimated_duration_minutes=10.0,
                        description="Comprehensive quiz on all topics"
                    )
                ]
            )
        ]
    )

    return CourseBlueprint(
        modules=[module1, module2],
        total_duration_minutes=90.0,
        content_distribution=ContentDistribution(
            video=0.33,
            reading=0.17,
            quiz=0.25,
            hands_on=0.25
        ),
        rationale="Two-module structure introduces basics first, then builds to control flow and functions. "
                  "Balanced mix of video, reading, hands-on, and assessment activities."
    )


def test_generate_blueprint_success(client, mocker):
    """Test successful blueprint generation."""
    # Mock Config.ANTHROPIC_API_KEY BEFORE creating course
    mocker.patch('src.api.blueprint.Config.ANTHROPIC_API_KEY', 'test-key')

    # Create course with description and outcomes
    response = client.post('/api/courses', json={
        'title': 'Python Fundamentals',
        'description': 'Learn Python programming basics',
        'target_duration_minutes': 90
    })
    assert response.status_code == 201
    course = response.get_json()
    course_id = course['id']

    # Add learning outcomes
    client.post(f'/api/courses/{course_id}/learning_outcomes', json={
        'audience': 'Students',
        'behavior': 'write',
        'condition': 'basic Python programs',
        'degree': 'with correct syntax',
        'bloom_level': 'apply'
    })

    # Mock BlueprintGenerator
    mock_generator_class = mocker.patch('src.api.blueprint.BlueprintGenerator')
    mock_instance = mock_generator_class.return_value
    mock_instance.generate.return_value = make_test_blueprint()

    # Generate blueprint (auto_fix=False to use mocked generate())
    response = client.post(f'/api/courses/{course_id}/blueprint/generate', json={
        'description': 'Learn Python programming basics',
        'learning_outcomes': ['Students write basic Python programs with correct syntax'],
        'target_duration': 90,
        'audience_level': 'beginner',
        'auto_fix': False
    })

    assert response.status_code == 200
    data = response.get_json()

    # Verify response structure
    assert 'blueprint' in data
    assert 'validation' in data
    assert 'status' in data
    assert data['status'] == 'pending_review'

    # Verify blueprint structure
    blueprint = data['blueprint']
    assert 'modules' in blueprint
    assert len(blueprint['modules']) == 2
    assert 'total_duration_minutes' in blueprint
    assert blueprint['total_duration_minutes'] == 90.0

    # Verify validation structure
    validation = data['validation']
    assert 'is_valid' in validation
    assert 'errors' in validation
    assert 'warnings' in validation
    assert 'suggestions' in validation
    assert 'metrics' in validation


def test_generate_blueprint_course_not_found(client):
    """Test generating blueprint for non-existent course."""
    response = client.post('/api/courses/invalid_id/blueprint/generate', json={
        'description': 'Test course',
        'learning_outcomes': ['Test outcome']
    })

    assert response.status_code == 404
    data = response.get_json()
    assert 'error' in data


def test_generate_blueprint_missing_description(client, mocker):
    """Test generating blueprint without description."""
    # Mock API key to pass AI check
    mocker.patch('src.api.blueprint.Config.ANTHROPIC_API_KEY', 'test-key')

    # Create course with empty description
    response = client.post('/api/courses', json={
        'title': 'Test Course',
        'description': '',
        'target_duration_minutes': 90
    })
    assert response.status_code == 201
    course_id = response.get_json()['id']

    # Try to generate without description in request
    response = client.post(f'/api/courses/{course_id}/blueprint/generate', json={
        'learning_outcomes': ['Test outcome']
    })

    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    assert 'description' in data['error'].lower()


def test_generate_blueprint_no_ai(client, mocker):
    """Test generating blueprint when AI not available."""
    # Create course
    response = client.post('/api/courses', json={
        'title': 'Test Course',
        'description': 'Test description'
    })
    course_id = response.get_json()['id']

    # Mock Config.ANTHROPIC_API_KEY to be None
    mocker.patch('src.api.blueprint.Config.ANTHROPIC_API_KEY', None)

    response = client.post(f'/api/courses/{course_id}/blueprint/generate', json={
        'description': 'Test description',
        'learning_outcomes': ['Test outcome']
    })

    assert response.status_code == 503
    data = response.get_json()
    assert 'error' in data
    assert 'AI not available' in data['error']


def test_accept_blueprint_success(client):
    """Test accepting a valid blueprint."""
    # Create course with matching target_duration
    response = client.post('/api/courses', json={
        'title': 'Python Fundamentals',
        'description': 'Learn Python basics',
        'target_duration_minutes': 90
    })
    course_id = response.get_json()['id']

    # Create valid blueprint
    blueprint = make_test_blueprint()

    # Accept blueprint
    response = client.post(f'/api/courses/{course_id}/blueprint/accept', json={
        'blueprint': blueprint.model_dump()
    })

    assert response.status_code == 200
    data = response.get_json()

    # Verify response
    assert 'message' in data
    assert 'module_count' in data
    assert 'lesson_count' in data
    assert 'activity_count' in data

    assert data['module_count'] == 2
    assert data['lesson_count'] == 6
    assert data['activity_count'] == 12


def test_accept_blueprint_validation_errors(client):
    """Test accepting blueprint with validation errors."""
    # Create course
    response = client.post('/api/courses', json={
        'title': 'Test Course',
        'description': 'Test'
    })
    course_id = response.get_json()['id']

    # Create invalid blueprint (5 modules - exceeds max of 3)
    blueprint = make_test_blueprint()
    blueprint_dict = blueprint.model_dump()

    # Duplicate modules to create 5 (invalid)
    blueprint_dict['modules'] = blueprint_dict['modules'] * 3  # 6 modules
    blueprint_dict['total_duration_minutes'] = 270.0

    # Try to accept
    response = client.post(f'/api/courses/{course_id}/blueprint/accept', json={
        'blueprint': blueprint_dict
    })

    assert response.status_code == 422
    data = response.get_json()
    assert 'error' in data
    assert 'validation' in data
    assert not data['validation']['is_valid']
    assert len(data['validation']['errors']) > 0


def test_accept_blueprint_missing_data(client):
    """Test accepting blueprint without blueprint data."""
    # Create course
    response = client.post('/api/courses', json={
        'title': 'Test Course',
        'description': 'Test'
    })
    course_id = response.get_json()['id']

    # Try to accept with empty body
    response = client.post(f'/api/courses/{course_id}/blueprint/accept', json={})

    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    assert 'blueprint' in data['error'].lower()


def test_accept_blueprint_creates_correct_structure(client):
    """Test that accepting blueprint creates the correct course structure."""
    # Create course with matching target_duration
    response = client.post('/api/courses', json={
        'title': 'Python Fundamentals',
        'description': 'Learn Python basics',
        'target_duration_minutes': 90
    })
    course_id = response.get_json()['id']

    # Create and accept blueprint
    blueprint = make_test_blueprint()
    response = client.post(f'/api/courses/{course_id}/blueprint/accept', json={
        'blueprint': blueprint.model_dump()
    })
    assert response.status_code == 200

    # Get course and verify structure
    response = client.get(f'/api/courses/{course_id}')
    assert response.status_code == 200
    course = response.get_json()

    # Verify counts
    assert len(course['modules']) == 2
    total_lessons = sum(len(module['lessons']) for module in course['modules'])
    assert total_lessons == 6

    total_activities = sum(
        len(lesson['activities'])
        for module in course['modules']
        for lesson in module['lessons']
    )
    assert total_activities == 12

    # Verify module structure
    module1 = course['modules'][0]
    assert module1['title'] == "Introduction to Python Basics"
    assert len(module1['lessons']) == 3

    # Verify lesson structure
    lesson1 = module1['lessons'][0]
    assert lesson1['title'] == "Python Setup and First Program"
    assert len(lesson1['activities']) == 2

    # Verify activity structure
    activity1 = lesson1['activities'][0]
    assert activity1['title'] == "Welcome to Python"
    assert activity1['content_type'] == 'video'
    assert activity1['bloom_level'] == 'remember'


def test_refine_blueprint_success(client, mocker):
    """Test refining a blueprint with feedback."""
    # Mock API key
    mocker.patch('src.api.blueprint.Config.ANTHROPIC_API_KEY', 'test-key')

    # Create course with outcomes
    response = client.post('/api/courses', json={
        'title': 'Python Fundamentals',
        'description': 'Learn Python programming basics',
        'target_duration_minutes': 90
    })
    course_id = response.get_json()['id']

    # Add learning outcome
    client.post(f'/api/courses/{course_id}/learning_outcomes', json={
        'audience': 'Students',
        'behavior': 'write',
        'condition': 'basic Python programs',
        'degree': 'with correct syntax',
        'bloom_level': 'apply'
    })

    # Create initial blueprint
    previous_blueprint = make_test_blueprint()

    # Mock the generator's client to return a refined blueprint
    mock_client = mocker.MagicMock()
    mock_response = mocker.MagicMock()
    # The response needs tool_use block with type and input attributes
    mock_tool_block = mocker.MagicMock()
    mock_tool_block.type = "tool_use"
    mock_tool_block.input = previous_blueprint.model_dump()
    mock_response.content = [mock_tool_block]
    mock_client.messages.create.return_value = mock_response

    # Patch BlueprintGenerator to use mock client
    mock_generator_class = mocker.patch('src.api.blueprint.BlueprintGenerator')
    mock_instance = mock_generator_class.return_value
    mock_instance.client = mock_client
    mock_instance.model = "claude-sonnet-4-20250514"

    # Refine blueprint
    response = client.post(f'/api/courses/{course_id}/blueprint/refine', json={
        'blueprint': previous_blueprint.model_dump(),
        'feedback': 'Add more hands-on activities and reduce video content'
    })

    assert response.status_code == 200
    data = response.get_json()

    # Verify response structure
    assert 'blueprint' in data
    assert 'validation' in data
    assert 'status' in data
    assert data['status'] == 'pending_review'


def test_refine_blueprint_missing_feedback(client, mocker):
    """Test refining blueprint without feedback."""
    # Mock API key
    mocker.patch('src.api.blueprint.Config.ANTHROPIC_API_KEY', 'test-key')

    # Create course
    response = client.post('/api/courses', json={
        'title': 'Test Course',
        'description': 'Test'
    })
    course_id = response.get_json()['id']

    blueprint = make_test_blueprint()

    # Try to refine without feedback
    response = client.post(f'/api/courses/{course_id}/blueprint/refine', json={
        'blueprint': blueprint.model_dump()
    })

    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    assert 'feedback' in data['error'].lower()


def test_generate_uses_course_defaults(client, mocker):
    """Test that generate endpoint accepts explicit parameters."""
    # Mock API key
    mocker.patch('src.api.blueprint.Config.ANTHROPIC_API_KEY', 'test-key')

    # Create course
    response = client.post('/api/courses', json={
        'title': 'Python Fundamentals',
        'description': 'Learn Python programming basics',
        'audience_level': 'intermediate',
        'target_duration_minutes': 90
    })
    course_id = response.get_json()['id']

    # Mock BlueprintGenerator
    mock_generator_class = mocker.patch('src.api.blueprint.BlueprintGenerator')
    mock_instance = mock_generator_class.return_value
    mock_instance.generate.return_value = make_test_blueprint()

    # Generate with explicit parameters (auto_fix=False to use mocked generate())
    response = client.post(f'/api/courses/{course_id}/blueprint/generate', json={
        'description': 'Custom description',
        'learning_outcomes': ['Custom outcome'],
        'target_duration': 120,
        'audience_level': 'beginner',
        'auto_fix': False
    })

    assert response.status_code == 200

    # Verify generator was called with provided values (not course defaults)
    mock_instance.generate.assert_called_once()
    call_args = mock_instance.generate.call_args
    assert call_args.kwargs['course_description'] == 'Custom description'
    assert call_args.kwargs['target_duration_minutes'] == 120
    assert call_args.kwargs['audience_level'] == 'beginner'
    assert call_args.kwargs['learning_outcomes'] == ['Custom outcome']


def test_accept_blueprint_preserves_course_id(client):
    """Test that accepting blueprint preserves course ID and metadata."""
    # Create course with matching target_duration
    response = client.post('/api/courses', json={
        'title': 'Python Fundamentals',
        'description': 'Learn Python basics',
        'target_duration_minutes': 90
    })
    original_course = response.get_json()
    course_id = original_course['id']

    # Accept blueprint
    blueprint = make_test_blueprint()
    response = client.post(f'/api/courses/{course_id}/blueprint/accept', json={
        'blueprint': blueprint.model_dump()
    })
    assert response.status_code == 200

    # Get course
    response = client.get(f'/api/courses/{course_id}')
    updated_course = response.get_json()

    # Verify ID and metadata preserved
    assert updated_course['id'] == course_id
    assert updated_course['title'] == original_course['title']
    assert updated_course['description'] == original_course['description']


def test_generate_blueprint_missing_learning_outcomes(client, mocker):
    """Test that generate requires at least one learning outcome."""
    # Mock API key
    mocker.patch('src.api.blueprint.Config.ANTHROPIC_API_KEY', 'test-key')

    # Create course with description but no outcomes
    response = client.post('/api/courses', json={
        'title': 'Test Course',
        'description': 'Test description'
    })
    course_id = response.get_json()['id']

    # Try to generate with no learning outcomes in request and none in course
    response = client.post(f'/api/courses/{course_id}/blueprint/generate', json={
        'description': 'Test description'
    })

    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    assert 'learning outcome' in data['error'].lower()
