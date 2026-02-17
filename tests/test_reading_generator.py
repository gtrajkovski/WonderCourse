"""Tests for ReadingGenerator with mocked Anthropic API."""

import json
import pytest
from unittest.mock import Mock, MagicMock
from src.generators.reading_generator import ReadingGenerator
from src.generators.schemas.reading import ReadingSchema, ReadingSection, Reference


# Sample valid reading response as dict
SAMPLE_READING_DATA = {
    "title": "Introduction to Machine Learning",
    "introduction": "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed. This reading explores fundamental concepts.",
    "sections": [
        {
            "heading": "Types of Machine Learning",
            "body": "There are three main types of machine learning: supervised learning, unsupervised learning, and reinforcement learning. Each type has distinct characteristics and use cases."
        },
        {
            "heading": "Applications",
            "body": "Machine learning powers many modern applications including recommendation systems, image recognition, natural language processing, and autonomous vehicles."
        }
    ],
    "conclusion": "Understanding machine learning fundamentals is essential for anyone working with modern data-driven systems. These concepts form the foundation for more advanced AI topics.",
    "references": [
        {
            "citation": "Russell, S., & Norvig, P. (2020). Artificial Intelligence: A Modern Approach (4th ed.). Pearson.",
            "url": "https://example.com"
        }
    ],
    "learning_objective": "Understand the basic concepts of machine learning"
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
    """Test that generate() returns a valid ReadingSchema instance."""
    # Mock Anthropic client
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_READING_DATA)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    # Generate reading
    generator = ReadingGenerator()
    reading, metadata = generator.generate(
        schema=ReadingSchema,
        learning_objective="Understand ML basics",
        topic="Machine Learning",
        audience_level="beginner"
    )

    # Assertions
    assert isinstance(reading, ReadingSchema)
    assert reading.title == "Introduction to Machine Learning"
    assert len(reading.sections) == 2
    assert len(reading.references) == 1
    assert reading.learning_objective == "Understand the basic concepts of machine learning"


def test_system_prompt_contains_apa7(mocker):
    """Test that system prompt includes APA 7 citation format guidance."""
    mock_client = MagicMock()
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    generator = ReadingGenerator()
    system_prompt = generator.system_prompt

    # Check for APA 7 reference
    assert "APA 7" in system_prompt or "APA-7" in system_prompt
    # Check for role definition
    assert "educational" in system_prompt.lower() or "expert" in system_prompt.lower()


def test_build_user_prompt_includes_max_words(mocker):
    """Test that build_user_prompt includes max_words parameter."""
    mock_client = MagicMock()
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    generator = ReadingGenerator()

    user_prompt = generator.build_user_prompt(
        learning_objective="Test objective",
        topic="Test topic",
        audience_level="intermediate",
        max_words=1500
    )

    # Check that max_words is mentioned
    assert "1500" in user_prompt or "1,500" in user_prompt
    assert "learning_objective" in user_prompt.lower() or "test objective" in user_prompt.lower()
    assert "test topic" in user_prompt.lower()


def test_extract_metadata_calculates_correctly(mocker):
    """Test that extract_metadata calculates word count and duration correctly."""
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_READING_DATA)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    generator = ReadingGenerator()
    reading, metadata = generator.generate(
        schema=ReadingSchema,
        learning_objective="Test",
        topic="Test",
        audience_level="beginner"
    )

    # Check metadata structure
    assert "word_count" in metadata
    assert "estimated_duration_minutes" in metadata
    assert "content_type" in metadata
    assert metadata["content_type"] == "reading"

    # Check that word count is positive
    assert metadata["word_count"] > 0
    assert metadata["estimated_duration_minutes"] > 0


def test_metadata_duration_uses_238_wpm(mocker):
    """Test that duration calculation uses 238 WPM reading rate."""
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_READING_DATA)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    generator = ReadingGenerator()
    reading, metadata = generator.generate(
        schema=ReadingSchema,
        learning_objective="Test",
        topic="Test",
        audience_level="beginner"
    )

    # Calculate expected duration manually
    expected_duration = round(metadata["word_count"] / 238, 1)

    assert metadata["estimated_duration_minutes"] == expected_duration


def test_api_called_with_tools(mocker):
    """Test that API is called with tools parameter for structured output."""
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_READING_DATA)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    generator = ReadingGenerator()
    generator.generate(
        schema=ReadingSchema,
        learning_objective="Test",
        topic="Test",
        audience_level="beginner"
    )

    # Verify API was called with tools
    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args[1]

    assert "tools" in call_kwargs
    assert len(call_kwargs["tools"]) == 1
    assert call_kwargs["tools"][0]["name"] == "output_structured"
    assert "tool_choice" in call_kwargs


def test_metadata_includes_section_and_reference_counts(mocker):
    """Test that metadata includes section_count and reference_count."""
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_READING_DATA)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    generator = ReadingGenerator()
    reading, metadata = generator.generate(
        schema=ReadingSchema,
        learning_objective="Test",
        topic="Test",
        audience_level="beginner"
    )

    assert "section_count" in metadata
    assert "reference_count" in metadata
    assert metadata["section_count"] == 2
    assert metadata["reference_count"] == 1
