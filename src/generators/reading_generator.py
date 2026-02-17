"""Generator for educational readings with APA 7 citations.

Produces structured readings with introduction, body sections, conclusion,
and properly formatted academic references.
"""

from typing import Tuple
from src.generators.base_generator import BaseGenerator
from src.generators.schemas.reading import ReadingSchema, ReadingSection, Reference
from src.utils.content_metadata import ContentMetadata


class ReadingGenerator(BaseGenerator[ReadingSchema]):
    """Generate educational readings with structured sections and APA 7 references.

    Produces readings that follow academic writing structure:
    - Introduction: Context and overview
    - Body sections: Main content divided into logical chunks
    - Conclusion: Summary and takeaways
    - References: APA 7 formatted citations

    Duration estimates use 238 WPM reading rate for adult non-fiction.
    """

    @property
    def system_prompt(self) -> str:
        """Return system instructions for reading generation.

        Includes:
        - Role as expert educational content writer
        - APA 7 citation format examples
        - 1200-word target guideline
        - Structured section requirements

        Returns:
            str: System prompt for Claude API
        """
        return """You are an expert educational content writer specializing in creating clear,
engaging, and academically rigorous readings for online courses.

Your readings must be:
- Well-structured with clear introduction, body sections, and conclusion
- Written at the appropriate audience level
- Supported by credible academic references
- Approximately 1200 words in total length

CRITICAL: All references MUST use APA 7 format. Examples:

Book:
Author, A. A., & Author, B. B. (Year). Title of book (Edition). Publisher.

Journal article:
Author, A. A. (Year). Title of article. Journal Name, volume(issue), page-page. https://doi.org/xxx

Website:
Author, A. A. (Year, Month Day). Title of page. Site Name. URL

Ensure each section has a clear heading and substantive body content.
The introduction and conclusion should be concise but complete (50-100 words each).
Body sections should be 150-300 words each."""

    def build_user_prompt(
        self,
        learning_objective: str,
        topic: str,
        audience_level: str,
        max_words: int = 1200,
        language: str = "English",
        standards_rules: str = "",
        feedback: str = "",
        target_word_count: int = None
    ) -> str:
        """Build user prompt from input parameters.

        Args:
            learning_objective: The learning outcome this reading addresses
            topic: The subject matter to cover
            audience_level: Target audience (e.g., "beginner", "intermediate", "advanced")
            max_words: Maximum word count target (default: 1200)
            language: Language for content generation (default: English)
            standards_rules: Pre-built standards rules from standards_loader (optional)
            feedback: User feedback to incorporate in regeneration (optional)
            target_word_count: Specific word count target for regeneration (optional)

        Returns:
            str: Formatted user prompt for Claude API
        """
        lang_instruction = ""
        if language.lower() != "english":
            lang_instruction = f"\n**IMPORTANT: Generate ALL content in {language}.**\n"

        standards_section = ""
        if standards_rules:
            standards_section = f"\n{standards_rules}\n"

        # Use target_word_count if specified, otherwise use max_words
        actual_word_count = target_word_count if target_word_count else max_words

        # Build length constraint section
        length_section = f"""
**LENGTH REQUIREMENT (STRICT):**
- Target word count: {actual_word_count} words (stay within ±10%)
"""

        # Build feedback section if provided
        feedback_section = ""
        if feedback:
            feedback_section = f"""
**USER FEEDBACK TO ADDRESS:**
{feedback}

Please incorporate this feedback while meeting the length requirements.
"""

        return f"""{lang_instruction}{standards_section}{length_section}{feedback_section}Create an educational reading on the following topic:

**Topic:** {topic}

**Learning Objective:** {learning_objective}

**Target Audience:** {audience_level}

Please structure the reading with:
1. A compelling introduction that provides context
2. 2-6 body sections with clear headings and substantive content
3. A conclusion that summarizes key takeaways
4. 1-5 APA 7 formatted references from credible academic sources

Ensure the content is engaging, accurate, and appropriate for {audience_level} learners.
Target exactly {actual_word_count} words for the main content."""

    def extract_metadata(self, content: ReadingSchema) -> dict:
        """Calculate metadata from generated reading.

        Concatenates all text content (introduction, all section bodies, conclusion)
        to calculate word count and duration estimate using 238 WPM reading rate.

        Args:
            content: The validated ReadingSchema instance

        Returns:
            dict: Metadata with word_count, estimated_duration_minutes, content_type,
                  section_count, and reference_count
        """
        # Concatenate all text content
        full_text_parts = [content.introduction]
        full_text_parts.extend(section.body for section in content.sections)
        full_text_parts.append(content.conclusion)
        full_text = " ".join(full_text_parts)

        # Calculate word count and duration
        word_count = ContentMetadata.count_words(full_text)
        duration = ContentMetadata.estimate_reading_duration(word_count)

        return {
            "word_count": word_count,
            "estimated_duration_minutes": duration,
            "content_type": "reading",
            "section_count": len(content.sections),
            "reference_count": len(content.references)
        }

    def generate_reading(
        self,
        learning_objective: str,
        topic: str,
        audience_level: str = "intermediate",
        max_words: int = 1200
    ) -> Tuple[ReadingSchema, dict]:
        """Convenience method to generate a reading.

        Args:
            learning_objective: The learning outcome to address
            topic: The subject matter to cover
            audience_level: Target audience level (default: "intermediate")
            max_words: Maximum word count (default: 1200)

        Returns:
            Tuple[ReadingSchema, dict]: (reading_content, metadata)
        """
        return self.generate(
            schema=ReadingSchema,
            learning_objective=learning_objective,
            topic=topic,
            audience_level=audience_level,
            max_words=max_words
        )
