"""AI-powered content converter for transforming plain text into structured formats.

Enables users to paste raw content and have Claude structure it into WWHAA video scripts,
readings with sections, or quizzes with questions.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import re
from anthropic import Anthropic

from src.config import Config
from src.core.models import ContentType
from src.generators.schemas.video_script import VideoScriptSchema
from src.generators.schemas.reading import ReadingSchema
from src.generators.schemas.quiz import QuizSchema


def _fix_schema_for_claude(schema: Dict) -> Dict:
    """Fix schema for Claude API compatibility.

    - Add additionalProperties: false to all object types
    - Remove unsupported properties like exclusiveMinimum, exclusiveMaximum
    """
    unsupported = {'exclusiveMinimum', 'exclusiveMaximum', 'format'}

    if isinstance(schema, dict):
        # Remove unsupported properties
        for prop in unsupported:
            schema.pop(prop, None)

        if schema.get("type") == "object":
            schema["additionalProperties"] = False

        for key, value in list(schema.items()):
            if isinstance(value, dict):
                _fix_schema_for_claude(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        _fix_schema_for_claude(item)
    return schema


@dataclass
class ConversionResult:
    """Result of content conversion operation.

    Contains original content, structured output, confidence score, and change log.
    """

    original: str
    structured: dict
    target_type: ContentType
    confidence: float
    changes: List[str]


class ContentConverter:
    """AI-powered content converter for transforming plain text into structured formats.

    Uses Claude structured outputs to intelligently structure imported content into:
    - WWHAA video scripts (hook, objective, content, ivq, summary, cta)
    - Readings with sections (introduction, sections, conclusion, references)
    - Quizzes with MCQ questions
    """

    def __init__(self, model: str = None, api_key: str = None):
        """Initialize converter with Claude client.

        Args:
            model: Model name (defaults to Config.MODEL)
            api_key: Anthropic API key (defaults to Config.ANTHROPIC_API_KEY)
        """
        self.client = Anthropic(api_key=api_key or Config.ANTHROPIC_API_KEY)
        self.model = model or Config.MODEL

    def convert(
        self,
        content: str,
        target_type: ContentType,
        context: Optional[Dict] = None
    ) -> ConversionResult:
        """Convert plain text content to structured format.

        Args:
            content: Original plain text content
            target_type: Target ContentType (VIDEO, READING, or QUIZ)
            context: Optional context dict with metadata (topic, learning_outcomes, etc.)

        Returns:
            ConversionResult with structured output and metadata

        Raises:
            ValueError: If target_type is not supported for conversion
        """
        context = context or {}

        # Route to appropriate conversion method
        if target_type == ContentType.VIDEO:
            structured = self.to_video_script(content, context)
        elif target_type == ContentType.READING:
            structured = self.to_reading(content, context)
        elif target_type == ContentType.QUIZ:
            structured = self.to_quiz(content, context)
        else:
            raise ValueError(f"Conversion not supported for content type: {target_type}")

        # Calculate confidence based on content characteristics
        confidence = self._calculate_confidence(content, target_type, structured)

        # Document changes made
        changes = self._document_changes(content, structured, target_type)

        return ConversionResult(
            original=content,
            structured=structured,
            target_type=target_type,
            confidence=confidence,
            changes=changes
        )

    def suggest_type(self, content: str) -> ContentType:
        """Suggest most appropriate content type for given content.

        Uses keyword detection and content pattern analysis to determine
        whether content is best suited as VIDEO, READING, or QUIZ.

        Args:
            content: Plain text content to analyze

        Returns:
            ContentType enum value (VIDEO, READING, or QUIZ)
        """
        content_lower = content.lower()

        # Quiz detection: question marks + multiple choice patterns
        has_questions = content.count('?') >= 2
        has_mc_pattern = bool(re.search(r'\b[A-D][\)\.:]', content))
        if has_questions and has_mc_pattern:
            return ContentType.QUIZ

        # Video script detection: WWHAA structure keywords
        video_keywords = ['hook', 'objective', 'summary', 'call to action', 'in-video question']
        video_score = sum(1 for kw in video_keywords if kw in content_lower)
        if video_score >= 2:
            return ContentType.VIDEO

        # Reading detection: long paragraphs, section headers, references
        paragraphs = [p for p in content.split('\n\n') if len(p) > 100]
        has_sections = bool(re.search(r'^[A-Z][^.!?]*:$', content, re.MULTILINE))
        has_references = 'references' in content_lower or 'bibliography' in content_lower

        if len(paragraphs) >= 2 or has_sections or has_references:
            return ContentType.READING

        # Default: reading for prose, video for short content
        if len(content.split()) > 200:
            return ContentType.READING
        else:
            return ContentType.VIDEO

    def to_video_script(self, content: str, context: Dict) -> dict:
        """Convert content into WWHAA video script structure.

        Args:
            content: Original plain text content
            context: Context dict with optional topic, learning_outcomes, target_duration

        Returns:
            Dict matching VideoScriptSchema structure
        """
        topic = context.get('topic', 'the topic')
        learning_objective = context.get('learning_objective', 'Learn about ' + topic)

        system_prompt = """You are an expert educational video scriptwriter specializing in WWHAA structure.

