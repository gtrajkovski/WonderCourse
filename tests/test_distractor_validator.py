"""Tests for DistractorValidator (TDD).

Tests distractor quality analysis for quiz content:
1. Multiple correct answers detection
2. No correct answer detection
3. Similar distractor detection (>85% similarity to correct answer)
4. Insufficient distractor count warning (only 1 distractor)
5. Implausible distractor detection (too short)
6. Invalid JSON handling
"""

import pytest
import json

from src.validators.distractor_validator import DistractorValidator
from src.validators.validation_result import ValidationResult


class TestMultipleCorrectAnswers:
    """Tests for detecting multiple correct answers in a question."""

    def test_flags_question_with_two_correct_answers(self):
        """Test that questions with 2+ correct answers are flagged as errors."""
        validator = DistractorValidator()

        quiz_data = {
            "title": "Test Quiz",
            "questions": [
                {
                    "question_text": "What is 2+2?",
                    "options": [
                        {"text": "4", "is_correct": True, "feedback": "Correct!"},
                        {"text": "5", "is_correct": True, "feedback": "Also correct?"},
                        {"text": "3", "is_correct": False, "feedback": "Incorrect"}
                    ]
                }
            ]
        }
        quiz_content = json.dumps(quiz_data)

        result = validator.validate_quiz(quiz_content)

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "Q1: Multiple correct answers" in result.errors[0]

    def test_flags_question_with_three_correct_answers(self):
        """Test that questions with all correct answers are flagged."""
        validator = DistractorValidator()

        quiz_data = {
            "title": "Test Quiz",
            "questions": [
                {
                    "question_text": "Select all?",
                    "options": [
                        {"text": "A", "is_correct": True, "feedback": "Yes"},
                        {"text": "B", "is_correct": True, "feedback": "Yes"},
                        {"text": "C", "is_correct": True, "feedback": "Yes"}
                    ]
                }
            ]
        }
        quiz_content = json.dumps(quiz_data)

        result = validator.validate_quiz(quiz_content)

        assert result.is_valid is False
        assert "Q1: Multiple correct answers" in result.errors[0]


class TestNoCorrectAnswer:
    """Tests for detecting questions with no correct answer."""

    def test_flags_question_with_no_correct_answer(self):
        """Test that questions with 0 correct answers are flagged as errors."""
        validator = DistractorValidator()

        quiz_data = {
            "title": "Test Quiz",
            "questions": [
                {
                    "question_text": "What is the capital of France?",
                    "options": [
                        {"text": "London", "is_correct": False, "feedback": "No"},
                        {"text": "Berlin", "is_correct": False, "feedback": "No"},
                        {"text": "Madrid", "is_correct": False, "feedback": "No"}
                    ]
                }
            ]
        }
        quiz_content = json.dumps(quiz_data)

        result = validator.validate_quiz(quiz_content)

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "Q1: No correct answer" in result.errors[0]


class TestSimilarDistractor:
    """Tests for detecting distractors too similar to correct answer."""

    def test_flags_distractor_85_percent_similar_to_correct(self):
        """Test that distractors >85% similar to correct answer are flagged."""
        validator = DistractorValidator()

        quiz_data = {
            "title": "Test Quiz",
            "questions": [
                {
                    "question_text": "What is object-oriented programming?",
                    "options": [
                        {
                            "text": "A programming paradigm based on objects containing data and methods",
                            "is_correct": True,
                            "feedback": "Correct!"
                        },
                        {
                            "text": "A programming paradigm based on objects containing data and method",  # 95% similar
                            "is_correct": False,
                            "feedback": "Close but not quite"
                        },
                        {
                            "text": "Functional programming",
                            "is_correct": False,
                            "feedback": "Different paradigm"
                        }
                    ]
                }
            ]
        }
        quiz_content = json.dumps(quiz_data)

        result = validator.validate_quiz(quiz_content)

        assert result.is_valid is False
        assert len(result.errors) >= 1
        assert any("Q1: Distractor too similar" in error for error in result.errors)

    def test_passes_distractor_below_similarity_threshold(self):
        """Test that distractors with <85% similarity are not flagged."""
        validator = DistractorValidator()

        quiz_data = {
            "title": "Test Quiz",
            "questions": [
                {
                    "question_text": "What is Python?",
                    "options": [
                        {"text": "A high-level programming language", "is_correct": True, "feedback": "Yes"},
                        {"text": "A type of snake", "is_correct": False, "feedback": "No"},
                        {"text": "A web framework", "is_correct": False, "feedback": "No"}
                    ]
                }
            ]
        }
        quiz_content = json.dumps(quiz_data)

        result = validator.validate_quiz(quiz_content)

        # Should not have similarity errors
        assert not any("too similar" in error.lower() for error in result.errors)


