"""Tests for BlueprintGenerator with mocked Anthropic API."""

import json
import pytest
from unittest.mock import MagicMock
from src.generators.blueprint_generator import (
    BlueprintGenerator,
    CourseBlueprint,
    ActivityBlueprint,
    LessonBlueprint,
    ModuleBlueprint
)


# Sample blueprint data as dict
SAMPLE_BLUEPRINT_DATA = {
    "modules": [
        {
            "title": "Introduction to Python Programming",
            "description": "Learn Python fundamentals and basic syntax",
            "lessons": [
                {
                    "title": "Python Basics",
                    "description": "Variables, data types, and operators",
                    "activities": [
                        {
                            "title": "Introduction to Variables",
                            "content_type": "video",
                            "activity_type": "video_lecture",
                            "wwhaa_phase": "hook",
                            "bloom_level": "remember",
                            "estimated_duration_minutes": 8.0,
                            "description": "Learn what variables are and why they matter"
                        },
                        {
                            "title": "Variables Practice Quiz",
                            "content_type": "quiz",
                            "activity_type": "practice_quiz",
                            "wwhaa_phase": None,
                            "bloom_level": "apply",
                            "estimated_duration_minutes": 4.0,
                            "description": "Test your understanding of Python variables"
                        }
                    ]
                },
                {
                    "title": "Control Flow",
                    "description": "Conditionals and loops in Python",
                    "activities": [
                        {
                            "title": "If Statements",
                            "content_type": "video",
                            "activity_type": "video_lecture",
                            "wwhaa_phase": "content",
                            "bloom_level": "understand",
                            "estimated_duration_minutes": 7.0,
                            "description": "Learn how to use conditional statements"
                        },
                        {
                            "title": "Loop Patterns",
                            "content_type": "reading",
                            "activity_type": "reading_material",
                            "wwhaa_phase": None,
                            "bloom_level": "analyze",
                            "estimated_duration_minutes": 10.0,
                            "description": "Understand common loop patterns and use cases"
                        },
                        {
                            "title": "Control Flow Lab",
                            "content_type": "hol",
                            "activity_type": "hands_on_lab",
                            "wwhaa_phase": None,
                            "bloom_level": "apply",
                            "estimated_duration_minutes": 20.0,
                            "description": "Practice writing conditional logic"
                        }
                    ]
                },
                {
                    "title": "Functions",
                    "description": "Defining and calling functions",
                    "activities": [
                        {
                            "title": "Function Basics",
                            "content_type": "video",
                            "activity_type": "video_lecture",
                            "wwhaa_phase": "objective",
                            "bloom_level": "understand",
                            "estimated_duration_minutes": 9.0,
                            "description": "Learn to define and call functions"
                        },
                        {
                            "title": "Function Quiz",
                            "content_type": "quiz",
                            "activity_type": "graded_quiz",
                            "wwhaa_phase": None,
                            "bloom_level": "apply",
                            "estimated_duration_minutes": 6.0,
                            "description": "Test your function knowledge"
                        }
                    ]
                }
            ]
        },
        {
            "title": "Data Structures in Python",
            "description": "Lists, dictionaries, and sets",
            "lessons": [
                {
                    "title": "Lists and Tuples",
                    "description": "Ordered collections in Python",
                    "activities": [
                        {
                            "title": "List Fundamentals",
                            "content_type": "video",
                            "activity_type": "video_lecture",
                            "wwhaa_phase": "hook",
                            "bloom_level": "understand",
                            "estimated_duration_minutes": 8.0,
                            "description": "Learn list operations and methods"
                        },
                        {
                            "title": "List Manipulation Lab",
                            "content_type": "lab",
                            "activity_type": "ungraded_lab",
                            "wwhaa_phase": None,
                            "bloom_level": "apply",
                            "estimated_duration_minutes": 15.0,
                            "description": "Practice list operations"
                        }
                    ]
                },
                {
                    "title": "Dictionaries",
                    "description": "Key-value data structures",
                    "activities": [
                        {
                            "title": "Dictionary Basics",
                            "content_type": "reading",
                            "activity_type": "reading_material",
                            "wwhaa_phase": None,
                            "bloom_level": "understand",
                            "estimated_duration_minutes": 10.0,
                            "description": "Understanding dictionary syntax and operations"
                        },
                        {
                            "title": "Dictionary Project",
                            "content_type": "project",
                            "activity_type": "project_milestone",
                            "wwhaa_phase": None,
                            "bloom_level": "create",
                            "estimated_duration_minutes": 30.0,
                            "description": "Build a simple contact manager using dictionaries"
                        }
                    ]
                },
                {
                    "title": "Sets and Advanced Collections",
                    "description": "Unique values and set operations",
                    "activities": [
                        {
                            "title": "Set Operations",
                            "content_type": "video",
                            "activity_type": "video_lecture",
                            "wwhaa_phase": "summary",
                            "bloom_level": "analyze",
                            "estimated_duration_minutes": 7.0,
                            "description": "Learn set union, intersection, difference"
                        }
                    ]
                }
            ]
        }
    ],
    "total_duration_minutes": 134.0,
    "content_distribution": {
        "video": 0.35,
        "reading": 0.15,
        "quiz": 0.15,
        "hands_on": 0.20,
        "other": 0.15
    },
    "rationale": "This blueprint divides Python fundamentals into two modules: basics (variables, control flow, functions) and data structures (lists, dicts, sets). Each lesson builds on the previous, progressing from simple concepts to practical application. The content distribution balances video lectures (35%) with hands-on practice (35%) and assessments (15%), ensuring learners can apply what they learn."
}

