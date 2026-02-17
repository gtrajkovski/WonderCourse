"""Tests for coach conversation management, guardrails, and persona."""

import pytest
from src.coach import (
    ConversationManager,
    Message,
    GuardrailEngine,
    CoverageResult,
    CoachPersona,
    PersonaBuilder
)


# ===========================
# ConversationManager Tests
# ===========================


def test_conversation_manager_initialization():
    """Test ConversationManager initializes correctly."""
    manager = ConversationManager(max_tokens=8000)

    assert manager.max_tokens == 8000
    assert manager.messages == []
    assert manager.summaries == []
    assert manager.session_id.startswith("session_")


def test_add_message_tracks_tokens():
    """Test adding messages tracks token counts."""
    manager = ConversationManager(max_tokens=8000)

    manager.add_message("user", "Hello coach")
    manager.add_message("assistant", "Hello! How can I help you today?")

    assert len(manager.messages) == 2
    assert manager.messages[0].role == "user"
    assert manager.messages[0].content == "Hello coach"
    assert manager.messages[0].token_count > 0
    assert manager.messages[1].role == "assistant"
    assert manager.messages[1].token_count > 0


def test_token_estimation():
    """Test token estimation from word count."""
    manager = ConversationManager()

    # "Hello world" = 2 words * 1.3 = 2.6 -> 2 tokens
    estimated = manager._estimate_tokens("Hello world")
    assert estimated == 2

    # Longer text
    text = "This is a longer message with many more words"
    estimated = manager._estimate_tokens(text)
    assert estimated == 11  # 9 words * 1.3 = 11.7 -> 11


def test_get_context_format():
    """Test get_context returns Claude API format."""
    manager = ConversationManager()

    manager.add_message("user", "What is Python?")
    manager.add_message("assistant", "Python is a programming language.")

    context = manager.get_context()

    assert len(context) == 2
    assert context[0] == {"role": "user", "content": "What is Python?"}
    assert context[1] == {"role": "assistant", "content": "Python is a programming language."}


def test_get_context_includes_summaries():
    """Test get_context includes summaries as system messages."""
    manager = ConversationManager()

    # Manually add a summary (normally done by compaction)
    manager.summaries.append("Previous discussion covered Python basics")
    manager.add_message("user", "Tell me about classes")

    context = manager.get_context()

    assert len(context) == 2
    assert context[0]["role"] == "system"
    assert "Previous discussion" in context[0]["content"]
    assert context[1]["role"] == "user"


def test_compact_history_keeps_recent_five():
    """Test history compaction keeps recent 5 messages."""
    manager = ConversationManager()

    # Add 10 messages
    for i in range(10):
        manager.add_message("user", f"Message {i}")

    # Force compaction
    manager.compact_history()

    # Should keep only last 5
    assert len(manager.messages) == 5
    assert manager.messages[0].content == "Message 5"
    assert manager.messages[-1].content == "Message 9"

    # Should have created a summary
    assert len(manager.summaries) == 1
    assert "Message 0" in manager.summaries[0]


def test_compact_history_no_op_for_short_history():
    """Test compaction does nothing with less than 6 messages."""
    manager = ConversationManager()

    for i in range(3):
        manager.add_message("user", f"Message {i}")

    manager.compact_history()

    # Should still have all 3 messages
    assert len(manager.messages) == 3
    assert len(manager.summaries) == 0


def test_auto_compaction_at_80_percent():
    """Test automatic compaction when reaching 80% token budget."""
    manager = ConversationManager(max_tokens=100)  # Small budget

    # Add messages until compaction triggers
    # Each message is ~10 tokens (8 words * 1.3), so 8 messages = 80 tokens
    # After 8th message, compaction triggers (keeps 5)
    # Then messages 9 and 10 are added, leaving 6 messages
    for i in range(10):
        manager.add_message("user", "This is a test message with several words")

    # Should have triggered compaction at least once
    # Final state: 6 messages (after compaction to 5, then 2 more added)
    assert len(manager.messages) <= 7  # Allow some variation
    assert len(manager.summaries) > 0  # Summary created during compaction


