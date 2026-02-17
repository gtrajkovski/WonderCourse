"""Generator for textbook chapters with hierarchical expansion.

Produces complete textbook chapters through a multi-step process:
1. Generate outline (5-8 sections) from learning outcome
2. Generate each section sequentially with context from previous sections
3. Assemble final chapter with introduction, conclusion, references, glossary, images

The hierarchical approach ensures coherent long-form content (~3000 words)
by maintaining context throughout the generation process.
"""

from typing import Tuple, Optional, Callable, List
from src.generators.base_generator import BaseGenerator
from src.generators.schemas.textbook import (
    TextbookChapterSchema,
    TextbookOutlineSchema,
    TextbookSectionSchema,
    SectionOutline
)
from src.utils.content_metadata import ContentMetadata
from src.config import Config


class TextbookGenerator(BaseGenerator[TextbookChapterSchema]):
    """Generate textbook chapters using hierarchical expansion.

    Uses a three-phase generation process:
    1. Outline generation: Plans chapter structure with 5-8 sections
    2. Section generation: Generates each section with accumulated context
    3. Chapter assembly: Combines sections into final chapter with all components

    Duration estimates use 238 WPM reading rate for academic content.
    """

    @property
    def system_prompt(self) -> str:
        """Return system instructions for textbook chapter generation.

        Includes:
        - Role as expert textbook author
        - Academic writing guidelines
        - ~3000 word target
        - APA 7 citation format examples
        - Progressive concept building
        - No redundancy between sections

        Returns:
            str: System prompt for Claude API
        """
        return """You are an expert textbook author for higher education, specializing in creating
comprehensive, academically rigorous chapters that guide learners through complex topics.

Your textbook chapters must:
- Be written in clear academic prose suitable for the target audience
- Target approximately 3000 words total across all sections
- Build concepts progressively, with earlier sections laying groundwork for later ones
- Avoid redundancy between sections - each section should cover unique content
- Include practical examples and applications where relevant

CRITICAL: All references MUST use APA 7 format. Examples:

Book:
Author, A. A., & Author, B. B. (Year). Title of book (Edition). Publisher.

Journal article:
Author, A. A. (Year). Title of article. Journal Name, volume(issue), page-page. https://doi.org/xxx

Website:
Author, A. A. (Year, Month Day). Title of page. Site Name. URL

IMAGE PLACEHOLDERS:
- Include 2-8 image placeholders throughout the chapter
- Each placeholder should specify figure number, caption, alt text, type, and placement
- Types: diagram, chart, photo, screenshot, illustration
- placement_after should be the first 20 characters of the paragraph after which to place the image

GLOSSARY TERMS:
- Define 5-20 key terms introduced in the chapter
- Each term needs: term, definition (1-2 sentences), and context showing usage from the chapter"""

    def build_user_prompt(
        self,
        learning_objective: str,
        topic: str,
        audience_level: str
    ) -> str:
        """Build user prompt for final chapter assembly.

        This prompt is used for the final API call that assembles
        all generated sections into a complete TextbookChapterSchema.

        Args:
            learning_objective: The learning outcome this chapter addresses
            topic: The subject matter to cover
            audience_level: Target audience (e.g., "beginner", "intermediate", "advanced")

        Returns:
            str: Formatted user prompt for Claude API
        """
        return f"""Create a complete textbook chapter for a higher education course.

**Learning Outcome:** {learning_objective}

**Topic:** {topic}

**Target Audience:** {audience_level}

Please create a chapter that:
1. Has a clear introduction (100-150 words) that establishes context
2. Contains 5-8 main sections, each covering a distinct aspect of the topic
3. Includes a conclusion (100-150 words) that summarizes key takeaways
4. Has 3-10 APA 7 formatted references from credible academic sources
5. Defines 5-20 key terms in the glossary
6. Includes 2-8 image placeholders at appropriate points

Ensure the content is appropriate for {audience_level} learners and directly addresses the learning outcome."""

    def extract_metadata(self, content: TextbookChapterSchema) -> dict:
        """Calculate metadata from generated chapter.

        Concatenates all text content (introduction, all section content, conclusion)
        to calculate word count and duration estimate using 238 WPM reading rate.

        Args:
            content: The validated TextbookChapterSchema instance

        Returns:
            dict: Metadata with word_count, estimated_duration_minutes, content_type,
                  section_count, reference_count, glossary_count, and image_count
        """
        # Concatenate all text content
        full_text_parts = [content.introduction]
        full_text_parts.extend(section.content for section in content.sections)
        full_text_parts.append(content.conclusion)
        full_text = " ".join(full_text_parts)

        # Calculate word count and duration
        word_count = ContentMetadata.count_words(full_text)
        duration = ContentMetadata.estimate_reading_duration(word_count)

        return {
            "word_count": word_count,
            "estimated_duration_minutes": duration,
            "content_type": "textbook_chapter",
            "section_count": len(content.sections),
            "reference_count": len(content.references),
            "glossary_count": len(content.glossary_terms),
            "image_count": len(content.image_placeholders)
        }

    def generate_outline(
        self,
        learning_objective: str,
        topic: str,
        audience_level: str
    ) -> TextbookOutlineSchema:
        """Generate chapter outline with 5-8 sections.

        First phase of hierarchical generation. Creates a structured plan
        for the chapter before generating individual sections.

        Args:
            learning_objective: The learning outcome this chapter addresses
            topic: The subject matter to cover
            audience_level: Target audience level

        Returns:
            TextbookOutlineSchema: Outline with section titles, descriptions, word estimates
        """
        outline_prompt = f"""Create an outline for a textbook chapter covering:

**Learning Outcome:** {learning_objective}

**Topic:** {topic}

**Target Audience:** {audience_level}

Create an outline with:
1. A chapter title aligned to the learning outcome
2. A brief summary of what the introduction will cover
3. 5-8 main sections, each with title, description (1-2 sentences), and estimated word count (400-600 per section)
4. A brief summary of what the conclusion will cover
5. An estimate of total words for the entire chapter (aim for ~3000 total)

Ensure sections flow logically and build upon each other."""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=Config.MAX_TOKENS,
            system=self.system_prompt,
            messages=[{"role": "user", "content": outline_prompt}],
            output_config={
                "format": {
                    "type": "json_schema",
                    "schema": TextbookOutlineSchema.model_json_schema()
                }
            }
        )

        content_json = response.content[0].text
        outline = TextbookOutlineSchema.model_validate_json(content_json)
        return outline

    def generate_section(
        self,
        section_outline: SectionOutline,
        chapter_context: str,
        covered_concepts: List[str]
    ) -> TextbookSectionSchema:
        """Generate a single section with context from previous sections.

        Args:
            section_outline: The outline entry for this section
            chapter_context: Overall chapter theme and context
            covered_concepts: Concepts already covered in previous sections (to avoid redundancy)

        Returns:
            TextbookSectionSchema: Generated section content with key concepts
        """
        covered_str = ", ".join(covered_concepts) if covered_concepts else "None yet"

        section_prompt = f"""Write the following textbook section:

**Section Title:** {section_outline.title}
**Description:** {section_outline.description}
**Target Word Count:** {section_outline.estimated_words} words

**Chapter Context:** {chapter_context}

**Concepts Already Covered in Previous Sections:** {covered_str}

Write this section with:
1. A heading matching the section title
2. Content that is approximately {section_outline.estimated_words} words
3. 2-5 key concepts that this section introduces or explains

IMPORTANT: Do not repeat concepts already covered. Build upon them instead."""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=Config.MAX_TOKENS,
            system=self.system_prompt,
            messages=[{"role": "user", "content": section_prompt}],
            output_config={
                "format": {
                    "type": "json_schema",
                    "schema": TextbookSectionSchema.model_json_schema()
                }
            }
        )

        content_json = response.content[0].text
        section = TextbookSectionSchema.model_validate_json(content_json)
        return section

    def generate_chapter(
        self,
        learning_objective: str,
        topic: str,
        audience_level: str,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> Tuple[TextbookChapterSchema, dict]:
        """Orchestrate complete chapter generation pipeline.

        Executes the three-phase hierarchical generation:
        1. Generate outline (5-8 sections)
        2. Generate each section sequentially with accumulated context
        3. Assemble final chapter with all components

        Args:
            learning_objective: The learning outcome this chapter addresses
            topic: The subject matter to cover
            audience_level: Target audience level
            progress_callback: Optional callback called at each step as
                              progress_callback(progress_float, step_description)

        Returns:
            Tuple[TextbookChapterSchema, dict]: (chapter_content, metadata)
        """
        def notify(progress: float, step: str):
            if progress_callback:
                progress_callback(progress, step)

        # Phase 1: Generate outline
        notify(0.1, "Generating chapter outline")
        outline = self.generate_outline(learning_objective, topic, audience_level)

        # Phase 2: Generate sections sequentially
        sections: List[TextbookSectionSchema] = []
        covered_concepts: List[str] = []
        chapter_context = f"Chapter: {outline.chapter_title}. {outline.introduction_summary}"

        num_sections = len(outline.sections)
        for i, section_outline in enumerate(outline.sections):
            progress = 0.1 + ((i + 1) / num_sections) * 0.5
            notify(progress, f"Generating section {i + 1}/{num_sections}: {section_outline.title}")

            section = self.generate_section(
                section_outline=section_outline,
                chapter_context=chapter_context,
                covered_concepts=covered_concepts
            )
            sections.append(section)

            # Accumulate covered concepts for next sections
            covered_concepts.extend(section.key_concepts)

        # Phase 3: Assemble final chapter
        notify(0.7, "Assembling chapter")

        # Build assembly prompt with all section content
        sections_text = "\n\n".join([
            f"## {s.heading}\n{s.content}\nKey concepts: {', '.join(s.key_concepts)}"
            for s in sections
        ])

        assembly_prompt = f"""Assemble a complete textbook chapter from the following generated content:

**Learning Outcome:** {learning_objective}

**Topic:** {topic}

**Target Audience:** {audience_level}

**Chapter Title:** {outline.chapter_title}

**Generated Sections:**
{sections_text}

Please create the final chapter with:
1. An introduction (100-150 words) based on: {outline.introduction_summary}
2. All the sections above (preserve the content exactly as provided)
3. A conclusion (100-150 words) based on: {outline.conclusion_summary}
4. 3-10 APA 7 formatted references for the topics covered
5. A glossary of 5-20 key terms from the chapter
6. 2-8 image placeholders at appropriate points in the chapter

The chapter_number should be 1, and learning_outcome_id should be left as a placeholder."""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=Config.MAX_TOKENS,
            system=self.system_prompt,
            messages=[{"role": "user", "content": assembly_prompt}],
            output_config={
                "format": {
                    "type": "json_schema",
                    "schema": TextbookChapterSchema.model_json_schema()
                }
            }
        )

        content_json = response.content[0].text
        chapter = TextbookChapterSchema.model_validate_json(content_json)

        # Extract metadata
        metadata = self.extract_metadata(chapter)

        return chapter, metadata
