"""Pydantic schemas for textbook chapter generation.

This module defines schemas for the textbook generation pipeline:
- TextbookOutlineSchema: Hierarchical outline for chapter structure planning
- TextbookSectionSchema: Individual section content generation
- TextbookChapterSchema: Complete assembled chapter with all components

The textbook generator uses a two-phase approach:
1. Generate outline (TextbookOutlineSchema) to plan chapter structure
2. Generate each section (TextbookSectionSchema) in parallel
3. Assemble final chapter (TextbookChapterSchema) with glossary and images
"""

from pydantic import BaseModel, Field
from typing import List

from src.generators.schemas.reading import Reference


class SectionOutline(BaseModel):
    """Outline entry for a textbook section.

    Used in the first phase of textbook generation to plan chapter structure.
    Each section outline becomes a TextbookSectionSchema during generation.
    """

    title: str = Field(description="Section heading")
    description: str = Field(description="1-2 sentence overview of section content")
    estimated_words: int = Field(
        description="Target word count for this section (400-600)",
        ge=100,
        le=1000
    )


class TextbookOutlineSchema(BaseModel):
    """Chapter outline for hierarchical textbook generation.

    The outline serves as a blueprint for section-by-section generation.
    Each chapter covers one learning outcome in depth with 5-8 main sections.
    """

    chapter_title: str = Field(description="Chapter title aligned to learning outcome")
    introduction_summary: str = Field(description="What the introduction will cover")
    sections: List[SectionOutline] = Field(
        min_length=5,
        max_length=8,
        description="Main content sections (5-8 required)"
    )
    conclusion_summary: str = Field(description="What the conclusion will summarize")
    estimated_total_words: int = Field(
        description="Sum of all section estimates plus intro/conclusion",
        ge=1000,
        le=10000
    )


class TextbookSectionSchema(BaseModel):
    """Individual textbook section with content and key concepts.

    Generated from a SectionOutline during the parallel section generation phase.
    Each section should be self-contained while connecting to the chapter theme.
    """

    heading: str = Field(description="Section heading from outline")
    content: str = Field(description="Section body text (400-600 words)")
    key_concepts: List[str] = Field(
        min_length=2,
        max_length=5,
        description="Main concepts covered in this section (2-5 items)"
    )


class GlossaryTerm(BaseModel):
    """Glossary entry for a technical term or concept.

    Each term includes context to show how it's used within the chapter.
    Definitions should be clear and accessible to the target audience.
    """

    term: str = Field(description="The term or concept")
    definition: str = Field(description="Clear, concise definition (1-2 sentences)")
    context: str = Field(description="Example usage from the chapter")


class ImagePlaceholder(BaseModel):
    """Placeholder for an image to be added to the textbook.

    Image placeholders specify where visual content should be inserted,
    with enough detail for a designer or AI image generator to create the asset.
    """

    figure_number: str = Field(description="Figure number (e.g., 'Figure 6.1')")
    caption: str = Field(description="1-2 sentence caption describing the figure")
    alt_text: str = Field(description="Accessibility description for screen readers")
    suggested_type: str = Field(
        description="Type: diagram, chart, photo, screenshot, illustration"
    )
    placement_after: str = Field(
        description="Place after this paragraph (first 20 chars of anchor text)"
    )


class TextbookChapterSchema(BaseModel):
    """Complete textbook chapter with all components.

    The final assembled output of the textbook generation pipeline.
    Includes all content sections plus supporting elements:
    - References for academic credibility
    - Glossary for key term definitions
    - Image placeholders for visual enhancement
    """

    chapter_number: int = Field(description="Chapter number in sequence", ge=1)
    title: str = Field(description="Chapter title")
    introduction: str = Field(description="Opening section (100-150 words)")
    sections: List[TextbookSectionSchema] = Field(
        min_length=5,
        max_length=8,
        description="Main content sections (5-8 required)"
    )
    conclusion: str = Field(description="Closing summary (100-150 words)")
    references: List[Reference] = Field(
        min_length=3,
        max_length=10,
        description="APA 7 references for the chapter"
    )
    glossary_terms: List[GlossaryTerm] = Field(
        min_length=5,
        max_length=20,
        description="Key terms and definitions"
    )
    image_placeholders: List[ImagePlaceholder] = Field(
        min_length=2,
        max_length=8,
        description="Placeholders for visual content"
    )
    learning_outcome_id: str = Field(
        description="The learning outcome this chapter addresses"
    )
