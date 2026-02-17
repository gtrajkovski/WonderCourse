"""Tests for quiz answer distribution validation."""

import pytest
from src.validators.standards_validator import StandardsValidator, ViolationSeverity
from src.core.models import ContentStandardsProfile


@pytest.fixture
def strict_standards():
    """Create strict standards profile for quiz validation."""
    return ContentStandardsProfile(
        quiz_require_balanced_distribution=True,
        quiz_max_distribution_skew_percent=35,
        quiz_min_distribution_percent=15,
    )


def make_quiz_content(questions: list) -> dict:
    """Helper to create quiz content from question specs."""
    return {"questions": questions}


def make_question(correct_answer: str, options: list = None) -> dict:
    """Helper to create a quiz question.

    Args:
        correct_answer: The correct answer letter (A, B, C, D).
        options: Optional list of option dicts with text and label.
    """
    if options is None:
        options = [
            {"label": "A", "text": "Option A text here"},
            {"label": "B", "text": "Option B text here"},
            {"label": "C", "text": "Option C text here"},
            {"label": "D", "text": "Option D text here"},
        ]
    return {
        "correct_answer": correct_answer,
        "options": options,
    }


# ===========================
# Distribution Tests
# ===========================

def test_balanced_distribution_passes(strict_standards):
    """Test that balanced answer distribution passes."""
    validator = StandardsValidator(strict_standards)
    questions = [
        make_question("A"),
        make_question("B"),
        make_question("C"),
        make_question("D"),
    ]
    content = make_quiz_content(questions)

    violations = validator.validate("quiz", content)

    dist_violations = [v for v in violations if "distribution" in v.rule.lower()]
    assert len(dist_violations) == 0


def test_skewed_distribution_flagged(strict_standards):
    """Test that skewed distribution (>35%) is flagged."""
    validator = StandardsValidator(strict_standards)
    # 6 out of 10 = 60% for answer A
    questions = [
        make_question("A"), make_question("A"), make_question("A"),
        make_question("A"), make_question("A"), make_question("A"),
        make_question("B"), make_question("C"), make_question("D"),
        make_question("B"),
    ]
    content = make_quiz_content(questions)

    violations = validator.validate("quiz", content)

    max_violations = [v for v in violations if "maximum" in v.rule.lower()]
    assert len(max_violations) == 1
    assert max_violations[0].severity == ViolationSeverity.WARNING


# ===========================
# Pattern Detection Tests
# ===========================

def test_repeating_pattern_detected(strict_standards):
    """Test that repeating pattern ABCD,ABCD is detected."""
    validator = StandardsValidator(strict_standards)
    # A,B,C,D,A,B,C,D pattern
    questions = [
        make_question("A"), make_question("B"), make_question("C"), make_question("D"),
        make_question("A"), make_question("B"), make_question("C"), make_question("D"),
    ]
    content = make_quiz_content(questions)

    violations = validator.validate("quiz", content)

    pattern_violations = [v for v in violations if "pattern" in v.rule.lower()]
    assert len(pattern_violations) == 1


def test_run_pattern_detected(strict_standards):
    """Test that 3+ same answers in a row is detected."""
    validator = StandardsValidator(strict_standards)
    questions = [
        make_question("A"), make_question("A"), make_question("A"),  # Run of A
        make_question("B"), make_question("C"), make_question("D"),
    ]
    content = make_quiz_content(questions)

    violations = validator.validate("quiz", content)

    run_violations = [v for v in violations if "run" in v.rule.lower()]
    assert len(run_violations) == 1


def test_random_distribution_passes(strict_standards):
    """Test that random-looking distribution passes pattern checks."""
    validator = StandardsValidator(strict_standards)
    questions = [
        make_question("B"), make_question("A"), make_question("D"), make_question("C"),
        make_question("A"), make_question("C"), make_question("B"), make_question("D"),
    ]
    content = make_quiz_content(questions)

    violations = validator.validate("quiz", content)

    pattern_violations = [v for v in violations if "pattern" in v.rule.lower() or "run" in v.rule.lower()]
    assert len(pattern_violations) == 0


# ===========================
# Option Length Tests
# ===========================

def test_consistent_option_lengths_pass(strict_standards):
    """Test that similar option lengths pass."""
    validator = StandardsValidator(strict_standards)
    options = [
        {"label": "A", "text": "Short text"},
        {"label": "B", "text": "Medium text"},
        {"label": "C", "text": "Another text"},
        {"label": "D", "text": "Final text"},
    ]
    questions = [make_question("A", options)]
    content = make_quiz_content(questions)

    violations = validator.validate("quiz", content)

    length_violations = [v for v in violations if "length" in v.rule.lower()]
    assert len(length_violations) == 0


def test_correct_answer_longest_flagged(strict_standards):
    """Test that correct answer being longest is flagged."""
    validator = StandardsValidator(strict_standards)
    options = [
        {"label": "A", "text": "This is a very long correct answer that contains much more detail than any other option available."},
        {"label": "B", "text": "Short"},
        {"label": "C", "text": "Short"},
        {"label": "D", "text": "Short"},
    ]
    questions = [make_question("A", options)]
    content = make_quiz_content(questions)

    violations = validator.validate("quiz", content)

    longest_violations = [v for v in violations if "longest" in v.rule.lower()]
    assert len(longest_violations) == 1
    assert longest_violations[0].severity == ViolationSeverity.WARNING


def test_correct_answer_shortest_flagged(strict_standards):
    """Test that correct answer being shortest is flagged."""
    validator = StandardsValidator(strict_standards)
    options = [
        {"label": "A", "text": "Yes"},  # Correct but very short
        {"label": "B", "text": "This is a much longer distractor with lots of extra text"},
        {"label": "C", "text": "Another lengthy option with additional context"},
        {"label": "D", "text": "Yet more verbose distractor content here"},
    ]
    questions = [make_question("A", options)]
    content = make_quiz_content(questions)

    violations = validator.validate("quiz", content)

    shortest_violations = [v for v in violations if "shortest" in v.rule.lower()]
    assert len(shortest_violations) == 1
    assert shortest_violations[0].severity == ViolationSeverity.INFO
