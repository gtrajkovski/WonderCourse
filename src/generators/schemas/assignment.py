"""Pydantic schema for assignment generation."""

from pydantic import BaseModel, Field
from typing import List


class AssignmentDeliverable(BaseModel):
    """Single deliverable item with point value.

    Each deliverable is a distinct artifact students must submit, with points
    indicating relative weight in the overall assignment grade.
    """

    item: str = Field(description="Deliverable description")
    points: int = Field(description="Points allocated to this deliverable", ge=0)


class ChecklistItem(BaseModel):
    """Single item in submission checklist.

    Checklist helps students ensure completeness before submission. Items marked
    required must be completed; optional items enhance quality.
    """

    item: str = Field(description="Checklist item description")
    required: bool = Field(description="Whether this item is mandatory")


class AssignmentSchema(BaseModel):
    """Complete assignment with deliverables and grading criteria.

    Assignments are individual or group work requiring synthesis and application
    of course concepts. Clear deliverables and grading criteria help students
    understand expectations. Submission checklist reduces incomplete submissions.
    """

    title: str = Field(description="Assignment title")
    overview: str = Field(description="Assignment purpose and context")
    deliverables: List[AssignmentDeliverable] = Field(
        min_length=1,
        max_length=5,
        description="What students must submit with point values"
    )
    grading_criteria: List[str] = Field(
        min_length=3,
        max_length=6,
        description="How the assignment will be evaluated"
    )
    submission_checklist: List[ChecklistItem] = Field(
        min_length=3,
        max_length=10,
        description="Items to verify before submitting"
    )
    total_points: int = Field(
        description="Maximum points for this assignment",
        gt=0
    )
    estimated_hours: int = Field(
        description="Estimated completion time in hours",
        ge=1,
        le=20
    )
    learning_objective: str = Field(description="The learning objective this assignment addresses")
