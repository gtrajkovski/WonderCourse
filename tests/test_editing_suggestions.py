"""Tests for AI editing suggestions with mocked Anthropic API."""

import pytest
from unittest.mock import MagicMock

from src.editing.suggestions import SuggestionEngine, Suggestion
from src.editing.diff_generator import DiffGenerator, DiffResult


# Fixtures

@pytest.fixture
def mock_anthropic(mocker):
    """Mock Anthropic API client to avoid real API calls."""
    mock_client = mocker.MagicMock()
    mock_response = mocker.MagicMock()

    # Mock response format: SUGGESTION:\n...\n\nEXPLANATION:\n...
    mock_response.content = [mocker.MagicMock(
        text="SUGGESTION:\nImproved version of the text.\n\nEXPLANATION:\nEnhanced clarity and flow."
    )]

    mock_client.messages.create.return_value = mock_response
    mocker.patch("src.editing.suggestions.Anthropic", return_value=mock_client)
    return mock_client


@pytest.fixture
def mock_anthropic_stream(mocker):
    """Mock Anthropic streaming API."""
    mock_client = mocker.MagicMock()

    # Create mock stream context manager
    mock_stream = mocker.MagicMock()
    mock_stream.text_stream = iter([
        "SUGGESTION:\n",
        "Improved ",
        "version ",
        "of the text.\n\n",
        "EXPLANATION:\n",
        "Enhanced clarity."
    ])
    mock_stream.__enter__ = mocker.MagicMock(return_value=mock_stream)
    mock_stream.__exit__ = mocker.MagicMock(return_value=False)

    mock_client.messages.stream.return_value = mock_stream
    mocker.patch("src.editing.suggestions.Anthropic", return_value=mock_client)
    return mock_client


@pytest.fixture
def mock_config_with_api_key(mocker):
    """Mock Config with API key set."""
    mocker.patch("src.config.Config.ANTHROPIC_API_KEY", "test-api-key")
    mocker.patch("src.config.Config.MODEL", "claude-sonnet-4-20250514")
    mocker.patch("src.config.Config.MAX_TOKENS", 4096)


@pytest.fixture
def mock_config_no_api_key(mocker):
    """Mock Config with no API key."""
    mocker.patch("src.config.Config.ANTHROPIC_API_KEY", None)


# DiffGenerator Tests

def test_diff_generator_unified_diff():
    """Test unified diff generation."""
    generator = DiffGenerator()
    original = "Hello world\nThis is a test"
    modified = "Hello world\nThis is a better test"

    result = generator.generate_diff(original, modified)

    assert result.original == original
    assert result.modified == modified
    assert "better" in result.unified_diff
    assert isinstance(result.unified_diff, str)


def test_diff_generator_html_diff():
    """Test HTML diff generation."""
    generator = DiffGenerator()
    original = "Hello world"
    modified = "Hello beautiful world"

    result = generator.generate_diff(original, modified)

    assert "<table" in result.html_diff
    assert isinstance(result.html_diff, str)


def test_diff_generator_changes():
    """Test structured changes list generation."""
    generator = DiffGenerator()
    original = "Line 1\nLine 2\nLine 3"
    modified = "Line 1\nModified Line 2\nLine 3"

    result = generator.generate_diff(original, modified)

    assert isinstance(result.changes, list)
    assert len(result.changes) == 1
    assert result.changes[0]['type'] == 'replace'


def test_diff_generator_inline_diff():
    """Test inline diff with <ins> and <del> tags."""
    generator = DiffGenerator()
    original = "This is old text"
    modified = "This is new text"

    inline_diff = generator.generate_inline_diff(original, modified)

    assert "<del>" in inline_diff
    assert "<ins>" in inline_diff
    assert "old" in inline_diff or "new" in inline_diff


# SuggestionEngine Tests

