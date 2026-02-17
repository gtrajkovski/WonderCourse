"""LabGenerator for creating hands-on programming labs with setup instructions."""

from typing import Tuple
from src.generators.base_generator import BaseGenerator
from src.generators.schemas.lab import LabSchema, SetupStep
from src.utils.content_metadata import ContentMetadata


class LabGenerator(BaseGenerator[LabSchema]):
    """Generator for creating ungraded hands-on programming labs.

    Produces practice labs with:
    - Clear setup instructions with numbered steps
    - Expected results for each setup step (verification)
    - Progressive exercises from simple to complex
    - Time estimates for planning work sessions
    - Labs are ungraded practice activities (no points or rubric)
    """

    @property
    def system_prompt(self) -> str:
        """Return system prompt for lab generation with setup guidelines."""
        return """You are an expert lab designer for technical education.

Your labs follow these best practices:

**Lab Philosophy:**
- Labs are UNGRADED practice activities focused on skill building
- Goal is exploration and hands-on learning, not assessment
- Students should feel safe to experiment and make mistakes
- Provide clear success criteria so students know they're on track

**Setup Instructions (CRITICAL):**
- Each step must be numbered sequentially starting from 1
- Include clear, actionable instructions for each step
- Provide expected results so students can verify successful setup
- Setup should be achievable in 5-15 minutes
- Test all setup steps to ensure they work on common environments

**Lab Exercises:**
- Structure exercises from simple to complex (scaffolding)
- Each exercise should build on previous ones
- Focus on active practice, not passive reading
- Exercises should take 30-90 minutes total
- Include enough detail that students know what success looks like

**Prerequisites and Environment:**
- Clearly state what students need before starting
- List required tools, software versions, and prior knowledge
- Reduce friction by anticipating common setup issues

**Time Estimates:**
- Provide realistic time estimates (15-120 minutes total)
- Help students plan work sessions effectively
- Account for different skill levels"""

    def build_user_prompt(
        self,
        learning_objective: str,
        topic: str,
        difficulty: str = "intermediate",
        estimated_minutes: int = 45,
        audience_level: str = "intermediate",
        language: str = "English",
        standards_rules: str = "",
        feedback: str = "",
        target_word_count: int = None
    ) -> str:
        """Build user prompt for lab generation.

        Args:
            learning_objective: The skills students will practice
            topic: Subject matter for the lab
            difficulty: Difficulty level (beginner, intermediate, advanced)
            estimated_minutes: Total estimated completion time (default 45)
            language: Language for content generation (default: English)
            standards_rules: Pre-built standards rules from standards_loader (optional)
            feedback: User feedback to incorporate in regeneration (optional)
            target_word_count: Specific word count target for regeneration (optional)

        Returns:
            str: Formatted user prompt
        """
        lang_instruction = ""
        if language.lower() != "english":
            lang_instruction = f"**IMPORTANT: Generate ALL content in {language}.**\n\n"

        standards_section = ""
        if standards_rules:
            standards_section = f"{standards_rules}\n\n"

        # Build length constraint section if specified
        length_section = ""
        if target_word_count:
            length_section = f"""
**LENGTH REQUIREMENT (STRICT):**
- Target word count: {target_word_count} words (stay within ±10%)

"""

        # Build feedback section if provided
        feedback_section = ""
        if feedback:
            feedback_section = f"""
**USER FEEDBACK TO ADDRESS:**
{feedback}

Please incorporate this feedback in the regenerated content.

"""

        return f"""{lang_instruction}{standards_section}{length_section}{feedback_section}**CONTEXT:**
Learning Objective: {learning_objective}
Topic: {topic}
Difficulty: {difficulty}
Estimated Time: {estimated_minutes} minutes

**TASK:**
Generate a hands-on programming lab that helps students practice the learning objective above.

**REQUIREMENTS:**
- Create 3-10 numbered setup steps with expected results for verification
- Design 3-8 progressive exercises that build on each other
- Lab is UNGRADED - focus on practice and exploration, not assessment
- Total time estimate: {estimated_minutes} minutes
- Include 2-3 learning objectives students will accomplish
- List 0-3 prerequisites (tools, prior knowledge)
- Provide clear overview of what students will build/accomplish

**LAB FOCUS:**
Create exercises that are hands-on and practical at the '{difficulty}' level. Students should actively build, code, or configure something, not just read documentation."""

    def extract_metadata(self, content: LabSchema) -> dict:
        """Calculate metadata from generated lab.

        Args:
            content: The validated LabSchema instance

        Returns:
            dict: Metadata with word_count, duration, setup/exercise counts, content_type
        """
        # Count words in all text fields
        word_count = 0

        # Count words in title and overview
        word_count += ContentMetadata.count_words(content.title)
        word_count += ContentMetadata.count_words(content.overview)

        # Count words in learning objectives
        for objective in content.learning_objectives:
            word_count += ContentMetadata.count_words(objective)

        # Count words in setup instructions
        for step in content.setup_instructions:
            word_count += ContentMetadata.count_words(step.instruction)
            word_count += ContentMetadata.count_words(step.expected_result)

        # Count words in exercises
        for exercise in content.lab_exercises:
            word_count += ContentMetadata.count_words(exercise)

        # Count words in prerequisites
        for prereq in content.prerequisites:
            word_count += ContentMetadata.count_words(prereq)

        # Duration comes from content.estimated_minutes (NOT calculated from word count)
        # Labs have fixed time estimates because they involve hands-on work
        duration = content.estimated_minutes

        return {
            "word_count": word_count,
            "estimated_duration_minutes": duration,
            "num_setup_steps": len(content.setup_instructions),
            "num_exercises": len(content.lab_exercises),
            "content_type": "lab"
        }

    def generate_lab(
        self,
        learning_objective: str,
        topic: str,
        difficulty: str = "intermediate",
        estimated_minutes: int = 45
    ) -> Tuple[LabSchema, dict]:
        """Convenience method for generating a lab.

        Args:
            learning_objective: The skills students will practice
            topic: Subject matter for the lab
            difficulty: Difficulty level (default "intermediate")
            estimated_minutes: Total estimated time (default 45)

        Returns:
            Tuple[LabSchema, dict]: (lab, metadata)
        """
        return self.generate(
            schema=LabSchema,
            learning_objective=learning_objective,
            topic=topic,
            difficulty=difficulty,
            estimated_minutes=estimated_minutes
        )
