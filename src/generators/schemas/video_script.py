"""Pydantic schema for WWHAA video script generation."""

from pydantic import BaseModel, Field
from typing import Literal


class VideoScriptSection(BaseModel):
    """Single WWHAA section of a video script.

    Each section represents one phase of the WWHAA structure:
    - Hook: Engage with relatable problem
    - Objective: State measurable learning goal
    - Content: Teach with concrete examples
    - IVQ: In-video question to check understanding
    - Summary: Reinforce key takeaways
    - CTA: Call to action directing to next activity
    """

    phase: Literal["hook", "objective", "content", "ivq", "summary", "cta"] = Field(
        description="WWHAA phase identifier"
    )
    title: str = Field(description="Section heading")
    script_text: str = Field(description="Narration/dialogue for this section")
    speaker_notes: str = Field(description="Delivery guidance for instructor")


class VideoScriptSchema(BaseModel):
    """Complete WWHAA-structured video script.

    Enforces WWHAA structure by having separate fields for each phase.
    This ensures generators produce all 6 required sections.
    """

    title: str = Field(description="Video title")
    hook: VideoScriptSection = Field(description="Hook section: Engage with relatable problem")
    objective: VideoScriptSection = Field(description="Objective section: State learning goal")
    content: VideoScriptSection = Field(description="Content section: Main teaching content")
    ivq: VideoScriptSection = Field(description="In-video question: Check understanding")
    summary: VideoScriptSection = Field(description="Summary section: Reinforce key takeaways")
    cta: VideoScriptSection = Field(description="Call to action: Direct to next activity")
    learning_objective: str = Field(description="The learning objective this video addresses")
