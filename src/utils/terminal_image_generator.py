"""Terminal screenshot image generator for HOL code examples.

Generates dark terminal-style images per Coursera v3.0 visual specs:
- Background: RGB(30, 30, 30)
- Text: RGB(204, 204, 204)
- Prompt ($): RGB(78, 201, 176)
- Font: DejaVu Sans Mono, 14pt
- Min width: 600px
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union, TYPE_CHECKING, Any
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
class TerminalStyle:
    """Terminal visual styling configuration."""

    # Colors (RGB tuples)
    background: Tuple[int, int, int] = (30, 30, 30)
    text: Tuple[int, int, int] = (204, 204, 204)
    prompt: Tuple[int, int, int] = (78, 201, 176)
    command: Tuple[int, int, int] = (255, 255, 255)
    output: Tuple[int, int, int] = (204, 204, 204)
    error: Tuple[int, int, int] = (255, 85, 85)
    success: Tuple[int, int, int] = (85, 255, 85)
    comment: Tuple[int, int, int] = (128, 128, 128)

    # Dimensions
    min_width: int = 600
    padding: int = 20
    line_height: int = 22

    # Font
    font_size: int = 14
    font_family: str = "DejaVu Sans Mono"

    # Window chrome
    show_title_bar: bool = True
    title_bar_height: int = 28
    title_bar_color: Tuple[int, int, int] = (45, 45, 45)
    button_colors: List[Tuple[int, int, int]] = None

    def __post_init__(self):
        if self.button_colors is None:
            self.button_colors = [
                (255, 95, 86),   # Red (close)
                (255, 189, 46),  # Yellow (minimize)
                (39, 201, 63),   # Green (maximize)
            ]


@dataclass
class TerminalLine:
    """A single line in terminal output."""

    text: str
    line_type: str = "output"  # prompt, command, output, error, success, comment

    @classmethod
    def prompt(cls, command: str, prompt_char: str = "$") -> "TerminalLine":
        """Create a prompt line with command."""
        return cls(f"{prompt_char} {command}", "prompt")

    @classmethod
    def output(cls, text: str) -> "TerminalLine":
        """Create an output line."""
        return cls(text, "output")

    @classmethod
    def error(cls, text: str) -> "TerminalLine":
        """Create an error line."""
        return cls(text, "error")

    @classmethod
    def success(cls, text: str) -> "TerminalLine":
        """Create a success line."""
        return cls(text, "success")

    @classmethod
    def comment(cls, text: str) -> "TerminalLine":
        """Create a comment line."""
        return cls(f"# {text}", "comment")


class TerminalImageGenerator:
    """Generates terminal screenshot images.

    Usage:
        generator = TerminalImageGenerator()

        # Simple command/output
        image = generator.generate_simple("ls -la", output_lines)

        # Complex multi-line
        lines = [
            TerminalLine.prompt("python --version"),
            TerminalLine.output("Python 3.11.0"),
            TerminalLine.prompt("pip install flask"),
            TerminalLine.success("Successfully installed flask-2.3.0"),
        ]
        image = generator.generate(lines)
    """

    def __init__(self, style: Optional[TerminalStyle] = None):
        if not PILLOW_AVAILABLE:
            raise ImportError(
                "Pillow is required for terminal image generation. "
                "Install it with: pip install Pillow"
            )

        self.style = style or TerminalStyle()
        self._font = self._load_font()

    def _load_font(self) -> Any:
        """Load the terminal font."""
        # Try to load the specified font family
        font_names = [
            self.style.font_family,
            "DejaVuSansMono.ttf",
            "Consolas",
            "Monaco",
            "Courier New",
            "monospace",
        ]

        for font_name in font_names:
            try:
                return ImageFont.truetype(font_name, self.style.font_size)
            except (IOError, OSError):
                continue

        # Fall back to default font
        return ImageFont.load_default()

    def _get_line_color(self, line: TerminalLine) -> Tuple[int, int, int]:
        """Get the color for a line based on its type."""
        color_map = {
            "prompt": self.style.prompt,
            "command": self.style.command,
            "output": self.style.output,
            "error": self.style.error,
            "success": self.style.success,
            "comment": self.style.comment,
        }
        return color_map.get(line.line_type, self.style.text)

    def _calculate_dimensions(self, lines: List[TerminalLine]) -> Tuple[int, int]:
        """Calculate image dimensions based on content."""
        # Calculate text width
        max_width = 0
        for line in lines:
            # Use getbbox for text width calculation (Pillow 9.2+)
            try:
                bbox = self._font.getbbox(line.text)
                text_width = bbox[2] - bbox[0] if bbox else 0
            except AttributeError:
                # Fallback for older Pillow versions
                text_width = self._font.getsize(line.text)[0]
            max_width = max(max_width, text_width)

        # Add padding and enforce minimum width
        width = max(self.style.min_width, max_width + (self.style.padding * 2))

        # Calculate height
        content_height = len(lines) * self.style.line_height
        title_bar = self.style.title_bar_height if self.style.show_title_bar else 0
        height = content_height + (self.style.padding * 2) + title_bar

        return width, height

    def _draw_title_bar(self, draw: ImageDraw.Draw, width: int):
        """Draw the macOS-style title bar."""
        if not self.style.show_title_bar:
            return

        # Draw title bar background
        draw.rectangle(
            [0, 0, width, self.style.title_bar_height],
            fill=self.style.title_bar_color
        )

        # Draw traffic light buttons
        button_y = self.style.title_bar_height // 2
        button_radius = 6
        button_start_x = 12
        button_spacing = 20

        for i, color in enumerate(self.style.button_colors):
            x = button_start_x + (i * button_spacing)
            draw.ellipse(
                [x - button_radius, button_y - button_radius,
                 x + button_radius, button_y + button_radius],
                fill=color
            )

    def generate(
        self,
        lines: List[TerminalLine],
        title: Optional[str] = None
    ) -> Any:
        """Generate a terminal screenshot image.

        Args:
            lines: List of TerminalLine objects
            title: Optional window title

        Returns:
            PIL Image object
        """
        width, height = self._calculate_dimensions(lines)

        # Create image
        image = Image.new("RGB", (width, height), self.style.background)
        draw = ImageDraw.Draw(image)

        # Draw title bar
        self._draw_title_bar(draw, width)

        # Calculate starting Y position
        y_offset = self.style.title_bar_height if self.style.show_title_bar else 0
        y = y_offset + self.style.padding

        # Draw each line
        for line in lines:
            color = self._get_line_color(line)

            # Handle prompt lines specially (color the $ differently)
            if line.line_type == "prompt" and line.text.startswith("$"):
                # Draw prompt character in prompt color
                draw.text(
                    (self.style.padding, y),
                    "$",
                    font=self._font,
                    fill=self.style.prompt
                )
                # Draw rest of command in command color
                try:
                    prompt_width = self._font.getbbox("$ ")[2]
                except AttributeError:
                    prompt_width = self._font.getsize("$ ")[0]

                draw.text(
                    (self.style.padding + prompt_width, y),
                    line.text[2:],  # Skip "$ "
                    font=self._font,
                    fill=self.style.command
                )
            else:
                draw.text(
                    (self.style.padding, y),
                    line.text,
                    font=self._font,
                    fill=color
                )

            y += self.style.line_height

        return image

    def generate_simple(
        self,
        command: str,
        output: Union[str, List[str]],
        prompt_char: str = "$"
    ) -> Any:
        """Generate a simple command/output terminal image.

        Args:
            command: The command to show
            output: Output lines (string or list of strings)
            prompt_char: Prompt character (default: $)

        Returns:
            PIL Image object
        """
        lines = [TerminalLine.prompt(command, prompt_char)]

        if isinstance(output, str):
            output = output.split("\n")

        for line in output:
            lines.append(TerminalLine.output(line))

        return self.generate(lines)

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


def generate_terminal_image(
    command: str,
    output: Union[str, List[str]],
    style: Optional[TerminalStyle] = None
) -> bytes:
    """Convenience function to generate a terminal image.

    Args:
        command: Command to display
        output: Command output (string or list of strings)
        style: Optional custom styling

    Returns:
        PNG image as bytes
    """
    generator = TerminalImageGenerator(style)
    image = generator.generate_simple(command, output)
    return generator.to_bytes(image)
