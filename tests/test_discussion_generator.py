"""Tests for DiscussionGenerator using TDD with mocked Anthropic API."""

import json
import pytest
from unittest.mock import Mock, MagicMock
from src.generators.discussion_generator import DiscussionGenerator
from src.generators.schemas.discussion import DiscussionSchema


# Sample discussion data as dict
SAMPLE_DISCUSSION_DATA = {
    "title": "The Ethics of AI in Healthcare",
    "main_prompt": "As AI systems become more prevalent in healthcare decision-making, what ethical considerations should guide their development and deployment? Consider issues of bias, transparency, accountability, and patient autonomy.",
    "facilitation_questions": [
        "How might algorithmic bias in training data affect patient outcomes across different demographics?",
        "What level of transparency should patients expect when AI is involved in their diagnosis or treatment?",
        "Who should be held accountable when an AI system makes an error that harms a patient?"
    ],
    "engagement_hooks": [
        "Recent studies show AI diagnostic tools have 15% lower accuracy for certain ethnic groups - how does this impact trust in healthcare?",
        "Would you want to know if an AI was involved in your medical diagnosis? Why or why not?"
    ],
    "connection_to_objective": "This discussion advances the learning objective by encouraging critical analysis of AI ethics through real-world healthcare scenarios, promoting evaluation of competing values (accuracy vs. fairness, efficiency vs. transparency).",
    "learning_objective": "Students will evaluate ethical implications of AI systems in professional contexts."
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
    """Test that generate() returns a valid DiscussionSchema instance."""
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_DISCUSSION_DATA)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    # Generate discussion
    generator = DiscussionGenerator()
    discussion, metadata = generator.generate(
        schema=DiscussionSchema,
        learning_objective="Evaluate ethical implications of AI systems",
        topic="AI Ethics in Healthcare",
        difficulty="intermediate"
    )

    # Verify it's a valid DiscussionSchema
    assert isinstance(discussion, DiscussionSchema)
    assert discussion.title == "The Ethics of AI in Healthcare"
    assert len(discussion.facilitation_questions) >= 3
    assert len(discussion.engagement_hooks) >= 2
    assert discussion.connection_to_objective
    assert discussion.learning_objective


def test_has_facilitation_questions(mocker):
    """Test that generated discussion has at least 3 facilitation questions."""
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_DISCUSSION_DATA)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    # Generate discussion
    generator = DiscussionGenerator()
    discussion, _ = generator.generate(
        schema=DiscussionSchema,
        learning_objective="Evaluate ethical implications of AI systems",
        topic="AI Ethics in Healthcare",
        difficulty="intermediate"
    )

    # Verify at least 3 facilitation questions
    assert len(discussion.facilitation_questions) >= 3
    # Verify they're substantive (not just empty strings)
    for question in discussion.facilitation_questions:
        assert len(question.strip()) > 20, "Facilitation questions should be substantive"


def test_has_engagement_hooks(mocker):
    """Test that generated discussion has at least 2 engagement hooks."""
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_DISCUSSION_DATA)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    # Generate discussion
    generator = DiscussionGenerator()
    discussion, _ = generator.generate(
        schema=DiscussionSchema,
        learning_objective="Evaluate ethical implications of AI systems",
        topic="AI Ethics in Healthcare",
        difficulty="intermediate"
    )

    # Verify at least 2 engagement hooks
    assert len(discussion.engagement_hooks) >= 2
    # Verify they're substantive
    for hook in discussion.engagement_hooks:
        assert len(hook.strip()) > 20, "Engagement hooks should be substantive"


def test_system_prompt_mentions_peer_learning():
    """Test that system prompt references peer interaction/learning."""
    generator = DiscussionGenerator()
    prompt = generator.system_prompt

    # Verify peer learning concepts are present
    peer_learning_keywords = ["peer", "interaction", "dialogue", "conversation", "collaborative"]
    assert any(keyword in prompt.lower() for keyword in peer_learning_keywords), \
        "System prompt should reference peer learning or interaction"


def test_build_user_prompt_includes_params():
    """Test that build_user_prompt includes learning_objective and topic."""
    generator = DiscussionGenerator()

    prompt = generator.build_user_prompt(
        learning_objective="Evaluate ethical implications of AI systems",
        topic="AI Ethics in Healthcare",
        difficulty="intermediate"
    )

    # Verify key parameters are in prompt
    assert "Evaluate ethical implications of AI systems" in prompt
    assert "AI Ethics in Healthcare" in prompt
    assert "intermediate" in prompt.lower()


def test_extract_metadata_counts_correctly(mocker):
    """Test that extract_metadata counts match list lengths."""
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_DISCUSSION_DATA)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    # Generate discussion
    generator = DiscussionGenerator()
    discussion, metadata = generator.generate(
        schema=DiscussionSchema,
        learning_objective="Evaluate ethical implications of AI systems",
        topic="AI Ethics in Healthcare",
        difficulty="intermediate"
    )

    # Verify metadata counts
    assert metadata["num_facilitation_questions"] == len(discussion.facilitation_questions)
    assert metadata["num_engagement_hooks"] == len(discussion.engagement_hooks)
    assert metadata["content_type"] == "discussion"
    assert "word_count" in metadata
    assert metadata["word_count"] > 0
