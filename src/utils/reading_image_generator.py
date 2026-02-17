"""Reading image generator for text-based activities.

Generates placeholder/concept images for readings based on content analysis:
- Extracts key concepts from reading text
- Creates placeholder images with concept descriptions
- Supports user-specified image count (1, 2, 3, etc.)
- Images can be used as placeholders for AI image generation

Usage:
    generator = ReadingImageGenerator()

    # Extract concepts and generate placeholders
    images = generator.generate_images(reading_content, count=3)

    # Get concept descriptions for external AI image generation
    concepts = generator.extract_concepts(reading_content, count=3)
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any, Union
from pathlib import Path
from enum import Enum

try:
    from PIL import Image, ImageDraw, ImageFont
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    Image = None  # type: ignore
    ImageDraw = None  # type: ignore
    ImageFont = None  # type: ignore


class ImageType(Enum):
    """Types of reading images."""
    CONCEPT = "concept"          # Abstract concept illustration
    DIAGRAM = "diagram"          # Process or flow diagram
    EXAMPLE = "example"          # Code or example illustration
    COMPARISON = "comparison"    # Compare/contrast visual
    INFOGRAPHIC = "infographic"  # Data or stats visual


@dataclass
class ImageStyle:
    """Reading image visual styling."""

    # Canvas (16:9)
    width: int = 1200
    height: int = 675

    # Colors
    background: Tuple[int, int, int] = (248, 249, 250)
    border: Tuple[int, int, int] = (222, 226, 230)
    text_primary: Tuple[int, int, int] = (33, 37, 41)
    text_secondary: Tuple[int, int, int] = (108, 117, 125)
    accent: Tuple[int, int, int] = (0, 86, 210)  # Coursera blue

    # Typography
    title_font_size: int = 36
    body_font_size: int = 24
    caption_font_size: int = 18

    # Layout
    padding: int = 60
    border_width: int = 2


@dataclass
class ImageConcept:
    """A concept extracted for image generation."""

    title: str
    description: str
    image_type: ImageType = ImageType.CONCEPT
    keywords: List[str] = field(default_factory=list)
    context: Optional[str] = None  # Surrounding text for context

    def to_prompt(self) -> str:
        """Convert to image generation prompt."""
        keywords_str = ", ".join(self.keywords[:5]) if self.keywords else ""
        prompt = f"Educational illustration: {self.title}. {self.description}"
        if keywords_str:
            prompt += f" Keywords: {keywords_str}"
        return prompt


@dataclass
class GeneratedImage:
    """A generated placeholder image with metadata."""

    concept: ImageConcept
    image_bytes: bytes
    format: str = "PNG"
    width: int = 1200
    height: int = 675


class ReadingImageGenerator:
    """Generates placeholder images for reading content.

    Usage:
        generator = ReadingImageGenerator()

        # Extract concepts from reading
        concepts = generator.extract_concepts(reading_content, count=3)

        # Generate placeholder images
        images = generator.generate_images(reading_content, count=3)

        # Or generate from specific concepts
        image = generator.generate_concept_image(concepts[0])
    """

    def __init__(self, style: Optional[ImageStyle] = None):
        self.style = style or ImageStyle()
        self._fonts: Optional[Dict[str, Any]] = None

        if PILLOW_AVAILABLE:
            self._fonts = self._load_fonts()

    def _load_fonts(self) -> Dict[str, Any]:
        """Load fonts for text rendering."""
        font_names = ["Arial Bold", "Helvetica Bold", "Arial", "DejaVu Sans"]

        def load_font(size: int) -> Any:
            for font_name in font_names:
                try:
                    return ImageFont.truetype(font_name, size)
                except (IOError, OSError):
                    continue
            return ImageFont.load_default()

        return {
            "title": load_font(self.style.title_font_size),
            "body": load_font(self.style.body_font_size),
            "caption": load_font(self.style.caption_font_size),
        }

    def extract_concepts(
        self,
        content: Union[str, Dict[str, Any]],
        count: int = 3
    ) -> List[ImageConcept]:
        """Extract key concepts from reading content.

        Args:
            content: Reading content (string or dict with 'content'/'body' key)
            count: Number of concepts to extract

        Returns:
            List of ImageConcept objects
        """
        # Extract text from content
        if isinstance(content, dict):
            text = content.get("content", "") or content.get("body", "")
            if isinstance(text, list):
                text = "\n".join(str(item) for item in text)
        else:
            text = content

        concepts = []

        # Strategy 1: Extract from headers/sections
        header_concepts = self._extract_from_headers(text)
        concepts.extend(header_concepts)

        # Strategy 2: Extract from key phrases
        phrase_concepts = self._extract_from_phrases(text)
        concepts.extend(phrase_concepts)

        # Strategy 3: Extract from definitions
        definition_concepts = self._extract_from_definitions(text)
        concepts.extend(definition_concepts)

        # Strategy 4: Extract from examples
        example_concepts = self._extract_from_examples(text)
        concepts.extend(example_concepts)

        # Deduplicate and rank
        unique_concepts = self._deduplicate_concepts(concepts)
        ranked = self._rank_concepts(unique_concepts, text)

        return ranked[:count]

    def _extract_from_headers(self, text: str) -> List[ImageConcept]:
        """Extract concepts from markdown headers."""
        concepts = []

        # Match markdown headers (allowing leading whitespace)
        header_pattern = r'^\s*#{1,3}\s+(.+?)$'
        matches = re.findall(header_pattern, text, re.MULTILINE)

        for match in matches:
            title = match.strip()
            if len(title) > 5 and len(title) < 100:
                concepts.append(ImageConcept(
                    title=title,
                    description=f"Visual representation of {title.lower()}",
                    image_type=ImageType.CONCEPT,
                    keywords=self._extract_keywords(title)
                ))

        return concepts

    def _extract_from_phrases(self, text: str) -> List[ImageConcept]:
        """Extract concepts from key educational phrases."""
        concepts = []

        patterns = [
            (r'(?:The key (?:concept|idea|principle) (?:is|of) )([^.]+)', ImageType.CONCEPT),
            (r'(?:This (?:demonstrates|shows|illustrates) )([^.]+)', ImageType.EXAMPLE),
            (r'(?:The process (?:of|for) )([^.]+)', ImageType.DIAGRAM),
            (r'(?:Compared to|Unlike|In contrast to) ([^,]+)', ImageType.COMPARISON),
            (r'(?:There are (?:\d+|several|multiple) (?:types|kinds|categories) of )([^.]+)', ImageType.INFOGRAPHIC),
        ]

        for pattern, img_type in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                title = match.strip()[:80]
                if len(title) > 10:
                    concepts.append(ImageConcept(
                        title=title,
                        description=f"Illustration showing {title.lower()}",
                        image_type=img_type,
                        keywords=self._extract_keywords(title)
                    ))

        return concepts

    def _extract_from_definitions(self, text: str) -> List[ImageConcept]:
        """Extract concepts from definitions."""
        concepts = []

        # Pattern: "X is defined as Y" or "X refers to Y"
        patterns = [
            r'(\w+(?:\s+\w+)?)\s+(?:is defined as|refers to|means)\s+([^.]+)',
            r'(?:A|An)\s+(\w+(?:\s+\w+)?)\s+is\s+([^.]+)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for term, definition in matches:
                if len(term) > 3 and len(definition) > 10:
                    concepts.append(ImageConcept(
                        title=term.strip(),
                        description=definition.strip()[:150],
                        image_type=ImageType.CONCEPT,
                        keywords=self._extract_keywords(f"{term} {definition}")
                    ))

        return concepts

    def _extract_from_examples(self, text: str) -> List[ImageConcept]:
        """Extract concepts from examples."""
        concepts = []

        # Pattern: "For example, X" or "such as X"
        patterns = [
            r'(?:For example|For instance),\s+([^.]+)',
            r'such as\s+([^.]+)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches[:2]:  # Limit examples
                example = match.strip()[:80]
                if len(example) > 15:
                    concepts.append(ImageConcept(
                        title=f"Example: {example[:40]}",
                        description=example,
                        image_type=ImageType.EXAMPLE,
                        keywords=self._extract_keywords(example)
                    ))

        return concepts

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text."""
        # Remove common words
        stop_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'must', 'can',
            'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
            'as', 'into', 'through', 'during', 'before', 'after', 'above',
            'below', 'between', 'under', 'and', 'but', 'or', 'nor', 'so',
            'yet', 'both', 'either', 'neither', 'not', 'only', 'own',
            'same', 'than', 'too', 'very', 'this', 'that', 'these', 'those',
        }

        # Extract words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())

        # Filter and deduplicate
        keywords = []
        seen = set()
        for word in words:
            if word not in stop_words and word not in seen:
                keywords.append(word)
                seen.add(word)

        return keywords[:10]

    def _deduplicate_concepts(self, concepts: List[ImageConcept]) -> List[ImageConcept]:
        """Remove duplicate concepts based on title similarity."""
        unique = []
        seen_titles = set()

        for concept in concepts:
            # Normalize title for comparison
            normalized = concept.title.lower().strip()
            if normalized not in seen_titles:
                unique.append(concept)
                seen_titles.add(normalized)

        return unique

    def _rank_concepts(
        self,
        concepts: List[ImageConcept],
        full_text: str
    ) -> List[ImageConcept]:
        """Rank concepts by importance."""
        # Simple ranking based on:
        # 1. Image type variety (prefer different types)
        # 2. Keyword count
        # 3. Title length (medium length preferred)

        def score(concept: ImageConcept) -> float:
            s = 0.0

            # Keyword count (more keywords = more specific)
            s += len(concept.keywords) * 0.5

            # Title length (prefer 20-60 chars)
            title_len = len(concept.title)
            if 20 <= title_len <= 60:
                s += 2.0
            elif title_len < 20:
                s += 1.0

            # Image type bonus
            type_scores = {
                ImageType.DIAGRAM: 2.0,
                ImageType.CONCEPT: 1.5,
                ImageType.COMPARISON: 1.5,
                ImageType.INFOGRAPHIC: 1.0,
                ImageType.EXAMPLE: 0.5,
            }
            s += type_scores.get(concept.image_type, 0)

            return s

        return sorted(concepts, key=score, reverse=True)

    def generate_concept_image(self, concept: ImageConcept) -> Any:
        """Generate a placeholder image for a concept.

        Args:
            concept: ImageConcept to visualize

        Returns:
            PIL Image object
        """
        if not PILLOW_AVAILABLE:
            raise ImportError(
                "Pillow is required for image generation. "
                "Install it with: pip install Pillow"
            )

        # Create image
        image = Image.new(
            "RGB",
            (self.style.width, self.style.height),
            self.style.background
        )
        draw = ImageDraw.Draw(image)

        # Draw border
        draw.rectangle(
            [0, 0, self.style.width - 1, self.style.height - 1],
            outline=self.style.border,
            width=self.style.border_width
        )

        # Draw image type indicator
        self._draw_type_indicator(draw, concept.image_type)

        # Draw title
        title_y = self.style.padding + 60
        self._draw_centered_text(
            draw,
            concept.title,
            title_y,
            self._fonts["title"],
            self.style.text_primary
        )

        # Draw description (wrapped)
        desc_y = title_y + 60
        wrapped_desc = self._wrap_text(concept.description, 50)
        for line in wrapped_desc[:3]:
            self._draw_centered_text(
                draw,
                line,
                desc_y,
                self._fonts["body"],
                self.style.text_secondary
            )
            desc_y += 35

        # Draw placeholder icon based on type
        self._draw_placeholder_icon(draw, concept.image_type)

        # Draw keywords at bottom
        if concept.keywords:
            keywords_text = "Keywords: " + ", ".join(concept.keywords[:5])
            self._draw_centered_text(
                draw,
                keywords_text,
                self.style.height - self.style.padding - 30,
                self._fonts["caption"],
                self.style.text_secondary
            )

        # Draw "placeholder" label
        self._draw_placeholder_label(draw)

        return image

    def _draw_type_indicator(self, draw: Any, image_type: ImageType):
        """Draw image type indicator at top."""
        type_labels = {
            ImageType.CONCEPT: "CONCEPT",
            ImageType.DIAGRAM: "DIAGRAM",
            ImageType.EXAMPLE: "EXAMPLE",
            ImageType.COMPARISON: "COMPARISON",
            ImageType.INFOGRAPHIC: "INFOGRAPHIC",
        }

        label = type_labels.get(image_type, "IMAGE")

        # Draw label box
        label_width = 120
        label_height = 28
        x = self.style.width - self.style.padding - label_width
        y = self.style.padding

        draw.rectangle(
            [x, y, x + label_width, y + label_height],
            fill=self.style.accent
        )

        # Draw label text
        try:
            bbox = self._fonts["caption"].getbbox(label)
            text_width = bbox[2] - bbox[0]
        except AttributeError:
            text_width = self._fonts["caption"].getsize(label)[0]

        text_x = x + (label_width - text_width) // 2
        text_y = y + 5
        draw.text(
            (text_x, text_y),
            label,
            font=self._fonts["caption"],
            fill=(255, 255, 255)
        )

    def _draw_placeholder_icon(self, draw: Any, image_type: ImageType):
        """Draw a placeholder icon based on image type."""
        center_x = self.style.width // 2
        center_y = self.style.height // 2 + 30

        # Draw a simple geometric shape based on type
        if image_type == ImageType.DIAGRAM:
            # Draw connected boxes
            self._draw_flow_diagram(draw, center_x, center_y)
        elif image_type == ImageType.COMPARISON:
            # Draw two columns
            self._draw_comparison_columns(draw, center_x, center_y)
        elif image_type == ImageType.INFOGRAPHIC:
            # Draw bar chart placeholder
            self._draw_bar_chart(draw, center_x, center_y)
        else:
            # Draw abstract concept circle
            self._draw_concept_circle(draw, center_x, center_y)

    def _draw_flow_diagram(self, draw: Any, cx: int, cy: int):
        """Draw a simple flow diagram placeholder."""
        box_width = 80
        box_height = 40
        spacing = 40

        # Three connected boxes
        for i, offset in enumerate([-1, 0, 1]):
            x = cx + offset * (box_width + spacing) - box_width // 2
            y = cy - box_height // 2

            draw.rectangle(
                [x, y, x + box_width, y + box_height],
                outline=self.style.accent,
                width=2
            )

            # Draw arrow between boxes
            if i < 2:
                arrow_x = x + box_width + 5
                arrow_y = cy
                draw.line(
                    [(arrow_x, arrow_y), (arrow_x + spacing - 10, arrow_y)],
                    fill=self.style.accent,
                    width=2
                )

    def _draw_comparison_columns(self, draw: Any, cx: int, cy: int):
        """Draw two column comparison placeholder."""
        col_width = 150
        col_height = 100
        spacing = 40

        for offset in [-1, 1]:
            x = cx + offset * (col_width // 2 + spacing // 2) - col_width // 2
            y = cy - col_height // 2

            draw.rectangle(
                [x, y, x + col_width, y + col_height],
                outline=self.style.accent,
                width=2
            )

            # Draw lines inside
            for i in range(3):
                line_y = y + 25 + i * 25
                draw.line(
                    [(x + 15, line_y), (x + col_width - 15, line_y)],
                    fill=self.style.border,
                    width=1
                )

    def _draw_bar_chart(self, draw: Any, cx: int, cy: int):
        """Draw bar chart placeholder."""
        bar_width = 30
        max_height = 80
        spacing = 15
        num_bars = 4

        total_width = num_bars * bar_width + (num_bars - 1) * spacing
        start_x = cx - total_width // 2

        heights = [60, 80, 45, 70]

        for i, h in enumerate(heights):
            x = start_x + i * (bar_width + spacing)
            y = cy + max_height // 2 - h

            draw.rectangle(
                [x, y, x + bar_width, cy + max_height // 2],
                fill=self.style.accent
            )

    def _draw_concept_circle(self, draw: Any, cx: int, cy: int):
        """Draw abstract concept circle."""
        radius = 50

        # Outer circle
        draw.ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            outline=self.style.accent,
            width=3
        )

        # Inner circle
        inner_radius = 30
        draw.ellipse(
            [cx - inner_radius, cy - inner_radius, cx + inner_radius, cy + inner_radius],
            outline=self.style.accent,
            width=2
        )

        # Center dot
        dot_radius = 8
        draw.ellipse(
            [cx - dot_radius, cy - dot_radius, cx + dot_radius, cy + dot_radius],
            fill=self.style.accent
        )

    def _draw_placeholder_label(self, draw: Any):
        """Draw 'PLACEHOLDER' label at bottom-left."""
        label = "IMAGE PLACEHOLDER"
        x = self.style.padding
        y = self.style.height - self.style.padding - 10

        draw.text(
            (x, y),
            label,
            font=self._fonts["caption"],
            fill=self.style.text_secondary
        )

    def _draw_centered_text(
        self,
        draw: Any,
        text: str,
        y: int,
        font: Any,
        color: Tuple[int, int, int]
    ):
        """Draw horizontally centered text."""
        try:
            bbox = font.getbbox(text)
            text_width = bbox[2] - bbox[0]
        except AttributeError:
            text_width = font.getsize(text)[0]

        x = (self.style.width - text_width) // 2
        draw.text((x, y), text, font=font, fill=color)

    def _wrap_text(self, text: str, max_chars: int) -> List[str]:
        """Wrap text to multiple lines."""
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            if len(' '.join(current_line + [word])) <= max_chars:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]

        if current_line:
            lines.append(' '.join(current_line))

        return lines

    def generate_images(
        self,
        content: Union[str, Dict[str, Any]],
        count: int = 3
    ) -> List[GeneratedImage]:
        """Generate placeholder images for reading content.

        Args:
            content: Reading content
            count: Number of images to generate (1-5)

        Returns:
            List of GeneratedImage objects
        """
        if not PILLOW_AVAILABLE:
            raise ImportError(
                "Pillow is required for image generation. "
                "Install it with: pip install Pillow"
            )

        # Clamp count
        count = max(1, min(5, count))

        # Extract concepts
        concepts = self.extract_concepts(content, count)

        # Generate images
        images = []
        for concept in concepts:
            pil_image = self.generate_concept_image(concept)
            image_bytes = self._to_bytes(pil_image)

            images.append(GeneratedImage(
                concept=concept,
                image_bytes=image_bytes,
                width=self.style.width,
                height=self.style.height
            ))

        return images

    def _to_bytes(self, image: Any, format: str = "PNG") -> bytes:
        """Convert PIL image to bytes."""
        buffer = io.BytesIO()
        image.save(buffer, format=format)
        return buffer.getvalue()

    def save_images(
        self,
        images: List[GeneratedImage],
        output_dir: Union[str, Path]
    ):
        """Save generated images to directory.

        Args:
            images: List of GeneratedImage objects
            output_dir: Output directory path
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        for i, img in enumerate(images):
            filename = f"reading_image_{i+1:02d}_{img.concept.image_type.value}.png"
            with open(output_dir / filename, "wb") as f:
                f.write(img.image_bytes)


def generate_reading_images(
    content: Union[str, Dict[str, Any]],
    count: int = 3,
    style: Optional[ImageStyle] = None
) -> List[bytes]:
    """Convenience function to generate reading images.

    Args:
        content: Reading content (string or dict)
        count: Number of images to generate
        style: Optional custom styling

    Returns:
        List of PNG images as bytes
    """
    generator = ReadingImageGenerator(style)
    images = generator.generate_images(content, count)
    return [img.image_bytes for img in images]


def extract_image_concepts(
    content: Union[str, Dict[str, Any]],
    count: int = 3
) -> List[Dict[str, Any]]:
    """Extract image concepts without generating images.

    Useful for passing to external AI image generators.

    Args:
        content: Reading content
        count: Number of concepts to extract

    Returns:
        List of concept dictionaries with prompts
    """
    generator = ReadingImageGenerator()
    concepts = generator.extract_concepts(content, count)

    return [
        {
            "title": c.title,
            "description": c.description,
            "image_type": c.image_type.value,
            "keywords": c.keywords,
            "prompt": c.to_prompt()
        }
        for c in concepts
    ]
