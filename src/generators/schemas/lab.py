"""Pydantic schema for lab generation."""

from pydantic import BaseModel, Field
from typing import List


class SetupStep(BaseModel):
    """Single setup step for lab environment preparation.

    Each step includes the instruction and what students should expect to see,
    helping them verify successful setup before proceeding to exercises.
    """

    step_number: int = Field(description="Step number in sequence", ge=1)
    instruction: str = Field(description="What to do in this step")
    expected_result: str = Field(description="What students should see after completing this step")


class LabSchema(BaseModel):
    """Complete lab with setup instructions and exercises.

    Labs provide hands-on technical practice with guided exercises. Clear setup
    instructions reduce friction and ensure all students can complete exercises.
    Time estimates help students plan work sessions effectively.
    """

    title: str = Field(description="Lab title")
    overview: str = Field(description="What students will accomplish in this lab")
    learning_objectives: List[str] = Field(
        min_length=2,
        max_length=4,
        description="Skills students will practice in this lab"
    )
    setup_instructions: List[SetupStep] = Field(
        min_length=3,
        max_length=10,
        description="Environment setup steps with expected results"
    )
    lab_exercises: List[str] = Field(
        min_length=3,
        max_length=8,
        description="Hands-on exercises to complete"
    )
    estimated_minutes: int = Field(
        description="Total estimated completion time",
        ge=15,
        le=120
    )
    prerequisites: List[str] = Field(
        min_length=0,
        max_length=3,
        description="Required prior knowledge or tools"
    )
