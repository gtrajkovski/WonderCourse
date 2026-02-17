"""Tests for ScreencastGenerator with mocked Anthropic API."""

import json
import pytest
from unittest.mock import MagicMock

from src.generators.screencast_generator import ScreencastGenerator
from src.generators.schemas.screencast import (
    ScreencastSchema, ScreencastScreen, ScreencastCommand,
    NarrationCue, ProgressBarDemo
)


# Sample valid ScreencastSchema JSON for mocking
SAMPLE_SCREENCAST_JSON = """{
  "title": "Introduction to Python Variables",
  "description": "A beginner-friendly demonstration of Python variable creation and usage",
  "learning_objective": "Create and use variables to store different types of data in Python",
  "default_typing_speed": "normal",
  "show_cursor": true,
  "intro_cue": {
    "title": "Welcome",
    "text": "In this screencast, we'll learn how to create and use variables in Python. Variables are the foundation of any program.",
    "duration": 5.0
  },
  "screens": [
    {
      "screen_number": 1,
      "title": "Creating Your First Variable",
      "narration_cue": {
        "title": "Variables 101",
        "text": "Let's start by creating a simple variable. We'll use the assignment operator to store a value.",
        "duration": 4.0
      },
      "prompt": ">>> ",
      "commands": [
        {
          "command": "name = 'Alice'",
          "output": [],
          "typing_speed": "slow",
          "pause_after": 1.0
        },
        {
          "command": "print(name)",
          "output": ["Alice"],
          "typing_speed": "normal",
          "pause_after": 1.5
        }
      ],
      "clear_screen": true
    },
    {
      "screen_number": 2,
      "title": "Numeric Variables",
      "narration_cue": {
        "title": "Numbers",
        "text": "Variables can store numbers too. Python automatically detects the type.",
        "duration": 3.0
      },
      "prompt": ">>> ",
      "commands": [
        {
          "command": "age = 25",
          "output": [],
          "typing_speed": "normal",
          "pause_after": 1.0
        },
        {
          "command": "price = 19.99",
          "output": [],
          "typing_speed": "normal",
          "pause_after": 1.0
        },
        {
          "command": "print(f'Age: {age}, Price: ${price}')",
          "output": ["Age: 25, Price: $19.99"],
          "typing_speed": "slow",
          "pause_after": 2.0
        }
      ],
      "clear_screen": true
    }
  ],
  "progress_demo": null,
  "outro_cue": {
    "title": "Summary",
    "text": "You've learned how to create variables for text and numbers. Variables are containers that store values you can use throughout your program.",
    "duration": 5.0
  },
  "state_variables": ["name", "age", "price"]
}"""


def _mock_tool_response(mock_client, json_str):
    """Helper to create properly structured tool_use response mock."""
    mock_response = MagicMock()
    mock_tool_use = MagicMock()
    mock_tool_use.type = "tool_use"
    mock_tool_use.input = json.loads(json_str)
    mock_response.content = [mock_tool_use]
    mock_client.messages.create.return_value = mock_response


def test_generate_returns_valid_schema(mocker):
    """Test that generate() returns a valid ScreencastSchema."""
    # Mock Anthropic client
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_SCREENCAST_JSON)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    generator = ScreencastGenerator()
    schema, metadata = generator.generate(
        schema=ScreencastSchema,
        learning_objective="Create and use variables in Python",
        topic="Python variables",
        audience_level="beginner"
    )

    # Verify it's a ScreencastSchema instance
    assert isinstance(schema, ScreencastSchema)
    assert schema.title == "Introduction to Python Variables"
    assert len(schema.screens) == 2
    assert schema.intro_cue.title == "Welcome"
    assert schema.outro_cue.title == "Summary"


def test_schema_to_python_generates_valid_code(mocker):
    """Test that schema_to_python generates executable Python code."""
    # Mock Anthropic client
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_SCREENCAST_JSON)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    generator = ScreencastGenerator()
    schema, _ = generator.generate(
        schema=ScreencastSchema,
        learning_objective="Create variables",
        topic="Python"
    )

    # Convert to Python code
    python_code = generator.schema_to_python(schema)

    # Verify code structure
    assert '"""' in python_code  # Docstring
    assert 'import sys' in python_code
    assert 'import time' in python_code
    assert 'def clear_screen():' in python_code
    assert 'def type_text(' in python_code
    assert 'def show_cue_card(' in python_code
    assert 'def run_screencast():' in python_code
    assert 'if __name__ == "__main__":' in python_code

    # Verify content is included
    assert 'Introduction to Python Variables' in python_code
    assert 'Variables 101' in python_code
    assert "name = 'Alice'" in python_code