Convert the provided content into a complete WWHAA video script with these six required sections:

1. Hook - Engage with a relatable problem or scenario (30-60 seconds)
2. Objective - State clear, measurable learning goal (15-30 seconds)
3. Content - Main teaching content with concrete examples (2-4 minutes)
4. IVQ (In-Video Question) - Check understanding with a question (30 seconds)
5. Summary - Reinforce key takeaways (30-60 seconds)
6. CTA (Call to Action) - Direct learners to next activity (15-30 seconds)

Each section needs:
- phase: The WWHAA phase name
- title: Section heading
- script_text: Narration/dialogue for the instructor
- speaker_notes: Delivery guidance

Write naturally. Avoid AI telltales like em-dashes, formal vocabulary, three-adjective lists."""

        user_prompt = f"""Convert this content into a WWHAA video script:

CONTENT:
{content}

CONTEXT:
- Learning objective: {learning_objective}
- Topic: {topic}

Preserve the core information while restructuring into the six WWHAA sections."""

        # Use Claude structured outputs
        schema = _fix_schema_for_claude(VideoScriptSchema.model_json_schema())
        tools = [{
            "name": "output_structured",
            "description": "Output the video script in WWHAA structure",
            "input_schema": schema
        }]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=Config.MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            tools=tools,
            tool_choice={"type": "tool", "name": "output_structured"}
        )

        # Extract tool use result
        for block in response.content:
            if block.type == "tool_use":
                return block.input

        raise ValueError("No tool_use block found in Claude response")

    def to_reading(self, content: str, context: Dict) -> dict:
        """Convert content into structured reading format.

        Args:
            content: Original plain text content
            context: Context dict with optional topic, learning_outcomes

        Returns:
            Dict matching ReadingSchema structure
        """
        topic = context.get('topic', 'the topic')
        learning_objective = context.get('learning_objective', 'Learn about ' + topic)

        system_prompt = """You are an expert educational content writer specializing in structured academic readings.

Convert the provided content into a well-structured reading with:

1. Introduction - Context and overview (50-100 words)
2. Sections - Main content divided into 2-6 logical sections, each with:
   - heading: Section title
   - body: Section content
3. Conclusion - Summary and takeaways (50-100 words)
4. References - 1-5 APA 7 formatted citations

Preserve key points from the original. Add credible references where sources are mentioned.
Use plain, clear language. Avoid em-dashes and overly formal vocabulary."""

        user_prompt = f"""Convert this content into a structured reading:

CONTENT:
{content}

CONTEXT:
- Learning objective: {learning_objective}
- Topic: {topic}

Structure it with introduction, logical sections, conclusion, and APA 7 references."""

        # Use Claude structured outputs
        schema = _fix_schema_for_claude(ReadingSchema.model_json_schema())
        tools = [{
            "name": "output_structured",
            "description": "Output the reading in structured format",
            "input_schema": schema
        }]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=Config.MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            tools=tools,
            tool_choice={"type": "tool", "name": "output_structured"}
        )

        # Extract tool use result
        for block in response.content:
            if block.type == "tool_use":
                return block.input

        raise ValueError("No tool_use block found in Claude response")

    def to_quiz(self, content: str, context: Dict) -> dict:
        """Convert content into quiz with MCQ questions.

        Args:
            content: Original plain text content
            context: Context dict with optional topic, learning_outcomes

        Returns:
            Dict matching QuizSchema structure
        """
        topic = context.get('topic', 'the topic')
        learning_objective = context.get('learning_objective', 'Assess understanding of ' + topic)

        system_prompt = """You are an expert educational assessment designer.

