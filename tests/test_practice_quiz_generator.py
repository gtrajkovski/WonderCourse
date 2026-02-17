"""Tests for PracticeQuizGenerator using TDD with mocked Anthropic API."""

import json
import pytest
from unittest.mock import Mock, MagicMock
from src.generators.practice_quiz_generator import PracticeQuizGenerator
from src.generators.schemas.practice_quiz import PracticeQuizSchema, PracticeQuizQuestion, PracticeQuizOption


# Sample practice quiz data as dict
SAMPLE_PRACTICE_QUIZ_DATA = {
    "title": "Python Functions Practice Quiz",
    "questions": [
        {
            "question_text": "What is the correct syntax for defining a function in Python?",
            "options": [
                {
                    "text": "def my_function():",
                    "is_correct": True,
                    "feedback": "Correct! Python uses 'def' keyword followed by function name and parentheses.",
                    "hint": "Think about the keyword Python uses to 'define' something."
                },
                {
                    "text": "function my_function():",
                    "is_correct": False,
                    "feedback": "Incorrect. Python uses 'def' keyword, not 'function'.",
                    "hint": "JavaScript uses 'function', but Python uses a shorter 3-letter keyword."
                },
                {
                    "text": "func my_function():",
                    "is_correct": False,
                    "feedback": "Incorrect. Python uses 'def' keyword, not 'func'.",
                    "hint": "It's an abbreviation of a common word for defining things."
                }
            ],
            "bloom_level": "remember",
            "explanation": "Python function definitions always start with the 'def' keyword, which is short for 'define'."
        },
        {
            "question_text": "What will this function return? def add(a, b): return a + b",
            "options": [
                {
                    "text": "The sum of a and b",
                    "is_correct": False,
                    "feedback": "Close, but this answer doesn't capture that it returns a value.",
                    "hint": "What does the 'return' statement do in Python?"
                },
                {
                    "text": "A value representing the sum of parameters a and b",
                    "is_correct": True,
                    "feedback": "Correct! The function returns the result of a + b.",
                    "hint": "Functions with 'return' send back a value to the caller."
                },
                {
                    "text": "Nothing, it prints the sum",
                    "is_correct": False,
                    "feedback": "Incorrect. The function uses return, not print.",
                    "hint": "Check if the function uses 'print()' or 'return'."
                }
            ],
            "bloom_level": "understand",
            "explanation": "The return statement sends back the calculated value to the caller, making it available for use."
        },
        {
            "question_text": "Which function call will raise an error?",
            "options": [
                {
                    "text": "add(1, 2)",
                    "is_correct": False,
                    "feedback": "This is valid - two positional arguments.",
                    "hint": "This provides both required parameters."
                },
                {
                    "text": "add()",
                    "is_correct": True,
                    "feedback": "Correct! This raises TypeError because add() requires 2 arguments.",
                    "hint": "How many parameters does add(a, b) expect?"
                },
                {
                    "text": "add(a=1, b=2)",
                    "is_correct": False,
                    "feedback": "This is valid - two keyword arguments.",
                    "hint": "Keyword arguments are valid in Python."
                }
            ],
            "bloom_level": "apply",
            "explanation": "Python functions require all positional parameters unless defaults are provided. Calling add() without arguments raises TypeError."
        }
    ],
    "learning_objective": "Students will be able to define and call Python functions with parameters."
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
    """Test that generate() returns a valid PracticeQuizSchema instance (NOT QuizSchema)."""
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_PRACTICE_QUIZ_DATA)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    # Generate practice quiz
    generator = PracticeQuizGenerator()
    quiz, metadata = generator.generate(
        schema=PracticeQuizSchema,
        learning_objective="Define and call Python functions",
        topic="Python Functions",
        bloom_level="apply",
        num_questions=3,
        difficulty="intermediate"
    )

    # Verify it's a valid PracticeQuizSchema (NOT QuizSchema)
    assert isinstance(quiz, PracticeQuizSchema)
    assert quiz.title == "Python Functions Practice Quiz"
    assert len(quiz.questions) == 3
    assert quiz.learning_objective == "Students will be able to define and call Python functions with parameters."


