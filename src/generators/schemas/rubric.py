"""Pydantic schema for rubric generation."""

from pydantic import BaseModel, Field
from typing import List


class RubricCriterion(BaseModel):
    """Single evaluation criterion with 3-level scoring.

    Uses Below/Meets/Exceeds Expectations model for clarity and fairness.
    Each level has descriptive text explaining performance expectations.
    """

    name: str = Field(description="Criterion name (e.g., 'Content Quality', 'Technical Accuracy')")
    description: str = Field(description="What this criterion evaluates")
    below_expectations: str = Field(description="Description of below expectations performance")
    meets_expectations: str = Field(description="Description of meets expectations performance")
    exceeds_expectations: str = Field(description="Description of exceeds expectations performance")
    weight_percentage: int = Field(
        description="Weight as percentage of total score",
        ge=0,
        le=100
    )


class RubricSchema(BaseModel):
    """Complete grading rubric with weighted criteria.

    3-level rubrics (Below/Meets/Exceeds) are clearer and more reliable than
    5+ level rubrics. Weights allow different criteria to contribute proportionally.

    Note: Criterion weights should sum to 100%, but validation happens in generator.
    """

    title: str = Field(description="Rubric title")
    criteria: List[RubricCriterion] = Field(
        min_length=2,
        max_length=6,
        description="Scoring criteria"
    )
    total_points: int = Field(
        description="Maximum points for this rubric",
        gt=0
    )
    learning_objective: str = Field(description="The learning objective this rubric evaluates")