def test_save_and_load_transcript():
    """Test saving and loading conversation state."""
    manager = ConversationManager(max_tokens=8000, session_id="test-session")

    manager.add_message("user", "Hello")
    manager.add_message("assistant", "Hi there")
    manager.summaries.append("Previous conversation")

    # Save
    saved = manager.save_transcript()

    assert saved["session_id"] == "test-session"
    assert saved["max_tokens"] == 8000
    assert len(saved["messages"]) == 2
    assert len(saved["summaries"]) == 1
    assert "saved_at" in saved

    # Load into new manager
    new_manager = ConversationManager()
    new_manager.load_transcript(saved)

    assert new_manager.session_id == "test-session"
    assert new_manager.max_tokens == 8000
    assert len(new_manager.messages) == 2
    assert new_manager.messages[0].content == "Hello"
    assert len(new_manager.summaries) == 1


def test_get_full_transcript():
    """Test getting full conversation transcript."""
    manager = ConversationManager()

    manager.add_message("user", "Question 1")
    manager.add_message("assistant", "Answer 1")

    transcript = manager.get_full_transcript()

    assert len(transcript) == 2
    assert isinstance(transcript[0], Message)
    assert transcript[0].content == "Question 1"


# ===========================
# GuardrailEngine Tests
# ===========================


def test_guardrail_engine_initialization():
    """Test GuardrailEngine initializes with dialogue structure."""
    dialogue = {
        "learning_objectives": ["Understand Python basics"],
        "tasks": ["Write a function", "Test the function"],
        "evaluation_criteria": ["Code quality", "Testing coverage"]
    }
    outcomes = ["Implement Python functions", "Write unit tests"]

    engine = GuardrailEngine(dialogue, outcomes)

    assert engine.dialogue_structure == dialogue
    assert engine.learning_outcomes == outcomes
    assert len(engine.key_points) > 0


def test_check_coverage_empty_transcript():
    """Test coverage check with empty transcript."""
    dialogue = {"learning_objectives": ["Test objective"]}
    outcomes = ["Test outcome"]
    engine = GuardrailEngine(dialogue, outcomes)

    result = engine.check_coverage([])

    assert isinstance(result, CoverageResult)
    assert result.coverage_percent == 0
    assert len(result.covered_sections) == 0
    assert len(result.remaining_sections) == len(engine.DIALOGUE_SECTIONS)


def test_check_coverage_detects_sections():
    """Test coverage detection from conversation keywords."""
    dialogue = {"learning_objectives": ["Test objective"]}
    outcomes = ["Test outcome"]
    engine = GuardrailEngine(dialogue, outcomes)

    # Create messages with section keywords
    messages = [
        Message("user", "Let me provide some context and background"),
        Message("assistant", "Great! Let's practice this skill"),
        Message("user", "I need to reflect on what I learned")
    ]

    result = engine.check_coverage(messages)

    # Should detect context_setting, skill_introduction, reflection
    assert result.coverage_percent > 0
    assert "context_setting" in result.covered_sections
    assert "skill_introduction" in result.covered_sections
    assert "reflection" in result.covered_sections


def test_is_on_topic_with_matching_keywords():
    """Test on-topic detection for messages matching learning outcomes."""
    dialogue = {"learning_objectives": ["Python functions"]}
    outcomes = ["Write Python functions", "Debug code"]
    engine = GuardrailEngine(dialogue, outcomes)

    # On-topic message
    assert engine.is_on_topic("How do I write a function in Python?")
    assert engine.is_on_topic("I'm having trouble debugging my code")


def test_is_on_topic_with_off_topic_message():
    """Test off-topic detection."""
    dialogue = {"learning_objectives": ["Python functions"]}
    outcomes = ["Write Python functions"]
    engine = GuardrailEngine(dialogue, outcomes)

    # Off-topic messages
    assert not engine.is_on_topic("What's the weather like today?")
    assert not engine.is_on_topic("I love pizza")


def test_get_redirect_prompt():
    """Test redirect prompt generation."""
    dialogue = {"learning_objectives": ["Python basics"]}
    outcomes = ["Learn Python syntax", "Write basic programs"]
    engine = GuardrailEngine(dialogue, outcomes)

    redirect = engine.get_redirect_prompt("What's for lunch?")

    assert "What's for lunch?" in redirect
    assert "off-topic" in redirect.lower()
    assert "Python" in redirect or "syntax" in redirect


