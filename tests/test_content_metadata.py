"""Tests for content metadata utilities."""

import pytest
from src.utils.content_metadata import ContentMetadata


class TestContentMetadata:
    """Test suite for ContentMetadata calculations."""

    def test_count_words_empty_string(self):
        """Empty string should return 0 words."""
        assert ContentMetadata.count_words("") == 0

    def test_count_words_whitespace_only(self):
        """Whitespace-only string should return 0 words."""
        assert ContentMetadata.count_words("   \n  \t  ") == 0

    def test_count_words_simple(self):
        """Simple two-word string should return 2."""
        assert ContentMetadata.count_words("hello world") == 2

    def test_count_words_multiple(self):
        """Multiple words with various whitespace."""
        text = "This is a test sentence with seven words."
        assert ContentMetadata.count_words(text) == 8

    def test_estimate_reading_duration_exact(self):
        """238 words should be exactly 1.0 minute."""
        assert ContentMetadata.estimate_reading_duration(238) == 1.0

    def test_estimate_reading_duration_double(self):
        """476 words should be exactly 2.0 minutes."""
        assert ContentMetadata.estimate_reading_duration(476) == 2.0

    def test_estimate_reading_duration_rounding(self):
        """Duration should round to 1 decimal place."""
        # 250 words / 238 WPM = 1.050... -> rounds to 1.1
        assert ContentMetadata.estimate_reading_duration(250) == 1.1

    def test_estimate_video_duration_exact(self):
        """150 words should be exactly 1.0 minute."""
        assert ContentMetadata.estimate_video_duration(150) == 1.0

    def test_estimate_video_duration_multiple(self):
        """750 words should be exactly 5.0 minutes."""
        assert ContentMetadata.estimate_video_duration(750) == 5.0

    def test_estimate_video_duration_rounding(self):
        """Duration should round to 1 decimal place."""
        # 225 words / 150 WPM = 1.5 minutes
        assert ContentMetadata.estimate_video_duration(225) == 1.5

    def test_estimate_quiz_duration_5_questions(self):
        """5 questions at 1.5 min each = 7.5 minutes."""
        assert ContentMetadata.estimate_quiz_duration(5) == 7.5

    def test_estimate_quiz_duration_10_questions(self):
        """10 questions at 1.5 min each = 15.0 minutes."""
        assert ContentMetadata.estimate_quiz_duration(10) == 15.0

    def test_estimate_quiz_duration_single(self):
        """1 question should be 1.5 minutes."""
        assert ContentMetadata.estimate_quiz_duration(1) == 1.5

    def test_reading_wpm_constant(self):
        """Verify WPM_READING constant is set correctly."""
        assert ContentMetadata.WPM_READING == 238

    def test_speaking_wpm_constant(self):
        """Verify WPM_SPEAKING constant is set correctly."""
        assert ContentMetadata.WPM_SPEAKING == 150

    def test_quiz_minutes_constant(self):
        """Verify MINUTES_PER_QUIZ_QUESTION constant is set correctly."""
        assert ContentMetadata.MINUTES_PER_QUIZ_QUESTION == 1.5
