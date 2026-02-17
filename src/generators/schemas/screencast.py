"""Pydantic schema for screencast simulation script generation.

Defines the structure for generating executable Python scripts that simulate
terminal screencasts with typing effects, narration cue cards, and visual elements.
"""

from pydantic import BaseModel, Field
from typing import List, Literal, Optional


class ScreencastCommand(BaseModel):
    """A single terminal command with its output."""

    command: str = Field(description="The command to type (e.g., 'python --version')")
    output: List[str] = Field(
        default_factory=list,
        description="Lines of output to display after the command"
    )
    typing_speed: Literal["slow", "normal", "fast"] = Field(
        default="normal",
        description="Typing speed: slow (0.08-0.15s), normal (0.03-0.08s), fast (0.01-0.03s)"
    )
    pause_after: float = Field(
        default=1.0,
        description="Seconds to pause after showing output"
    )


class NarrationCue(BaseModel):
    """A narration cue card shown between screens."""

    title: str = Field(description="Heading for the cue card")
    text: str = Field(description="Main narration text to display")
    duration: float = Field(
        default=5.0,
        description="Seconds to display before auto-advancing (0 = wait for keypress)"
    )


class ScreencastScreen(BaseModel):
    """A single screen in the screencast simulation."""

    screen_number: int = Field(description="Sequential screen number (1, 2, 3...)")
    title: str = Field(description="Screen title for reference")
    narration_cue: Optional[NarrationCue] = Field(
        default=None,
        description="Optional cue card to show before terminal commands"
    )
    prompt: str = Field(
        default="$ ",
        description="Terminal prompt to display (e.g., '$ ', '>>> ', 'user@host:~$ ')"
    )
    commands: List[ScreencastCommand] = Field(
        description="Commands to execute on this screen"
    )
    clear_screen: bool = Field(
        default=True,
        description="Whether to clear terminal before this screen"
    )


class ProgressBarDemo(BaseModel):
    """Configuration for a progress bar demonstration."""

    label: str = Field(description="Label text (e.g., 'Processing files')")
    steps: int = Field(default=20, description="Number of steps in the progress bar")
    step_delay: float = Field(default=0.1, description="Delay between steps in seconds")
    color: Literal["green", "blue", "yellow", "red", "cyan", "white"] = Field(
        default="green",
        description="Progress bar color"
    )


class ScreencastSchema(BaseModel):
    """Complete screencast simulation script structure.

    This schema defines an executable Python script that, when run in a terminal,
    simulates typing commands, displays output, shows narration cue cards, and
    creates professional-looking terminal recordings.
    """

    title: str = Field(description="Screencast title")
    description: str = Field(description="Brief description of what this screencast demonstrates")
    learning_objective: str = Field(description="The learning objective this screencast addresses")

    # Script configuration
    default_typing_speed: Literal["slow", "normal", "fast"] = Field(
        default="normal",
        description="Default typing speed for all commands"
    )
    show_cursor: bool = Field(
        default=True,
        description="Whether to show a blinking cursor effect"
    )

    # Opening cue card
    intro_cue: NarrationCue = Field(
        description="Opening narration cue card with title and context"
    )

    # Main content screens
    screens: List[ScreencastScreen] = Field(
        description="Sequence of screens in the screencast"
    )

    # Optional progress bar demo
    progress_demo: Optional[ProgressBarDemo] = Field(
        default=None,
        description="Optional progress bar demonstration"
    )

    # Closing cue card
    outro_cue: NarrationCue = Field(
        description="Closing narration cue card with summary"
    )

    # Session state variables (for continuity between screens)
    state_variables: List[str] = Field(
        default_factory=list,
        description="Variable names to track across screens (e.g., 'created_file', 'config_value')"
    )
