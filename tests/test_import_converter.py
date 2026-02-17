"""Tests for AI-powered content converter."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from importlib import import_module
from src.core.models import ContentType

# Import ContentConverter avoiding keyword issue
import_pkg = import_module('src.import')
ContentConverter = import_pkg.ContentConverter
ConversionResult = import_pkg.ConversionResult


@pytest.fixture
def mock_anthropic():
    """Mock Anthropic client for testing."""
    # Use full module path to avoid keyword issue
    with patch('src.import.converter.Anthropic') as mock_client_class:
        # Create mock client instance
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Create mock response structure
        mock_response = MagicMock()
        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_response.content = [mock_tool_block]

        mock_client.messages.create.return_value = mock_response

        yield mock_client, mock_tool_block


class TestSuggestType:
    """Tests for suggest_type content type detection."""

    def test_suggest_quiz_multiple_choice_pattern(self):
        """Test quiz detection for multiple choice questions."""
        content = """
        Question 1: What is Python?
        A) A snake
        B) A programming language
        C) A type of food

        Question 2: What is Flask?
        A) A container
        B) A web framework
        C) A type of metal
        """
        converter = ContentConverter()
        result = converter.suggest_type(content)
        assert result == ContentType.QUIZ

    def test_suggest_video_wwhaa_keywords(self):
        """Test video detection for WWHAA structure keywords."""
        content = """
        Hook: Imagine trying to build a website
        Objective: Learn about web frameworks
        Summary: Flask makes web development easy
        Call to action: Try building your first app
        """
        converter = ContentConverter()
        result = converter.suggest_type(content)
        assert result == ContentType.VIDEO

    def test_suggest_reading_long_paragraphs(self):
        """Test reading detection for long form content."""
        content = """
        Introduction to Web Development

        Web development is the process of creating websites and web applications.
        It involves several different technologies working together to create
        dynamic, interactive experiences for users across the internet.

        Front-end Development

        Front-end development focuses on what users see and interact with.
        This includes HTML for structure, CSS for styling, and JavaScript for
        interactivity. Modern front-end frameworks like React and Vue make
        building complex interfaces much easier than traditional approaches.
        """
        converter = ContentConverter()
        result = converter.suggest_type(content)
        assert result == ContentType.READING

    def test_suggest_reading_with_references(self):
        """Test reading detection when references are present."""
        content = """
        Some content about web frameworks.

        References:
        Smith, J. (2023). Web Development Fundamentals.
        """
        converter = ContentConverter()
        result = converter.suggest_type(content)
        assert result == ContentType.READING

    def test_suggest_video_for_short_content(self):
        """Test video suggestion for short content (default)."""
        content = "This is a short piece of content about Python."
        converter = ContentConverter()
        result = converter.suggest_type(content)
        assert result == ContentType.VIDEO


class TestToVideoScript:
    """Tests for video script conversion."""

    def test_to_video_script_basic(self, mock_anthropic):
        """Test basic video script conversion."""
        mock_client, mock_tool_block = mock_anthropic

        # Mock video script response
        mock_tool_block.input = {
            "title": "Introduction to Flask",
            "hook": {
                "phase": "hook",
                "title": "Hook",
                "script_text": "Imagine building a website in minutes.",
                "speaker_notes": "Be enthusiastic"
            },
            "objective": {
                "phase": "objective",
                "title": "Learning Objective",
                "script_text": "Learn how to use Flask.",
                "speaker_notes": "State clearly"
            },
            "content": {
                "phase": "content",
                "title": "Main Content",
                "script_text": "Flask is a micro web framework.",
                "speaker_notes": "Show examples"
            },
            "ivq": {
                "phase": "ivq",
                "title": "In-Video Question",
                "script_text": "What is Flask?",
                "speaker_notes": "Pause for thought"
            },
            "summary": {
                "phase": "summary",
                "title": "Summary",
                "script_text": "Flask makes web development easy.",
                "speaker_notes": "Reinforce key points"
            },
            "cta": {
                "phase": "cta",
                "title": "Call to Action",
                "script_text": "Try building your first Flask app.",
                "speaker_notes": "Be encouraging"
            },
            "learning_objective": "Learn Flask basics"
        }

        converter = ContentConverter()
        result = converter.to_video_script(
            "Flask is a web framework for Python",
            {"topic": "Flask", "learning_objective": "Learn Flask basics"}
        )

        # Verify API was called
        assert mock_client.messages.create.called

        # Verify result structure
        assert "title" in result
        assert "hook" in result
        assert "objective" in result
        assert "content" in result
        assert "ivq" in result
        assert "summary" in result
        assert "cta" in result

    def test_to_video_script_with_context(self, mock_anthropic):
        """Test video script conversion with context."""
        mock_client, mock_tool_block = mock_anthropic
        mock_tool_block.input = {
            "title": "Test",
            "hook": {"phase": "hook", "title": "Hook", "script_text": "Text", "speaker_notes": "Notes"},
            "objective": {"phase": "objective", "title": "Obj", "script_text": "Text", "speaker_notes": "Notes"},
            "content": {"phase": "content", "title": "Content", "script_text": "Text", "speaker_notes": "Notes"},
            "ivq": {"phase": "ivq", "title": "IVQ", "script_text": "Text", "speaker_notes": "Notes"},
            "summary": {"phase": "summary", "title": "Summary", "script_text": "Text", "speaker_notes": "Notes"},
            "cta": {"phase": "cta", "title": "CTA", "script_text": "Text", "speaker_notes": "Notes"},
            "learning_objective": "Custom objective"
        }

        converter = ContentConverter()
        context = {
            "topic": "Advanced Flask",
            "learning_objective": "Master Flask routing",
            "target_duration": 5
        }
        result = converter.to_video_script("Content", context)

        # Verify context was included in prompt
        call_args = mock_client.messages.create.call_args
        messages = call_args[1]['messages']
        user_prompt = messages[0]['content']

        assert "Advanced Flask" in user_prompt
        assert "Master Flask routing" in user_prompt


class TestToReading:
    """Tests for reading conversion."""

    def test_to_reading_basic(self, mock_anthropic):
        """Test basic reading conversion."""
        mock_client, mock_tool_block = mock_anthropic

        # Mock reading response
        mock_tool_block.input = {
            "title": "Introduction to Flask",
            "introduction": "Flask is a Python web framework.",
            "sections": [
                {"heading": "Getting Started", "body": "Install Flask with pip."},
                {"heading": "First App", "body": "Create your first Flask application."}
            ],
            "conclusion": "Flask makes web development accessible.",
            "references": [
                {"citation": "Flask Documentation (2023)", "url": "https://flask.palletsprojects.com"}
            ],
            "learning_objective": "Understand Flask basics"
        }

        converter = ContentConverter()
        result = converter.to_reading(
            "Flask is a great web framework",
            {"topic": "Flask"}
        )

        # Verify result structure
        assert "title" in result
        assert "introduction" in result
        assert "sections" in result
        assert len(result["sections"]) >= 2
        assert "conclusion" in result
        assert "references" in result

    def test_to_reading_preserves_structure(self, mock_anthropic):
        """Test that reading conversion preserves logical structure."""
        mock_client, mock_tool_block = mock_anthropic
        mock_tool_block.input = {
            "title": "Web Development",
            "introduction": "Intro text",
            "sections": [
                {"heading": "Section 1", "body": "Body 1"},
                {"heading": "Section 2", "body": "Body 2"},
                {"heading": "Section 3", "body": "Body 3"}
            ],
            "conclusion": "Conclusion text",
            "references": [{"citation": "Ref 1", "url": ""}],
            "learning_objective": "Learn web dev"
        }

        converter = ContentConverter()
        result = converter.to_reading("Content with multiple topics", {})

        # Sections should be preserved
        assert len(result["sections"]) == 3


class TestToQuiz:
    """Tests for quiz conversion."""

    def test_to_quiz_basic(self, mock_anthropic):
        """Test basic quiz conversion."""
        mock_client, mock_tool_block = mock_anthropic

        # Mock quiz response
        mock_tool_block.input = {
            "title": "Flask Quiz",
            "questions": [
                {
                    "question_text": "What is Flask?",
                    "options": [
                        {"text": "A web framework", "is_correct": True, "feedback": "Correct!"},
                        {"text": "A database", "is_correct": False, "feedback": "No, that's not right."},
                        {"text": "A programming language", "is_correct": False, "feedback": "Flask is built with Python."}
                    ],
                    "bloom_level": "remember",
                    "explanation": "Flask is a micro web framework for Python."
                },
                {
                    "question_text": "What command installs Flask?",
                    "options": [
                        {"text": "pip install flask", "is_correct": True, "feedback": "Correct!"},
                        {"text": "npm install flask", "is_correct": False, "feedback": "That's for Node.js."},
                        {"text": "apt-get flask", "is_correct": False, "feedback": "That's a system package manager."}
                    ],
                    "bloom_level": "remember",
                    "explanation": "Use pip to install Python packages."
                },
                {
                    "question_text": "How do you create a Flask route?",
                    "options": [
                        {"text": "@app.route('/path')", "is_correct": True, "feedback": "Correct!"},
                        {"text": "app.get('/path')", "is_correct": False, "feedback": "That's Express syntax."},
                        {"text": "route('/path')", "is_correct": False, "feedback": "Missing the decorator."}
                    ],
                    "bloom_level": "apply",
                    "explanation": "Flask uses decorators for routing."
                }
            ],
            "passing_score_percentage": 70,
            "learning_objective": "Assess Flask knowledge"
        }

        converter = ContentConverter()
        result = converter.to_quiz(
            "Flask is a web framework. Install it with pip install flask.",
            {"topic": "Flask"}
        )

        # Verify result structure
        assert "title" in result
        assert "questions" in result
        assert len(result["questions"]) >= 3
        assert "passing_score_percentage" in result

        # Verify question structure
        question = result["questions"][0]
        assert "question_text" in question
        assert "options" in question
        assert "bloom_level" in question
        assert "explanation" in question

    def test_to_quiz_multiple_bloom_levels(self, mock_anthropic):
        """Test quiz conversion spans multiple Bloom's levels."""
        mock_client, mock_tool_block = mock_anthropic
        mock_tool_block.input = {
            "title": "Quiz",
            "questions": [
                {
                    "question_text": "Q1",
                    "options": [
                        {"text": "A", "is_correct": True, "feedback": "Yes"},
                        {"text": "B", "is_correct": False, "feedback": "No"}
                    ],
                    "bloom_level": "remember",
                    "explanation": "Explanation"
                },
                {
                    "question_text": "Q2",
                    "options": [
                        {"text": "A", "is_correct": True, "feedback": "Yes"},
                        {"text": "B", "is_correct": False, "feedback": "No"}
                    ],
                    "bloom_level": "apply",
                    "explanation": "Explanation"
                },
                {
                    "question_text": "Q3",
                    "options": [
                        {"text": "A", "is_correct": True, "feedback": "Yes"},
                        {"text": "B", "is_correct": False, "feedback": "No"}
                    ],
                    "bloom_level": "analyze",
                    "explanation": "Explanation"
                }
            ],
            "passing_score_percentage": 70,
            "learning_objective": "Assess understanding"
        }

        converter = ContentConverter()
        result = converter.to_quiz("Content", {})

        # Check for different Bloom's levels
        bloom_levels = [q["bloom_level"] for q in result["questions"]]
        assert len(set(bloom_levels)) > 1  # Multiple different levels