class TestInsufficientDistractors:
    """Tests for warning when only 1 distractor exists."""

    def test_warns_when_only_one_distractor(self):
        """Test that questions with only 1 distractor get a warning."""
        validator = DistractorValidator()

        quiz_data = {
            "title": "Test Quiz",
            "questions": [
                {
                    "question_text": "Is the sky blue?",
                    "options": [
                        {"text": "Yes", "is_correct": True, "feedback": "Correct"},
                        {"text": "No", "is_correct": False, "feedback": "Incorrect"}
                    ]
                }
            ]
        }
        quiz_content = json.dumps(quiz_data)

        result = validator.validate_quiz(quiz_content)

        assert len(result.warnings) >= 1
        assert any("Q1: Only 1 distractor" in warning for warning in result.warnings)
        assert any("recommended 2-3" in warning for warning in result.warnings)

    def test_no_warning_with_two_distractors(self):
        """Test that no warning is given for 2 distractors."""
        validator = DistractorValidator()

        quiz_data = {
            "title": "Test Quiz",
            "questions": [
                {
                    "question_text": "What is 1+1?",
                    "options": [
                        {"text": "2", "is_correct": True, "feedback": "Yes"},
                        {"text": "3", "is_correct": False, "feedback": "No"},
                        {"text": "4", "is_correct": False, "feedback": "No"}
                    ]
                }
            ]
        }
        quiz_content = json.dumps(quiz_data)

        result = validator.validate_quiz(quiz_content)

        # Should not have distractor count warnings
        assert not any("Only 1 distractor" in warning for warning in result.warnings)


class TestImplausibleDistractor:
    """Tests for detecting implausible distractors that are too short."""

    def test_flags_distractor_less_than_5_chars(self):
        """Test that distractors <5 characters are flagged as errors."""
        validator = DistractorValidator()

        quiz_data = {
            "title": "Test Quiz",
            "questions": [
                {
                    "question_text": "What is the full name of the HTTP protocol?",
                    "options": [
                        {"text": "HyperText Transfer Protocol", "is_correct": True, "feedback": "Correct"},
                        {"text": "Hi", "is_correct": False, "feedback": "Too short"},
                        {"text": "HTTPS secure version", "is_correct": False, "feedback": "Different protocol"}
                    ]
                }
            ]
        }
        quiz_content = json.dumps(quiz_data)

        result = validator.validate_quiz(quiz_content)

        assert result.is_valid is False
        assert len(result.errors) >= 1
        assert any("Q1: Implausible distractor too short" in error for error in result.errors)

    def test_passes_distractor_at_5_chars(self):
        """Test that distractors with exactly 5 characters pass."""
        validator = DistractorValidator()

        quiz_data = {
            "title": "Test Quiz",
            "questions": [
                {
                    "question_text": "What is the answer?",
                    "options": [
                        {"text": "Correct answer", "is_correct": True, "feedback": "Yes"},
                        {"text": "Wrong", "is_correct": False, "feedback": "No"},  # 5 chars
                        {"text": "Also wrong", "is_correct": False, "feedback": "No"}
                    ]
                }
            ]
        }
        quiz_content = json.dumps(quiz_data)

        result = validator.validate_quiz(quiz_content)

        # Should not have short distractor errors
        assert not any("too short" in error.lower() for error in result.errors)


class TestInvalidJSON:
    """Tests for handling invalid JSON input."""

    def test_flags_invalid_json(self):
        """Test that invalid JSON is flagged as an error."""
        validator = DistractorValidator()

        quiz_content = "not valid json {"

        result = validator.validate_quiz(quiz_content)

        assert result.is_valid is False
        assert len(result.errors) >= 1
        assert any("Invalid quiz content" in error for error in result.errors)

    def test_flags_missing_questions_key(self):
        """Test that JSON without 'questions' key is flagged."""
        validator = DistractorValidator()

        quiz_data = {"title": "Test Quiz"}  # Missing 'questions'
        quiz_content = json.dumps(quiz_data)

        result = validator.validate_quiz(quiz_content)

        assert result.is_valid is False
        assert any("Invalid quiz content" in error for error in result.errors)


