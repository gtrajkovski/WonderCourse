"""Tests for QuizGenerator using TDD with mocked Anthropic API."""

import json
import pytest
from unittest.mock import Mock, MagicMock
from src.generators.quiz_generator import QuizGenerator
from src.generators.schemas.quiz import QuizSchema, QuizQuestion, QuizOption


# Sample quiz data as dict
SAMPLE_QUIZ_DATA = {
    "title": "Python Functions Quiz",
    "questions": [
        {
            "question_text": "What is the correct syntax for defining a function in Python?",
            "options": [
                {
                    "text": "def my_function():",
                    "is_correct": True,
                    "feedback": "Correct! Python uses 'def' keyword followed by function name and parentheses."
                },
                {
                    "text": "function my_function():",
                    "is_correct": False,
                    "feedback": "Incorrect. Python uses 'def' keyword, not 'function'."
                },
                {
                    "text": "func my_function():",
                    "is_correct": False,
                    "feedback": "Incorrect. Python uses 'def' keyword, not 'func'."
                }
            ],
            "bloom_level": "remember",
            "explanation": "Python function definitions always start with the 'def' keyword."
        },
        {
            "question_text": "What will this function return? def add(a, b): return a + b",
            "options": [
                {
                    "text": "The sum of a and b",
                    "is_correct": False,
                    "feedback": "Close, but this answer doesn't capture that it returns a value."
                },
                {
                    "text": "A value representing the sum of parameters a and b",
                    "is_correct": True,
                    "feedback": "Correct! The function returns the result of a + b."
                },
                {
                    "text": "Nothing, it prints the sum",
                    "is_correct": False,
                    "feedback": "Incorrect. The function uses return, not print."
                }
            ],
            "bloom_level": "understand",
            "explanation": "The return statement sends back the calculated value to the caller."
        },
        {
            "question_text": "Which function call will raise an error?",
            "options": [
                {
                    "text": "add(1, 2)",
                    "is_correct": False,
                    "feedback": "This is valid - two positional arguments."
                },
                {
                    "text": "add()",
                    "is_correct": True,
                    "feedback": "Correct! This raises TypeError because add() requires 2 arguments."
                },
                {
                    "text": "add(a=1, b=2)",
                    "is_correct": False,
                    "feedback": "This is valid - two keyword arguments."
                }
            ],
            "bloom_level": "apply",
            "explanation": "Python functions require all positional parameters unless defaults are provided."
        }
    ],
    "passing_score_percentage": 70,
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
    """Test that generate() returns a valid QuizSchema instance."""
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_QUIZ_DATA)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    # Generate quiz
    generator = QuizGenerator()
    quiz, metadata = generator.generate(
        schema=QuizSchema,
        learning_objective="Define and call Python functions",
        topic="Python Functions",
        bloom_level="apply",
        num_questions=3,
        difficulty="intermediate"
    )

    # Verify it's a valid QuizSchema
    assert isinstance(quiz, QuizSchema)
    assert quiz.title == "Python Functions Quiz"
    assert len(quiz.questions) == 3
    assert quiz.passing_score_percentage == 70


def test_each_question_has_one_correct(mocker):
    """Test that each question has exactly one correct answer."""
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_QUIZ_DATA)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    # Generate quiz
    generator = QuizGenerator()
    quiz, _ = generator.generate(
        schema=QuizSchema,
        learning_objective="Define and call Python functions",
        topic="Python Functions",
        bloom_level="apply",
        num_questions=3
    )

    # Verify each question has exactly 1 correct answer
    for question in quiz.questions:
        correct_count = sum(1 for opt in question.options if opt.is_correct)
        assert correct_count == 1, f"Question '{question.question_text}' has {correct_count} correct answers"


def test_system_prompt_contains_distractor_guidelines():
    """Test that system prompt includes distractor quality guidelines."""
    generator = QuizGenerator()
    prompt = generator.system_prompt

    # Verify distractor guidelines are present
    assert "distractor" in prompt.lower() or "plausible" in prompt.lower()
    assert "misconception" in prompt.lower() or "common error" in prompt.lower()


