"""Tests for textbook Pydantic schemas."""

import pytest
from pydantic import ValidationError

from src.generators.schemas.textbook import (
    SectionOutline,
    TextbookOutlineSchema,
    TextbookSectionSchema,
    TextbookChapterSchema,
    GlossaryTerm,
    ImagePlaceholder,
)
from src.generators.schemas.reading import Reference


def test_outline_schema_validates():
    """Test that TextbookOutlineSchema validates with proper field values."""
    sections = [
        SectionOutline(
            title=f"Section {i}",
            description=f"Overview of section {i} content.",
            estimated_words=500
        )
        for i in range(1, 6)  # 5 sections
    ]

    outline = TextbookOutlineSchema(
        chapter_title="Introduction to Machine Learning",
        introduction_summary="This chapter introduces ML fundamentals.",
        sections=sections,
        conclusion_summary="We summarized the key ML concepts.",
        estimated_total_words=3000
    )

    assert outline.chapter_title == "Introduction to Machine Learning"
    assert len(outline.sections) == 5
    assert outline.sections[0].title == "Section 1"
    assert outline.estimated_total_words == 3000


def test_section_schema_validates():
    """Test that TextbookSectionSchema validates with heading, content, and key_concepts."""
    section = TextbookSectionSchema(
        heading="Understanding Neural Networks",
        content="Neural networks are computational models inspired by biological neurons. " * 50,
        key_concepts=["neurons", "layers", "activation functions"]
    )

    assert section.heading == "Understanding Neural Networks"
    assert len(section.content) > 400
    assert len(section.key_concepts) == 3
    assert "neurons" in section.key_concepts


def test_chapter_schema_validates():
    """Test that TextbookChapterSchema validates with all sub-components."""
    sections = [
        TextbookSectionSchema(
            heading=f"Section {i}",
            content=f"Content for section {i}. " * 50,
            key_concepts=[f"concept_{i}_a", f"concept_{i}_b"]
        )
        for i in range(1, 6)  # 5 sections
    ]

    references = [
        Reference(citation="Smith, J. (2024). Machine Learning. Publisher.", url="https://example.com/1"),
        Reference(citation="Jones, A. (2023). Deep Learning. Publisher.", url="https://example.com/2"),
        Reference(citation="Brown, B. (2022). Neural Networks. Publisher.", url="https://example.com/3"),
    ]

    glossary = [
        GlossaryTerm(term=f"Term {i}", definition=f"Definition of term {i}.", context=f"Used in context {i}.")
        for i in range(1, 6)  # 5 glossary terms
    ]

    images = [
        ImagePlaceholder(
            figure_number="Figure 1.1",
            caption="Neural network architecture diagram.",
            alt_text="A diagram showing layers of neurons connected by edges.",
            suggested_type="diagram",
            placement_after="Neural networks are"
        ),
        ImagePlaceholder(
            figure_number="Figure 1.2",
            caption="Training loss curve over epochs.",
            alt_text="A line chart showing decreasing loss over training epochs.",
            suggested_type="chart",
            placement_after="During training, the"
        ),
    ]

    chapter = TextbookChapterSchema(
        chapter_number=1,
        title="Introduction to Machine Learning",
        introduction="This chapter introduces the fundamentals of machine learning. " * 10,
        sections=sections,
        conclusion="In this chapter, we covered the basics of machine learning. " * 10,
        references=references,
        glossary_terms=glossary,
        image_placeholders=images,
        learning_outcome_id="LO-001"
    )

    assert chapter.chapter_number == 1
    assert chapter.title == "Introduction to Machine Learning"
    assert len(chapter.sections) == 5
    assert len(chapter.references) == 3
    assert len(chapter.glossary_terms) == 5
    assert len(chapter.image_placeholders) == 2
    assert chapter.learning_outcome_id == "LO-001"


