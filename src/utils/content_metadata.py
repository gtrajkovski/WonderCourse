"""Utilities for calculating content metadata (word counts, duration estimates).

Provides deterministic calculations based on industry-standard rates:
- Reading: 238 WPM (adult non-fiction average)
- Speaking: 150 WPM (video delivery rate)
- Quiz: 1.5 minutes per question
"""


class ContentMetadata:
    """Static methods for content metadata calculations."""

    # Industry-standard rates
    WPM_READING = 238    # Adult non-fiction average
    WPM_SPEAKING = 150   # Video delivery rate
    MINUTES_PER_QUIZ_QUESTION = 1.5

    @staticmethod
    def count_words(text) -> int:
        """Count words in text or structured content.

        Args:
            text: Text string or dict to count words in

        Returns:
            int: Number of words (split on whitespace)
        """
        # Handle dict/structured content by converting to JSON string
        if isinstance(text, dict):
            import json
            text = json.dumps(text)

        if not text or not text.strip():
            return 0
        return len(text.split())

    @staticmethod
    def estimate_reading_duration(word_count: int) -> float:
        """Estimate reading duration in minutes.

        Uses 238 WPM (adult non-fiction average).

        Args:
            word_count: Number of words

        Returns:
            float: Duration in minutes, rounded to 1 decimal place
        """
        duration = word_count / ContentMetadata.WPM_READING
        return round(duration, 1)

    @staticmethod
    def estimate_video_duration(word_count: int) -> float:
        """Estimate video duration in minutes.

        Uses 150 WPM (speaking rate for instructional video).

        Args:
            word_count: Number of words in script

        Returns:
            float: Duration in minutes, rounded to 1 decimal place
        """
        duration = word_count / ContentMetadata.WPM_SPEAKING
        return round(duration, 1)

    @staticmethod
    def estimate_quiz_duration(num_questions: int) -> float:
        """Estimate quiz completion duration in minutes.

        Uses 1.5 minutes per question.

        Args:
            num_questions: Number of questions in quiz

        Returns:
            float: Duration in minutes, rounded to 1 decimal place
        """
        duration = num_questions * ContentMetadata.MINUTES_PER_QUIZ_QUESTION
        return round(duration, 1)
