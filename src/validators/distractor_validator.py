"""DistractorValidator for quiz distractor quality analysis.

Validates quiz content for:
- Correct answer count (must be exactly 1 per question)
- Distractor quality (similarity to correct answer)
- Distractor count (recommends 2-3 per question)
- Distractor plausibility (minimum length check)
"""

import json
from typing import Dict, Any, List
from difflib import SequenceMatcher

from src.validators.validation_result import ValidationResult


class DistractorValidator:
    """Validates distractor quality in quiz content.

    Checks for:
    - Multiple correct answers (error)
    - No correct answer (error)
    - Distractors too similar to correct answer (error, >85% similarity)
    - Only 1 distractor (warning, recommends 2-3)
    - Implausible distractors (error, <5 characters)
    """

    SIMILARITY_THRESHOLD = 0.85
    MIN_DISTRACTOR_LENGTH = 5
    RECOMMENDED_MIN_DISTRACTORS = 2

    def validate_quiz(self, quiz_content: str) -> ValidationResult:
        """Validate quiz content for distractor quality.

        Args:
            quiz_content: JSON string containing quiz data with questions and options

        Returns:
            ValidationResult with errors, warnings, and metrics
        """
        errors = []
        warnings = []
        suggestions = []

        # Parse JSON
        try:
            quiz_data = json.loads(quiz_content)
            if "questions" not in quiz_data:
                return self._error_result("Invalid quiz content: missing 'questions' field")
            questions = quiz_data["questions"]
        except json.JSONDecodeError:
            return self._error_result("Invalid quiz content: malformed JSON")

        # Track metrics
        total_questions = len(questions)
        flagged_questions = set()

        # Validate each question
        for q_idx, question in enumerate(questions, start=1):
            question_number = f"Q{q_idx}"
            options = question.get("options", [])

            # Count correct answers
            correct_answers = [opt for opt in options if opt.get("is_correct", False)]
            distractors = [opt for opt in options if not opt.get("is_correct", False)]

            # Check for multiple correct answers
            if len(correct_answers) > 1:
                errors.append(f"{question_number}: Multiple correct answers (found {len(correct_answers)})")
                flagged_questions.add(q_idx)

            # Check for no correct answer
            if len(correct_answers) == 0:
                errors.append(f"{question_number}: No correct answer marked")
                flagged_questions.add(q_idx)

            # Check distractor count
            if len(distractors) == 1:
                warnings.append(f"{question_number}: Only 1 distractor (recommended 2-3)")
                flagged_questions.add(q_idx)

            # Check distractor quality (only if we have a correct answer)
            if len(correct_answers) == 1:
                correct_text = correct_answers[0].get("text", "")

                for dist_idx, distractor in enumerate(distractors):
                    dist_text = distractor.get("text", "")

                    # Check for implausible distractors (too short)
                    if len(dist_text) < self.MIN_DISTRACTOR_LENGTH:
                        errors.append(
                            f"{question_number}: Implausible distractor too short "
                            f"('{dist_text}' is {len(dist_text)} chars, minimum {self.MIN_DISTRACTOR_LENGTH})"
                        )
                        flagged_questions.add(q_idx)

                    # Check for similarity to correct answer
                    similarity = self._calculate_similarity(correct_text, dist_text)
                    if similarity > self.SIMILARITY_THRESHOLD:
                        errors.append(
                            f"{question_number}: Distractor too similar to correct answer "
                            f"({int(similarity * 100)}% similarity)"
                        )
                        flagged_questions.add(q_idx)

        # Calculate distractor quality score
        clean_questions = total_questions - len(flagged_questions)
        quality_score = int((clean_questions / total_questions * 100)) if total_questions > 0 else 0

        metrics = {
            "total_questions": total_questions,
            "flagged_questions": len(flagged_questions),
            "distractor_quality_score": quality_score
        }

        is_valid = len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            metrics=metrics
        )

    def _error_result(self, error_message: str) -> ValidationResult:
        """Create an error ValidationResult with empty metrics.

        Args:
            error_message: Error message to include

        Returns:
            ValidationResult with is_valid=False and zero metrics
        """
        return ValidationResult(
            is_valid=False,
            errors=[error_message],
            metrics={"total_questions": 0, "flagged_questions": 0, "distractor_quality_score": 0}
        )

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two strings using SequenceMatcher.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity ratio between 0.0 and 1.0
        """
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