def test_chapter_schema_reuses_reference():
    """Verify that TextbookChapterSchema.references uses the same Reference model from reading.py."""
    # Create a Reference instance (from reading.py)
    ref = Reference(citation="Test Author. (2024). Test Book. Publisher.", url="https://test.com")

    # Verify it can be used in chapter schema (same type)
    sections = [
        TextbookSectionSchema(
            heading=f"Section {i}",
            content=f"Content {i}. " * 50,
            key_concepts=["a", "b"]
        )
        for i in range(5)
    ]

    glossary = [
        GlossaryTerm(term=f"Term {i}", definition=f"Def {i}.", context=f"Context {i}.")
        for i in range(5)
    ]

    images = [
        ImagePlaceholder(
            figure_number=f"Figure {i}",
            caption=f"Caption {i}.",
            alt_text=f"Alt {i}.",
            suggested_type="diagram",
            placement_after=f"After {i}"
        )
        for i in range(2)
    ]

    chapter = TextbookChapterSchema(
        chapter_number=1,
        title="Test Chapter",
        introduction="Introduction text. " * 10,
        sections=sections,
        conclusion="Conclusion text. " * 10,
        references=[ref, ref, ref],  # Using reading.py Reference
        glossary_terms=glossary,
        image_placeholders=images,
        learning_outcome_id="LO-001"
    )

    # Verify references are the same type
    assert isinstance(chapter.references[0], Reference)
    assert chapter.references[0].citation == "Test Author. (2024). Test Book. Publisher."


def test_glossary_term_validates():
    """Test that GlossaryTerm validates with term, definition, and context."""
    term = GlossaryTerm(
        term="Machine Learning",
        definition="A subset of AI that enables systems to learn from data.",
        context="Machine learning algorithms improve through experience."
    )

    assert term.term == "Machine Learning"
    assert "AI" in term.definition
    assert "algorithms" in term.context


def test_image_placeholder_validates():
    """Test that ImagePlaceholder validates with all required fields."""
    image = ImagePlaceholder(
        figure_number="Figure 3.2",
        caption="Decision tree structure showing classification paths.",
        alt_text="A tree diagram with nodes representing decisions and leaves representing classes.",
        suggested_type="diagram",
        placement_after="Decision trees split"
    )

    assert image.figure_number == "Figure 3.2"
    assert "classification" in image.caption
    assert "tree diagram" in image.alt_text
    assert image.suggested_type == "diagram"
    assert len(image.placement_after) > 0


def test_chapter_schema_produces_json_schema():
    """Test that model_json_schema() produces valid JSON schema with expected keys."""
    schema = TextbookChapterSchema.model_json_schema()

    # Verify top-level structure
    assert "properties" in schema
    assert "required" in schema
    assert "$defs" in schema

    # Verify main properties exist
    properties = schema["properties"]
    assert "chapter_number" in properties
    assert "title" in properties
    assert "introduction" in properties
    assert "sections" in properties
    assert "conclusion" in properties
    assert "references" in properties
    assert "glossary_terms" in properties
    assert "image_placeholders" in properties
    assert "learning_outcome_id" in properties

    # Verify nested schemas are defined
    defs = schema["$defs"]
    assert "TextbookSectionSchema" in defs
    assert "GlossaryTerm" in defs
    assert "ImagePlaceholder" in defs
    assert "Reference" in defs


def test_outline_min_sections_enforced():
    """Test that fewer than 5 sections raises ValidationError."""
    sections = [
        SectionOutline(
            title=f"Section {i}",
            description=f"Overview of section {i}.",
            estimated_words=500
        )
        for i in range(1, 5)  # Only 4 sections (need min 5)
    ]

    with pytest.raises(ValidationError) as exc_info:
        TextbookOutlineSchema(
            chapter_title="Test Chapter",
            introduction_summary="Intro summary.",
            sections=sections,  # Only 4, need 5
            conclusion_summary="Conclusion summary.",
            estimated_total_words=2000
        )

    # Verify error is about list length
    error = exc_info.value
    assert "sections" in str(error).lower() or "list" in str(error).lower()
