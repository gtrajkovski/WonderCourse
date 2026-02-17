"""HOLGenerator for creating hands-on labs with scenario-based structure and skill-based rubrics."""

from typing import Tuple
from src.generators.base_generator import BaseGenerator
from src.generators.schemas.hol import HOLSchema, HOLPart, HOLRubricCriterion
from src.utils.content_metadata import ContentMetadata


class HOLGenerator(BaseGenerator[HOLSchema]):
    """Generator for creating hands-on lab activities with scaffolded exercises.

    Produces HOL activities with:
    - Real-world scenario framing
    - 3 scaffolded parts building from basic to advanced
    - Submission criteria for deliverables
    - Skill-based rubric with Advanced/Intermediate/Beginner scoring (5/4/2 points)
    """

    @property
    def system_prompt(self) -> str:
        """Return system prompt for HOL generation with skill-based rubric guidelines.

        Note: Rubric criteria count and levels are injected via standards_rules
        parameter from ContentStandardsProfile for flexibility (v1.2.0).
        """
        return """You are an expert instructional designer specializing in hands-on learning experiences.

Your hands-on labs (HOLs) follow these best practices:

**Scenario Design:**
- Create authentic, real-world scenarios that motivate learning
- Scenarios should be specific and relatable to professional contexts
- Frame the lab as solving a practical problem or building something useful

**3-Part Scaffolding Structure:**
- Part 1: Foundation - Basic setup and core concepts
- Part 2: Development - Building on fundamentals with more complexity
- Part 3: Integration - Advanced features and comprehensive implementation
- Each part should have clear instructions and realistic time estimates
- Total time typically 45-90 minutes for a complete lab

**Submission Criteria:**
- Specify exactly what students must submit (code files, documentation, screenshots)
- Include deliverable format and any required documentation
- Make expectations concrete and verifiable

**Skill-Based Rubric:**
- Use the performance levels specified in the standards rules (injected at generation time)
- Criteria count and point values come from the standards profile
- Each level should clearly describe observable performance characteristics
- Focus on skill progression, not just compliance with requirements
- Criteria should assess different aspects: implementation, accuracy, documentation

**Quality Guidelines:**
- Instructions should be clear and actionable
- Avoid vague language - be specific about what to do
- Balance guidance with opportunities for problem-solving
- Rubric should reward deeper understanding and best practices"""

    def build_user_prompt(
        self,
        learning_objective: str,
        topic: str,
        difficulty: str = "intermediate",
        audience_level: str = "intermediate",
        language: str = "English",
        standards_rules: str = "",
        feedback: str = "",
        target_word_count: int = None
    ) -> str:
        """Build user prompt for HOL generation.

        Args:
            learning_objective: The learning objective this HOL addresses
            topic: Subject matter for the hands-on lab
            difficulty: Difficulty level (beginner, intermediate, advanced)
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

**TASK:**
Generate a hands-on lab activity that provides scaffolded practice for the learning objective above.

**REQUIREMENTS:**

**Scenario:**
- Create a real-world scenario that frames the lab exercise
- Scenario should be specific and motivating

**3-Part Structure:**
- Part 1: Foundation (basic setup and core concepts)
- Part 2: Development (building complexity)
- Part 3: Integration (advanced features)
- Each part must have:
  * Clear title
  * Step-by-step instructions
  * Realistic time estimate (5-30 minutes per part)

**Submission Criteria:**
- Specify exactly what students must submit for evaluation
- Include file names, documentation requirements, any screenshots needed

**Skill-Based Rubric:**
- Create evaluation criteria as specified in the standards rules above
- Each criterion must have descriptions for ALL specified performance levels
- Use the exact point values from the standards rules
- Criteria should assess different aspects of the work:
  - Implementation Quality (code organization, best practices)
  - Technical Accuracy (correctness, proper techniques)
  - Testing and Documentation (completeness, clarity)

**CRITICAL:** Follow the rubric configuration in the standards rules. Use the EXACT performance level names and point values specified."""

    def extract_metadata(self, content: HOLSchema) -> dict:
        """Calculate metadata from generated HOL.

        Args:
            content: The validated HOLSchema instance

        Returns:
            dict: Metadata with word_count, duration, total_points, content_type
        """
        # Count words in all text fields
        word_count = 0

        # Count words in title and scenario
        word_count += ContentMetadata.count_words(content.title)
        word_count += ContentMetadata.count_words(content.scenario)

        # Count words in all parts
        for part in content.parts:
            word_count += ContentMetadata.count_words(part.title)
            word_count += ContentMetadata.count_words(part.instructions)

        # Count words in submission criteria
        word_count += ContentMetadata.count_words(content.submission_criteria)

        # Count words in rubric criteria
        for criterion in content.rubric:
            word_count += ContentMetadata.count_words(criterion.name)
            word_count += ContentMetadata.count_words(criterion.advanced)
            word_count += ContentMetadata.count_words(criterion.intermediate)
            word_count += ContentMetadata.count_words(criterion.beginner)

        # Calculate duration as sum of part estimated_minutes
        duration = sum(part.estimated_minutes for part in content.parts)

        # Calculate total points (3 criteria × 5 max points)
        total_points = len(content.rubric) * 5

        return {
            "word_count": word_count,
            "estimated_duration_minutes": duration,
            "total_points": total_points,
            "content_type": "hol"
        }

    def generate_hol(
        self,
        learning_objective: str,
        topic: str,
        difficulty: str = "intermediate"
    ) -> Tuple[HOLSchema, dict]:
        """Convenience method for generating a hands-on lab.

        Args:
            learning_objective: The learning objective this HOL addresses
            topic: Subject matter for the lab
            difficulty: Difficulty level (default "intermediate")

        Returns:
            Tuple[HOLSchema, dict]: (hol, metadata)
        """
        return self.generate(
            schema=HOLSchema,
            learning_objective=learning_objective,
            topic=topic,
            difficulty=difficulty
        )
