"""QuizGenerator for creating MCQ quizzes with plausible distractors and option-level feedback."""

from typing import Tuple
from src.generators.base_generator import BaseGenerator
from src.generators.schemas.quiz import QuizSchema, QuizQuestion
from src.utils.content_metadata import ContentMetadata


class QuizGenerator(BaseGenerator[QuizSchema]):
    """Generator for creating multiple-choice quizzes with distractor quality checks.

    Produces graded MCQ quizzes with:
    - 3-4 options per question (1 correct, 2-3 plausible distractors)
    - Option-level feedback for immediate learning
    - Balanced answer distribution (correct answer not always first)
    - Bloom's taxonomy alignment
    """

    @property
    def system_prompt(self) -> str:
        """Return system prompt for quiz generation with distractor guidelines."""
        return """You are an expert assessment designer specializing in multiple-choice questions.

Your quizzes follow these MCQ best practices:

**Question Quality:**
- Clear, unambiguous question stems
- Single correct answer per question
- Align with specified Bloom's taxonomy level
- Avoid "all of the above" or "none of the above"

**Distractor Quality (CRITICAL):**
- Distractors must be plausible and represent common misconceptions
- Each distractor should reflect a specific error in understanding
- All options should have similar length and complexity
- Avoid obvious wrong answers or trick questions
- Distractors should require genuine understanding to eliminate

**Option-Level Feedback:**
- Correct answer feedback: Reinforce why it's correct
- Distractor feedback: Explain the misconception and guide toward correct understanding
- Feedback should be instructional, not just "correct" or "incorrect"

**Answer Key Balance:**
- Vary the position of correct answers across questions
- Avoid patterns (e.g., correct answer always first or always C)
- Natural distribution helps prevent test-wise guessing"""

    def build_user_prompt(
        self,
        learning_objective: str,
        topic: str,
        bloom_level: str = "apply",
        num_questions: int = 5,
        difficulty: str = "intermediate",
        audience_level: str = "intermediate",
        language: str = "English",
        standards_rules: str = ""
    ) -> str:
        """Build user prompt for quiz generation.

        Args:
            learning_objective: The learning objective being assessed
            topic: Subject matter for the quiz
            bloom_level: Bloom's taxonomy level (remember, understand, apply, etc.)
            num_questions: Number of questions to generate (default 5)
            difficulty: Difficulty level (beginner, intermediate, advanced)
            audience_level: Target audience level (beginner, intermediate, advanced)
            language: Language for content generation (default: English)
            standards_rules: Pre-built standards rules from standards_loader (optional)

        Returns:
            str: Formatted user prompt
        """
        lang_instruction = ""
        if language.lower() != "english":
            lang_instruction = f"**IMPORTANT: Generate ALL content in {language}.**\n\n"

        standards_section = ""
        if standards_rules:
            standards_section = f"{standards_rules}\n\n"

        return f"""{lang_instruction}{standards_section}**CONTEXT:**
Learning Objective: {learning_objective}
Topic: {topic}
Bloom's Taxonomy Level: {bloom_level}
Difficulty: {difficulty}

**TASK:**
Generate a {num_questions}-question multiple-choice quiz that assesses the learning objective above.

**REQUIREMENTS:**
- Each question must have exactly 1 correct answer and 2-3 plausible distractors
- All questions should align with the '{bloom_level}' cognitive level
- Distractors must represent common misconceptions or errors
- CRITICAL: Every option (correct AND incorrect) MUST have a feedback justification that explains:
  - For correct answers: WHY it is correct, what concept it demonstrates
  - For incorrect answers: WHAT misconception it represents, WHY it is wrong, and what the student should understand instead
- Vary the position of correct answers across questions (no patterns)
- Set passing score to 70%

**ASSESSMENT FOCUS:**
Create questions that genuinely assess understanding at the '{bloom_level}' level. Avoid questions that can be answered through test-taking strategies alone."""

    def extract_metadata(self, content: QuizSchema) -> dict:
        """Calculate metadata from generated quiz.

        Args:
            content: The validated QuizSchema instance

        Returns:
            dict: Metadata with word_count, duration, question_count, content_type
        """
        # Count words in all question text and option text
        word_count = 0

        for question in content.questions:
            # Count words in question text
            word_count += ContentMetadata.count_words(question.question_text)

            # Count words in all options
            for option in question.options:
                word_count += ContentMetadata.count_words(option.text)

        # Calculate duration using standard rate (1.5 min per question)
        num_questions = len(content.questions)
        duration = ContentMetadata.estimate_quiz_duration(num_questions)

        return {
            "word_count": word_count,
            "estimated_duration_minutes": duration,
            "question_count": num_questions,
            "content_type": "quiz"
        }

    @staticmethod
    def validate_answer_distribution(quiz: QuizSchema) -> dict:
        """Validate that correct answers are balanced across positions.

        Checks that no single position (0, 1, 2, 3) contains more than 50% of correct answers.
        This prevents predictable patterns that enable test-wise guessing.

        Args:
            quiz: QuizSchema to validate

        Returns:
            dict: {
                "balanced": bool,
                "distribution": {position: count, ...}
            }
        """
        # Track position of correct answer for each question
        distribution = {}

        for question in quiz.questions:
            # Find position of correct answer
            for i, option in enumerate(question.options):
                if option.is_correct:
                    distribution[i] = distribution.get(i, 0) + 1
                    break

        # Check if any position has > 50% of answers
        total_questions = len(quiz.questions)
        max_count = max(distribution.values()) if distribution else 0
        balanced = max_count <= (total_questions / 2)

        return {
            "balanced": balanced,
            "distribution": distribution
        }

    def generate_quiz(
        self,
        learning_objective: str,
        topic: str,
        bloom_level: str,
        num_questions: int = 5,
        difficulty: str = "intermediate"
    ) -> Tuple[QuizSchema, dict]:
        """Convenience method for generating a quiz.

        Args:
            learning_objective: The learning objective being assessed
            topic: Subject matter for the quiz
            bloom_level: Bloom's taxonomy level
            num_questions: Number of questions (default 5)
            difficulty: Difficulty level (default "intermediate")

        Returns:
            Tuple[QuizSchema, dict]: (quiz, metadata)
        """
        return self.generate(
            schema=QuizSchema,
            learning_objective=learning_objective,
            topic=topic,
            bloom_level=bloom_level,
            num_questions=num_questions,
            difficulty=difficulty
        )
