"""Pydantic schemas and generator for AI-powered course blueprint generation.

These models define the AI-generated blueprint structure that gets validated
and converted to actual Course dataclasses.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Literal, Dict, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from src.validators.blueprint_autofix import AutoFixResult
    from src.validators.course_validator import BlueprintValidation
from anthropic import Anthropic
from src.config import Config


def _fix_schema_additional_properties(schema: dict) -> dict:
    """Fix schema for Anthropic API compatibility.

    - Set additionalProperties: false on all object types
    - Remove unsupported properties (exclusiveMinimum, exclusiveMaximum, format)
    - Handles Pydantic v2 schemas with $defs for nested models
    """
    unsupported = {'exclusiveMinimum', 'exclusiveMaximum', 'format'}

    if isinstance(schema, dict):
        # Remove unsupported properties
        for prop in unsupported:
            schema.pop(prop, None)

        # Handle object types
        if schema.get("type") == "object" or "properties" in schema:
            schema["additionalProperties"] = False

        # Process $defs (Pydantic v2 nested model definitions)
        if "$defs" in schema:
            for def_name, def_schema in schema["$defs"].items():
                _fix_schema_additional_properties(def_schema)

        # Recurse into all dict values
        for key, value in list(schema.items()):
            if key == "$defs":
                continue  # Already handled above
            if isinstance(value, dict):
                _fix_schema_additional_properties(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        _fix_schema_additional_properties(item)
    return schema


class ActivityBlueprint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    """Blueprint for a single activity within a lesson."""

    title: str = Field(max_length=200, description="Activity title")
    content_type: Literal["video", "reading", "quiz", "hol", "lab", "discussion", "assignment", "project"]
    activity_type: str = Field(description="Specific activity type (e.g., 'video_lecture', 'graded_quiz')")
    wwhaa_phase: Optional[Literal["hook", "objective", "content", "ivq", "summary", "cta"]] = None
    bloom_level: Literal["remember", "understand", "apply", "analyze", "evaluate", "create"]
    estimated_duration_minutes: float = Field(ge=2.0, le=60.0, description="Estimated time to complete")
    description: str = Field(max_length=500, description="Brief activity description")


class LessonBlueprint(BaseModel):
    """Blueprint for a lesson containing multiple activities."""
    model_config = ConfigDict(extra="forbid")

    title: str = Field(max_length=200, description="Lesson title")
    description: str = Field(max_length=1000, description="Lesson description")
    activities: List[ActivityBlueprint] = Field(min_length=1, description="Activities in the lesson")


class ModuleBlueprint(BaseModel):
    """Blueprint for a module containing multiple lessons."""
    model_config = ConfigDict(extra="forbid")

    title: str = Field(max_length=200, description="Module title")
    description: str = Field(max_length=1000, description="Module description")
    lessons: List[LessonBlueprint] = Field(min_length=1, description="Lessons in the module")


class ContentDistribution(BaseModel):
    """Percentage breakdown by content type (as decimals, e.g., 0.30 = 30%)."""
    model_config = ConfigDict(extra="forbid")

    video: float = Field(default=0.3, ge=0.0, le=1.0, description="Video content percentage")
    reading: float = Field(default=0.2, ge=0.0, le=1.0, description="Reading content percentage")
    quiz: float = Field(default=0.2, ge=0.0, le=1.0, description="Quiz content percentage")
    hands_on: float = Field(default=0.2, ge=0.0, le=1.0, description="Hands-on (lab/hol) content percentage")
    other: float = Field(default=0.1, ge=0.0, le=1.0, description="Other content percentage")


class CourseBlueprint(BaseModel):
    """Complete course blueprint with modules, lessons, and activities."""
    model_config = ConfigDict(extra="forbid")

    modules: List[ModuleBlueprint] = Field(min_length=1, description="Modules in the course")
    total_duration_minutes: float = Field(ge=1.0, description="Total course duration")
    content_distribution: Optional[ContentDistribution] = Field(
        default=None,
        description="Percentage breakdown by content_type (as decimals: 0.30 = 30%)"
    )
    rationale: str = Field(
        max_length=2000,
        description="Brief explanation of module/lesson structure decisions"
    )


class BlueprintGenerator:
    """Generates course blueprints using Claude structured outputs API.

    This generator creates complete course structures (modules, lessons, activities)
    from high-level course descriptions and learning outcomes. Uses Claude's
    structured outputs feature to guarantee JSON schema compliance.
    """

    SYSTEM_PROMPT = """You are an expert instructional designer specializing in Coursera short courses.