def test_suggestion_engine_improve_action(mock_anthropic, mock_config_with_api_key):
    """Test improve action generates suggestion."""
    engine = SuggestionEngine()
    text = "This is text that needs improvement."

    suggestion = engine.suggest(text, "improve")

    assert isinstance(suggestion, Suggestion)
    assert suggestion.original == text
    assert suggestion.action == "improve"
    assert len(suggestion.suggestion) > 0
    assert len(suggestion.explanation) > 0
    assert mock_anthropic.messages.create.called


def test_suggestion_engine_expand_action(mock_anthropic, mock_config_with_api_key):
    """Test expand action adds detail."""
    engine = SuggestionEngine()
    text = "This is brief."

    suggestion = engine.suggest(text, "expand")

    assert suggestion.action == "expand"
    assert mock_anthropic.messages.create.called


def test_suggestion_engine_simplify_action(mock_anthropic, mock_config_with_api_key):
    """Test simplify action reduces complexity."""
    engine = SuggestionEngine()
    text = "This is unnecessarily verbose and complex text."

    suggestion = engine.suggest(text, "simplify")

    assert suggestion.action == "simplify"
    assert mock_anthropic.messages.create.called


def test_suggestion_engine_rewrite_action(mock_anthropic, mock_config_with_api_key):
    """Test rewrite action completely rewrites text."""
    engine = SuggestionEngine()
    text = "Original text."

    suggestion = engine.suggest(text, "rewrite")

    assert suggestion.action == "rewrite"
    assert mock_anthropic.messages.create.called


def test_suggestion_engine_fix_grammar_action(mock_anthropic, mock_config_with_api_key):
    """Test fix_grammar action fixes errors."""
    engine = SuggestionEngine()
    text = "This have bad grammar."

    suggestion = engine.suggest(text, "fix_grammar")

    assert suggestion.action == "fix_grammar"
    assert mock_anthropic.messages.create.called


def test_suggestion_engine_make_academic_action(mock_anthropic, mock_config_with_api_key):
    """Test make_academic action formalizes tone."""
    engine = SuggestionEngine()
    text = "This is pretty cool stuff."

    suggestion = engine.suggest(text, "make_academic")

    assert suggestion.action == "make_academic"
    assert mock_anthropic.messages.create.called


def test_suggestion_engine_make_conversational_action(mock_anthropic, mock_config_with_api_key):
    """Test make_conversational action casualizes tone."""
    engine = SuggestionEngine()
    text = "This constitutes an examination of the subject matter."

    suggestion = engine.suggest(text, "make_conversational")

    assert suggestion.action == "make_conversational"
    assert mock_anthropic.messages.create.called


def test_suggestion_engine_summarize_action(mock_anthropic, mock_config_with_api_key):
    """Test summarize action condenses text."""
    engine = SuggestionEngine()
    text = "This is a long piece of text with many details that could be condensed."

    suggestion = engine.suggest(text, "summarize")

    assert suggestion.action == "summarize"
    assert mock_anthropic.messages.create.called


def test_suggestion_engine_add_examples_action(mock_anthropic, mock_config_with_api_key):
    """Test add_examples action inserts examples."""
    engine = SuggestionEngine()
    text = "This concept is important."

    suggestion = engine.suggest(text, "add_examples")

    assert suggestion.action == "add_examples"
    assert mock_anthropic.messages.create.called


def test_suggestion_engine_custom_action_with_prompt(mock_anthropic, mock_config_with_api_key):
    """Test custom action with custom prompt."""
    engine = SuggestionEngine()
    text = "This is text."
    context = {"prompt": "Make this sound like a pirate."}

    suggestion = engine.suggest(text, "custom", context)

    assert suggestion.action == "custom"
    assert mock_anthropic.messages.create.called


def test_suggestion_engine_custom_action_requires_prompt(mock_anthropic, mock_config_with_api_key):
    """Test custom action without prompt raises error."""
    engine = SuggestionEngine()
    text = "This is text."

    # Custom action without prompt should raise ValueError
    with pytest.raises(ValueError, match="Custom action requires 'prompt' in context"):
        suggestion = engine.suggest(text, "custom", {})


