"""Tests for LabGenerator using TDD with mocked Anthropic API."""

import json
import pytest
from unittest.mock import Mock, MagicMock
from src.generators.lab_generator import LabGenerator
from src.generators.schemas.lab import LabSchema, SetupStep


# Sample lab data as dict
SAMPLE_LAB_DATA = {
    "title": "Introduction to Git Branching",
    "overview": "Learn to create, switch, and merge Git branches for parallel development workflows.",
    "learning_objectives": [
        "Create and switch between Git branches",
        "Merge branches and resolve conflicts",
        "Understand branch-based development workflows"
    ],
    "setup_instructions": [
        {
            "step_number": 1,
            "instruction": "Create a new directory called 'git-lab' and navigate into it",
            "expected_result": "You should see 'git-lab' as your current directory in the terminal"
        },
        {
            "step_number": 2,
            "instruction": "Initialize a new Git repository with 'git init'",
            "expected_result": "You should see the message 'Initialized empty Git repository in...'"
        },
        {
            "step_number": 3,
            "instruction": "Create a file called 'README.md' with some content and commit it",
            "expected_result": "Running 'git log' should show your first commit"
        }
    ],
    "lab_exercises": [
        "Create a new branch called 'feature-1' and switch to it",
        "Add a new file 'feature.txt' and commit it on the feature branch",
        "Switch back to main branch and create another file 'main.txt'",
        "Merge 'feature-1' branch into main and verify both files exist"
    ],
    "estimated_minutes": 45,
    "prerequisites": [
        "Git installed on your machine",
        "Basic command line knowledge"
    ]
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
    """Test that generate() returns a valid LabSchema instance."""
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_LAB_DATA)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    # Generate lab
    generator = LabGenerator()
    lab, metadata = generator.generate(
        schema=LabSchema,
        learning_objective="Master Git branching workflows",
        topic="Git Branching",
        difficulty="intermediate",
        estimated_minutes=45
    )

    # Verify it's a valid LabSchema
    assert isinstance(lab, LabSchema)
    assert lab.title == "Introduction to Git Branching"
    assert len(lab.setup_instructions) >= 3
    assert len(lab.lab_exercises) >= 3


def test_setup_steps_are_numbered(mocker):
    """Test that each SetupStep has sequential step_number."""
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_LAB_DATA)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    # Generate lab
    generator = LabGenerator()
    lab, _ = generator.generate(
        schema=LabSchema,
        learning_objective="Master Git branching workflows",
        topic="Git Branching"
    )

    # Verify steps are sequentially numbered starting from 1
    for i, step in enumerate(lab.setup_instructions, start=1):
        assert step.step_number == i, f"Step {i} has step_number {step.step_number}"


def test_system_prompt_mentions_ungraded():
    """Test that system prompt says ungraded/practice."""
    generator = LabGenerator()
    prompt = generator.system_prompt

    # Verify ungraded/practice language is present
    assert "ungraded" in prompt.lower() or "practice" in prompt.lower()
    assert "setup" in prompt.lower()


def test_build_user_prompt_includes_params():
    """Test that build_user_prompt includes learning_objective, topic, estimated_minutes."""
    generator = LabGenerator()

    prompt = generator.build_user_prompt(
        learning_objective="Master Git branching workflows",
        topic="Git Branching",
        difficulty="intermediate",
        estimated_minutes=45
    )

    # Verify key parameters are in prompt
    assert "Master Git branching workflows" in prompt or "Git branching" in prompt
    assert "Git Branching" in prompt or "Git branching" in prompt
    assert "45" in prompt or "forty-five" in prompt.lower()


def test_extract_metadata_uses_lab_duration(mocker):
    """Test that extract_metadata duration comes from content.estimated_minutes, not word count."""
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_LAB_DATA)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    # Generate lab
    generator = LabGenerator()
    lab, metadata = generator.generate(
        schema=LabSchema,
        learning_objective="Master Git branching workflows",
        topic="Git Branching"
    )

    # Verify duration comes from lab.estimated_minutes (45)
    assert metadata["estimated_duration_minutes"] == 45
    assert metadata["num_setup_steps"] == len(lab.setup_instructions)
    assert metadata["num_exercises"] == len(lab.lab_exercises)
    assert metadata["content_type"] == "lab"
    assert "word_count" in metadata


def test_api_called_with_tools(mocker):
    """Test that API is called with tools parameter for structured output."""
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_LAB_DATA)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    # Generate lab
    generator = LabGenerator()
    generator.generate(
        schema=LabSchema,
        learning_objective="Master Git branching workflows",
        topic="Git Branching",
        estimated_minutes=45
    )

    # Verify API was called with tools
    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args[1]
    assert "tools" in call_kwargs
    assert len(call_kwargs["tools"]) == 1
    assert call_kwargs["tools"][0]["name"] == "output_structured"
    assert "tool_choice" in call_kwargs
