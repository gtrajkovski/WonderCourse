"""Pydantic schema for project milestone generation."""

from pydantic import BaseModel, Field
from typing import List, Literal


class MilestoneDeliverable(BaseModel):
    """Single deliverable for a project milestone.

    Each deliverable specifies what to submit, description of expectations,
    and the required format (document, code, presentation, etc.).
    """

    name: str = Field(description="Deliverable name")
    description: str = Field(description="What this deliverable should contain")
    format: str = Field(description="Required format (e.g., 'PDF report', 'GitHub repository', 'Slide deck')")


class ProjectMilestoneSchema(BaseModel):
    """Complete project milestone with deliverables and grading criteria.

    Projects are staged across 3 milestones (A1/A2/A3) to scaffold complex work
    and provide formative feedback. Each milestone has specific deliverables and
    grading criteria. A1 is proposal/planning, A2 is implementation, A3 is final
    product with reflection.
    """

    title: str = Field(description="Milestone title")
    milestone_type: Literal["A1", "A2", "A3"] = Field(
        description="Milestone stage: A1 (proposal), A2 (implementation), A3 (final)"
    )
    overview: str = Field(description="What students will accomplish in this milestone")
    prerequisites: List[str] = Field(
        min_length=0,
        max_length=3,
        description="Prior work or knowledge required for this milestone"
    )
    deliverables: List[MilestoneDeliverable] = Field(
        min_length=2,
        max_length=5,
        description="What students must submit for this milestone"
    )
    grading_criteria: List[str] = Field(
        min_length=3,
        max_length=6,
        description="How this milestone will be evaluated"
    )
    estimated_hours: int = Field(
        description="Estimated completion time in hours",
        ge=1,
        le=40
    )
    learning_objective: str = Field(description="The learning objective this milestone addresses")
