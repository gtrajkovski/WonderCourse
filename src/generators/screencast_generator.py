"""Screencast simulation script generator.

Generates executable Python scripts that simulate terminal screencasts with
typing effects, narration cue cards, and visual elements. The output is
runnable Python code that creates professional terminal recordings.
"""

from anthropic import Anthropic
from src.generators.base_generator import BaseGenerator
from src.generators.schemas.screencast import ScreencastSchema
from src.utils.content_metadata import ContentMetadata


class ScreencastGenerator(BaseGenerator[ScreencastSchema]):
    """Generator for screencast simulation Python scripts.

    Extends BaseGenerator to produce ScreencastSchema instances that define
    terminal screencast simulations. The schema is then converted to
    executable Python code.
    """

    @property
    def system_prompt(self) -> str:
        """Return system instructions for screencast script generation."""
        return """You are an expert instructional designer creating terminal screencast simulations.

Your task is to design a screencast simulation that will be converted to an executable Python script.
When the script runs in a terminal, it will:
- Simulate realistic typing of commands
- Display command output
- Show narration cue cards between screens
- Create a professional recording-ready experience

**Design Guidelines:**

1. **Screen Structure**: Break the demonstration into logical screens, each focusing on one concept or step.

2. **Narration Cues**: Use cue cards to:
   - Introduce each section before showing commands
   - Explain what's about to happen
   - Give viewers time to absorb information

3. **Commands**: Design realistic terminal commands that:
   - Build progressively in complexity
   - Show meaningful output
   - Demonstrate practical skills

4. **Pacing**:
   - Use "slow" typing for important commands learners should study
   - Use "normal" for regular commands
   - Use "fast" for repeated or obvious commands
   - Add pauses after significant output

5. **Visual Elements**: Include progress bars or colored output when demonstrating:
   - Installation processes
   - Build/compile operations
   - Data processing tasks

**Content Flow:**
- Open with intro cue (what we'll learn)
- Progress through screens with commands
- Each screen should have a clear learning point
- Close with outro cue (summary and next steps)

**Quality Criteria:**
- Commands must be syntactically correct
- Output should be realistic for the commands
- Pacing should allow comfortable viewing
- Narration should be clear and instructive"""

    def build_user_prompt(
        self,
        learning_objective: str,
        topic: str,
        audience_level: str = "intermediate",
        duration_minutes: int = 5,
        language: str = "English",
        programming_language: str = "python",
        environment: str = "terminal",
        standards_rules: str = ""
    ) -> str:
        """Build user prompt for screencast generation.

        Args:
            learning_objective: What learners will be able to do
            topic: The subject matter being demonstrated
            audience_level: Target audience (beginner/intermediate/advanced)
            duration_minutes: Target screencast duration
            language: Language for narration text
            programming_language: Primary language being demonstrated
            environment: Terminal environment (terminal, python repl, etc.)
            standards_rules: Pre-built standards rules from standards_loader

        Returns:
            str: Formatted user prompt for Claude API
        """
        lang_instruction = ""
        if language.lower() != "english":
            lang_instruction = f"\n**IMPORTANT: Generate ALL narration text in {language}.**\n"

        standards_section = ""
        if standards_rules:
            standards_section = f"\n{standards_rules}\n"

        return f"""{lang_instruction}{standards_section}Design a terminal screencast simulation for an online course.

**CONTEXT:**
- Topic: {topic}
- Programming Language: {programming_language}
- Environment: {environment}
- Audience Level: {audience_level}
- Target Duration: {duration_minutes} minutes

**LEARNING OBJECTIVE:**
{learning_objective}

**TASK:**
Create a screencast simulation that:
1. Opens with an intro cue card explaining what we'll learn
2. Demonstrates concepts through terminal commands with realistic output
3. Uses narration cue cards to explain each section
4. Includes appropriate pauses for viewers to follow along
5. Closes with an outro cue summarizing what was learned

**Requirements:**
- Design 3-6 screens depending on complexity
- Each screen should have 1-4 commands
- Use appropriate typing speeds (slow for key commands, normal otherwise)
- Include realistic command output
- Narration cues should be concise but informative
- Match the {audience_level} level in language and depth

**Terminal Prompt:**
Use a prompt appropriate for the environment:
- Python REPL: ">>> "
- Bash/Terminal: "$ "
- User-specific: "user@host:~$ "

Remember: This will become a runnable Python script that simulates the terminal session."""

    def extract_metadata(self, content: ScreencastSchema) -> dict:
        """Calculate metadata from generated screencast schema.

        Args:
            content: The validated ScreencastSchema instance

        Returns:
            dict: Metadata with screen count, command count, estimated duration
        """
        # Count screens and commands
        num_screens = len(content.screens)
        num_commands = sum(len(screen.commands) for screen in content.screens)

        # Estimate duration based on:
        # - Typing time (~50 chars/sec average)
        # - Pause times
        # - Cue card display times
        total_typing_chars = 0
        total_pause_time = 0.0

        # Intro cue
        total_pause_time += content.intro_cue.duration

        for screen in content.screens:
            # Narration cue time
            if screen.narration_cue:
                total_pause_time += screen.narration_cue.duration

            for cmd in screen.commands:
                # Typing time (varies by speed)
                total_typing_chars += len(cmd.command)
                # Pause after command
                total_pause_time += cmd.pause_after

        # Outro cue
        total_pause_time += content.outro_cue.duration

        # Calculate typing duration (average 50 chars/sec with variations)
        typing_duration = total_typing_chars / 30  # Conservative estimate

        estimated_duration = (typing_duration + total_pause_time) / 60

        # Count narration words for reference
        narration_words = 0
        narration_words += ContentMetadata.count_words(content.intro_cue.text)
        narration_words += ContentMetadata.count_words(content.outro_cue.text)
        for screen in content.screens:
            if screen.narration_cue:
                narration_words += ContentMetadata.count_words(screen.narration_cue.text)

        return {
            "content_type": "screencast",
            "num_screens": num_screens,
            "num_commands": num_commands,
            "estimated_duration_minutes": round(estimated_duration, 1),
            "total_typing_chars": total_typing_chars,
            "narration_word_count": narration_words,
            "has_progress_demo": content.progress_demo is not None,
        }

    def schema_to_python(self, schema: ScreencastSchema) -> str:
        """Convert ScreencastSchema to executable Python code.

        Args:
            schema: The screencast schema to convert

        Returns:
            str: Complete executable Python script
        """
        # Build the Python script
        lines = []

        # Header and imports
        lines.append('"""')
        lines.append(f'{schema.title}')
        lines.append('')
        lines.append(f'{schema.description}')
        lines.append('')
        lines.append(f'Learning Objective: {schema.learning_objective}')
        lines.append('')
        lines.append('Generated by Course Builder Studio')
        lines.append('Run this script in a terminal and record your screen.')
        lines.append('"""')
        lines.append('')
        lines.append('import sys')
        lines.append('import os')
        lines.append('import time')
        lines.append('import random')
        lines.append('')
        lines.append('')
        lines.append('# === Configuration ===')
        lines.append('')
        lines.append('TYPING_SPEEDS = {')
        lines.append('    "slow": (0.08, 0.15),')
        lines.append('    "normal": (0.03, 0.08),')
        lines.append('    "fast": (0.01, 0.03),')
        lines.append('}')
        lines.append('')
        lines.append(f'DEFAULT_SPEED = "{schema.default_typing_speed}"')
        lines.append(f'SHOW_CURSOR = {schema.show_cursor}')
        lines.append('')
        lines.append('# ANSI color codes')
        lines.append('COLORS = {')
        lines.append('    "green": "\\033[32m",')
        lines.append('    "blue": "\\033[34m",')
        lines.append('    "yellow": "\\033[33m",')
        lines.append('    "red": "\\033[31m",')
        lines.append('    "cyan": "\\033[36m",')
        lines.append('    "white": "\\033[37m",')
        lines.append('    "bold": "\\033[1m",')
        lines.append('    "reset": "\\033[0m",')
        lines.append('}')
        lines.append('')
        lines.append('')
        lines.append('# === Utility Functions ===')
        lines.append('')
        lines.append('def clear_screen():')
        lines.append('    """Clear terminal screen (cross-platform)."""')
        lines.append('    os.system("cls" if sys.platform == "win32" else "clear")')
        lines.append('')
        lines.append('')
        lines.append('def type_text(text, speed="normal"):')
        lines.append('    """Simulate typing with realistic delays."""')
        lines.append('    min_delay, max_delay = TYPING_SPEEDS.get(speed, TYPING_SPEEDS["normal"])')
        lines.append('    for char in text:')
        lines.append('        print(char, end="", flush=True)')
        lines.append('        time.sleep(random.uniform(min_delay, max_delay))')
        lines.append('    print()  # Newline after typing')
        lines.append('')
        lines.append('')
        lines.append('def show_output(lines, delay=0.05):')
        lines.append('    """Display command output line by line."""')
        lines.append('    for line in lines:')
        lines.append('        print(line)')
        lines.append('        time.sleep(delay)')
        lines.append('')
        lines.append('')
        lines.append('def show_cue_card(title, text, duration=5.0):')
        lines.append('    """Display a narration cue card."""')
        lines.append('    clear_screen()')
        lines.append('    width = 60')
        lines.append('    print()')
        lines.append('    print("+" + "-" * (width - 2) + "+")')
        lines.append('    print("|" + " " * (width - 2) + "|")')
        lines.append('    # Center the title')
        lines.append('    title_line = title.center(width - 4)')
        lines.append('    print("|  " + COLORS["bold"] + title_line + COLORS["reset"] + "  |")')
        lines.append('    print("|" + " " * (width - 2) + "|")')
        lines.append('    # Word wrap the text')
        lines.append('    words = text.split()')
        lines.append('    line = ""')
        lines.append('    for word in words:')
        lines.append('        if len(line) + len(word) + 1 <= width - 6:')
        lines.append('            line = line + " " + word if line else word')
        lines.append('        else:')
        lines.append('            print("|  " + line.ljust(width - 6) + "  |")')
        lines.append('            line = word')
        lines.append('    if line:')
        lines.append('        print("|  " + line.ljust(width - 6) + "  |")')
        lines.append('    print("|" + " " * (width - 2) + "|")')
        lines.append('    print("+" + "-" * (width - 2) + "+")')
        lines.append('    print()')
        lines.append('    if duration > 0:')
        lines.append('        print(f"[Continuing in {duration:.0f} seconds...]")')
        lines.append('        time.sleep(duration)')
        lines.append('    else:')
        lines.append('        input("[Press Enter to continue...]")')
        lines.append('')
        lines.append('')

        # Progress bar function if needed
        if schema.progress_demo:
            lines.append('def show_progress_bar(label, steps=20, delay=0.1, color="green"):')
            lines.append('    """Display an animated progress bar."""')
            lines.append('    color_code = COLORS.get(color, COLORS["green"])')
            lines.append('    for i in range(steps + 1):')
            lines.append('        percent = int(100 * i / steps)')
            lines.append('        filled = "█" * i')
            lines.append('        empty = "░" * (steps - i)')
            lines.append('        print(f"\\r{label}: {color_code}[{filled}{empty}]{COLORS[\'reset\']} {percent}%", end="", flush=True)')
            lines.append('        time.sleep(delay)')
            lines.append('    print()  # Newline after completion')
            lines.append('')
            lines.append('')

        # Main function
        lines.append('def run_screencast():')
        lines.append(f'    """Run the screencast: {schema.title}"""')
        lines.append('')

        # Intro cue
        lines.append('    # === Intro ===')
        lines.append(f'    show_cue_card(')
        lines.append(f'        {repr(schema.intro_cue.title)},')
        lines.append(f'        {repr(schema.intro_cue.text)},')
        lines.append(f'        duration={schema.intro_cue.duration}')
        lines.append('    )')
        lines.append('')

        # Each screen
        for screen in schema.screens:
            lines.append(f'    # === Screen {screen.screen_number}: {screen.title} ===')

            # Narration cue if present
            if screen.narration_cue:
                lines.append(f'    show_cue_card(')
                lines.append(f'        {repr(screen.narration_cue.title)},')
                lines.append(f'        {repr(screen.narration_cue.text)},')
                lines.append(f'        duration={screen.narration_cue.duration}')
                lines.append('    )')

            # Clear screen if needed
            if screen.clear_screen:
                lines.append('    clear_screen()')

            lines.append('')

            # Commands
            for cmd in screen.commands:
                # Show prompt and type command
                lines.append(f'    print({repr(screen.prompt)}, end="")')
                lines.append(f'    type_text({repr(cmd.command)}, speed="{cmd.typing_speed}")')

                # Show output if any
                if cmd.output:
                    output_list = repr(cmd.output)
                    lines.append(f'    show_output({output_list})')

                # Pause
                if cmd.pause_after > 0:
                    lines.append(f'    time.sleep({cmd.pause_after})')
                lines.append('')

        # Progress demo if present
        if schema.progress_demo:
            lines.append('    # === Progress Bar Demo ===')
            lines.append(f'    show_progress_bar(')
            lines.append(f'        {repr(schema.progress_demo.label)},')
            lines.append(f'        steps={schema.progress_demo.steps},')
            lines.append(f'        delay={schema.progress_demo.step_delay},')
            lines.append(f'        color="{schema.progress_demo.color}"')
            lines.append('    )')
            lines.append('')

        # Outro cue
        lines.append('    # === Outro ===')
        lines.append(f'    show_cue_card(')
        lines.append(f'        {repr(schema.outro_cue.title)},')
        lines.append(f'        {repr(schema.outro_cue.text)},')
        lines.append(f'        duration={schema.outro_cue.duration}')
        lines.append('    )')
        lines.append('')
        lines.append('    print("\\n[Screencast complete]")')
        lines.append('')
        lines.append('')
        lines.append('if __name__ == "__main__":')
        lines.append('    try:')
        lines.append('        run_screencast()')
        lines.append('    except KeyboardInterrupt:')
        lines.append('        print("\\n\\n[Screencast interrupted]")')
        lines.append('        sys.exit(0)')
        lines.append('')

        return '\n'.join(lines)

    def generate_screencast(
        self,
        learning_objective: str,
        topic: str,
        audience_level: str = "intermediate",
        duration_minutes: int = 5,
        programming_language: str = "python",
        environment: str = "terminal"
    ) -> tuple[str, dict]:
        """Generate a complete screencast simulation script.

        This is the main entry point. It generates the schema and converts
        it to executable Python code.

        Args:
            learning_objective: What learners will be able to do
            topic: The subject matter being demonstrated
            audience_level: Target audience level
            duration_minutes: Target screencast duration
            programming_language: Primary language being demonstrated
            environment: Terminal environment

        Returns:
            tuple: (python_script_code, metadata_dict)
        """
        # Generate the structured schema
        schema, metadata = self.generate(
            schema=ScreencastSchema,
            learning_objective=learning_objective,
            topic=topic,
            audience_level=audience_level,
            duration_minutes=duration_minutes,
            programming_language=programming_language,
            environment=environment
        )

        # Convert schema to executable Python code
        python_code = self.schema_to_python(schema)

        # Add code-specific metadata
        metadata["code_lines"] = len(python_code.split('\n'))
        metadata["code_chars"] = len(python_code)

        return python_code, metadata