def test_suggestion_engine_invalid_action_raises_error(mock_anthropic, mock_config_with_api_key):
    """Test invalid action type raises ValueError."""
    engine = SuggestionEngine()
    text = "This is text."

    with pytest.raises(ValueError, match="Invalid action type"):
        engine.suggest(text, "invalid_action")


def test_suggestion_engine_context_with_learning_outcomes(mock_anthropic, mock_config_with_api_key):
    """Test context with learning outcomes affects prompt."""
    engine = SuggestionEngine()
    text = "This is educational content."
    context = {
        "learning_outcomes": [
            "Understand machine learning basics",
            "Apply neural networks"
        ]
    }

    suggestion = engine.suggest(text, "improve", context)

    assert mock_anthropic.messages.create.called
    # Check that system prompt included learning outcomes
    call_args = mock_anthropic.messages.create.call_args
    system_prompt = call_args.kwargs.get('system', '')
    assert "learning outcomes" in system_prompt.lower() or "Learning outcomes" in system_prompt


def test_suggestion_engine_context_with_bloom_level(mock_anthropic, mock_config_with_api_key):
    """Test context with Bloom level affects prompt."""
    engine = SuggestionEngine()
    text = "This is educational content."
    context = {"bloom_level": "analyze"}

    suggestion = engine.suggest(text, "improve", context)

    assert mock_anthropic.messages.create.called
    call_args = mock_anthropic.messages.create.call_args
    system_prompt = call_args.kwargs.get('system', '')
    assert "analyze" in system_prompt.lower()


def test_suggestion_engine_context_with_content_type(mock_anthropic, mock_config_with_api_key):
    """Test context with content type affects prompt."""
    engine = SuggestionEngine()
    text = "This is content."
    context = {"content_type": "video_script"}

    suggestion = engine.suggest(text, "improve", context)

    assert mock_anthropic.messages.create.called
    call_args = mock_anthropic.messages.create.call_args
    system_prompt = call_args.kwargs.get('system', '')
    assert "video_script" in system_prompt


def test_suggestion_engine_stream_suggest(mock_anthropic_stream, mock_config_with_api_key):
    """Test streaming suggestion generation."""
    engine = SuggestionEngine()
    text = "This is text to improve."

    chunks = list(engine.stream_suggest(text, "improve"))

    assert len(chunks) > 0
    assert mock_anthropic_stream.messages.stream.called


def test_suggestion_engine_get_available_actions(mock_config_with_api_key, mocker):
    """Test getting list of available actions."""
    mocker.patch("anthropic.Anthropic")
    engine = SuggestionEngine()

    actions = engine.get_available_actions()

    assert isinstance(actions, list)
    assert len(actions) == 10  # We have 10 action types
    assert all('action' in a and 'description' in a for a in actions)

    # Check specific actions exist
    action_names = [a['action'] for a in actions]
    assert 'improve' in action_names
    assert 'expand' in action_names
    assert 'simplify' in action_names
    assert 'custom' in action_names


def test_suggestion_includes_diff(mock_anthropic, mock_config_with_api_key):
    """Test suggestion includes diff result."""
    engine = SuggestionEngine()
    text = "Original text."

    suggestion = engine.suggest(text, "improve")

    assert isinstance(suggestion.diff, DiffResult)
    assert suggestion.diff.original == text
    assert len(suggestion.diff.unified_diff) > 0


def test_no_api_key_raises_error(mocker):
    """Test that missing API key raises ValueError."""
    # Patch at both the source and the import location to handle caching
    mocker.patch("src.config.Config.ANTHROPIC_API_KEY", None)
    mocker.patch("src.editing.suggestions.Config.ANTHROPIC_API_KEY", None)

    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY not set"):
        SuggestionEngine()
