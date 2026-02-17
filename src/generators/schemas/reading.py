"""Pydantic schema for educational reading generation."""

from pydantic import BaseModel, Field
from typing import List


class ReadingSection(BaseModel):
    """Single content section within a reading.

    Readings are structured as: introduction → sections → conclusion.
    Each section covers one sub-topic of the overall reading.
    """

    heading: str = Field(description="Section heading")
    body: str = Field(description="Section content text")


class Reference(BaseModel):
    """Citation for a reading reference.

    Uses APA 7 format for academic credibility.
    """

    citation: str = Field(description="APA 7 formatted citation")
    url: str = Field(description="URL or DOI if available", default="")


class ReadingSchema(BaseModel):
    """Complete educational reading with sections and references.

    Structure follows academic writing best practices:
    - Introduction: Context and overview (50-100 words)
    - Sections: Main content divided into logical chunks (2-6 sections)
    - Conclusion: Summary and takeaways (50-100 words)
    - References: APA 7 citations (1-5 sources)
    """

    title: str = Field(description="Reading title")
    introduction: str = Field(description="Opening paragraph, 50-100 words")
    sections: List[ReadingSection] = Field(
        min_length=2,
        max_length=6,
        description="Main content sections"
    )
    conclusion: str = Field(description="Closing paragraph, 50-100 words")
    references: List[Reference] = Field(
        min_length=1,
        max_length=5,
        description="APA 7 references"
    )
    learning_objective: str = Field(description="The learning objective this reading addresses")