Convert the provided content into a quiz with 3-10 multiple choice questions.

Each question should:
- Test key concepts from the content
- Have 3-4 answer options (1 correct, 2-3 plausible distractors)
- Include feedback for each option explaining why it's correct/incorrect
- Specify Bloom's taxonomy level (remember, understand, apply, analyze, evaluate, create)
- Include detailed explanation of the correct answer

Span multiple Bloom's levels with emphasis on apply/analyze.
Set passing score to 70%.

Write questions clearly without AI telltales."""

        user_prompt = f"""Convert this content into quiz questions:

CONTENT:
{content}

CONTEXT:
- Learning objective: {learning_objective}
- Topic: {topic}

Extract key concepts and generate MCQ questions that assess understanding."""

        # Use Claude structured outputs
        schema = _fix_schema_for_claude(QuizSchema.model_json_schema())
        tools = [{
            "name": "output_structured",
            "description": "Output the quiz in structured format",
            "input_schema": schema
        }]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=Config.MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            tools=tools,
            tool_choice={"type": "tool", "name": "output_structured"}
        )

        # Extract tool use result
        for block in response.content:
            if block.type == "tool_use":
                return block.input

        raise ValueError("No tool_use block found in Claude response")

    def _calculate_confidence(
        self,
        content: str,
        target_type: ContentType,
        structured: dict
    ) -> float:
        """Calculate confidence score for conversion quality.

        Args:
            content: Original content
            target_type: Target content type
            structured: Converted structured output

        Returns:
            Float between 0.0 and 1.0 indicating confidence
        """
        # Base confidence starts high
        confidence = 0.9

        # Reduce confidence if original content is very short
        word_count = len(content.split())
        if word_count < 50:
            confidence -= 0.2
        elif word_count < 100:
            confidence -= 0.1

        # Type-specific confidence adjustments
        if target_type == ContentType.VIDEO:
            # Check if all WWHAA sections present
            required = ['hook', 'objective', 'content', 'ivq', 'summary', 'cta']
            if all(section in structured for section in required):
                confidence += 0.1

        elif target_type == ContentType.READING:
            # Check if has reasonable section count
            section_count = len(structured.get('sections', []))
            if 2 <= section_count <= 6:
                confidence += 0.1

        elif target_type == ContentType.QUIZ:
            # Check if has reasonable question count
            question_count = len(structured.get('questions', []))
            if 3 <= question_count <= 10:
                confidence += 0.1

        # Clamp to 0.0-1.0
        return max(0.0, min(1.0, confidence))

    def _document_changes(
        self,
        content: str,
        structured: dict,
        target_type: ContentType
    ) -> List[str]:
        """Document what changes were made during conversion.

        Args:
            content: Original content
            structured: Converted structured output
            target_type: Target content type

        Returns:
            List of change descriptions
        """
        changes = []

        if target_type == ContentType.VIDEO:
            changes.append("Restructured into WWHAA format (Hook, Objective, Content, IVQ, Summary, CTA)")
            changes.append("Added speaker notes for delivery guidance")
            changes.append("Created in-video question for engagement")

        elif target_type == ContentType.READING:
            section_count = len(structured.get('sections', []))
            changes.append(f"Organized into {section_count} logical sections")
            changes.append("Added introduction and conclusion")
            ref_count = len(structured.get('references', []))
            changes.append(f"Added {ref_count} APA 7 formatted references")

        elif target_type == ContentType.QUIZ:
            question_count = len(structured.get('questions', []))
            changes.append(f"Extracted {question_count} multiple choice questions")
            changes.append("Generated answer options with feedback")
            changes.append("Classified questions by Bloom's taxonomy level")

        return changes
