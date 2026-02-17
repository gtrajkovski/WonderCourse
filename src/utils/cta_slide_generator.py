"""CTA (Call-to-Action) slide generator for video endings.

Generates end-of-video CTA slides per Coursera v3.0 specs:
- Canvas: 1280x720 px (16:9 HD)
- Coursera blue: #0056D2
- Course label, video title, tagline, footer
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Optional, Tuple, Union, Any
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    # Stub types for when Pillow isn't available
    Image = None  # type: ignore
    ImageDraw = None  # type: ignore
    ImageFont = None  # type: ignore


@dataclass
class CTASlideStyle:
    """CTA slide visual styling configuration."""

    # Canvas dimensions (16:9 HD)
    width: int = 1280
    height: int = 720

    # Colors
    background: Tuple[int, int, int] = (0, 86, 210)  # Coursera blue #0056D2
    text_primary: Tuple[int, int, int] = (255, 255, 255)
    text_secondary: Tuple[int, int, int] = (200, 220, 255)
    accent: Tuple[int, int, int] = (255, 255, 255)

    # Typography
    title_font_size: int = 48
    subtitle_font_size: int = 32
    label_font_size: int = 24
    footer_font_size: int = 18

    # Layout
    padding: int = 60
    line_spacing: float = 1.5

    # Branding
    show_coursera_logo: bool = True
    logo_position: str = "bottom-right"  # bottom-right, bottom-left, top-right

    # Optional decorations
    show_gradient: bool = True
    gradient_start: Tuple[int, int, int] = (0, 86, 210)
    gradient_end: Tuple[int, int, int] = (0, 60, 160)


@dataclass
class CTASlideContent:
    """Content for a CTA slide."""

    # Required
    video_title: str

    # Optional
    course_label: Optional[str] = None  # e.g., "Module 1, Lesson 3"
    tagline: Optional[str] = None  # e.g., "Ready to put this into practice?"
    footer: Optional[str] = None  # e.g., "Continue learning on Coursera"

    # CTA text
    cta_text: Optional[str] = None  # e.g., "Next: Hands-on Lab"


class CTASlideGenerator:
    """Generates CTA slides for video endings.

    Usage:
        generator = CTASlideGenerator()

        content = CTASlideContent(
            video_title="Building REST APIs with Flask",
            course_label="Module 2, Lesson 1",
            tagline="Ready to build your first API?",
            footer="Continue your journey on Coursera"
        )

        image = generator.generate(content)
        generator.save(image, "cta_slide.png")
    """

    def __init__(self, style: Optional[CTASlideStyle] = None):
        if not PILLOW_AVAILABLE:
            raise ImportError(
                "Pillow is required for CTA slide generation. "
                "Install it with: pip install Pillow"
            )

        self.style = style or CTASlideStyle()
        self._fonts = self._load_fonts()

    def _load_fonts(self) -> dict:
        """Load fonts for different text sizes."""
        font_names = [
            "Arial Bold",
            "Helvetica Bold",
            "Arial",
            "Helvetica",
            "DejaVu Sans",
        ]

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
            "label": load_font(self.style.label_font_size),
            "footer": load_font(self.style.footer_font_size),
        }

    def _draw_gradient_background(self, image: Any):
        """Draw a gradient background."""
        if not self.style.show_gradient:
            return

        pixels = image.load()
        r1, g1, b1 = self.style.gradient_start
        r2, g2, b2 = self.style.gradient_end

        for y in range(self.style.height):
            ratio = y / self.style.height
            r = int(r1 + (r2 - r1) * ratio)
            g = int(g1 + (g2 - g1) * ratio)
            b = int(b1 + (b2 - b1) * ratio)

            for x in range(self.style.width):
                pixels[x, y] = (r, g, b)

    def _get_text_size(self, text: str, font: Any) -> Tuple[int, int]:
        """Get text dimensions."""
        try:
            bbox = font.getbbox(text)
            return (bbox[2] - bbox[0], bbox[3] - bbox[1])
        except AttributeError:
            return font.getsize(text)

    def _draw_centered_text(
        self,
        draw: Any,
        text: str,
        y: int,
        font: Any,
        color: Tuple[int, int, int]
    ) -> int:
        """Draw centered text and return the bottom Y position."""
        text_width, text_height = self._get_text_size(text, font)
        x = (self.style.width - text_width) // 2
        draw.text((x, y), text, font=font, fill=color)
        return y + int(text_height * self.style.line_spacing)

    def _draw_decorative_line(self, draw: Any, y: int, width: int = 100):
        """Draw a decorative accent line."""
        x_start = (self.style.width - width) // 2
        x_end = x_start + width
        draw.line(
            [(x_start, y), (x_end, y)],
            fill=self.style.accent,
            width=3
        )

    def generate(self, content: CTASlideContent) -> Any:
        """Generate a CTA slide image.

        Args:
            content: CTASlideContent object with slide content

        Returns:
            PIL Image object
        """
        # Create image with background
        image = Image.new("RGB", (self.style.width, self.style.height), self.style.background)

        # Apply gradient if enabled
        if self.style.show_gradient:
            self._draw_gradient_background(image)

        draw = ImageDraw.Draw(image)

        # Calculate vertical layout
        content_start_y = self.style.height // 3

        # Draw course label (if provided)
        current_y = content_start_y
        if content.course_label:
            current_y = self._draw_centered_text(
                draw,
                content.course_label.upper(),
                current_y,
                self._fonts["label"],
                self.style.text_secondary
            )
            current_y += 10

        # Draw video title
        current_y = self._draw_centered_text(
            draw,
            content.video_title,
            current_y,
            self._fonts["title"],
            self.style.text_primary
        )

        # Draw decorative line
        current_y += 20
        self._draw_decorative_line(draw, current_y)
        current_y += 40

        # Draw tagline (if provided)
        if content.tagline:
            current_y = self._draw_centered_text(
                draw,
                content.tagline,
                current_y,
                self._fonts["subtitle"],
                self.style.text_primary
            )

        # Draw CTA text (if provided)
        if content.cta_text:
            current_y += 20
            self._draw_centered_text(
                draw,
                content.cta_text,
                current_y,
                self._fonts["label"],
                self.style.text_secondary
            )

        # Draw footer at bottom
        if content.footer:
            footer_y = self.style.height - self.style.padding - 20
            self._draw_centered_text(
                draw,
                content.footer,
                footer_y,
                self._fonts["footer"],
                self.style.text_secondary
            )

        return image

    def save(
        self,
        image: Any,
        path: Union[str, Path],
        format: str = "PNG"
    ):
        """Save image to file.

        Args:
            image: PIL Image to save
            path: Output file path
            format: Image format (PNG, JPEG, etc.)
        """
        image.save(path, format=format)

    def to_bytes(
        self,
        image: Any,
        format: str = "PNG"
    ) -> bytes:
        """Convert image to bytes.

        Args:
            image: PIL Image
            format: Image format

        Returns:
            Image as bytes
        """
        buffer = io.BytesIO()
        image.save(buffer, format=format)
        return buffer.getvalue()


def generate_cta_slide(
    video_title: str,
    course_label: Optional[str] = None,
    tagline: Optional[str] = None,
    footer: Optional[str] = None,
    style: Optional[CTASlideStyle] = None
) -> bytes:
    """Convenience function to generate a CTA slide.

    Args:
        video_title: Title of the video
        course_label: Optional course/module label
        tagline: Optional motivational tagline
        footer: Optional footer text
        style: Optional custom styling

    Returns:
        PNG image as bytes
    """
    generator = CTASlideGenerator(style)
    content = CTASlideContent(
        video_title=video_title,
        course_label=course_label,
        tagline=tagline,
        footer=footer
    )
    image = generator.generate(content)
    return generator.to_bytes(image)
