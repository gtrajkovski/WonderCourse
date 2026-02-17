"""Tests for AI clients with mocked Anthropic API."""

import pytest
from unittest.mock import MagicMock

from src.ai.client import AIClient
from src.utils import ai_client as oneshot_client


# Fixtures

@pytest.fixture
def mock_anthropic(mocker):
    """Mock Anthropic API client to avoid real API calls."""
    mock_client = mocker.MagicMock()
    mock_response = mocker.MagicMock()
    mock_response.content = [mocker.MagicMock(text="AI response text")]
    mock_client.messages.create.return_value = mock_response
    mocker.patch("anthropic.Anthropic", return_value=mock_client)
    return mock_client


@pytest.fixture
def mock_anthropic_stream(mocker):
    """Mock Anthropic streaming API."""
    mock_client = mocker.MagicMock()

    # Create mock stream context manager
    mock_stream = mocker.MagicMock()
    mock_stream.text_stream = iter(["AI ", "response ", "text"])
    mock_stream.__enter__ = mocker.MagicMock(return_value=mock_stream)
    mock_stream.__exit__ = mocker.MagicMock(return_value=False)

    mock_client.messages.stream.return_value = mock_stream
    mocker.patch("anthropic.Anthropic", return_value=mock_client)
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


# Conversational AIClient Tests

def test_chat_returns_response(mock_anthropic, mock_config_with_api_key):
    """Test that chat() returns the AI response."""
    client = AIClient()
    response = client.chat("Hello AI")

    assert response == "AI response text"
    assert mock_anthropic.messages.create.called


def test_chat_accumulates_history(mock_anthropic, mock_config_with_api_key):
    """Test that chat() accumulates messages in conversation history."""
    client = AIClient()

    # First call
    client.chat("First message")
    assert len(client.conversation_history) == 2  # user + assistant
    assert client.conversation_history[0]["role"] == "user"
    assert client.conversation_history[0]["content"] == "First message"
    assert client.conversation_history[1]["role"] == "assistant"
    assert client.conversation_history[1]["content"] == "AI response text"

    # Second call
    client.chat("Second message")
    assert len(client.conversation_history) == 4  # 2 user + 2 assistant
    assert client.conversation_history[2]["role"] == "user"
    assert client.conversation_history[2]["content"] == "Second message"


def test_chat_sends_system_prompt(mock_anthropic, mock_config_with_api_key):
    """Test that chat() sends system prompt to API."""
    client = AIClient()
    custom_prompt = "You are a test assistant"
    client.chat("Test message", system_prompt=custom_prompt)

    call_args = mock_anthropic.messages.create.call_args
    assert call_args.kwargs["system"] == custom_prompt


def test_chat_uses_default_system_prompt(mock_anthropic, mock_config_with_api_key):
    """Test that chat() uses default system prompt when none provided."""
    client = AIClient()
    client.chat("Test message")

    call_args = mock_anthropic.messages.create.call_args
    assert "course authoring assistant" in call_args.kwargs["system"]


def test_generate_no_history_pollution(mock_anthropic, mock_config_with_api_key):
    """Test that generate() doesn't add to conversation history."""
    client = AIClient()

    # Call generate()
    response = client.generate("System prompt", "User prompt")

    # History should remain empty
    assert len(client.conversation_history) == 0
    assert response == "AI response text"


def test_generate_with_custom_max_tokens(mock_anthropic, mock_config_with_api_key):
    """Test that generate() accepts custom max_tokens."""
    client = AIClient()
    client.generate("System", "User", max_tokens=2000)

    call_args = mock_anthropic.messages.create.call_args
    assert call_args.kwargs["max_tokens"] == 2000


def test_clear_history(mock_anthropic, mock_config_with_api_key):
    """Test that clear_history() resets conversation history."""
    client = AIClient()

    # Build up history
    client.chat("Message 1")
    client.chat("Message 2")
    assert len(client.conversation_history) == 4

    # Clear history
    client.clear_history()
    assert len(client.conversation_history) == 0


def test_missing_api_key_raises(mock_config_no_api_key):
    """Test that missing API key raises ValueError."""
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY not set"):
        AIClient()


def test_chat_error_removes_user_message(mock_anthropic, mock_config_with_api_key):
    """Test that chat() removes user message from history on error."""
    client = AIClient()

    # Configure mock to raise error
    mock_anthropic.messages.create.side_effect = Exception("API error")

    # Attempt chat
    with pytest.raises(Exception):
        client.chat("Test message")

    # History should be empty (user message rolled back)
    assert len(client.conversation_history) == 0


def test_chat_stream_yields_chunks(mock_anthropic_stream, mock_config_with_api_key):
    """Test that chat_stream() yields text chunks."""
    client = AIClient()
    chunks = list(client.chat_stream("Test message"))

    assert chunks == ["AI ", "response ", "text"]


def test_chat_stream_accumulates_history(mock_anthropic_stream, mock_config_with_api_key):
    """Test that chat_stream() adds complete response to history."""
    client = AIClient()
    list(client.chat_stream("Test message"))  # Consume generator

    assert len(client.conversation_history) == 2
    assert client.conversation_history[0]["content"] == "Test message"
    assert client.conversation_history[1]["content"] == "AI response text"


# One-shot Client Tests

def test_oneshot_generate(mock_anthropic, mock_config_with_api_key):
    """Test that one-shot generate() returns response."""
    response = oneshot_client.generate("System prompt", "User prompt")

    assert response == "AI response text"
    assert mock_anthropic.messages.create.called


def test_oneshot_uses_temperature(mock_anthropic, mock_config_with_api_key):
    """Test that one-shot generate() uses temperature parameter."""
    oneshot_client.generate("System", "User", temperature=0.7)

    call_args = mock_anthropic.messages.create.call_args
    assert call_args.kwargs["temperature"] == 0.7


def test_oneshot_default_max_tokens(mock_anthropic, mock_config_with_api_key):
    """Test that one-shot generate() uses Config.MAX_TOKENS by default."""
    oneshot_client.generate("System", "User")

    call_args = mock_anthropic.messages.create.call_args
    assert call_args.kwargs["max_tokens"] == 4096  # From mock config


def test_oneshot_custom_max_tokens(mock_anthropic, mock_config_with_api_key):
    """Test that one-shot generate() accepts custom max_tokens."""
    oneshot_client.generate("System", "User", max_tokens=2000)

    call_args = mock_anthropic.messages.create.call_args
    assert call_args.kwargs["max_tokens"] == 2000


def test_oneshot_missing_api_key_raises(mock_config_no_api_key):
    """Test that one-shot generate() raises error on missing API key."""
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY not set"):
        oneshot_client.generate("System", "User")


def test_oneshot_uses_config_model(mock_anthropic, mock_config_with_api_key):
    """Test that one-shot generate() uses Config.MODEL."""
    oneshot_client.generate("System", "User")

    call_args = mock_anthropic.messages.create.call_args
    assert call_args.kwargs["model"] == "claude-sonnet-4-20250514"
