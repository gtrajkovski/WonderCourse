"""Tests for CTA validation in standards validator."""

import pytest
from src.validators.standards_validator import StandardsValidator, ViolationSeverity
from src.core.models import ContentStandardsProfile


@pytest.fixture
def default_standards():
    """Create default standards profile with CTA validation enabled.

    Disables section timing validation to focus tests on CTA validation.
    """
    return ContentStandardsProfile(
        video_cta_max_words=35,
        video_cta_forbid_activity_previews=True,
        video_section_timing_enabled=False,  # Disable to focus on CTA tests
        video_visual_cue_enabled=False,  # Disable visual cue validation
    )


def make_video_content(cta_text: str) -> dict:
    """Helper to create video content with a CTA section."""
    return {
        "sections": [
            {"section_name": "Hook", "script_text": "Welcome to this video."},
            {"section_name": "Objective", "script_text": "You will learn about APIs."},
            {"section_name": "Content", "script_text": "APIs are interfaces that allow applications to communicate."},
            {"section_name": "IVQ", "script_text": "What is an API?"},
            {"section_name": "Summary", "script_text": "We covered the basics of APIs."},
            {"section_name": "CTA", "script_text": cta_text},
        ],
        "estimated_duration_min": 5,
        "full_script": ""
    }


# ===========================
# CTA Word Count Tests
# ===========================

def test_cta_within_word_limit(default_standards):
    """Test that CTA within word limit passes."""
    validator = StandardsValidator(default_standards)
    content = make_video_content("Start building your own APIs today!")

    violations = validator.validate("video", content)

    cta_violations = [v for v in violations if v.field == "sections.cta"]
    assert len(cta_violations) == 0


def test_cta_exceeds_word_limit(default_standards):
    """Test that CTA exceeding word limit is flagged."""
    validator = StandardsValidator(default_standards)
    # Create a CTA with more than 35 words
    long_cta = " ".join(["word"] * 40)
    content = make_video_content(long_cta)

    violations = validator.validate("video", content)

    cta_word_violations = [v for v in violations if "word count" in v.rule.lower()]
    assert len(cta_word_violations) == 1
    assert cta_word_violations[0].severity == ViolationSeverity.WARNING


# ===========================
# CTA Forbidden Phrase Tests
# ===========================

def test_cta_forbidden_phrase_coach_dialogue(default_standards):
    """Test that CTA mentioning 'coach dialogue' is flagged."""
    validator = StandardsValidator(default_standards)
    content = make_video_content("In the coach dialogue, you'll practice these skills.")

    violations = validator.validate("video", content)

    cta_violations = [v for v in violations if v.field == "sections.cta" and "preview" in v.rule.lower()]
    assert len(cta_violations) >= 1


def test_cta_forbidden_phrase_graded_assessment(default_standards):
    """Test that CTA mentioning 'graded assessment' is flagged."""
    validator = StandardsValidator(default_standards)
    content = make_video_content("Prepare for the graded assessment coming up.")

    violations = validator.validate("video", content)

    cta_violations = [v for v in violations if v.field == "sections.cta" and "preview" in v.rule.lower()]
    assert len(cta_violations) >= 1


# ===========================
# CTA Pattern Tests (v1.2.0)
# ===========================

def test_cta_pattern_next_youll(default_standards):
    """Test that 'next you'll' pattern is flagged."""
    validator = StandardsValidator(default_standards)
    content = make_video_content("Next, you'll work through a reading on this topic.")

    violations = validator.validate("video", content)

    cta_violations = [v for v in violations if v.field == "sections.cta"]
    assert len(cta_violations) >= 1


def test_cta_pattern_in_the_next_video(default_standards):
    """Test that 'in the next video' pattern is flagged."""
    validator = StandardsValidator(default_standards)
    content = make_video_content("In the next video, we will explore advanced topics.")

    violations = validator.validate("video", content)

    cta_violations = [v for v in violations if v.field == "sections.cta"]
    assert len(cta_violations) >= 1


def test_cta_pattern_upcoming_quiz(default_standards):
    """Test that 'upcoming quiz' pattern is flagged."""
    validator = StandardsValidator(default_standards)
    content = make_video_content("The upcoming quiz will test your knowledge.")

    violations = validator.validate("video", content)

    cta_violations = [v for v in violations if v.field == "sections.cta"]
    assert len(cta_violations) >= 1


def test_cta_pattern_take_the_quiz(default_standards):
    """Test that 'take the quiz' pattern is flagged."""
    validator = StandardsValidator(default_standards)
    content = make_video_content("Now take the quiz to test your understanding.")

    violations = validator.validate("video", content)

    cta_violations = [v for v in violations if v.field == "sections.cta"]
    assert len(cta_violations) >= 1


def test_cta_pattern_work_through_reading(default_standards):
    """Test that 'work through a reading' pattern is flagged."""
    validator = StandardsValidator(default_standards)
    content = make_video_content("Go ahead and work through a reading on this topic.")

    violations = validator.validate("video", content)

    cta_violations = [v for v in violations if v.field == "sections.cta"]
    assert len(cta_violations) >= 1


# ===========================
# Good CTA Tests
# ===========================

def test_good_cta_motivation_only(default_standards):
    """Test that a good motivational CTA passes validation."""
    validator = StandardsValidator(default_standards)
    content = make_video_content("Put these concepts into practice and start building something amazing!")

    violations = validator.validate("video", content)

    cta_violations = [v for v in violations if v.field == "sections.cta"]
    assert len(cta_violations) == 0


def test_good_cta_call_to_action(default_standards):
    """Test that a good call-to-action CTA passes validation."""
    validator = StandardsValidator(default_standards)
    content = make_video_content("Ready to try this yourself? Open your code editor and experiment with what you've learned!")

    violations = validator.validate("video", content)

    # Should not have activity preview violations
    preview_violations = [v for v in violations if v.field == "sections.cta" and "preview" in v.rule.lower()]
    assert len(preview_violations) == 0
