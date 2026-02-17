"""Pydantic schema for quiz generation."""

from pydantic import BaseModel, Field
from typing import List, Literal


class QuizOption(BaseModel):
    """Single answer option for a quiz question.

    Each question has 3-4 options with exactly one correct answer.
    Feedback is shown immediately after selection for formative assessment.
    """

    text: str = Field(description="Answer option text")
    is_correct: bool = Field(description="Whether this is the correct answer")
    feedback: str = Field(
        description="REQUIRED justification for this option. For correct answers: explain WHY it is correct and reinforce the concept. For incorrect answers: explain the specific misconception this option represents and why it is wrong."
    )


class QuizQuestion(BaseModel):
    """Single quiz question with options and metadata.

    Uses Bloom's taxonomy to ensure appropriate cognitive level.
    Includes detailed explanation to support learning (not just assessment).
    """

    question_text: str = Field(description="Question stem")
    options: List[QuizOption] = Field(
        min_length=3,
        max_length=4,
        description="Answer options (1 correct, 2-3 distractors)"
    )
    bloom_level: Literal["remember", "understand", "apply", "analyze", "evaluate", "create"] = Field(
        description="Bloom's taxonomy cognitive level"
    )
    explanation: str = Field(description="Detailed explanation of correct answer")


class QuizSchema(BaseModel):
    """Complete quiz with questions and scoring criteria.

    Quizzes serve both formative (practice) and summative (graded) purposes.
    Questions should span multiple Bloom's levels with emphasis on apply/analyze.
    """

    title: str = Field(description="Quiz title")
    questions: List[QuizQuestion] = Field(
        min_length=3,
        max_length=10,
        description="Quiz questions"
    )
    passing_score_percentage: int = Field(
        description="Passing threshold, typically 70",
        ge=0,
        le=100
    )
    learning_objective: str = Field(description="The learning objective this quiz assesses")
