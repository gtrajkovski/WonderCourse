"""Tests for HOLGenerator using TDD with mocked Anthropic API."""

import json
import pytest
from unittest.mock import Mock, MagicMock
from src.generators.hol_generator import HOLGenerator
from src.generators.schemas.hol import HOLSchema, HOLPart, HOLRubricCriterion


# Sample HOL data as dict
SAMPLE_HOL_DATA = {
    "title": "Building a REST API with Flask",
    "scenario": "You are a backend developer tasked with creating a REST API for a task management application. The API needs to handle CRUD operations for tasks with proper error handling and validation.",
    "parts": [
        {
            "part_number": 1,
            "title": "Setup and Basic Route",
            "instructions": "1. Create a Flask application\n2. Implement GET /tasks endpoint that returns a list of tasks\n3. Add basic error handling for 404 errors",
            "estimated_minutes": 15
        },
        {
            "part_number": 2,
            "title": "CRUD Operations",
            "instructions": "1. Implement POST /tasks to create new tasks\n2. Implement PUT /tasks/<id> to update tasks\n3. Implement DELETE /tasks/<id> to delete tasks\n4. Add validation for required fields",
            "estimated_minutes": 25
        },
        {
            "part_number": 3,
            "title": "Advanced Features",
            "instructions": "1. Add filtering by status (?status=complete)\n2. Implement pagination (?page=1&limit=10)\n3. Add comprehensive error handling for all endpoints\n4. Write integration tests for all CRUD operations",
            "estimated_minutes": 20
        }
    ],
    "submission_criteria": "Submit your Python file (app.py) and a README documenting all endpoints with example curl commands. Include a screenshot of successful Postman tests for all CRUD operations.",
    "rubric": [
        {
            "name": "Implementation Quality",
            "advanced": "All CRUD operations work correctly with comprehensive error handling. Code is well-organized with proper separation of concerns. Uses Flask best practices (blueprints, error handlers).",
            "intermediate": "All CRUD operations work correctly with basic error handling. Code is functional but could benefit from better organization.",
            "beginner": "Some CRUD operations work, but several have bugs or missing error handling. Code structure needs improvement.",
            "points_advanced": 5,
            "points_intermediate": 4,
            "points_beginner": 2
        },
        {
            "name": "Technical Accuracy",
            "advanced": "Proper HTTP status codes, RESTful conventions followed, request/response handling is correct. Validation is robust.",
            "intermediate": "Mostly correct HTTP status codes and REST conventions. Minor validation issues.",
            "beginner": "Inconsistent HTTP status codes or REST conventions. Validation is minimal or incorrect.",
            "points_advanced": 5,
            "points_intermediate": 4,
            "points_beginner": 2
        },
        {
            "name": "Testing and Documentation",
            "advanced": "Comprehensive integration tests covering all endpoints. Clear documentation with examples. README is professional and complete.",
            "intermediate": "Basic tests covering main scenarios. Documentation is present but could be more detailed.",
            "beginner": "Minimal or missing tests. Documentation is incomplete or unclear.",
            "points_advanced": 5,
            "points_intermediate": 4,
            "points_beginner": 2
        }
    ],
    "learning_objective": "Students will be able to build RESTful APIs with Flask including CRUD operations, error handling, and validation."
}


def _mock_tool_response(mock_client, data):
    """Helper to create properly structured tool_use response mock."""
    mock_response = MagicMock()
    mock_tool_use = MagicMock()
    mock_tool_use.type = "tool_use"
    mock_tool_use.input = data if isinstance(data, dict) else json.loads(data)
    mock_response.content = [mock_tool_use]
    mock_client.messages.create.return_value = mock_response