class TestConvert:
    """Tests for main convert() method."""

    def test_convert_to_video(self, mock_anthropic):
        """Test conversion to video script."""
        mock_client, mock_tool_block = mock_anthropic
        mock_tool_block.input = {
            "title": "Test",
            "hook": {"phase": "hook", "title": "Hook", "script_text": "Text", "speaker_notes": "Notes"},
            "objective": {"phase": "objective", "title": "Obj", "script_text": "Text", "speaker_notes": "Notes"},
            "content": {"phase": "content", "title": "Content", "script_text": "Text", "speaker_notes": "Notes"},
            "ivq": {"phase": "ivq", "title": "IVQ", "script_text": "Text", "speaker_notes": "Notes"},
            "summary": {"phase": "summary", "title": "Summary", "script_text": "Text", "speaker_notes": "Notes"},
            "cta": {"phase": "cta", "title": "CTA", "script_text": "Text", "speaker_notes": "Notes"},
            "learning_objective": "Learn"
        }

        converter = ContentConverter()
        result = converter.convert("Content", ContentType.VIDEO, {})

        assert isinstance(result, ConversionResult)
        assert result.original == "Content"
        assert result.target_type == ContentType.VIDEO
        assert 0.0 <= result.confidence <= 1.0
        assert len(result.changes) > 0
        assert "WWHAA" in result.changes[0]

    def test_convert_to_reading(self, mock_anthropic):
        """Test conversion to reading."""
        mock_client, mock_tool_block = mock_anthropic
        mock_tool_block.input = {
            "title": "Reading",
            "introduction": "Intro",
            "sections": [
                {"heading": "Section 1", "body": "Body 1"},
                {"heading": "Section 2", "body": "Body 2"}
            ],
            "conclusion": "Conclusion",
            "references": [{"citation": "Ref", "url": ""}],
            "learning_objective": "Learn"
        }

        converter = ContentConverter()
        result = converter.convert("Content", ContentType.READING, {})

        assert result.target_type == ContentType.READING
        assert "sections" in result.changes[0].lower()

    def test_convert_to_quiz(self, mock_anthropic):
        """Test conversion to quiz."""
        mock_client, mock_tool_block = mock_anthropic
        mock_tool_block.input = {
            "title": "Quiz",
            "questions": [
                {
                    "question_text": "Q1",
                    "options": [
                        {"text": "A", "is_correct": True, "feedback": "Yes"},
                        {"text": "B", "is_correct": False, "feedback": "No"}
                    ],
                    "bloom_level": "remember",
                    "explanation": "Explanation"
                }
            ],
            "passing_score_percentage": 70,
            "learning_objective": "Assess"
        }

        converter = ContentConverter()
        result = converter.convert("Content", ContentType.QUIZ, {})

        assert result.target_type == ContentType.QUIZ
        assert "questions" in result.changes[0].lower()

    def test_convert_unsupported_type_raises_error(self):
        """Test that unsupported content types raise ValueError."""
        converter = ContentConverter()

        with pytest.raises(ValueError, match="Conversion not supported"):
            converter.convert("Content", ContentType.HOL, {})

    def test_convert_confidence_decreases_for_short_content(self, mock_anthropic):
        """Test that confidence is lower for very short content."""
        mock_client, mock_tool_block = mock_anthropic
        mock_tool_block.input = {
            "title": "Test",
            "hook": {"phase": "hook", "title": "Hook", "script_text": "Text", "speaker_notes": "Notes"},
            "objective": {"phase": "objective", "title": "Obj", "script_text": "Text", "speaker_notes": "Notes"},
            "content": {"phase": "content", "title": "Content", "script_text": "Text", "speaker_notes": "Notes"},
            "ivq": {"phase": "ivq", "title": "IVQ", "script_text": "Text", "speaker_notes": "Notes"},
            "summary": {"phase": "summary", "title": "Summary", "script_text": "Text", "speaker_notes": "Notes"},
            "cta": {"phase": "cta", "title": "CTA", "script_text": "Text", "speaker_notes": "Notes"},
            "learning_objective": "Learn"
        }

        converter = ContentConverter()

        # Short content
        result_short = converter.convert("Short", ContentType.VIDEO, {})

        # Longer content
        long_content = " ".join(["word"] * 200)
        result_long = converter.convert(long_content, ContentType.VIDEO, {})

        # Short content should have lower confidence
        assert result_short.confidence < result_long.confidence


class TestConversionResult:
    """Tests for ConversionResult dataclass."""

    def test_conversion_result_structure(self):
        """Test ConversionResult has expected fields."""
        result = ConversionResult(
            original="Original text",
            structured={"key": "value"},
            target_type=ContentType.VIDEO,
            confidence=0.85,
            changes=["Change 1", "Change 2"]
        )

        assert result.original == "Original text"
        assert result.structured == {"key": "value"}
        assert result.target_type == ContentType.VIDEO
        assert result.confidence == 0.85
        assert len(result.changes) == 2
