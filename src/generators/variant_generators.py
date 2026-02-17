"""Variant generators for UDL content transformation.

Provides generators that transform primary content into alternative formats
(e.g., video script → transcript) and adapters for depth level adjustment.
"""

from abc import ABC, abstractmethod
from typing import Tuple, Dict, Any, Optional
from pydantic import BaseModel
from anthropic import Anthropic
import json

from src.config import Config
from src.core.models import VariantType, DepthLevel, ContentVariant, BuildState
from src.utils.content_metadata import ContentMetadata
from src.utils.retry import ai_retry


class VariantGenerator(ABC):
    """Base class for variant generators.

    Variant generators transform primary content into alternative representations
    for Universal Design for Learning (UDL) support.
    """

    def __init__(self, api_key: str = None, model: str = None):
        """Initialize generator with Anthropic client.

        Args:
            api_key: Optional API key override.
            model: Optional model override.
        """
        self.client = Anthropic(api_key=api_key or Config.ANTHROPIC_API_KEY)
        self.model = model or Config.MODEL

    @property
    @abstractmethod
    def source_variant_type(self) -> VariantType:
        """The variant type this generator accepts as input."""
        pass

    @property
    @abstractmethod
    def target_variant_type(self) -> VariantType:
        """The variant type this generator produces."""
        pass

    @abstractmethod
    def transform(
        self,
        source_content: str,
        depth_level: DepthLevel = DepthLevel.STANDARD,
        **kwargs
    ) -> Tuple[str, Dict[str, Any]]:
        """Transform source content into target variant.

        Args:
            source_content: JSON string of source content
            depth_level: Target depth level
            **kwargs: Additional parameters

        Returns:
            Tuple of (transformed content JSON, metadata dict)
        """
        pass

    def generate_variant(
        self,
        source_variant: ContentVariant,
        target_depth: DepthLevel = DepthLevel.STANDARD,
        **kwargs
    ) -> ContentVariant:
        """Generate a new ContentVariant from source.

        Args:
            source_variant: The source ContentVariant to transform
            target_depth: Target depth level
            **kwargs: Additional parameters

        Returns:
            New ContentVariant with transformed content
        """
        content, metadata = self.transform(
            source_variant.content,
            target_depth,
            **kwargs
        )

        return ContentVariant(
            variant_type=self.target_variant_type,
            depth_level=target_depth,
            content=content,
            build_state=BuildState.GENERATED,
            word_count=metadata.get("word_count", 0),
            estimated_duration_minutes=metadata.get("estimated_duration_minutes", 0.0),
            generated_from_variant_id=source_variant.id,
        )


class TranscriptVariantGenerator(VariantGenerator):
    """Generates text transcript from video script.

    Transforms VideoScriptSchema into a readable transcript format,
    removing speaker notes and visual cues while preserving content.
    """

    @property
    def source_variant_type(self) -> VariantType:
        return VariantType.PRIMARY

    @property
    def target_variant_type(self) -> VariantType:
        return VariantType.TRANSCRIPT

    def transform(
        self,
        source_content: str,
        depth_level: DepthLevel = DepthLevel.STANDARD,
        **kwargs
    ) -> Tuple[str, Dict[str, Any]]:
        """Transform video script into transcript.

        Extracts script_text from each WWHAA section and formats
        as a readable transcript document.
        """
        try:
            script = json.loads(source_content)
        except json.JSONDecodeError:
            # If not valid JSON, return as-is
            return source_content, {"word_count": len(source_content.split())}

        # Extract script text from each section in WWHAA order
        sections = ["hook", "objective", "content", "ivq", "summary", "cta"]
        transcript_parts = []

        title = script.get("title", "Transcript")
        transcript_parts.append(f"# {title}\n")

        for section_name in sections:
            section = script.get(section_name)
            if section and isinstance(section, dict):
                section_title = section.get("title", section_name.title())
                script_text = section.get("script_text", "")
                if script_text:
                    transcript_parts.append(f"## {section_title}\n\n{script_text}\n")

        transcript = "\n".join(transcript_parts)

        # Apply depth adaptation if needed
        if depth_level == DepthLevel.ESSENTIAL:
            transcript = self._compress_to_essential(transcript)
        elif depth_level == DepthLevel.ADVANCED:
            # For transcript, advanced just preserves full content
            pass

        # Calculate metadata
        word_count = len(transcript.split())
        # Reading time at 238 WPM
        duration = word_count / 238.0

        result = {
            "title": title,
            "content": transcript,
            "format": "markdown",
            "learning_objective": script.get("learning_objective", ""),
        }

        return json.dumps(result), {
            "word_count": word_count,
            "estimated_duration_minutes": duration,
        }

    def _compress_to_essential(self, transcript: str) -> str:
        """Compress transcript to essential points only.

        This is a simple heuristic - a more sophisticated approach
        would use AI summarization.
        """
        lines = transcript.split("\n")
        essential_lines = []

        for line in lines:
            # Keep headers
            if line.startswith("#"):
                essential_lines.append(line)
            # Keep first sentence of each paragraph (simplified)
            elif line.strip() and not line.startswith(" "):
                # Take first sentence
                sentences = line.split(". ")
                if sentences:
                    essential_lines.append(sentences[0] + "." if not sentences[0].endswith(".") else sentences[0])

        return "\n".join(essential_lines)