class TestMetrics:
    """Tests for validation metrics."""

    def test_calculates_total_questions(self):
        """Test that total_questions metric is calculated correctly."""
        validator = DistractorValidator()

        quiz_data = {
            "title": "Test Quiz",
            "questions": [
                {
                    "question_text": "Q1?",
                    "options": [
                        {"text": "A", "is_correct": True, "feedback": "Yes"},
                        {"text": "B", "is_correct": False, "feedback": "No"},
                        {"text": "C", "is_correct": False, "feedback": "No"}
                    ]
                },
                {
                    "question_text": "Q2?",
                    "options": [
                        {"text": "X", "is_correct": True, "feedback": "Yes"},
                        {"text": "Y", "is_correct": False, "feedback": "No"},
                        {"text": "Z", "is_correct": False, "feedback": "No"}
                    ]
                }
            ]
        }
        quiz_content = json.dumps(quiz_data)

        result = validator.validate_quiz(quiz_content)

        assert result.metrics["total_questions"] == 2

    def test_calculates_flagged_questions(self):
        """Test that flagged_questions metric counts questions with issues."""
        validator = DistractorValidator()

        quiz_data = {
            "title": "Test Quiz",
            "questions": [
                {
                    "question_text": "Q1 - Good question",
                    "options": [
                        {"text": "Good answer", "is_correct": True, "feedback": "Yes"},
                        {"text": "Good distractor 1", "is_correct": False, "feedback": "No"},
                        {"text": "Good distractor 2", "is_correct": False, "feedback": "No"}
                    ]
                },
                {
                    "question_text": "Q2 - Has issue",
                    "options": [
                        {"text": "Answer", "is_correct": False, "feedback": "No"},  # No correct answer
                        {"text": "Another", "is_correct": False, "feedback": "No"},
                        {"text": "Third", "is_correct": False, "feedback": "No"}
                    ]
                }
            ]
        }
        quiz_content = json.dumps(quiz_data)

        result = validator.validate_quiz(quiz_content)

        assert result.metrics["flagged_questions"] == 1

    def test_calculates_distractor_quality_score(self):
        """Test that distractor_quality_score is calculated as percentage of clean questions."""
        validator = DistractorValidator()

        quiz_data = {
            "title": "Test Quiz",
            "questions": [
                {
                    "question_text": "Q1 - Good",
                    "options": [
                        {"text": "Correct", "is_correct": True, "feedback": "Yes"},
                        {"text": "Wrong 1", "is_correct": False, "feedback": "No"},
                        {"text": "Wrong 2", "is_correct": False, "feedback": "No"}
                    ]
                },
                {
                    "question_text": "Q2 - Good",
                    "options": [
                        {"text": "Correct", "is_correct": True, "feedback": "Yes"},
                        {"text": "Wrong 1", "is_correct": False, "feedback": "No"},
                        {"text": "Wrong 2", "is_correct": False, "feedback": "No"}
                    ]
                },
                {
                    "question_text": "Q3 - Bad",
                    "options": [
                        {"text": "Answer", "is_correct": False, "feedback": "No"},  # No correct
                        {"text": "Another", "is_correct": False, "feedback": "No"}
                    ]
                },
                {
                    "question_text": "Q4 - Bad",
                    "options": [
                        {"text": "Correct", "is_correct": True, "feedback": "Yes"},
                        {"text": "Hi", "is_correct": False, "feedback": "No"}  # Too short
                    ]
                }
            ]
        }
        quiz_content = json.dumps(quiz_data)

        result = validator.validate_quiz(quiz_content)

        # 2 good questions out of 4 = 50%
        assert result.metrics["distractor_quality_score"] == 50


class TestMultipleIssuesPerQuestion:
    """Tests for questions with multiple issues."""

    def test_reports_all_issues_for_single_question(self):
        """Test that all issues in a single question are reported."""
        validator = DistractorValidator()

        quiz_data = {
            "title": "Test Quiz",
            "questions": [
                {
                    "question_text": "Bad question",
                    "options": [
                        {"text": "Correct answer", "is_correct": True, "feedback": "Yes"},
                        {"text": "No", "is_correct": False, "feedback": "Too short"}  # Only 1 distractor AND too short
                    ]
                }
            ]
        }
        quiz_content = json.dumps(quiz_data)

        result = validator.validate_quiz(quiz_content)

        # Should have both an error (short distractor) and warning (only 1 distractor)
        assert len(result.errors) >= 1
        assert len(result.warnings) >= 1
        assert any("too short" in error.lower() for error in result.errors)
        assert any("Only 1 distractor" in warning for warning in result.warnings)