Your blueprints follow these principles:
1. WWHAA pedagogy: Each video activity uses Why/What/How/Apply/Assess structure
2. Bloom's taxonomy: Activities span Remember → Create with emphasis on Apply/Analyze
3. Content distribution: ~30% video, ~20% reading, ~30% hands-on, ~20% assessment
4. Scaffolding: Lessons progress from concrete examples → abstract concepts → application

COURSERA SHORT COURSE REQUIREMENTS:
- Duration: 30-180 minutes total
- Modules: 2-3 modules per course
- Lessons per module: 3-5 lessons
- Activities per lesson: 2-4 activities
- Learning outcomes: 1-3 measurable outcomes using Bloom's action verbs

WWHAA PHASES (for video activities only):
- HOOK (10%): Engage with relatable problem
- OBJECTIVE (10%): State measurable learning goal
- CONTENT (60%): Teach with concrete examples
- IVQ (in-video quiz): Check understanding
- SUMMARY (10%): Reinforce key takeaways
- CTA (10%): Direct to next activity

ACTIVITY DURATION GUIDELINES:
- Video (WWHAA): 5-10 minutes
- Reading: 8-12 minutes
- Graded quiz: 5-10 minutes
- Practice quiz: 3-5 minutes
- Hands-on lab: 15-30 minutes
- Discussion: 10-15 minutes
- Assignment: 20-45 minutes

Your output will be valid JSON matching the CourseBlueprint schema."""

    def __init__(self, api_key: str = None, model: str = None):
        """Initialize BlueprintGenerator with Anthropic client.

        Args:
            api_key: Optional API key override. Defaults to Config.ANTHROPIC_API_KEY.
            model: Optional model override. Defaults to Config.MODEL.
        """
        self.client = Anthropic(api_key=api_key or Config.ANTHROPIC_API_KEY)
        self.model = model or Config.MODEL

    def generate(
        self,
        course_description: str,
        learning_outcomes: List[str],
        target_duration_minutes: int = 90,
        audience_level: str = "intermediate"
    ) -> CourseBlueprint:
        """Generate a complete course blueprint using Claude structured outputs.

        Args:
            course_description: High-level description of the course content
            learning_outcomes: List of measurable learning outcomes
            target_duration_minutes: Target total duration (default: 90)
            audience_level: Target audience expertise level (default: "intermediate")

        Returns:
            CourseBlueprint: Validated Pydantic model with complete course structure
        """
        # Build user prompt
        user_prompt = self._build_prompt(
            course_description,
            learning_outcomes,
            target_duration_minutes,
            audience_level
        )

        # Use tool-based structured output (more reliable than output_config)
        schema = _fix_schema_additional_properties(CourseBlueprint.model_json_schema())
        tools = [{
            "name": "output_blueprint",
            "description": "Output the generated course blueprint",
            "input_schema": schema
        }]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=8192,
            system=self.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
            tools=tools,
            tool_choice={"type": "tool", "name": "output_blueprint"}
        )

        # Extract from tool use response
        content_data = None
        for block in response.content:
            if block.type == "tool_use":
                content_data = block.input
                break

        if content_data is None:
            raise ValueError("No tool_use block in response")

        # Parse and validate with Pydantic
        blueprint = CourseBlueprint.model_validate(content_data)

        return blueprint

    def _build_prompt(
        self,
        description: str,
        outcomes: List[str],
        duration: int,
        level: str
    ) -> str:
        """Build user prompt with CONTEXT-TASK structure.

        Args:
            description: Course description
            outcomes: Learning outcomes
            duration: Target duration in minutes
            level: Audience level

        Returns:
            str: Formatted prompt for Claude
        """
        # Format outcomes as numbered list
        outcomes_text = "\n".join(
            f"{i+1}. {outcome}"
            for i, outcome in enumerate(outcomes)
        )

        return f"""Design a Coursera short course blueprint.

CONTEXT:
- Description: {description}
- Audience: {level} learners
- Target duration: {duration} minutes

LEARNING OUTCOMES:
{outcomes_text}

TASK:
Create a complete blueprint with:
1. 2-3 modules covering all learning outcomes
2. 3-5 lessons per module with clear progression
3. 2-4 activities per lesson (mix of video, reading, quiz, hands-on)
4. WWHAA phase assignments for video activities
5. Bloom's taxonomy levels matching outcome complexity
6. Realistic duration estimates per activity
7. Content distribution with video, reading, quiz, hands_on percentages (as decimals: 0.30 = 30%)