class AudioNarrationGenerator(VariantGenerator):
    """Generates audio narration script from primary content.

    Transforms primary content into a format optimized for text-to-speech:
    - Shorter sentences for natural pacing
    - Pronunciation hints for technical terms
    - Natural speech patterns and transitions
    - No visual references that don't make sense in audio
    """

    @property
    def source_variant_type(self) -> VariantType:
        return VariantType.PRIMARY

    @property
    def target_variant_type(self) -> VariantType:
        return VariantType.AUDIO_ONLY

    @ai_retry
    def transform(
        self,
        source_content: str,
        depth_level: DepthLevel = DepthLevel.STANDARD,
        **kwargs
    ) -> Tuple[str, Dict[str, Any]]:
        """Transform primary content into audio narration script.

        Uses AI to rewrite content for optimal TTS delivery.
        """
        try:
            content_data = json.loads(source_content)
        except json.JSONDecodeError:
            # If not valid JSON, treat as plain text
            content_data = {"text": source_content}

        # Extract readable text from content
        text_content = self._extract_text(content_data)

        system_prompt = """You are an expert at converting written content into audio narration scripts optimized for text-to-speech (TTS) delivery.

Your output should:
1. Use shorter sentences (15-20 words max) for natural pacing
2. Replace visual references ("as shown above", "in the diagram") with descriptive language
3. Add natural transitions between sections
4. Include pronunciation hints in [brackets] for technical terms or acronyms
5. Use conversational but professional tone
6. Avoid bullet points - convert to flowing prose
7. Include pause markers with "..." for natural breathing points

Return a JSON object with:
- title: The title of the content
- narration: The full narration text ready for TTS
- duration_estimate_minutes: Estimated narration duration at 150 WPM
- pronunciation_notes: Array of {term, pronunciation} for technical terms"""

        user_prompt = f"""Convert this content into an audio narration script:

{text_content}

Target depth level: {depth_level.value}
{"Compress to essential points only." if depth_level == DepthLevel.ESSENTIAL else ""}
{"Expand with additional detail and examples." if depth_level == DepthLevel.ADVANCED else ""}"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=Config.MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        result_text = response.content[0].text

        # Try to extract JSON
        if "```json" in result_text:
            start = result_text.find("```json") + 7
            end = result_text.find("```", start)
            if end > start:
                result_text = result_text[start:end].strip()
        elif "```" in result_text:
            start = result_text.find("```") + 3
            end = result_text.find("```", start)
            if end > start:
                result_text = result_text[start:end].strip()

        try:
            result_data = json.loads(result_text)
        except json.JSONDecodeError:
            # Fallback to wrapping as narration
            result_data = {
                "title": content_data.get("title", "Audio Narration"),
                "narration": result_text,
                "duration_estimate_minutes": len(result_text.split()) / 150.0,
                "pronunciation_notes": []
            }

        word_count = len(result_data.get("narration", "").split())
        duration = result_data.get("duration_estimate_minutes", word_count / 150.0)

        return json.dumps(result_data), {
            "word_count": word_count,
            "estimated_duration_minutes": duration,
        }

    def _extract_text(self, content_data: Dict) -> str:
        """Extract readable text from various content formats."""
        parts = []

        if isinstance(content_data, str):
            return content_data

        # Handle title
        if "title" in content_data:
            parts.append(f"Title: {content_data['title']}")

        # Handle video script sections
        sections = ["hook", "objective", "content", "ivq", "summary", "cta"]
        for section in sections:
            if section in content_data and content_data[section]:
                section_data = content_data[section]
                if isinstance(section_data, dict):
                    if section_data.get("script_text"):
                        parts.append(section_data["script_text"])
                elif isinstance(section_data, str):
                    parts.append(section_data)

        # Handle reading content
        if "introduction" in content_data:
            parts.append(content_data["introduction"])

        if "sections" in content_data:
            for section in content_data["sections"]:
                if isinstance(section, dict):
                    if section.get("heading") or section.get("title"):
                        parts.append(section.get("heading") or section.get("title"))
                    if section.get("body") or section.get("content"):
                        parts.append(section.get("body") or section.get("content"))

        if "conclusion" in content_data:
            parts.append(content_data["conclusion"])

        # Handle generic text field
        if "text" in content_data:
            parts.append(content_data["text"])

        return "\n\n".join(parts) if parts else str(content_data)


class DepthAdapter:
    """Adapts content between depth levels using AI.

    Compresses content for Essential level or expands for Advanced level.
    """

    def __init__(self, api_key: str = None, model: str = None):
        """Initialize adapter with Anthropic client."""
        self.client = Anthropic(api_key=api_key or Config.ANTHROPIC_API_KEY)
        self.model = model or Config.MODEL

    @ai_retry
    def adapt_depth(
        self,
        content: str,
        source_depth: DepthLevel,
        target_depth: DepthLevel,
        content_type: str = "general"
    ) -> Tuple[str, Dict[str, Any]]:
        """Adapt content from one depth level to another.

        Args:
            content: Source content (JSON string)
            source_depth: Current depth level
            target_depth: Target depth level
            content_type: Type of content for context

        Returns:
            Tuple of (adapted content JSON, metadata dict)
        """
        if source_depth == target_depth:
            return content, {"word_count": len(content.split())}

        direction = "compress" if target_depth == DepthLevel.ESSENTIAL else "expand"

        system_prompt = f"""You are an expert content adapter specializing in {content_type} content.
