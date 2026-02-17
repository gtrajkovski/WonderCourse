"""Pydantic schema for hands-on lab (HOL) generation."""

from pydantic import BaseModel, Field
from typing import List


class HOLPart(BaseModel):
    """Single part/exercise within a hands-on lab.

    HOLs are divided into 3 parts to scaffold learning and build complexity.
    Each part has clear instructions and time estimates for pacing.
    """

    part_number: int = Field(description="Part number (1-3)", ge=1)
    title: str = Field(description="Part title")
    instructions: str = Field(description="Step-by-step instructions for this part")
    estimated_minutes: int = Field(description="Estimated completion time in minutes", ge=1)


class HOLRubricCriterion(BaseModel):
    """Single evaluation criterion with 3-level scoring for HOL.

    Uses Advanced/Intermediate/Beginner performance levels with point values.
    This scoring model emphasizes skill development progression over pass/fail.
    """

    name: str = Field(description="Criterion name (e.g., 'Implementation Quality', 'Technical Accuracy')")
    advanced: str = Field(description="Advanced performance (5 points)")
    intermediate: str = Field(description="Intermediate performance (4 points)")
    beginner: str = Field(description="Beginner performance (2 points)")
    points_advanced: int = Field(default=5, description="Points for advanced level")
    points_intermediate: int = Field(default=4, description="Points for intermediate level")
    points_beginner: int = Field(default=2, description="Points for beginner level")


class HOLSchema(BaseModel):
    """Complete hands-on lab with scaffolded parts and configurable rubric.

    HOLs provide guided practice with scaffolded exercises. The part structure
    builds from basic to advanced skills. Rubric criteria count and levels are
    configurable via ContentStandardsProfile (default: 3 criteria, 2-5 allowed).
    """

    title: str = Field(description="HOL title")
    scenario: str = Field(description="Real-world scenario framing the lab")
    parts: List[HOLPart] = Field(
        min_length=3,
        max_length=3,
        description="3 scaffolded parts building in complexity"
    )
    submission_criteria: str = Field(description="What students must submit for evaluation")
    rubric: List[HOLRubricCriterion] = Field(
        min_length=2,   # v1.2.0: Allow 2-5 criteria (configurable via standards)
        max_length=5,
        description="Evaluation criteria (count configured by standards profile)"
    )
    learning_objective: str = Field(description="The learning objective this HOL addresses")