def test_generate_screencast_returns_python_code(mocker):
    """Test that generate_screencast returns Python code and metadata."""
    # Mock Anthropic client
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_SCREENCAST_JSON)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    generator = ScreencastGenerator()
    python_code, metadata = generator.generate_screencast(
        learning_objective="Create variables",
        topic="Python variables",
        audience_level="beginner",
        duration_minutes=3
    )

    # Verify Python code is returned
    assert isinstance(python_code, str)
    assert 'def run_screencast():' in python_code

    # Verify metadata
    assert metadata["content_type"] == "screencast"
    assert metadata["num_screens"] == 2
    assert metadata["num_commands"] == 5  # 2 + 3 commands
    assert "code_lines" in metadata
    assert "code_chars" in metadata


def test_extract_metadata_counts_correctly(mocker):
    """Test that extract_metadata calculates correct counts."""
    # Mock Anthropic client
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_SCREENCAST_JSON)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    generator = ScreencastGenerator()
    schema, metadata = generator.generate(
        schema=ScreencastSchema,
        learning_objective="Create variables",
        topic="Python"
    )

    # Verify metadata structure
    assert metadata["content_type"] == "screencast"
    assert metadata["num_screens"] == 2
    assert metadata["num_commands"] == 5
    assert metadata["has_progress_demo"] is False
    assert "estimated_duration_minutes" in metadata
    assert "narration_word_count" in metadata


def test_system_prompt_contains_guidelines():
    """Test that system prompt contains screencast-specific guidelines."""
    generator = ScreencastGenerator()
    prompt = generator.system_prompt

    # Check for key elements
    assert "screencast" in prompt.lower()
    assert "terminal" in prompt.lower()
    assert "typing" in prompt.lower()
    assert "cue" in prompt.lower()


def test_build_user_prompt_includes_params(mocker):
    """Test that build_user_prompt includes all parameters."""
    mock_client = MagicMock()
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    generator = ScreencastGenerator()
    prompt = generator.build_user_prompt(
        learning_objective="Install packages with pip",
        topic="Python package management",
        audience_level="intermediate",
        duration_minutes=5,
        programming_language="python",
        environment="terminal"
    )

    # Verify parameters appear in prompt
    assert "Install packages with pip" in prompt
    assert "Python package management" in prompt
    assert "intermediate" in prompt
    assert "5" in prompt
    assert "python" in prompt
    assert "terminal" in prompt


def test_api_called_with_tools(mocker):
    """Test that API is called with tools parameter for structured output."""
    # Mock Anthropic client
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_SCREENCAST_JSON)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    generator = ScreencastGenerator()
    generator.generate(
        schema=ScreencastSchema,
        learning_objective="Test",
        topic="Test"
    )

    # Verify API was called with tools
    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args[1]
    assert "tools" in call_kwargs
    assert len(call_kwargs["tools"]) == 1
    assert call_kwargs["tools"][0]["name"] == "output_structured"
    assert "tool_choice" in call_kwargs


def test_screencast_with_progress_bar(mocker):
    """Test screencast generation with progress bar demo."""
    json_with_progress = SAMPLE_SCREENCAST_JSON.replace(
        '"progress_demo": null',
        '''"progress_demo": {
            "label": "Installing packages",
            "steps": 10,
            "step_delay": 0.2,
            "color": "green"
        }'''
    )

    # Mock Anthropic client
    mock_client = MagicMock()
    _mock_tool_response(mock_client, json_with_progress)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    generator = ScreencastGenerator()
    python_code, metadata = generator.generate_screencast(
        learning_objective="Install packages",
        topic="pip"
    )

    # Verify progress bar code is included
    assert 'def show_progress_bar(' in python_code
    assert 'Installing packages' in python_code
    assert metadata["has_progress_demo"] is True
