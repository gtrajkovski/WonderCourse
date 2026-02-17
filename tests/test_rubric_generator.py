"""Tests for RubricGenerator with mocked Anthropic API."""

import json
import pytest
from src.generators.rubric_generator import RubricGenerator
from src.generators.schemas.rubric import RubricSchema, RubricCriterion


# Sample rubric JSON for testing
SAMPLE_RUBRIC_JSON = """{
  "title": "Data Analysis Assignment Rubric",
  "criteria": [
    {
      "name": "Data Cleaning",
      "description": "Quality of data preprocessing and handling missing values",
      "below_expectations": "Data cleaning is incomplete or incorrect; missing values not addressed; inconsistencies remain",
      "meets_expectations": "Data is cleaned adequately; missing values handled appropriately; most inconsistencies resolved",
      "exceeds_expectations": "Comprehensive data cleaning with documentation; advanced techniques for missing values; all inconsistencies resolved with justification",
      "weight_percentage": 25
    },
    {
      "name": "Analysis Approach",
      "description": "Selection and application of appropriate analytical methods",
      "below_expectations": "Methods are inappropriate for the data or question; limited analysis depth",
      "meets_expectations": "Appropriate methods selected; analysis addresses the question adequately",
      "exceeds_expectations": "Sophisticated methods applied correctly; analysis is thorough and insightful; multiple approaches compared",
      "weight_percentage": 30
    },
    {
      "name": "Visualization Quality",
      "description": "Effectiveness and clarity of data visualizations",
      "below_expectations": "Visualizations are unclear, misleading, or poorly labeled",
      "meets_expectations": "Visualizations are clear, accurate, and properly labeled",
      "exceeds_expectations": "Visualizations are publication-quality; thoughtfully chosen for the data; enhance understanding significantly",
      "weight_percentage": 20
    },
    {
      "name": "Documentation and Communication",
      "description": "Quality of code documentation and written explanations",
      "below_expectations": "Code lacks documentation; explanations are unclear or missing",
      "meets_expectations": "Code is documented; explanations are clear and sufficient",
      "exceeds_expectations": "Comprehensive documentation; explanations are clear, detailed, and demonstrate deep understanding",
      "weight_percentage": 25
    }
  ],
  "total_points": 100,
  "learning_objective": "Students will analyze real-world datasets using Python to extract meaningful insights"
}"""


def test_generate_returns_valid_schema(mocker):
    """Test generate() returns RubricSchema with criteria present."""
    # Mock Anthropic client
    mock_client = mocker.MagicMock()
    mock_response = mocker.MagicMock()
    mock_tool_use = mocker.MagicMock()
    mock_tool_use.type = "tool_use"
    mock_tool_use.input = json.loads(SAMPLE_RUBRIC_JSON)
    mock_response.content = [mock_tool_use]
    mock_client.messages.create.return_value = mock_response
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    # Create generator and call generate
    generator = RubricGenerator(api_key="test-key")
    rubric, metadata = generator.generate(
        schema=RubricSchema,
        learning_objective="Analyze datasets with Python",
        activity_title="Data Analysis Assignment",
        activity_type="project",
        num_criteria=4,
        total_points=100
    )

    # Verify result is a RubricSchema
    assert isinstance(rubric, RubricSchema)
    assert len(rubric.criteria) == 4
    assert rubric.total_points == 100
    assert rubric.title == "Data Analysis Assignment Rubric"

    # Verify API was called
    mock_client.messages.create.assert_called_once()


def test_criteria_have_three_levels(mocker):
    """Verify each criterion has below/meets/exceeds text."""
    # Mock Anthropic client
    mock_client = mocker.MagicMock()
    mock_response = mocker.MagicMock()
    mock_tool_use = mocker.MagicMock()
    mock_tool_use.type = "tool_use"
    mock_tool_use.input = json.loads(SAMPLE_RUBRIC_JSON)
    mock_response.content = [mock_tool_use]
    mock_client.messages.create.return_value = mock_response
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    # Generate rubric
    generator = RubricGenerator(api_key="test-key")
    rubric, metadata = generator.generate(
        schema=RubricSchema,
        learning_objective="Analyze datasets",
        activity_title="Assignment",
        activity_type="project",
        num_criteria=4,
        total_points=100
    )

    # Check each criterion has all three levels with content
    for criterion in rubric.criteria:
        assert criterion.below_expectations
        assert criterion.meets_expectations
        assert criterion.exceeds_expectations
        assert len(criterion.below_expectations) > 10  # Substantive text
        assert len(criterion.meets_expectations) > 10
        assert len(criterion.exceeds_expectations) > 10


def test_system_prompt_contains_scoring_levels():
    """Verify system_prompt mentions Below/Meets/Exceeds Expectations."""
    generator = RubricGenerator(api_key="test-key")

    system_prompt = generator.system_prompt

    # Check for 3-level scoring mentions
    assert "Below" in system_prompt or "below" in system_prompt
    assert "Meets" in system_prompt or "meets" in system_prompt
    assert "Exceeds" in system_prompt or "exceeds" in system_prompt
    assert "Expectations" in system_prompt or "expectations" in system_prompt


