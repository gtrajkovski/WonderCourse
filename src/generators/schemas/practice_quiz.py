"""Pydantic schema for practice quiz generation."""

from pydantic import BaseModel, Field
from typing import List, Literal


class PracticeQuizOption(BaseModel):
    """Single answer option for a practice quiz question.

    Practice quizzes include hints to guide learning, unlike graded quizzes.
    Each option has feedback plus a hint to help students learn from mistakes.
    """

    text: str = Field(description="Answer option text")
    is_correct: bool = Field(description="Whether this is the correct answer")
    feedback: str = Field(
        description="REQUIRED justification for this option. For correct answers: explain WHY it is correct and reinforce the concept. For incorrect answers: explain the specific misconception this option represents and why it is wrong."
    )
    hint: str = Field(
        description="Guidance to help student think through this option WITHOUT revealing the answer. Should prompt reflection on relevant concepts."
    )


class PracticeQuizQuestion(BaseModel):
    """Single practice quiz question with options and learning support.

    Uses Bloom's taxonomy to ensure appropriate cognitive level.
    Includes detailed explanation to support learning (formative, not summative).
    """

    question_text: str = Field(description="Question stem")
    options: List[PracticeQuizOption] = Field(
        min_length=3,
        max_length=4,
        description="Answer options (1 correct, 2-3 distractors) with hints"
    )
    bloom_level: Literal["remember", "understand", "apply", "analyze", "evaluate", "create"] = Field(
        description="Bloom's taxonomy cognitive level"
    )
    explanation: str = Field(description="Detailed explanation of correct answer")


class PracticeQuizSchema(BaseModel):
    """Complete practice quiz for formative assessment.

    Practice quizzes focus on learning rather than grading. They include hints
    and detailed explanations to help students understand concepts. Unlike graded
    quizzes, practice quizzes have no passing score threshold.
    """

    title: str = Field(description="Practice quiz title")
    questions: List[PracticeQuizQuestion] = Field(
        min_length=3,
        max_length=10,
        description="Practice questions with hints and explanations"
    )
    learning_objective: str = Field(description="The learning objective this practice quiz reinforces")
