"""Video slide generator for non-screencast video portions.

Generates presentation slides from video script sections:
- Title slides for hooks and objectives
- Content slides with key points
- Visual cue slides
- Summary slides
- CTA slides

Slides are generated on-demand after narrative is finalized.
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


class SlideType(Enum):
    """Types of video presentation slides."""
    TITLE = "title"
    OBJECTIVE = "objective"
    CONTENT = "content"
    KEY_POINT = "key_point"
    VISUAL_CUE = "visual_cue"
    DIAGRAM = "diagram"
    SUMMARY = "summary"
    CTA = "cta"


@dataclass
class SlideStyle:
    """Presentation slide visual styling."""

    # Canvas (16:9 HD)
    width: int = 1920
    height: int = 1080

    # Colors
    background: Tuple[int, int, int] = (255, 255, 255)
    title_bg: Tuple[int, int, int] = (0, 86, 210)  # Coursera blue
    text_primary: Tuple[int, int, int] = (33, 33, 33)
    text_light: Tuple[int, int, int] = (255, 255, 255)
    accent: Tuple[int, int, int] = (0, 86, 210)
    bullet_color: Tuple[int, int, int] = (0, 86, 210)

    # Typography
    title_font_size: int = 64
    subtitle_font_size: int = 36
    body_font_size: int = 32
    caption_font_size: int = 24

    # Layout
    margin: int = 80
    line_spacing: float = 1.6
    bullet_indent: int = 40


@dataclass
class Slide:
    """A single presentation slide."""

    slide_type: SlideType
    title: str
    content: List[str] = field(default_factory=list)  # Bullet points or paragraphs
    subtitle: Optional[str] = None
    speaker_notes: Optional[str] = None
    visual_cue: Optional[str] = None  # Description of visual element
    image_placeholder: Optional[str] = None  # Placeholder description


@dataclass
class SlideSet:
    """A collection of slides for a video."""

    video_title: str
    slides: List[Slide] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class VideoSlideGenerator:
    """Generates presentation slides from video scripts.

    Usage:
        generator = VideoSlideGenerator()

        # Parse video script into slides
        slides = generator.parse_script(video_content)

        # Generate images for all slides
        images = generator.generate_images(slides)

        # Or generate a specific slide
        image = generator.generate_slide_image(slides.slides[0])
    """

    def __init__(self, style: Optional[SlideStyle] = None):
        if not PILLOW_AVAILABLE:
            raise ImportError(
                "Pillow is required for slide generation. "
                "Install it with: pip install Pillow"
            )

        self.style = style or SlideStyle()
        self._fonts = self._load_fonts()

    def _load_fonts(self) -> Dict[str, Any]:
        """Load fonts for different text sizes."""
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
            "subtitle": load_font(self.style.subtitle_font_size),
            "body": load_font(self.style.body_font_size),
            "caption": load_font(self.style.caption_font_size),
        }

    def parse_script(self, video_content: Dict[str, Any]) -> SlideSet:
        """Parse video script into slides.

        Args:
            video_content: Video content dict with sections, title, etc.

        Returns:
            SlideSet with parsed slides
        """
        slides = []
        video_title = video_content.get("title", "Video")
        sections = video_content.get("sections", [])

        for section in sections:
            section_name = section.get("section_name", "").lower()
            script_text = section.get("script_text", "")
            speaker_notes = section.get("speaker_notes", "")

            if section_name == "hook":
                slides.extend(self._parse_hook_section(script_text, video_title))
            elif section_name == "objective":
                slides.extend(self._parse_objective_section(script_text))
            elif section_name == "content":
                slides.extend(self._parse_content_section(script_text, speaker_notes))
            elif section_name == "ivq":
                slides.extend(self._parse_ivq_section(script_text))
            elif section_name == "summary":
                slides.extend(self._parse_summary_section(script_text))
            elif section_name == "cta":
                slides.extend(self._parse_cta_section(script_text, video_title))

        return SlideSet(video_title=video_title, slides=slides)

    def _parse_hook_section(self, text: str, video_title: str) -> List[Slide]:
        """Parse hook section into title slide."""
        return [Slide(
            slide_type=SlideType.TITLE,
            title=video_title,
            subtitle=self._extract_tagline(text),
            speaker_notes=text
        )]

    def _parse_objective_section(self, text: str) -> List[Slide]:
        """Parse objective section into learning objective slide."""
        objectives = self._extract_bullet_points(text)
        return [Slide(
            slide_type=SlideType.OBJECTIVE,
            title="Learning Objectives",
            content=objectives if objectives else [text],
            speaker_notes=text
        )]

    def _parse_content_section(self, text: str, notes: str) -> List[Slide]:
        """Parse content section into content slides."""
        slides = []

        # Extract visual cues and create slides around them
        visual_cue_pattern = r"\[([^\]]+)\]"
        segments = re.split(visual_cue_pattern, text)

        current_points = []
        slide_number = 1

        for i, segment in enumerate(segments):
            segment = segment.strip()
            if not segment:
                continue

            # Check if this is a visual cue
            if i % 2 == 1:  # Odd indices are captured groups (visual cues)
                # Create a visual cue slide
                if ":" in segment:
                    cue_type, cue_desc = segment.split(":", 1)
                    slides.append(Slide(
                        slide_type=SlideType.VISUAL_CUE,
                        title=cue_type.strip(),
                        content=[cue_desc.strip()],
                        visual_cue=segment,
                        image_placeholder=f"Visual: {cue_desc.strip()}"
                    ))
            else:
                # Extract key points from content
                points = self._extract_key_points(segment)
                if points:
                    # Group points into slides (max 4 per slide)
                    for j in range(0, len(points), 4):
                        slide_points = points[j:j+4]
                        slides.append(Slide(
                            slide_type=SlideType.KEY_POINT,
                            title=f"Key Points ({slide_number})",
                            content=slide_points,
                            speaker_notes=segment[:200]
                        ))
                        slide_number += 1

        return slides if slides else [Slide(
            slide_type=SlideType.CONTENT,
            title="Content",
            content=self._extract_bullet_points(text) or [text[:200]],
            speaker_notes=notes or text
        )]

    def _parse_ivq_section(self, text: str) -> List[Slide]:
        """Parse IVQ section into check-for-understanding slide."""
        return [Slide(
            slide_type=SlideType.KEY_POINT,
            title="Check Your Understanding",
            content=self._extract_bullet_points(text) or [text],
            speaker_notes=text
        )]

    def _parse_summary_section(self, text: str) -> List[Slide]:
        """Parse summary section into summary slide."""
        return [Slide(
            slide_type=SlideType.SUMMARY,
            title="Key Takeaways",
            content=self._extract_bullet_points(text) or [text],
            speaker_notes=text
        )]

    def _parse_cta_section(self, text: str, video_title: str) -> List[Slide]:
        """Parse CTA section into call-to-action slide."""
        return [Slide(
            slide_type=SlideType.CTA,
            title=video_title,
            subtitle=text,
            speaker_notes=text
        )]

    def _extract_tagline(self, text: str) -> str:
        """Extract a short tagline from text."""
        # Take first sentence as tagline
        sentences = re.split(r'[.!?]', text)
        return sentences[0].strip()[:100] if sentences else ""

    def _extract_bullet_points(self, text: str) -> List[str]:
        """Extract bullet points from text."""
        # Look for numbered lists or bullet markers
        patterns = [
            r'^\s*[-•*]\s*(.+?)$',  # Bullet markers
            r'^\s*\d+[.)]\s*(.+?)$',  # Numbered lists
        ]

        points = []
        for line in text.split('\n'):
            for pattern in patterns:
                match = re.match(pattern, line, re.MULTILINE)
                if match:
                    points.append(match.group(1).strip())
                    break

        return points

    def _extract_key_points(self, text: str) -> List[str]:
        """Extract key points from content text."""
        # Split into sentences and filter for key statements
        sentences = re.split(r'[.!?]', text)
        points = []

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20 and len(sentence) < 150:
                points.append(sentence)

        return points[:8]  # Max 8 key points

    def generate_slide_image(self, slide: Slide) -> Any:
        """Generate a single slide image.

        Args:
            slide: Slide object to render

        Returns:
            PIL Image object
        """
        # Create image
        image = Image.new("RGB", (self.style.width, self.style.height), self.style.background)
        draw = ImageDraw.Draw(image)

        # Draw based on slide type
        if slide.slide_type == SlideType.TITLE:
            self._draw_title_slide(draw, slide)
        elif slide.slide_type == SlideType.CTA:
            self._draw_cta_slide(draw, slide)
        else:
            self._draw_content_slide(draw, slide)

        return image

    def _draw_title_slide(self, draw: Any, slide: Slide):
        """Draw a title slide with centered text on colored background."""
        # Fill with title background color
        draw.rectangle([0, 0, self.style.width, self.style.height], fill=self.style.title_bg)

        # Draw title centered
        title_y = self.style.height // 3
        self._draw_centered_text(draw, slide.title, title_y, self._fonts["title"], self.style.text_light)

        # Draw subtitle if present
        if slide.subtitle:
            subtitle_y = title_y + 100
            self._draw_centered_text(draw, slide.subtitle, subtitle_y, self._fonts["subtitle"], self.style.text_light)

    def _draw_cta_slide(self, draw: Any, slide: Slide):
        """Draw a CTA slide."""
        # Same as title slide with different layout
        draw.rectangle([0, 0, self.style.width, self.style.height], fill=self.style.title_bg)

        title_y = self.style.height // 2 - 50
        self._draw_centered_text(draw, slide.title, title_y, self._fonts["title"], self.style.text_light)

        if slide.subtitle:
            subtitle_y = title_y + 100
            # Wrap long subtitle
            wrapped = self._wrap_text(slide.subtitle, 60)
            for i, line in enumerate(wrapped[:3]):
                self._draw_centered_text(draw, line, subtitle_y + i * 50, self._fonts["subtitle"], self.style.text_light)

    def _draw_content_slide(self, draw: Any, slide: Slide):
        """Draw a content slide with title and bullet points."""
        # Draw header bar
        header_height = 150
        draw.rectangle([0, 0, self.style.width, header_height], fill=self.style.accent)

        # Draw title in header
        title_y = (header_height - self.style.title_font_size) // 2
        draw.text(
            (self.style.margin, title_y),
            slide.title,
            font=self._fonts["title"],
            fill=self.style.text_light
        )

        # Draw bullet points
        y = header_height + self.style.margin
        for point in slide.content:
            # Draw bullet
            bullet_x = self.style.margin
            draw.text((bullet_x, y), "•", font=self._fonts["body"], fill=self.style.bullet_color)

            # Draw text
            text_x = self.style.margin + self.style.bullet_indent
            wrapped = self._wrap_text(point, 70)
            for line in wrapped[:2]:
                draw.text((text_x, y), line, font=self._fonts["body"], fill=self.style.text_primary)
                y += int(self.style.body_font_size * self.style.line_spacing)

            y += 10  # Extra spacing between points

    def _draw_centered_text(self, draw: Any, text: str, y: int, font: Any, color: Tuple[int, int, int]):
        """Draw centered text."""
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

    def generate_images(self, slide_set: SlideSet) -> List[Tuple[Slide, Any]]:
        """Generate images for all slides.

        Args:
            slide_set: SlideSet with slides to render

        Returns:
            List of (Slide, PIL Image) tuples
        """
        return [(slide, self.generate_slide_image(slide)) for slide in slide_set.slides]

    def save_slides(self, slide_set: SlideSet, output_dir: Union[str, Path]):
        """Save all slides as images.

        Args:
            slide_set: SlideSet to save
            output_dir: Directory to save images to
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        for i, slide in enumerate(slide_set.slides):
            image = self.generate_slide_image(slide)
            filename = f"slide_{i+1:02d}_{slide.slide_type.value}.png"
            image.save(output_dir / filename, "PNG")

    def to_bytes(self, image: Any, format: str = "PNG") -> bytes:
        """Convert image to bytes."""
        buffer = io.BytesIO()
        image.save(buffer, format=format)
        return buffer.getvalue()


def generate_video_slides(video_content: Dict[str, Any]) -> List[bytes]:
    """Convenience function to generate slides from video content.

    Args:
        video_content: Video content dictionary

    Returns:
        List of PNG images as bytes
    """
    generator = VideoSlideGenerator()
    slide_set = generator.parse_script(video_content)
    results = []

    for slide, image in generator.generate_images(slide_set):
        results.append(generator.to_bytes(image))

    return results