def test_options_have_hints(mocker):
    """Test that every option has a non-empty hint field."""
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_PRACTICE_QUIZ_DATA)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    # Generate practice quiz
    generator = PracticeQuizGenerator()
    quiz, _ = generator.generate(
        schema=PracticeQuizSchema,
        learning_objective="Define and call Python functions",
        topic="Python Functions",
        bloom_level="apply",
        num_questions=3
    )

    # Verify every option has a non-empty hint
    for question in quiz.questions:
        for option in question.options:
            assert hasattr(option, 'hint'), f"Option '{option.text}' missing hint field"
            assert len(option.hint) > 0, f"Option '{option.text}' has empty hint"


def test_questions_have_bloom_level(mocker):
    """Test that each question has bloom_level field."""
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_PRACTICE_QUIZ_DATA)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    # Generate practice quiz
    generator = PracticeQuizGenerator()
    quiz, _ = generator.generate(
        schema=PracticeQuizSchema,
        learning_objective="Define and call Python functions",
        topic="Python Functions",
        bloom_level="apply",
        num_questions=3
    )

    # Verify each question has bloom_level
    valid_levels = ["remember", "understand", "apply", "analyze", "evaluate", "create"]
    for question in quiz.questions:
        assert hasattr(question, 'bloom_level'), f"Question '{question.question_text}' missing bloom_level"
        assert question.bloom_level in valid_levels, f"Invalid bloom_level: {question.bloom_level}"


def test_system_prompt_emphasizes_formative():
    """Test that system prompt mentions formative/practice/learning focus."""
    generator = PracticeQuizGenerator()
    prompt = generator.system_prompt

    # Verify formative assessment language is present
    formative_keywords = ["formative", "practice", "learning", "feedback", "hint", "guide"]
    found_keywords = [kw for kw in formative_keywords if kw in prompt.lower()]

    assert len(found_keywords) >= 2, f"System prompt should emphasize formative assessment (found only: {found_keywords})"


def test_build_user_prompt_includes_params(mocker):
    """Test that build_user_prompt includes learning_objective, bloom_level, num_questions."""
    mock_client = MagicMock()
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    generator = PracticeQuizGenerator()

    prompt = generator.build_user_prompt(
        learning_objective="Define Python functions",
        topic="Python Functions",
        bloom_level="apply",
        num_questions=5,
        difficulty="intermediate"
    )

    # Verify key parameters are in prompt
    assert "Define Python functions" in prompt
    assert "apply" in prompt.lower()
    assert "5" in prompt or "five" in prompt.lower()
    assert "Python Functions" in prompt or "Python functions" in prompt


def test_extract_metadata_calculates_duration():
    """Test that extract_metadata calculates duration using 1.5 min/question rate."""
    generator = PracticeQuizGenerator()

    # Create a sample practice quiz with 5 questions
    quiz = PracticeQuizSchema(
        title="Test Practice Quiz",
        questions=[
            PracticeQuizQuestion(
                question_text=f"Question {i}?",
                options=[
                    PracticeQuizOption(
                        text="Option A",
                        is_correct=True,
                        feedback="Correct",
                        hint="Think about this carefully"
                    ),
                    PracticeQuizOption(
                        text="Option B",
                        is_correct=False,
                        feedback="Wrong",
                        hint="Consider another option"
                    ),
                    PracticeQuizOption(
                        text="Option C",
                        is_correct=False,
                        feedback="Wrong",
                        hint="Try again"
                    )
                ],
                bloom_level="apply",
                explanation="Explanation text here"
            )
            for i in range(5)
        ],
        learning_objective="Test objective"
    )

    metadata = generator.extract_metadata(quiz)

    # Verify duration calculation (5 questions * 1.5 minutes = 7.5)
    assert metadata["estimated_duration_minutes"] == 7.5
    assert metadata["question_count"] == 5
    assert metadata["content_type"] == "practice_quiz"
    assert "word_count" in metadata


def test_api_called_with_tools(mocker):
    """Test that API is called with tools parameter for structured output."""
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_PRACTICE_QUIZ_DATA)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    # Generate practice quiz
    generator = PracticeQuizGenerator()
    generator.generate(
        schema=PracticeQuizSchema,
        learning_objective="Define Python functions",
        topic="Python Functions",
        bloom_level="apply",
        num_questions=3
    )

    # Verify API was called with tools
    mock_client.messages.create.assert_called_once()
    call_kwargs = mock_client.messages.create.call_args[1]
    assert "tools" in call_kwargs
    assert len(call_kwargs["tools"]) == 1
    assert call_kwargs["tools"][0]["name"] == "output_structured"
    assert "tool_choice" in call_kwargs