def test_build_user_prompt_includes_activity_type(mocker):
    """Verify activity_type and num_criteria appear in user prompt."""
    # Mock Anthropic client
    mock_client = mocker.MagicMock()
    mock_response = mocker.MagicMock()
    mock_tool_use = mocker.MagicMock()
    mock_tool_use.type = "tool_use"
    mock_tool_use.input = json.loads(SAMPLE_RUBRIC_JSON)
    mock_response.content = [mock_tool_use]
    mock_client.messages.create.return_value = mock_response
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    # Generate with specific activity type
    generator = RubricGenerator(api_key="test-key")
    generator.generate(
        schema=RubricSchema,
        learning_objective="Build web applications",
        activity_title="Final Project",
        activity_type="capstone_project",
        num_criteria=5,
        total_points=150
    )

    # Capture the call arguments
    call_args = mock_client.messages.create.call_args
    messages = call_args.kwargs['messages']
    user_message = messages[0]['content']

    # Verify activity_type in prompt
    assert "capstone_project" in user_message

    # Verify num_criteria in prompt
    assert "5" in user_message

    # Verify total_points in prompt
    assert "150" in user_message


def test_extract_metadata_counts_criteria():
    """Test extract_metadata() counts total criteria correctly."""
    generator = RubricGenerator(api_key="test-key")

    # Create RubricSchema with 3 criteria
    rubric = RubricSchema(
        title="Test Rubric",
        criteria=[
            RubricCriterion(
                name="Criterion 1",
                description="First criterion",
                below_expectations="Below text",
                meets_expectations="Meets text",
                exceeds_expectations="Exceeds text",
                weight_percentage=40
            ),
            RubricCriterion(
                name="Criterion 2",
                description="Second criterion",
                below_expectations="Below text",
                meets_expectations="Meets text",
                exceeds_expectations="Exceeds text",
                weight_percentage=30
            ),
            RubricCriterion(
                name="Criterion 3",
                description="Third criterion",
                below_expectations="Below text",
                meets_expectations="Meets text",
                exceeds_expectations="Exceeds text",
                weight_percentage=30
            )
        ],
        total_points=100,
        learning_objective="Test objective"
    )

    metadata = generator.extract_metadata(rubric)

    # Verify total_criteria
    assert metadata["total_criteria"] == 3
    assert metadata["total_points"] == 100
    assert "word_count" in metadata


def test_extract_metadata_validates_weights():
    """Test extract_metadata() validates weights sum to 100."""
    generator = RubricGenerator(api_key="test-key")

    # Create rubric where weights sum to 100
    rubric = RubricSchema(
        title="Valid Weights Rubric",
        criteria=[
            RubricCriterion(
                name="Criterion 1",
                description="First",
                below_expectations="Below",
                meets_expectations="Meets",
                exceeds_expectations="Exceeds",
                weight_percentage=50
            ),
            RubricCriterion(
                name="Criterion 2",
                description="Second",
                below_expectations="Below",
                meets_expectations="Meets",
                exceeds_expectations="Exceeds",
                weight_percentage=50
            )
        ],
        total_points=100,
        learning_objective="Test"
    )

    metadata = generator.extract_metadata(rubric)

    # Weights sum to 100, should be valid
    assert metadata["weights_valid"] is True


def test_extract_metadata_detects_invalid_weights():
    """Test extract_metadata() detects when weights don't sum to 100."""
    generator = RubricGenerator(api_key="test-key")

    # Create rubric where weights sum to 90 (invalid)
    rubric = RubricSchema(
        title="Invalid Weights Rubric",
        criteria=[
            RubricCriterion(
                name="Criterion 1",
                description="First",
                below_expectations="Below",
                meets_expectations="Meets",
                exceeds_expectations="Exceeds",
                weight_percentage=40
            ),
            RubricCriterion(
                name="Criterion 2",
                description="Second",
                below_expectations="Below",
                meets_expectations="Meets",
                exceeds_expectations="Exceeds",
                weight_percentage=50
            )
        ],
        total_points=100,
        learning_objective="Test"
    )

    metadata = generator.extract_metadata(rubric)

    # Weights sum to 90, should be invalid
    assert metadata["weights_valid"] is False


def test_api_called_with_output_config(mocker):
    """CRITICAL: Verify generate() uses tools with tool_choice for structured output."""
    # Mock Anthropic client
    mock_client = mocker.MagicMock()
    mock_response = mocker.MagicMock()
    mock_tool_use = mocker.MagicMock()
    mock_tool_use.type = "tool_use"
    mock_tool_use.input = json.loads(SAMPLE_RUBRIC_JSON)
    mock_response.content = [mock_tool_use]
    mock_client.messages.create.return_value = mock_response
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    # Generate rubric
    generator = RubricGenerator(api_key="test-key")
    generator.generate(
        schema=RubricSchema,
        learning_objective="Test objective",
        activity_title="Test Activity",
        activity_type="assignment",
        num_criteria=4,
        total_points=100
    )

    # Capture the call arguments
    call_kwargs = mock_client.messages.create.call_args.kwargs

    # Verify tools parameter exists
    assert 'tools' in call_kwargs, "Must use tools parameter for structured output"
    assert len(call_kwargs['tools']) == 1
    assert call_kwargs['tools'][0]['name'] == 'output_structured'

    # Verify tool_choice forces tool use
    assert 'tool_choice' in call_kwargs
    assert call_kwargs['tool_choice']['type'] == 'tool'
    assert call_kwargs['tool_choice']['name'] == 'output_structured'

    # Ensure response_format is NOT used
    assert 'response_format' not in call_kwargs, "Must NOT use response_format (OpenAI API convention)"
