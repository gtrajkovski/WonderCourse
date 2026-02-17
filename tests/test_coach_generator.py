"""Tests for CoachGenerator using TDD with mocked Anthropic API."""

import json
import pytest
from unittest.mock import Mock, MagicMock
from src.generators.coach_generator import CoachGenerator
from src.generators.schemas.coach import CoachSchema, ConversationStarter, SampleResponse


@pytest.fixture
def mock_anthropic_client(mocker):
    """Mock Anthropic client to avoid real API calls."""
    mock_client = MagicMock()
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)
    return mock_client


def _mock_tool_response(mock_client, json_str):
    """Helper to create properly structured tool_use response mock."""
    mock_response = Mock()
    mock_tool_use = Mock()
    mock_tool_use.type = "tool_use"
    mock_tool_use.input = json.loads(json_str)
    mock_response.content = [mock_tool_use]
    mock_client.messages.create.return_value = mock_response


@pytest.fixture
def sample_coach_json():
    """Sample coach dialogue JSON response from API with all 8 sections."""
    return '''{
        "title": "Coaching Dialogue: Agile Sprint Planning",
        "learning_objectives": [
            "Understand the purpose and structure of sprint planning",
            "Identify key artifacts needed for effective sprint planning",
            "Apply story point estimation techniques"
        ],
        "scenario": "You are a Scrum Master facilitating your team's first sprint planning meeting. The product owner has presented the prioritized backlog, and your team needs to commit to a realistic sprint goal and select items they can complete in the next two weeks.",
        "tasks": [
            "Review the product backlog and identify dependencies",
            "Facilitate story point estimation using planning poker",
            "Help the team establish a sprint goal",
            "Ensure the team commits to a sustainable workload"
        ],
        "conversation_starters": [
            {
                "starter_text": "What information do you need from the product owner before your team can commit to a sprint goal?",
                "purpose": "Elicits understanding of sprint planning inputs and prerequisites"
            },
            {
                "starter_text": "How would you handle a situation where team members have very different story point estimates?",
                "purpose": "Assesses conflict resolution and facilitation skills"
            },
            {
                "starter_text": "What factors should your team consider when determining how many story points to commit to?",
                "purpose": "Evaluates capacity planning and risk awareness"
            }
        ],
        "sample_responses": [
            {
                "response_text": "We need the product owner to explain each user story's acceptance criteria, show us the designs if available, and clarify any dependencies. We should also review our team's velocity from past sprints and account for any planned time off.",
                "evaluation_level": "exceeds",
                "feedback": "Excellent! You've identified multiple critical inputs: acceptance criteria for clarity, designs for implementation guidance, dependencies for risk management, and historical velocity with capacity adjustments. This comprehensive approach sets your team up for realistic commitments."
            },
            {
                "response_text": "We should ask the product owner to explain the requirements and check what we completed last sprint.",
                "evaluation_level": "meets",
                "feedback": "Good start. You've identified the need for requirement clarification and considering past performance. To strengthen your approach, also consider team capacity changes, dependencies between stories, and ensuring everyone understands the acceptance criteria."
            },
            {
                "response_text": "Just pick the top items from the backlog and start working.",
                "evaluation_level": "needs_improvement",
                "feedback": "This approach skips essential planning steps. Without understanding requirements, assessing capacity, or checking dependencies, your team risks overcommitting or encountering blockers. Sprint planning requires collaborative discussion to ensure shared understanding and realistic commitments."
            }
        ],
        "evaluation_criteria": [
            "Demonstrates understanding of sprint planning inputs and artifacts",
            "Shows ability to facilitate collaborative estimation and discussion",
            "Considers team capacity and sustainability",
            "Identifies and addresses dependencies and risks"
        ],
        "wrap_up": "Effective sprint planning balances ambition with realism. By ensuring your team has clear requirements, collaborative estimates, and a shared understanding of capacity and risks, you set the foundation for a successful sprint. Remember that the sprint goal should be achievable yet meaningful, and the team should feel ownership of their commitment.",
        "reflection_prompts": [
            "How would you adjust your facilitation approach if team members seem reluctant to commit to the sprint goal?",
            "What signs during sprint planning might indicate your team is overcommitting?",
            "How can you use sprint planning to improve team collaboration and shared understanding?"
        ]
    }'''


