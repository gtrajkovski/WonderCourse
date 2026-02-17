"""Pydantic schemas for course page generation.

Defines structured output schemas for syllabus, about, and resources pages.
"""

from pydantic import BaseModel, Field
from typing import List


class PageSection(BaseModel):
    """A section within a course page."""

    title: str = Field(..., description="Section heading")
    content: str = Field(..., description="Section content in markdown format")


class CoursePageSchema(BaseModel):
    """Schema for a generated course page."""

    title: str = Field(..., description="Page title")
    introduction: str = Field(..., description="Brief introductory paragraph")
    sections: List[PageSection] = Field(..., description="Main content sections")
    conclusion: str = Field(default="", description="Optional closing paragraph")


class SyllabusSchema(CoursePageSchema):
    """Schema for syllabus page with schedule."""

    weekly_schedule: List[PageSection] = Field(
        default_factory=list,
        description="Week-by-week breakdown of modules and activities"
    )
    grading_breakdown: str = Field(
        default="",
        description="Grading policy and assessment weights"
    )


class AboutSchema(CoursePageSchema):
    """Schema for about page with course overview."""

    key_takeaways: List[str] = Field(
        default_factory=list,
        description="3-5 key things learners will gain"
    )
    target_audience: str = Field(
        default="",
        description="Description of who this course is for"
    )


class ResourcesSchema(CoursePageSchema):
    """Schema for resources page with tools and materials."""

    tools: List[PageSection] = Field(
        default_factory=list,
        description="Tools and technologies used in the course"
    )
    additional_resources: List[PageSection] = Field(
        default_factory=list,
        description="Supplementary learning materials"
    )