def test_build_user_prompt_includes_bloom_level(mocker):
    """Test that build_user_prompt includes bloom_level and num_questions."""
    mock_client = MagicMock()
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    generator = QuizGenerator()

    prompt = generator.build_user_prompt(
        learning_objective="Define Python functions",
        topic="Python Functions",
        bloom_level="apply",
        num_questions=5,
        difficulty="intermediate"
    )

    # Verify key parameters are in prompt
    assert "apply" in prompt.lower()
    assert "5" in prompt or "five" in prompt.lower()
    assert "Python functions" in prompt or "Python Functions" in prompt


def test_extract_metadata_calculates_duration():
    """Test that extract_metadata calculates duration at 1.5 min per question."""
    generator = QuizGenerator()

    # Create a sample quiz with 5 questions
    quiz = QuizSchema(
        title="Test Quiz",
        questions=[
            QuizQuestion(
                question_text=f"Question {i}?",
                options=[
                    QuizOption(text="Option A", is_correct=True, feedback="Correct"),
                    QuizOption(text="Option B", is_correct=False, feedback="Wrong"),
                    QuizOption(text="Option C", is_correct=False, feedback="Wrong")
                ],
                bloom_level="apply",
                explanation="Explanation"
            )
            for i in range(5)
        ],
        passing_score_percentage=70,
        learning_objective="Test objective"
    )

    metadata = generator.extract_metadata(quiz)

    # Verify duration calculation (5 questions * 1.5 minutes = 7.5)
    assert metadata["estimated_duration_minutes"] == 7.5
    assert metadata["question_count"] == 5
    assert metadata["content_type"] == "quiz"
    assert "word_count" in metadata


def test_validate_answer_distribution_balanced():
    """Test validate_answer_distribution detects balanced answer keys."""
    # Create quiz with varied correct answer positions
    quiz = QuizSchema(
        title="Balanced Quiz",
        questions=[
            QuizQuestion(
                question_text="Q1",
                options=[
                    QuizOption(text="A", is_correct=True, feedback="Correct"),
                    QuizOption(text="B", is_correct=False, feedback="Wrong"),
                    QuizOption(text="C", is_correct=False, feedback="Wrong")
                ],
                bloom_level="apply",
                explanation="Explanation"
            ),
            QuizQuestion(
                question_text="Q2",
                options=[
                    QuizOption(text="A", is_correct=False, feedback="Wrong"),
                    QuizOption(text="B", is_correct=True, feedback="Correct"),
                    QuizOption(text="C", is_correct=False, feedback="Wrong")
                ],
                bloom_level="apply",
                explanation="Explanation"
            ),
            QuizQuestion(
                question_text="Q3",
                options=[
                    QuizOption(text="A", is_correct=False, feedback="Wrong"),
                    QuizOption(text="B", is_correct=False, feedback="Wrong"),
                    QuizOption(text="C", is_correct=True, feedback="Correct")
                ],
                bloom_level="apply",
                explanation="Explanation"
            )
        ],
        passing_score_percentage=70,
        learning_objective="Test"
    )

    result = QuizGenerator.validate_answer_distribution(quiz)

    assert result["balanced"] is True
    assert result["distribution"] == {0: 1, 1: 1, 2: 1}


def test_validate_answer_distribution_biased():
    """Test validate_answer_distribution detects biased answer keys."""
    # Create quiz where all correct answers are position 0
    quiz = QuizSchema(
        title="Biased Quiz",
        questions=[
            QuizQuestion(
                question_text=f"Q{i}",
                options=[
                    QuizOption(text="A", is_correct=True, feedback="Correct"),
                    QuizOption(text="B", is_correct=False, feedback="Wrong"),
                    QuizOption(text="C", is_correct=False, feedback="Wrong")
                ],
                bloom_level="apply",
                explanation="Explanation"
            )
            for i in range(4)
        ],
        passing_score_percentage=70,
        learning_objective="Test"
    )

    result = QuizGenerator.validate_answer_distribution(quiz)

    assert result["balanced"] is False
    assert result["distribution"] == {0: 4}


def test_api_called_with_tools(mocker):
    """Test that API is called with tools parameter for structured output."""
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_QUIZ_DATA)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    # Generate quiz
    generator = QuizGenerator()
    generator.generate(
        schema=QuizSchema,
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