def test_generate_returns_valid_schema(mock_anthropic_client, sample_coach_json):
    """Test that generate() returns a valid CoachSchema instance with all 8 sections."""
    # Mock API response with tool_use structure
    _mock_tool_response(mock_anthropic_client, sample_coach_json)

    # Generate coach dialogue
    generator = CoachGenerator()
    coach, metadata = generator.generate(
        schema=CoachSchema,
        learning_objective="Understand and facilitate agile sprint planning",
        topic="Agile Sprint Planning",
        difficulty="intermediate"
    )

    # Verify it's a valid CoachSchema with all 8 sections
    assert isinstance(coach, CoachSchema)
    assert coach.title == "Coaching Dialogue: Agile Sprint Planning"
    assert len(coach.learning_objectives) >= 2
    assert coach.scenario != ""
    assert len(coach.tasks) >= 2
    assert len(coach.conversation_starters) >= 3
    assert len(coach.sample_responses) == 3
    assert len(coach.evaluation_criteria) >= 3
    assert coach.wrap_up != ""
    assert len(coach.reflection_prompts) >= 2


def test_sample_responses_cover_all_levels(mock_anthropic_client, sample_coach_json):
    """Test that sample responses include all 3 evaluation levels."""
    # Mock API response with tool_use structure
    _mock_tool_response(mock_anthropic_client, sample_coach_json)

    # Generate coach dialogue
    generator = CoachGenerator()
    coach, _ = generator.generate(
        schema=CoachSchema,
        learning_objective="Understand and facilitate agile sprint planning",
        topic="Agile Sprint Planning"
    )

    # Extract evaluation levels
    levels = {response.evaluation_level for response in coach.sample_responses}

    # Verify all 3 levels are present
    assert "exceeds" in levels, "Missing 'exceeds' evaluation level"
    assert "meets" in levels, "Missing 'meets' evaluation level"
    assert "needs_improvement" in levels, "Missing 'needs_improvement' evaluation level"
    assert len(levels) == 3, f"Expected 3 levels, got {len(levels)}"


def test_system_prompt_mentions_eight_sections():
    """Test that system prompt references all 8 required sections."""
    generator = CoachGenerator()
    prompt = generator.system_prompt

    # Check for key section indicators
    sections_to_find = [
        "learning objectives",
        "scenario",
        "tasks",
        "conversation starters",
        "sample responses",
        "evaluation criteria",
        "wrap-up",
        "reflection"
    ]

    missing_sections = []
    for section in sections_to_find:
        if section.lower() not in prompt.lower():
            missing_sections.append(section)

    assert len(missing_sections) == 0, f"System prompt missing sections: {missing_sections}"


def test_build_user_prompt_includes_params(mock_anthropic_client):
    """Test that build_user_prompt includes learning_objective and topic."""
    generator = CoachGenerator()

    prompt = generator.build_user_prompt(
        learning_objective="Facilitate agile ceremonies",
        topic="Sprint Planning",
        difficulty="intermediate"
    )

    # Verify key parameters are in prompt
    assert "Facilitate agile ceremonies" in prompt or "facilitate agile ceremonies" in prompt.lower()
    assert "Sprint Planning" in prompt or "sprint planning" in prompt.lower()
    assert "intermediate" in prompt.lower()


def test_extract_metadata_counts_sections(mock_anthropic_client, sample_coach_json):
    """Test that extract_metadata calculates correct section counts."""
    # Mock API response with tool_use structure
    _mock_tool_response(mock_anthropic_client, sample_coach_json)

    # Generate coach dialogue
    generator = CoachGenerator()
    coach, metadata = generator.generate(
        schema=CoachSchema,
        learning_objective="Facilitate sprint planning",
        topic="Agile"
    )

    # Verify metadata structure
    assert "word_count" in metadata
    assert metadata["word_count"] > 0, "Word count should include all text fields"
    assert metadata["num_conversation_starters"] == len(coach.conversation_starters)
    assert metadata["num_sample_responses"] == len(coach.sample_responses)
    assert metadata["num_evaluation_criteria"] == len(coach.evaluation_criteria)
    assert metadata["content_type"] == "coach"


def test_api_called_with_output_config(mock_anthropic_client, sample_coach_json):
    """Test that API is called with tools and tool_choice for structured output."""
    # Mock API response with tool_use structure
    _mock_tool_response(mock_anthropic_client, sample_coach_json)

    # Generate coach dialogue
    generator = CoachGenerator()
    generator.generate(
        schema=CoachSchema,
        learning_objective="Facilitate sprint planning",
        topic="Agile Sprint Planning",
        difficulty="intermediate"
    )

    # Verify API was called with tools for structured output
    mock_anthropic_client.messages.create.assert_called_once()
    call_kwargs = mock_anthropic_client.messages.create.call_args[1]
    assert "tools" in call_kwargs
    assert len(call_kwargs["tools"]) == 1
    assert call_kwargs["tools"][0]["name"] == "output_structured"
    assert "tool_choice" in call_kwargs
    assert call_kwargs["tool_choice"]["type"] == "tool"
