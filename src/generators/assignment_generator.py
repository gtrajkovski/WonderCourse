"""AssignmentGenerator for creating assignment specifications with deliverables and grading criteria."""

from typing import Tuple
from src.generators.base_generator import BaseGenerator
from src.generators.schemas.assignment import AssignmentSchema
from src.utils.content_metadata import ContentMetadata


class AssignmentGenerator(BaseGenerator[AssignmentSchema]):
    """Generator for creating assignment specifications with deliverables, grading criteria, and submission checklists.

    Produces standalone assignment specs with:
    - Clear deliverables with point values
    - Actionable grading criteria
    - Submission checklist to reduce incomplete submissions
    - Realistic time estimates
    - Alignment with learning objectives
    """

    @property
    def system_prompt(self) -> str:
        """Return system prompt for assignment generation with clear expectations."""
        return """You are an expert assessment designer specializing in higher education assignments.

Your assignments follow these best practices:

**Deliverables:**
- Each deliverable is a distinct artifact students must submit
- Point values reflect relative importance and effort
- Descriptions are specific and actionable (not vague)
- Total points across deliverables sum to assignment total_points

**Grading Criteria:**
- Criteria are observable and measurable
- Focus on quality dimensions (accuracy, completeness, clarity, creativity, etc.)
- Avoid subjective terms without definition
- Criteria apply across all deliverables (holistic evaluation)

**Submission Checklist:**
- Required items prevent incomplete submissions
- Optional items guide students toward excellence
- Items are specific and verifiable (not ambiguous)
- Checklist includes formatting, file naming, and content requirements

**Time Estimates:**
- Realistic estimates help students plan their work
- Account for research, drafting, revision, and formatting time
- Align with course workload expectations (1-20 hours)

**Learning Alignment:**
- Every deliverable connects to the learning objective
- Assignment requires synthesis and application (not just recall)
- Complexity matches student level (beginner/intermediate/advanced)"""

    def build_user_prompt(
        self,
        learning_objective: str,
        topic: str,
        total_points: int = 100,
        estimated_hours: int = 5,
        difficulty: str = "intermediate",
        audience_level: str = "intermediate",
        language: str = "English",
        standards_rules: str = "",
        feedback: str = "",
        target_word_count: int = None
    ) -> str:
        """Build user prompt for assignment generation.

        Args:
            learning_objective: The learning objective this assignment addresses
            topic: Subject matter for the assignment
            total_points: Maximum points for the assignment (default 100)
            estimated_hours: Estimated completion time in hours (default 5)
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
Maximum Points: {total_points}
Estimated Time: {estimated_hours} hours

**TASK:**
Generate a complete assignment specification that assesses the learning objective above.

**REQUIREMENTS:**
- Create {total_points}-point assignment with 1-5 distinct deliverables
- Each deliverable must have a point value (points must sum to {total_points})
- Include 3-6 grading criteria that define quality expectations
- Create submission checklist with 3-10 items (mix of required and optional)
- Set estimated_hours to {estimated_hours}
- Ensure assignment requires synthesis and application at '{difficulty}' level

**DELIVERABLE GUIDANCE:**
- Deliverables should be varied (written work, artifacts, demonstrations, etc.)
- Point distribution should reflect effort and importance
- Descriptions should be specific enough for students to understand expectations

**GRADING CRITERIA GUIDANCE:**
- Criteria should cover different quality dimensions
- Avoid redundancy (each criterion assesses something unique)
- Use measurable language when possible

**CHECKLIST GUIDANCE:**
- Required items prevent common submission errors
- Optional items guide students toward excellence
- Include formatting, naming conventions, and content requirements"""

    def extract_metadata(self, content: AssignmentSchema) -> dict:
        """Calculate metadata from generated assignment.

        Args:
            content: The validated AssignmentSchema instance

        Returns:
            dict: Metadata with word_count, duration, total_points, num_deliverables, content_type
        """
        # Count words in all text fields
        word_count = 0

        # Count words in title and overview
        word_count += ContentMetadata.count_words(content.title)
        word_count += ContentMetadata.count_words(content.overview)

        # Count words in deliverables
        for deliverable in content.deliverables:
            word_count += ContentMetadata.count_words(deliverable.item)

        # Count words in grading criteria
        for criterion in content.grading_criteria:
            word_count += ContentMetadata.count_words(criterion)

        # Count words in submission checklist
        for checklist_item in content.submission_checklist:
            word_count += ContentMetadata.count_words(checklist_item.item)

        # Count words in learning objective
        word_count += ContentMetadata.count_words(content.learning_objective)

        # Calculate duration from estimated_hours (convert to minutes)
        duration = content.estimated_hours * 60

        return {
            "word_count": word_count,
            "estimated_duration_minutes": duration,
            "total_points": content.total_points,
            "num_deliverables": len(content.deliverables),
            "content_type": "assignment"
        }

    def generate_assignment(
        self,
        learning_objective: str,
        topic: str,
        total_points: int = 100,
        estimated_hours: int = 5,
        difficulty: str = "intermediate"
    ) -> Tuple[AssignmentSchema, dict]:
        """Convenience method for generating an assignment.

        Args:
            learning_objective: The learning objective this assignment addresses
            topic: Subject matter for the assignment
            total_points: Maximum points for the assignment (default 100)
            estimated_hours: Estimated completion time in hours (default 5)
            difficulty: Difficulty level (default "intermediate")

        Returns:
            Tuple[AssignmentSchema, dict]: (assignment, metadata)
        """
        return self.generate(
            schema=AssignmentSchema,
            learning_objective=learning_objective,
            topic=topic,
            total_points=total_points,
            estimated_hours=estimated_hours,
            difficulty=difficulty
        )