def test_generate_returns_valid_schema(mocker):
    """Test that generate() returns a valid HOLSchema instance."""
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_HOL_DATA)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    # Generate HOL
    generator = HOLGenerator()
    hol, metadata = generator.generate(
        schema=HOLSchema,
        learning_objective="Build RESTful APIs with Flask",
        topic="Flask REST API",
        difficulty="intermediate"
    )

    # Verify it's a valid HOLSchema
    assert isinstance(hol, HOLSchema)
    assert hol.title == "Building a REST API with Flask"
    assert len(hol.parts) == 3
    assert len(hol.rubric) == 3


def test_rubric_uses_correct_scoring(mocker):
    """Test that rubric uses Advanced/Intermediate/Beginner (5/4/2), NOT Below/Meets/Exceeds."""
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_HOL_DATA)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    # Generate HOL
    generator = HOLGenerator()
    hol, _ = generator.generate(
        schema=HOLSchema,
        learning_objective="Build RESTful APIs with Flask",
        topic="Flask REST API",
        difficulty="intermediate"
    )

    # Verify rubric uses correct scoring model
    for criterion in hol.rubric:
        # Check field names are correct (advanced/intermediate/beginner)
        assert hasattr(criterion, 'advanced')
        assert hasattr(criterion, 'intermediate')
        assert hasattr(criterion, 'beginner')

        # Verify point values (5/4/2)
        assert criterion.points_advanced == 5
        assert criterion.points_intermediate == 4
        assert criterion.points_beginner == 2


def test_system_prompt_mentions_scoring():
    """Test that system prompt references skill-based rubric and standards configuration.

    v1.2.0: Rubric configuration is now dynamic via standards_rules, not hardcoded.
    """
    generator = HOLGenerator()
    prompt = generator.system_prompt

    # Verify skill-based rubric is referenced
    assert "skill-based rubric" in prompt.lower()
    # Verify that it mentions standards profile configuration
    assert "standards" in prompt.lower() or "profile" in prompt.lower()
    # Should mention performance levels (dynamically configured)
    assert "performance level" in prompt.lower()

    # Ensure it does NOT mention Below/Meets/Exceeds (wrong model)
    assert "meets expectations" not in prompt.lower()
    assert "exceeds expectations" not in prompt.lower()


def test_build_user_prompt_includes_params():
    """Test that build_user_prompt includes learning_objective, topic, difficulty."""
    generator = HOLGenerator()

    prompt = generator.build_user_prompt(
        learning_objective="Build RESTful APIs with Flask",
        topic="Flask REST API",
        difficulty="intermediate"
    )

    # Verify key parameters are in prompt
    assert "Build RESTful APIs with Flask" in prompt
    assert "Flask REST API" in prompt
    assert "intermediate" in prompt.lower()


def test_extract_metadata_calculates_duration(mocker):
    """Test that extract_metadata calculates duration as sum of part.estimated_minutes."""
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_HOL_DATA)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    # Generate HOL
    generator = HOLGenerator()
    hol, metadata = generator.generate(
        schema=HOLSchema,
        learning_objective="Build RESTful APIs with Flask",
        topic="Flask REST API",
        difficulty="intermediate"
    )

    # Verify metadata
    # Duration should be sum of part.estimated_minutes (15 + 25 + 20 = 60)
    assert metadata["estimated_duration_minutes"] == 60
    assert metadata["total_points"] == 15  # 3 criteria * 5 max points
    assert metadata["content_type"] == "hol"
    assert "word_count" in metadata


def test_api_called_with_tools(mocker):
    """Test that API is called with tools parameter for structured output."""
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_HOL_DATA)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    # Generate HOL
    generator = HOLGenerator()
    generator.generate(
        schema=HOLSchema,
        learning_objective="Build RESTful APIs with Flask",
        topic="Flask REST API",
        difficulty="intermediate"
    )

    # Verify API was called with tools
    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args[1]
    assert "tools" in call_kwargs
    assert len(call_kwargs["tools"]) == 1
    assert call_kwargs["tools"][0]["name"] == "output_structured"
    assert "tool_choice" in call_kwargs
