"""RubricGenerator for creating assessment rubrics with 3-level scoring criteria.

Generates grading rubrics using the Below/Meets/Exceeds Expectations model for
clear and fair assessment of student work.
"""

from typing import Tuple
from src.generators.base_generator import BaseGenerator
from src.generators.schemas.rubric import RubricSchema
from src.utils.content_metadata import ContentMetadata


class RubricGenerator(BaseGenerator[RubricSchema]):
    """Generator for assessment rubrics with 3-level scoring criteria.

    Produces rubrics with Below/Meets/Exceeds Expectations levels for each criterion.
    Each criterion includes descriptive text for all three performance levels and
    a weight percentage. Weights should sum to 100% for valid rubrics.

    Example usage:
        generator = RubricGenerator()
        rubric, metadata = generator.generate(
            schema=RubricSchema,
            learning_objective="Students will analyze datasets using Python",
            activity_title="Data Analysis Assignment",
            activity_type="project",
            num_criteria=4,
            total_points=100
        )
    """

    @property
    def system_prompt(self) -> str:
        """Return system instructions for rubric design.

        Returns:
            str: Expert rubric designer system prompt with 3-level scoring guidance
        """
        return """You are an expert assessment rubric designer specializing in creating clear, fair, and measurable grading criteria for educational activities.

Your rubrics use the 3-level analytic model:
- Below Expectations: Performance does not meet the standard
- Meets Expectations: Performance meets the standard adequately
- Exceeds Expectations: Performance surpasses the standard with excellence

RUBRIC DESIGN PRINCIPLES:
1. Each criterion must be observable and measurable (avoid vague language like "good" or "adequate")
2. Use descriptive language that clearly differentiates between performance levels
3. Focus on specific behaviors, features, or qualities that can be objectively assessed
4. Ensure criteria are appropriate for the activity type and learning objective
5. Distribute weights to reflect the relative importance of each criterion
6. All criterion weights should sum to 100%

PERFORMANCE LEVEL GUIDELINES:
- Below Expectations: Describes incomplete, incorrect, or insufficient work
- Meets Expectations: Describes competent work that fulfills requirements
- Exceeds Expectations: Describes exceptional work showing depth, sophistication, or innovation

Create rubrics that are transparent, actionable, and aligned with learning objectives."""

    def build_user_prompt(
        self,
        learning_objective: str,
        activity_title: str,
        activity_type: str,
        num_criteria: int = 4,
        total_points: int = 100,
        audience_level: str = "intermediate",
        language: str = "English",
        standards_rules: str = ""
    ) -> str:
        """Build user prompt for rubric generation.

        Args:
            learning_objective: The learning objective this rubric evaluates
            activity_title: Title of the activity being assessed
            activity_type: Type of activity (e.g., "assignment", "project", "lab")
            num_criteria: Number of scoring criteria to generate (default: 4)
            total_points: Maximum points for the rubric (default: 100)
            language: Language for content generation (default: English)
            standards_rules: Pre-built standards rules from standards_loader (optional)

        Returns:
            str: Formatted user prompt for Claude API
        """
        lang_instruction = ""
        if language.lower() != "english":
            lang_instruction = f"**IMPORTANT: Generate ALL content in {language}.**\n\n"

        standards_section = ""
        if standards_rules:
            standards_section = f"{standards_rules}\n\n"

        return f"""{lang_instruction}{standards_section}CONTEXT:
Activity: {activity_title}
Activity Type: {activity_type}
Learning Objective: {learning_objective}
Total Points: {total_points}

TASK:
Create a {num_criteria}-criterion rubric with {total_points} total points for evaluating this activity.

Each criterion should:
1. Have a clear name and description
2. Include Below Expectations, Meets Expectations, and Exceeds Expectations descriptions
3. Have a weight_percentage (all weights must sum to 100%)
4. Be directly relevant to the learning objective and activity type

The rubric should enable fair, consistent grading while providing clear performance expectations to students."""

    def extract_metadata(self, content: RubricSchema) -> dict:
        """Calculate metadata from generated rubric.

        Metadata includes:
        - word_count: Total words across all criterion text fields
        - total_criteria: Number of criteria in the rubric
        - total_points: Maximum points from the rubric schema
        - weights_valid: Whether criterion weights sum to 100%

        Args:
            content: The validated RubricSchema instance

        Returns:
            dict: Metadata dictionary with computed values
        """
        # Count words across all criterion fields
        total_words = 0
        for criterion in content.criteria:
            total_words += ContentMetadata.count_words(criterion.name)
            total_words += ContentMetadata.count_words(criterion.description)
            total_words += ContentMetadata.count_words(criterion.below_expectations)
            total_words += ContentMetadata.count_words(criterion.meets_expectations)
            total_words += ContentMetadata.count_words(criterion.exceeds_expectations)

        # Calculate total weight to validate
        total_weight = sum(c.weight_percentage for c in content.criteria)

        return {
            "word_count": total_words,
            "total_criteria": len(content.criteria),
            "total_points": content.total_points,
            "weights_valid": total_weight == 100
        }

    def generate_rubric(
        self,
        learning_objective: str,
        activity_title: str,
        activity_type: str,
        num_criteria: int = 4,
        total_points: int = 100
    ) -> Tuple[RubricSchema, dict]:
        """Convenience method for generating rubrics.

        Args:
            learning_objective: The learning objective this rubric evaluates
            activity_title: Title of the activity being assessed
            activity_type: Type of activity (e.g., "assignment", "project", "lab")
            num_criteria: Number of scoring criteria to generate (default: 4)
            total_points: Maximum points for the rubric (default: 100)

        Returns:
            Tuple[RubricSchema, dict]: (validated rubric, metadata dict)
        """
        return self.generate(
            schema=RubricSchema,
            learning_objective=learning_objective,
            activity_title=activity_title,
            activity_type=activity_type,
            num_criteria=num_criteria,
            total_points=total_points
        )
