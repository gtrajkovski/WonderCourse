"""Pydantic schema for coach dialogue generation."""

from pydantic import BaseModel, Field
from typing import List, Literal


class ConversationStarter(BaseModel):
    """Conversation starter prompt for coach dialogue.

    Each starter is designed to elicit specific types of thinking or responses
    from students, with a clear pedagogical purpose.
    """

    starter_text: str = Field(description="The conversation starter prompt")
    purpose: str = Field(description="Why this starter is included (pedagogical goal)")


class SampleResponse(BaseModel):
    """Sample student response with evaluation and feedback.

    Demonstrates different quality levels to help students understand expectations
    and calibrate their own responses.
    """

    response_text: str = Field(description="Sample student response")
    evaluation_level: Literal["exceeds", "meets", "needs_improvement"] = Field(
        description="Quality level of this response"
    )
    feedback: str = Field(description="Coaching feedback on this response")


class CoachSchema(BaseModel):
    """Complete coach dialogue activity with all 8 required sections.

    Coach dialogues provide structured conversational learning experiences where
    students engage with realistic scenarios and receive formative feedback.
    All 8 sections work together to create a complete learning experience.
    """

    title: str = Field(description="Coach dialogue title")
    learning_objectives: List[str] = Field(
        min_length=2,
        max_length=4,
        description="What students will learn from this dialogue"
    )
    scenario: str = Field(description="Realistic scenario students will engage with")
    tasks: List[str] = Field(
        min_length=2,
        max_length=5,
        description="Specific tasks students must complete"
    )
    conversation_starters: List[ConversationStarter] = Field(
        min_length=3,
        max_length=5,
        description="Prompts to initiate different aspects of dialogue"
    )
    sample_responses: List[SampleResponse] = Field(
        min_length=3,
        max_length=3,
        description="Example responses at different quality levels"
    )
    evaluation_criteria: List[str] = Field(
        min_length=3,
        max_length=5,
        description="How responses will be evaluated"
    )
    wrap_up: str = Field(description="Concluding summary and reflection")
    reflection_prompts: List[str] = Field(
        min_length=2,
        max_length=4,
        description="Questions to deepen reflection on the experience"
    )
