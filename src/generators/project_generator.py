"""ProjectMilestoneGenerator for creating scaffolded project milestones with A1/A2/A3 staging."""

from typing import Tuple
from src.generators.base_generator import BaseGenerator
from src.generators.schemas.project import ProjectMilestoneSchema
from src.utils.content_metadata import ContentMetadata


class ProjectMilestoneGenerator(BaseGenerator[ProjectMilestoneSchema]):
    """Generator for creating scaffolded project milestones with progressive deliverables.

    Produces project milestones with A1/A2/A3 staging:
    - A1: Foundation/proposal (planning, scope definition, initial setup)
    - A2: Core implementation (main deliverables, integration, testing)
    - A3: Advanced features/polish (refinement, documentation, presentation)

    Each milestone includes:
    - Clear deliverables with submission formats
    - Grading criteria aligned to milestone stage
    - Prerequisites that connect milestones
    - Realistic time estimates
    """

    @property
    def system_prompt(self) -> str:
        """Return system prompt for project milestone generation with scaffolding guidelines."""
        return """You are an expert in project-based learning design, specializing in scaffolded milestone structures.

Your project milestones follow these scaffolding principles:

**Progressive Milestone Structure:**
- **A1 (Foundation/Setup)**: Planning, proposal, initial architecture, environment setup
  - Focus: Scope definition, resource planning, initial design
  - Deliverables: Proposals, planning documents, setup verification
  - Goal: Ensure students have clear direction before implementation

- **A2 (Core Implementation)**: Main functionality, integration, core features
  - Focus: Building working system, implementing key features, testing
  - Deliverables: Working code, documentation, test results
  - Goal: Students deliver functional core product

- **A3 (Advanced/Polish)**: Advanced features, refinement, presentation
  - Focus: Enhancement, optimization, polish, reflection
  - Deliverables: Final product, presentation, reflective analysis
  - Goal: Professional-quality deliverable with thoughtful reflection

**Deliverable Design:**
- Each deliverable has clear NAME, DESCRIPTION, and required FORMAT
- Formats are specific (e.g., "PDF report", "GitHub repository", "5-minute video")
- Descriptions specify what to include and expectations
- 2-5 deliverables per milestone (more for A3, fewer for A1)

**Grading Criteria:**
- Aligned to milestone stage (A1=planning quality, A2=implementation, A3=polish)
- 3-6 concrete criteria per milestone
- Criteria are observable and assessable
- Avoid vague criteria like "good quality"

**Prerequisites:**
- Connect milestones (A2 depends on A1, A3 depends on A2)
- Include prior learning or course modules needed
- Help students understand progression

**Time Estimates:**
- Realistic hours based on complexity
- A1: 5-15 hours (planning is faster than building)
- A2: 15-30 hours (most time-intensive)
- A3: 10-20 hours (refinement and polish)"""

    def build_user_prompt(
        self,
        learning_objective: str,
        topic: str,
        milestone_type: str = "A1",
        estimated_hours: int = 10,
        difficulty: str = "intermediate",
        audience_level: str = "intermediate",
        language: str = "English",
        standards_rules: str = "",
        feedback: str = "",
        target_word_count: int = None
    ) -> str:
        """Build user prompt for project milestone generation.

        Args:
            learning_objective: The learning objective this milestone addresses
            topic: Project subject matter
            milestone_type: Milestone stage (A1, A2, or A3)
            estimated_hours: Expected completion time (default 10)
            difficulty: Difficulty level (beginner, intermediate, advanced)
            language: Language for content generation (default: English)
            standards_rules: Pre-built standards rules from standards_loader (optional)
            feedback: User feedback to incorporate in regeneration (optional)
            target_word_count: Specific word count target for regeneration (optional)

        Returns:
            str: Formatted user prompt
        """
        # Map milestone type to stage description
        stage_descriptions = {
            "A1": "foundation/proposal stage (planning, scope, initial setup)",
            "A2": "core implementation stage (main features, integration, testing)",
            "A3": "advanced/polish stage (refinement, optimization, final presentation)"
        }

        stage_desc = stage_descriptions.get(milestone_type, "project milestone")

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
Milestone Type: {milestone_type} ({stage_desc})
Estimated Effort: {estimated_hours} hours
Difficulty: {difficulty}

**TASK:**
Generate a project milestone for the {milestone_type} stage that scaffolds student learning through progressive deliverables.

**REQUIREMENTS:**
- Title should clearly indicate this is {milestone_type} milestone
- Overview explains what students will accomplish in this milestone
- Include 2-5 deliverables with NAME, DESCRIPTION, and specific FORMAT
- Provide 3-6 grading criteria aligned to {milestone_type} stage expectations
- List prerequisites (prior milestones if A2/A3, or required course modules)
- Set estimated_hours to approximately {estimated_hours} hours

**MILESTONE FOCUS:**
For {milestone_type}, emphasize: {stage_desc}

**SCAFFOLDING:**
Ensure this milestone builds appropriately on prior work and prepares for next stage."""

    def extract_metadata(self, content: ProjectMilestoneSchema) -> dict:
        """Calculate metadata from generated project milestone.

        Args:
            content: The validated ProjectMilestoneSchema instance

        Returns:
            dict: Metadata with word_count, duration, milestone_type, num_deliverables, content_type
        """
        # Count words in all text fields
        word_count = 0

        # Title, overview, learning_objective
        word_count += ContentMetadata.count_words(content.title)
        word_count += ContentMetadata.count_words(content.overview)
        word_count += ContentMetadata.count_words(content.learning_objective)

        # Prerequisites
        for prereq in content.prerequisites:
            word_count += ContentMetadata.count_words(prereq)

        # Deliverables
        for deliverable in content.deliverables:
            word_count += ContentMetadata.count_words(deliverable.name)
            word_count += ContentMetadata.count_words(deliverable.description)
            word_count += ContentMetadata.count_words(deliverable.format)

        # Grading criteria
        for criterion in content.grading_criteria:
            word_count += ContentMetadata.count_words(criterion)

        # Duration is estimated_hours converted to minutes
        duration_minutes = content.estimated_hours * 60

        return {
            "word_count": word_count,
            "estimated_duration_minutes": duration_minutes,
            "milestone_type": content.milestone_type,
            "num_deliverables": len(content.deliverables),
            "content_type": "project"
        }

    def generate_milestone(
        self,
        learning_objective: str,
        topic: str,
        milestone_type: str = "A1",
        estimated_hours: int = 10,
        difficulty: str = "intermediate"
    ) -> Tuple[ProjectMilestoneSchema, dict]:
        """Convenience method for generating a project milestone.

        Args:
            learning_objective: The learning objective this milestone addresses
            topic: Project subject matter
            milestone_type: Milestone stage (A1, A2, or A3, default A1)
            estimated_hours: Expected completion time (default 10)
            difficulty: Difficulty level (default "intermediate")

        Returns:
            Tuple[ProjectMilestoneSchema, dict]: (milestone, metadata)
        """
        return self.generate(
            schema=ProjectMilestoneSchema,
            learning_objective=learning_objective,
            topic=topic,
            milestone_type=milestone_type,
            estimated_hours=estimated_hours,
            difficulty=difficulty
        )