# JSON string for schema validation tests
SAMPLE_BLUEPRINT_JSON = json.dumps(SAMPLE_BLUEPRINT_DATA)


def _mock_tool_response(mock_client, data):
    """Helper to create properly structured tool_use response mock."""
    mock_response = MagicMock()
    mock_tool_use = MagicMock()
    mock_tool_use.type = "tool_use"
    mock_tool_use.input = data if isinstance(data, dict) else json.loads(data)
    mock_response.content = [mock_tool_use]
    mock_client.messages.create.return_value = mock_response


def test_course_blueprint_schema_valid():
    """Verify CourseBlueprint parses valid JSON correctly."""
    blueprint = CourseBlueprint.model_validate_json(SAMPLE_BLUEPRINT_JSON)

    # Check structure
    assert len(blueprint.modules) == 2
    assert len(blueprint.modules[0].lessons) == 3
    assert len(blueprint.modules[1].lessons) == 3

    # Check total activity count (2 + 3 + 2 + 2 + 2 + 1 = 12)
    total_activities = sum(
        len(lesson.activities)
        for module in blueprint.modules
        for lesson in module.lessons
    )
    assert total_activities == 12

    # Check activity types are present
    all_activities = [
        activity
        for module in blueprint.modules
        for lesson in module.lessons
        for activity in lesson.activities
    ]
    content_types = {a.content_type for a in all_activities}
    assert "video" in content_types
    assert "quiz" in content_types
    assert "hol" in content_types

    # Check Bloom levels
    bloom_levels = {a.bloom_level for a in all_activities}
    assert "remember" in bloom_levels
    assert "understand" in bloom_levels
    assert "apply" in bloom_levels
    assert "analyze" in bloom_levels
    assert "create" in bloom_levels

    # Check content distribution (now a Pydantic model, not a dict)
    assert blueprint.content_distribution.video == 0.35
    assert blueprint.total_duration_minutes == 134.0


def test_activity_blueprint_fields():
    """Verify ActivityBlueprint fields work correctly."""
    # Create activity with all fields
    activity = ActivityBlueprint(
        title="Test Activity",
        content_type="video",
        activity_type="video_lecture",
        wwhaa_phase="hook",
        bloom_level="understand",
        estimated_duration_minutes=8.0,
        description="A test activity for validation"
    )

    assert activity.title == "Test Activity"
    assert activity.content_type == "video"
    assert activity.wwhaa_phase == "hook"
    assert activity.bloom_level == "understand"
    assert activity.estimated_duration_minutes == 8.0

    # Test wwhaa_phase is optional (None for non-video activities)
    quiz_activity = ActivityBlueprint(
        title="Quiz",
        content_type="quiz",
        activity_type="graded_quiz",
        wwhaa_phase=None,  # No WWHAA for quizzes
        bloom_level="apply",
        estimated_duration_minutes=5.0,
        description="Test quiz"
    )

    assert quiz_activity.wwhaa_phase is None


