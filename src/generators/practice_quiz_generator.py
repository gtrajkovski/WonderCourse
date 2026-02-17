"""PracticeQuizGenerator for creating formative assessment quizzes with hints and immediate feedback."""

from typing import Tuple
from src.generators.base_generator import BaseGenerator
from src.generators.schemas.practice_quiz import PracticeQuizSchema, PracticeQuizQuestion
from src.utils.content_metadata import ContentMetadata


class PracticeQuizGenerator(BaseGenerator[PracticeQuizSchema]):
    """Generator for creating practice quizzes with hints for formative assessment.

    Produces formative MCQ quizzes with:
    - Hints on every option to guide learning (not just feedback)
    - Detailed explanations to reinforce correct understanding
    - No passing score (formative, not graded)
    - Bloom's taxonomy alignment for cognitive level
    """

    @property
    def system_prompt(self) -> str:
        """Return system prompt for practice quiz generation with formative focus."""
        return """You are an expert assessment designer specializing in formative assessment and practice quizzes.

Your practice quizzes focus on LEARNING, not EVALUATION. This is a critical distinction:

**Formative vs. Summative Assessment:**
- Practice quizzes are FOR learning (formative), not OF learning (summative)
- Goal: Build understanding through immediate feedback and guidance
- No grades or passing scores - only learning support

**Question Quality:**
- Clear, unambiguous question stems aligned with Bloom's taxonomy
- Single correct answer per question
- Questions that scaffold understanding at appropriate difficulty level
- Avoid trick questions - focus on genuine comprehension

**Hints - CRITICAL Feature:**
- Every option (correct AND incorrect) must include a hint field
- Hints guide students toward correct answer WITHOUT giving it away
- Hints should:
  - Point to relevant concepts or principles
  - Ask reflective questions that prompt thinking
  - Suggest reviewing specific material or concepts
  - NOT reveal the answer directly
- Correct option hints: Reinforce the reasoning pathway
- Incorrect option hints: Guide toward reconsidering without stating "this is wrong"

**Feedback (in addition to hints):**
- Correct answer feedback: Explain WHY it's correct and reinforce understanding
- Distractor feedback: Explain the misconception and correct it
- Feedback is shown AFTER selection; hints BEFORE/DURING consideration

**Distractor Quality:**
- Represent common misconceptions or errors in understanding
- Plausible enough to require real thinking to eliminate
- Similar length and complexity to correct answer
- Each distractor maps to a specific learning gap

**Explanations:**
- Detailed explanation field for each question
- Goes beyond "the answer is X" to explain the concept
- Helps students learn from both correct and incorrect attempts

**Scaffolded Difficulty:**
- Questions build confidence through progression
- Earlier questions may be slightly easier to build momentum
- Later questions reinforce deeper understanding"""

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
        """Build user prompt for practice quiz generation.

        Args:
            learning_objective: The learning objective being reinforced
            topic: Subject matter for the practice quiz
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
Audience Level: {audience_level}
Difficulty: {difficulty}

**TASK:**
Generate a {num_questions}-question practice quiz that reinforces the learning objective above.

**REQUIREMENTS:**
- Each question must have exactly 1 correct answer and 2-3 plausible distractors
- All questions should align with the '{bloom_level}' cognitive level
- CRITICAL: EVERY option (correct AND incorrect) must include BOTH:
  - feedback: Justification explaining WHY this option is correct or incorrect. For wrong answers, explain the specific misconception and what the student should understand instead.
  - hint: Guidance to help student think through the question (WITHOUT giving away the answer)
- Include detailed explanation for each question
- Distractors should represent common misconceptions
- This is a PRACTICE quiz (formative) - no passing score, focus on learning

**FORMATIVE ASSESSMENT FOCUS:**
Create questions that help students LEARN through:
1. Thoughtful hints that guide without revealing answers
2. Detailed feedback that explains misconceptions
3. Scaffolded difficulty that builds confidence
4. Explanations that deepen understanding

Remember: The goal is learning support, not evaluation. Every element should help students understand the '{bloom_level}' level concept more deeply."""

    def extract_metadata(self, content: PracticeQuizSchema) -> dict:
        """Calculate metadata from generated practice quiz.

        Args:
            content: The validated PracticeQuizSchema instance

        Returns:
            dict: Metadata with word_count, duration, question_count, content_type
        """
        # Count words in all question text, option text, and explanations
        word_count = 0

        for question in content.questions:
            # Count words in question text
            word_count += ContentMetadata.count_words(question.question_text)

            # Count words in explanation
            word_count += ContentMetadata.count_words(question.explanation)

            # Count words in all options (text, feedback, and hints)
            for option in question.options:
                word_count += ContentMetadata.count_words(option.text)
                word_count += ContentMetadata.count_words(option.feedback)
                word_count += ContentMetadata.count_words(option.hint)

        # Calculate duration using standard rate (1.5 min per question)
        num_questions = len(content.questions)
        duration = ContentMetadata.estimate_quiz_duration(num_questions)

        return {
            "word_count": word_count,
            "estimated_duration_minutes": duration,
            "question_count": num_questions,
            "content_type": "practice_quiz"
        }

    def generate_practice_quiz(
        self,
        learning_objective: str,
        topic: str,
        bloom_level: str,
        num_questions: int = 5,
        difficulty: str = "intermediate"
    ) -> Tuple[PracticeQuizSchema, dict]:
        """Convenience method for generating a practice quiz.

        Args:
            learning_objective: The learning objective being reinforced
            topic: Subject matter for the practice quiz
            bloom_level: Bloom's taxonomy level
            num_questions: Number of questions (default 5)
            difficulty: Difficulty level (default "intermediate")

        Returns:
            Tuple[PracticeQuizSchema, dict]: (practice_quiz, metadata)
        """
        return self.generate(
            schema=PracticeQuizSchema,
            learning_objective=learning_objective,
            topic=topic,
            bloom_level=bloom_level,
            num_questions=num_questions,
            difficulty=difficulty
        )