Ensure balanced content distribution and complete outcome coverage.
Provide rationale explaining your module/lesson structure decisions."""

    def generate_with_autofix(
        self,
        course_description: str,
        learning_outcomes: List[str],
        target_duration_minutes: int = 90,
        audience_level: str = "intermediate",
        max_refinements: int = 1
    ) -> Tuple["CourseBlueprint", "AutoFixResult", "BlueprintValidation"]:
        """Generate a blueprint with automatic fixing and optional refinement.

        This method:
        1. Generates an initial blueprint
        2. Validates it
        3. Applies automatic fixes for common issues
        4. Optionally regenerates with feedback if critical issues remain

        Args:
            course_description: High-level description of the course content
            learning_outcomes: List of measurable learning outcomes
            target_duration_minutes: Target total duration (default: 90)
            audience_level: Target audience expertise level (default: "intermediate")
            max_refinements: Max AI refinement attempts for critical issues (default: 1)

        Returns:
            Tuple of (final_blueprint, auto_fix_result, final_validation)
        """
        from src.validators.blueprint_autofix import (
            BlueprintAutoFixer, AutoFixResult, auto_fix_blueprint
        )
        from src.validators.course_validator import CourseraValidator, BlueprintValidation

        validator = CourseraValidator()
        fixer = BlueprintAutoFixer()

        # Step 1: Generate initial blueprint
        blueprint = self.generate(
            course_description,
            learning_outcomes,
            target_duration_minutes,
            audience_level
        )

        # Step 2: Initial validation
        validation = validator.validate(blueprint, target_duration_minutes)

        # Step 3: Apply automatic fixes
        fix_result = fixer.auto_fix(blueprint, target_duration_minutes)
        blueprint = fix_result.blueprint

        # Step 4: Re-validate after auto-fix
        validation = validator.validate(blueprint, target_duration_minutes)

        # Step 5: If critical errors remain and refinements allowed, regenerate
        refinement_count = 0
        while not validation.is_valid and refinement_count < max_refinements:
            refinement_count += 1

            # Generate feedback for AI refinement
            feedback = fixer.generate_refinement_feedback(validation)
            if not feedback:
                break

            # Build refinement prompt
            refinement_prompt = self._build_refinement_prompt(
                course_description,
                learning_outcomes,
                target_duration_minutes,
                audience_level,
                blueprint,
                feedback
            )

            # Use tool-based structured output
            schema = _fix_schema_additional_properties(CourseBlueprint.model_json_schema())
            tools = [{
                "name": "output_blueprint",
                "description": "Output the refined course blueprint",
                "input_schema": schema
            }]

            response = self.client.messages.create(
                model=self.model,
                max_tokens=8192,
                system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": refinement_prompt}],
                tools=tools,
                tool_choice={"type": "tool", "name": "output_blueprint"}
            )

            # Extract from tool use response
            content_data = None
            for block in response.content:
                if block.type == "tool_use":
                    content_data = block.input
                    break

            if content_data is None:
                break

            # Parse and validate
            blueprint = CourseBlueprint.model_validate(content_data)

            # Apply auto-fixes to refined blueprint
            fix_result = fixer.auto_fix(blueprint, target_duration_minutes)
            blueprint = fix_result.blueprint

            # Re-validate
            validation = validator.validate(blueprint, target_duration_minutes)

        return blueprint, fix_result, validation

    def _build_refinement_prompt(
        self,
        description: str,
        outcomes: List[str],
        duration: int,
        level: str,
        previous_blueprint: "CourseBlueprint",
        feedback: str
    ) -> str:
        """Build refinement prompt with previous blueprint and feedback.

        Args:
            description: Course description
            outcomes: Learning outcomes
            duration: Target duration
            level: Audience level
            previous_blueprint: The blueprint that needs refinement
            feedback: Validation feedback to address

        Returns:
            str: Formatted refinement prompt
        """
        outcomes_text = "\n".join(
            f"{i+1}. {outcome}"
            for i, outcome in enumerate(outcomes)
        )

        # Summarize previous structure
        prev_structure = []
        for i, module in enumerate(previous_blueprint.modules, 1):
            lesson_count = len(module.lessons)
            activity_count = sum(len(l.activities) for l in module.lessons)
            prev_structure.append(
                f"- Module {i}: {module.title} ({lesson_count} lessons, {activity_count} activities)"
            )

        return f"""Refine this Coursera short course blueprint to address validation issues.

CONTEXT:
- Description: {description}
- Audience: {level} learners
- Target duration: {duration} minutes

LEARNING OUTCOMES:
{outcomes_text}

PREVIOUS BLUEPRINT STRUCTURE:
{chr(10).join(prev_structure)}
Total duration: {previous_blueprint.total_duration_minutes:.0f} minutes

VALIDATION FEEDBACK:
{feedback}

TASK:
Create a refined blueprint that:
1. Addresses ALL validation issues listed above
2. Maintains coverage of learning outcomes
3. Keeps the overall structure similar where possible
4. Ensures activities have appropriate durations

Focus on fixing the specific issues identified while preserving good aspects of the original."""