def test_build_system_prompt():
    """Test building complete system prompt with persona."""
    dialogue = {
        "learning_objectives": ["Test objective"],
        "tasks": ["Task 1"]
    }
    outcomes = ["Outcome 1", "Outcome 2"]
    engine = GuardrailEngine(dialogue, outcomes)

    persona = CoachPersona(
        name="TestCoach",
        personality="supportive",
        socratic=True,
        off_topic_handling="moderate"
    )

    prompt = engine.build_system_prompt(persona)

    assert "TestCoach" in prompt or "supportive" in prompt
    assert "Outcome 1" in prompt
    assert "Outcome 2" in prompt
    assert "moderate" in prompt
    assert "Socratic" in prompt


# ===========================
# CoachPersona Tests
# ===========================


def test_coach_persona_defaults():
    """Test CoachPersona default values."""
    persona = CoachPersona()

    assert persona.name == "Coach"
    assert persona.personality == "supportive"
    assert persona.style == "encouraging and patient"
    assert persona.socratic is True
    assert persona.off_topic_handling == "moderate"
    assert persona.avatar is None


def test_coach_persona_custom_values():
    """Test CoachPersona with custom values."""
    persona = CoachPersona(
        name="Professor Smith",
        personality="challenging",
        style="rigorous and demanding",
        socratic=False,
        off_topic_handling="strict",
        avatar="prof-avatar"
    )

    assert persona.name == "Professor Smith"
    assert persona.personality == "challenging"
    assert persona.style == "rigorous and demanding"
    assert persona.socratic is False
    assert persona.off_topic_handling == "strict"
    assert persona.avatar == "prof-avatar"


def test_persona_builder_from_activity_no_metadata():
    """Test PersonaBuilder with activity without metadata."""
    class MockActivity:
        metadata = None

    activity = MockActivity()
    persona = PersonaBuilder.from_activity(activity)

    # Should return defaults
    assert persona.name == "Coach"
    assert persona.personality == "supportive"


def test_persona_builder_from_activity_with_metadata():
    """Test PersonaBuilder with activity metadata."""
    class MockActivity:
        metadata = {
            "coach_persona": {
                "name": "Dr. Johnson",
                "personality": "formal",
                "style": "professional and structured",
                "socratic": False,
                "off_topic_handling": "strict"
            }
        }

    activity = MockActivity()
    persona = PersonaBuilder.from_activity(activity)

    assert persona.name == "Dr. Johnson"
    assert persona.personality == "formal"
    assert persona.style == "professional and structured"
    assert persona.socratic is False
    assert persona.off_topic_handling == "strict"


def test_get_personality_prompt_supportive():
    """Test personality prompt for supportive persona."""
    persona = CoachPersona(personality="supportive")
    prompt = PersonaBuilder.get_personality_prompt(persona)

    assert "supportive" in prompt.lower()
    assert "encouraging" in prompt.lower()
    assert "patient" in prompt.lower()


def test_get_personality_prompt_challenging():
    """Test personality prompt for challenging persona."""
    persona = CoachPersona(personality="challenging")
    prompt = PersonaBuilder.get_personality_prompt(persona)

    assert "challenging" in prompt.lower()
    assert "high expectations" in prompt.lower()


def test_get_personality_prompt_with_socratic():
    """Test personality prompt includes Socratic method when enabled."""
    persona = CoachPersona(personality="supportive", socratic=True)
    prompt = PersonaBuilder.get_personality_prompt(persona)

    assert "Socratic" in prompt
    assert "questions" in prompt.lower()
    assert "why" in prompt.lower()


def test_get_personality_prompt_without_socratic():
    """Test personality prompt without Socratic method."""
    persona = CoachPersona(personality="supportive", socratic=False)
    prompt = PersonaBuilder.get_personality_prompt(persona)

    # Socratic section should not be present
    assert "Socratic Method" not in prompt


def test_all_personality_types_have_prompts():
    """Test all personality types have defined prompts."""
    personalities = ["supportive", "challenging", "formal", "friendly"]

    for personality_type in personalities:
        persona = CoachPersona(personality=personality_type)
        prompt = PersonaBuilder.get_personality_prompt(persona)

        assert len(prompt) > 0
        assert "Your Role" in prompt