def test_generate_blueprint(mocker):
    """Test generate() returns CourseBlueprint with mocked API."""
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_BLUEPRINT_DATA)
    mocker.patch('src.generators.blueprint_generator.Anthropic', return_value=mock_client)

    # Create generator and call generate
    generator = BlueprintGenerator(api_key="test-key")
    blueprint = generator.generate(
        course_description="Learn Python programming basics",
        learning_outcomes=["Write Python code", "Use data structures"],
        target_duration_minutes=120,
        audience_level="beginner"
    )

    # Verify result is a CourseBlueprint
    assert isinstance(blueprint, CourseBlueprint)
    assert len(blueprint.modules) == 2

    # Verify API was called
    mock_client.messages.create.assert_called_once()


def test_generate_blueprint_prompt_includes_description(mocker):
    """Verify course description appears in the user prompt."""
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_BLUEPRINT_DATA)
    mocker.patch('src.generators.blueprint_generator.Anthropic', return_value=mock_client)

    # Generate with specific description
    generator = BlueprintGenerator(api_key="test-key")
    generator.generate(
        course_description="Advanced Machine Learning Techniques",
        learning_outcomes=["Build neural networks"],
        target_duration_minutes=90,
        audience_level="advanced"
    )

    # Capture the call arguments
    call_args = mock_client.messages.create.call_args

    # Check messages parameter
    messages = call_args.kwargs['messages']
    user_message = messages[0]['content']

    # Verify description is in the prompt
    assert "Advanced Machine Learning Techniques" in user_message


def test_generate_blueprint_prompt_includes_outcomes(mocker):
    """Verify learning outcomes appear in the user prompt."""
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_BLUEPRINT_DATA)
    mocker.patch('src.generators.blueprint_generator.Anthropic', return_value=mock_client)

    # Generate with specific outcomes
    generator = BlueprintGenerator(api_key="test-key")
    generator.generate(
        course_description="Data Science Course",
        learning_outcomes=["Analyze datasets", "Build predictive models", "Visualize results"],
        target_duration_minutes=120,
        audience_level="intermediate"
    )

    # Capture the call arguments
    call_args = mock_client.messages.create.call_args
    messages = call_args.kwargs['messages']
    user_message = messages[0]['content']

    # Verify all outcomes are in the prompt
    assert "Analyze datasets" in user_message
    assert "Build predictive models" in user_message
    assert "Visualize results" in user_message


def test_generate_blueprint_uses_tools(mocker):
    """CRITICAL: Verify generate() uses tool-based structured output."""
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_BLUEPRINT_DATA)
    mocker.patch('src.generators.blueprint_generator.Anthropic', return_value=mock_client)

    # Generate blueprint
    generator = BlueprintGenerator(api_key="test-key")
    generator.generate(
        course_description="Test Course",
        learning_outcomes=["Learn something"],
        target_duration_minutes=60,
        audience_level="beginner"
    )

    # Capture the call arguments
    call_kwargs = mock_client.messages.create.call_args.kwargs

    # Check for tools parameter (blueprint generator uses tool-based output)
    assert 'tools' in call_kwargs, "Must use tools parameter for structured output"
    assert len(call_kwargs['tools']) == 1
    assert call_kwargs['tools'][0]['name'] == 'output_blueprint'

    # Check for tool_choice
    assert 'tool_choice' in call_kwargs

    # Ensure response_format is NOT used (OpenAI's convention, not Anthropic's)
    assert 'response_format' not in call_kwargs, "Must NOT use response_format (OpenAI API convention)"


def test_build_prompt_format():
    """Test _build_prompt() includes all required elements."""
    generator = BlueprintGenerator(api_key="test-key")

    prompt = generator._build_prompt(
        description="Web Development Fundamentals",
        outcomes=["Build HTML pages", "Style with CSS", "Add JavaScript interactivity"],
        duration=90,
        level="beginner"
    )

    # Verify course description appears
    assert "Web Development Fundamentals" in prompt

    # Verify audience level appears
    assert "beginner" in prompt

    # Verify target duration appears
    assert "90" in prompt

    # Verify outcomes are formatted as numbered list
    assert "1. Build HTML pages" in prompt
    assert "2. Style with CSS" in prompt
    assert "3. Add JavaScript interactivity" in prompt

    # Verify structure includes CONTEXT and TASK sections
    assert "CONTEXT:" in prompt
    assert "TASK:" in prompt
    assert "LEARNING OUTCOMES:" in prompt
