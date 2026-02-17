"""Tests for VideoScriptGenerator with mocked Anthropic API."""

import pytest
from unittest.mock import MagicMock

from src.generators.video_script_generator import VideoScriptGenerator
from src.generators.schemas.video_script import VideoScriptSchema, VideoScriptSection


# Sample valid VideoScriptSchema JSON for mocking
SAMPLE_VIDEO_SCRIPT_JSON = """{
  "title": "Introduction to Python Variables",
  "hook": {
    "phase": "hook",
    "title": "The Problem",
    "script_text": "Have you ever wondered how programs remember information? Let's explore the fundamental concept that makes this possible.",
    "speaker_notes": "Open with relatable question, pause for effect"
  },
  "objective": {
    "phase": "objective",
    "title": "Learning Goal",
    "script_text": "By the end of this video, you will be able to create and use variables to store different types of data in Python.",
    "speaker_notes": "State clearly and confidently"
  },
  "content": {
    "phase": "content",
    "title": "Main Content",
    "script_text": "A variable in Python is like a labeled container that holds a value. To create a variable, we simply assign a value using the equals sign. For example, name equals 'Alice' creates a variable called name that stores the text Alice. We can create variables for numbers too, like age equals 25. Python is smart enough to figure out what type of data you're storing. Let's see this in action with a concrete example. Imagine you're building a user profile system. You might have variables like username equals 'johndoe', email equals 'john@example.com', and is_active equals True. These variables work together to represent a user in your program. You can change variable values anytime by assigning a new value, making your programs dynamic and responsive.",
    "speaker_notes": "Use clear examples, show code on screen, speak slowly through examples"
  },
  "ivq": {
    "phase": "ivq",
    "title": "Check Your Understanding",
    "script_text": "Quick question: If I write score equals 100, what type of data is Python storing? Think about it for a moment. The answer is a number, specifically an integer. Python recognizes 100 as numeric data.",
    "speaker_notes": "Pause 3 seconds after question, then reveal answer"
  },
  "summary": {
    "phase": "summary",
    "title": "Key Takeaways",
    "script_text": "Let's recap what we learned. Variables are labeled containers that store values. You create them using the assignment operator. Python automatically determines the data type. And you can change variable values anytime you need to. These concepts are fundamental to every Python program you'll write.",
    "speaker_notes": "Emphasize each point, use hand gestures for counting"
  },
  "cta": {
    "phase": "cta",
    "title": "Next Steps",
    "script_text": "Now it's your turn to practice! Complete the next exercise where you'll create your own variables and see them in action. This hands-on practice will solidify your understanding.",
    "speaker_notes": "Smile and encourage, point to exercise link on screen"
  },
  "learning_objective": "Create and use variables to store different types of data in Python"
}"""


def test_generate_returns_valid_schema(mocker):
    """Test that generate() returns a valid VideoScriptSchema with all 6 sections."""
    import json
    # Mock Anthropic client - patch in base_generator where it's actually used
    mock_client = mocker.MagicMock()
    mock_response = mocker.MagicMock()
    # Create mock tool_use block with proper structure
    mock_tool_use = mocker.MagicMock()
    mock_tool_use.type = "tool_use"
    mock_tool_use.input = json.loads(SAMPLE_VIDEO_SCRIPT_JSON)
    mock_response.content = [mock_tool_use]
    mock_client.messages.create.return_value = mock_response
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    generator = VideoScriptGenerator(api_key="test-key")

    script, metadata = generator.generate(
        schema=VideoScriptSchema,
        learning_objective="Create and use variables to store different types of data",
        topic="Python variables",
        audience_level="beginner"
    )

    # Verify it's a VideoScriptSchema instance
    assert isinstance(script, VideoScriptSchema)

    # Verify all 6 WWHAA sections are present
    assert script.hook is not None
    assert script.objective is not None
    assert script.content is not None
    assert script.ivq is not None
    assert script.summary is not None
    assert script.cta is not None

    # Verify sections have correct phase identifiers
    assert script.hook.phase == "hook"
    assert script.objective.phase == "objective"
    assert script.content.phase == "content"
    assert script.ivq.phase == "ivq"
    assert script.summary.phase == "summary"
    assert script.cta.phase == "cta"

    # Verify all sections have required fields
    for section in [script.hook, script.objective, script.content, script.ivq, script.summary, script.cta]:
        assert section.title
        assert section.script_text
        assert section.speaker_notes


def test_system_prompt_contains_wwhaa(mocker):
    """Test that system_prompt mentions WWHAA structure and percentages."""
    # Mock Anthropic client - patch in base_generator where it's actually used
    mock_client = mocker.MagicMock()
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    generator = VideoScriptGenerator(api_key="test-key")

    system_prompt = generator.system_prompt

    # Verify WWHAA sections are mentioned
    assert "hook" in system_prompt.lower() or "Hook" in system_prompt
    assert "objective" in system_prompt.lower() or "Objective" in system_prompt
    assert "content" in system_prompt.lower() or "Content" in system_prompt
    assert "summary" in system_prompt.lower() or "Summary" in system_prompt
    assert "cta" in system_prompt.lower() or "call to action" in system_prompt.lower()

    # Verify percentage guidelines are present
    assert "10%" in system_prompt or "60%" in system_prompt  # At least some percentages


