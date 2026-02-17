"""Pydantic schema for discussion prompt generation."""

from pydantic import BaseModel, Field
from typing import List


class DiscussionSchema(BaseModel):
    """Complete discussion prompt with facilitation support.

    Discussion prompts encourage peer learning and reflection. Facilitation
    questions help instructors guide conversations. Engagement hooks make
    discussions relevant and interesting to students.
    """

    title: str = Field(description="Discussion title")
    main_prompt: str = Field(description="Primary discussion question or scenario")
    facilitation_questions: List[str] = Field(
        min_length=3,
        max_length=5,
        description="Follow-up questions to deepen discussion"
    )
    engagement_hooks: List[str] = Field(
        min_length=2,
        max_length=3,
        description="Real-world connections to spark interest"
    )
    connection_to_objective: str = Field(
        description="How this discussion advances the learning objective"
    )
    learning_objective: str = Field(description="The learning objective this discussion supports")