Your task is to {direction} the given content while preserving its educational value.

{"For ESSENTIAL level: Focus on key takeaways, remove examples and elaboration, keep only core concepts." if direction == "compress" else "For ADVANCED level: Add deeper explanations, additional examples, edge cases, and connections to related topics."}

Maintain the same JSON structure as the input."""

        user_prompt = f"""Adapt this content from {source_depth.value} to {target_depth.value} depth:

{content}

Return the adapted content in the same JSON format."""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=Config.MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        adapted_content = response.content[0].text

        # Try to extract JSON if wrapped in markdown code blocks
        if "```json" in adapted_content:
            start = adapted_content.find("```json") + 7
            end = adapted_content.find("```", start)
            if end > start:
                adapted_content = adapted_content[start:end].strip()
        elif "```" in adapted_content:
            start = adapted_content.find("```") + 3
            end = adapted_content.find("```", start)
            if end > start:
                adapted_content = adapted_content[start:end].strip()

        word_count = len(adapted_content.split())

        return adapted_content, {
            "word_count": word_count,
            "source_depth": source_depth.value,
            "target_depth": target_depth.value,
        }


# Registry of available variant generators by (source_type, target_type)
VARIANT_GENERATORS = {
    (VariantType.PRIMARY, VariantType.TRANSCRIPT): TranscriptVariantGenerator,
    (VariantType.PRIMARY, VariantType.AUDIO_ONLY): AudioNarrationGenerator,
}


def get_variant_generator(
    source_type: VariantType,
    target_type: VariantType
) -> Optional[VariantGenerator]:
    """Get the appropriate variant generator for a transformation.

    Args:
        source_type: Source variant type
        target_type: Target variant type

    Returns:
        VariantGenerator instance or None if not supported
    """
    generator_class = VARIANT_GENERATORS.get((source_type, target_type))
    if generator_class:
        return generator_class()
    return None