def test_build_user_prompt_includes_params(mocker):
    """Test that build_user_prompt includes learning_objective, topic, and audience_level."""
    # Mock Anthropic client - patch in base_generator where it's actually used
    mock_client = mocker.MagicMock()
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    generator = VideoScriptGenerator(api_key="test-key")

    prompt = generator.build_user_prompt(
        learning_objective="Implement functions with parameters and return values",
        topic="Python functions",
        audience_level="intermediate",
        duration_minutes=10
    )

    # Verify all parameters appear in the prompt
    assert "functions with parameters and return values" in prompt.lower()
    assert "python functions" in prompt.lower()
    assert "intermediate" in prompt.lower()
    assert "10" in prompt  # Duration


def test_extract_metadata_calculates_correctly(mocker):
    """Test that extract_metadata calculates word_count and duration correctly."""
    # Mock Anthropic client - patch in base_generator where it's actually used
    mock_client = mocker.MagicMock()
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    generator = VideoScriptGenerator(api_key="test-key")

    # Create a VideoScriptSchema manually with known word counts
    script = VideoScriptSchema(
        title="Test Video",
        hook=VideoScriptSection(
            phase="hook",
            title="Hook",
            script_text="This is a hook.",  # 4 words
            speaker_notes="Note"
        ),
        objective=VideoScriptSection(
            phase="objective",
            title="Objective",
            script_text="This is an objective.",  # 4 words
            speaker_notes="Note"
        ),
        content=VideoScriptSection(
            phase="content",
            title="Content",
            script_text="This is the main content section.",  # 6 words
            speaker_notes="Note"
        ),
        ivq=VideoScriptSection(
            phase="ivq",
            title="IVQ",
            script_text="This is a question.",  # 4 words
            speaker_notes="Note"
        ),
        summary=VideoScriptSection(
            phase="summary",
            title="Summary",
            script_text="This is a summary.",  # 4 words
            speaker_notes="Note"
        ),
        cta=VideoScriptSection(
            phase="cta",
            title="CTA",
            script_text="This is the call to action.",  # 6 words
            speaker_notes="Note"
        ),
        learning_objective="Test objective"
    )

    metadata = generator.extract_metadata(script)

    # Total: 4+4+6+4+4+6 = 28 words
    assert metadata["word_count"] == 28

    # Duration at 150 WPM: 28/150 = 0.186... ≈ 0.2 minutes
    assert metadata["estimated_duration_minutes"] == 0.2

    # Verify content_type
    assert metadata["content_type"] == "video"


def test_metadata_includes_section_word_counts(mocker):
    """Test that metadata includes per-section word counts."""
    # Mock Anthropic client - patch in base_generator where it's actually used
    mock_client = mocker.MagicMock()
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    generator = VideoScriptGenerator(api_key="test-key")

    # Create a VideoScriptSchema manually
    script = VideoScriptSchema(
        title="Test Video",
        hook=VideoScriptSection(
            phase="hook",
            title="Hook",
            script_text="One two three",  # 3 words
            speaker_notes="Note"
        ),
        objective=VideoScriptSection(
            phase="objective",
            title="Objective",
            script_text="Four five",  # 2 words
            speaker_notes="Note"
        ),
        content=VideoScriptSection(
            phase="content",
            title="Content",
            script_text="Six seven eight nine",  # 4 words
            speaker_notes="Note"
        ),
        ivq=VideoScriptSection(
            phase="ivq",
            title="IVQ",
            script_text="Ten",  # 1 word
            speaker_notes="Note"
        ),
        summary=VideoScriptSection(
            phase="summary",
            title="Summary",
            script_text="Eleven twelve",  # 2 words
            speaker_notes="Note"
        ),
        cta=VideoScriptSection(
            phase="cta",
            title="CTA",
            script_text="Thirteen fourteen fifteen",  # 3 words
            speaker_notes="Note"
        ),
        learning_objective="Test objective"
    )

    metadata = generator.extract_metadata(script)

    # Verify section_word_counts dict exists
    assert "section_word_counts" in metadata
    section_counts = metadata["section_word_counts"]

    # Verify counts for each section
    assert section_counts["hook"] == 3
    assert section_counts["objective"] == 2
    assert section_counts["content"] == 4
    assert section_counts["ivq"] == 1
    assert section_counts["summary"] == 2
    assert section_counts["cta"] == 3


def test_api_called_with_output_config(mocker):
    """Test that messages.create is called with tools and tool_choice for structured output."""
    import json
    # Mock Anthropic client - patch in base_generator where it's actually used
    mock_client = mocker.MagicMock()
    mock_response = mocker.MagicMock()
    # Create mock tool_use block with proper structure
    mock_tool_use = mocker.MagicMock()
    mock_tool_use.type = "tool_use"
    mock_tool_use.input = json.loads(SAMPLE_VIDEO_SCRIPT_JSON)
    mock_response.content = [mock_tool_use]
    mock_client.messages.create.return_value = mock_response
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    generator = VideoScriptGenerator(api_key="test-key")

    generator.generate(
        schema=VideoScriptSchema,
        learning_objective="Test objective",
        topic="Test topic",
        audience_level="beginner"
    )

    # Verify messages.create was called
    mock_client.messages.create.assert_called_once()

    # Get the call arguments
    call_kwargs = mock_client.messages.create.call_args[1]

    # Verify tools parameter exists
    assert "tools" in call_kwargs
    assert len(call_kwargs["tools"]) == 1
    assert call_kwargs["tools"][0]["name"] == "output_structured"

    # Verify tool_choice parameter exists and forces tool use
    assert "tool_choice" in call_kwargs
    assert call_kwargs["tool_choice"]["type"] == "tool"
    assert call_kwargs["tool_choice"]["name"] == "output_structured"
