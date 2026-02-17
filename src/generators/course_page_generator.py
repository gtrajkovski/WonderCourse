"""Generator for auto-generated course pages (syllabus, about, resources).

Produces consistent course documentation pages from course metadata
and structure, ensuring learners have clear information about the course.
"""

from typing import Dict, Any
from anthropic import Anthropic
from src.config import Config
from src.core.models import Course, PageType, CoursePage, BuildState
from src.generators.schemas.course_page import (
    SyllabusSchema,
    AboutSchema,
    ResourcesSchema,
    PageSection
)
from datetime import datetime


def _fix_schema_for_claude(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Fix schema for Claude API compatibility."""
    unsupported = {'exclusiveMinimum', 'exclusiveMaximum', 'format'}

    if isinstance(schema, dict):
        for prop in unsupported:
            schema.pop(prop, None)

        if schema.get("type") == "object":
            schema["additionalProperties"] = False

        for key, value in list(schema.items()):
            if isinstance(value, dict):
                _fix_schema_for_claude(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        _fix_schema_for_claude(item)
    return schema


class CoursePageGenerator:
    """Generate course pages from course metadata and structure.

    Produces three types of pages:
    - Syllabus: Schedule, objectives, grading policy
    - About: Course description, prerequisites, target audience
    - Resources: Tools, technologies, additional materials
    """

    SYSTEM_PROMPT = """You are an expert instructional designer creating course documentation.

Your pages must be:
- Clear and professional in tone
- Well-organized with logical sections
- Informative but concise
- Written for the target audience level

Format all content in clean markdown. Use headers, lists, and emphasis appropriately.
Do not include any AI-sounding phrases or filler content."""

    def __init__(self, api_key: str = None, model: str = None):
        """Initialize generator with Anthropic client."""
        self.client = Anthropic(api_key=api_key or Config.ANTHROPIC_API_KEY)
        self.model = model or Config.MODEL

    def generate_syllabus(self, course: Course, language: str = "English") -> CoursePage:
        """Generate a syllabus page from course structure.

        Args:
            course: Course object with modules and learning outcomes
            language: Target language for content

        Returns:
            CoursePage with syllabus content
        """
        prompt = self._build_syllabus_prompt(course, language)

        tool_schema = _fix_schema_for_claude(SyllabusSchema.model_json_schema())
        tools = [{
            "name": "output_syllabus",
            "description": "Output the syllabus page in structured format",
            "input_schema": tool_schema
        }]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=Config.MAX_TOKENS,
            system=self.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
            tools=tools,
            tool_choice={"type": "tool", "name": "output_syllabus"}
        )

        data = response.content[0].input
        schema = SyllabusSchema.model_validate(data)

        return self._schema_to_page(schema, PageType.SYLLABUS, "Course Syllabus")

    def generate_about(self, course: Course, language: str = "English") -> CoursePage:
        """Generate an about page from course metadata.

        Args:
            course: Course object with description and learning outcomes
            language: Target language for content

        Returns:
            CoursePage with about content
        """
        prompt = self._build_about_prompt(course, language)

        tool_schema = _fix_schema_for_claude(AboutSchema.model_json_schema())
        tools = [{
            "name": "output_about",
            "description": "Output the about page in structured format",
            "input_schema": tool_schema
        }]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=Config.MAX_TOKENS,
            system=self.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
            tools=tools,
            tool_choice={"type": "tool", "name": "output_about"}
        )

        data = response.content[0].input
        schema = AboutSchema.model_validate(data)

        return self._schema_to_page(schema, PageType.ABOUT, "About This Course")

    def generate_resources(self, course: Course, language: str = "English") -> CoursePage:
        """Generate a resources page from course tools and materials.

        Args:
            course: Course object with tools list
            language: Target language for content

        Returns:
            CoursePage with resources content
        """
        prompt = self._build_resources_prompt(course, language)

        tool_schema = _fix_schema_for_claude(ResourcesSchema.model_json_schema())
        tools = [{
            "name": "output_resources",
            "description": "Output the resources page in structured format",
            "input_schema": tool_schema
        }]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=Config.MAX_TOKENS,
            system=self.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
            tools=tools,
            tool_choice={"type": "tool", "name": "output_resources"}
        )

        data = response.content[0].input
        schema = ResourcesSchema.model_validate(data)

        return self._schema_to_page(schema, PageType.RESOURCES, "Course Resources")

    def generate_all(self, course: Course, language: str = "English") -> Dict[str, CoursePage]:
        """Generate all three course pages.

        Args:
            course: Course object
            language: Target language for content

        Returns:
            Dict mapping page type to CoursePage
        """
        return {
            "syllabus": self.generate_syllabus(course, language),
            "about": self.generate_about(course, language),
            "resources": self.generate_resources(course, language)
        }

    def _build_syllabus_prompt(self, course: Course, language: str) -> str:
        """Build prompt for syllabus generation."""
        lang_instruction = ""
        if language.lower() != "english":
            lang_instruction = f"\n**IMPORTANT: Generate ALL content in {language}.**\n"

        # Build module/lesson structure
        structure_lines = []
        for i, module in enumerate(course.modules, 1):
            structure_lines.append(f"Module {i}: {module.title}")
            if module.description:
                structure_lines.append(f"  Description: {module.description}")
            for j, lesson in enumerate(module.lessons, 1):
                activity_count = len(lesson.activities) if lesson.activities else 0
                structure_lines.append(f"  Lesson {j}: {lesson.title} ({activity_count} activities)")

        structure_text = "\n".join(structure_lines) if structure_lines else "No modules defined yet."

        # Build learning outcomes
        outcomes_lines = []
        for lo in course.learning_outcomes:
            outcomes_lines.append(f"- {lo.audience} will be able to {lo.behavior}")

        outcomes_text = "\n".join(outcomes_lines) if outcomes_lines else "No learning outcomes defined."

        return f"""{lang_instruction}
Generate a course syllabus for:

**Course Title:** {course.title}
**Description:** {course.description or 'Not provided'}
**Audience Level:** {course.audience_level}
**Duration:** {course.target_duration_minutes} minutes
**Modality:** {course.modality}

**Prerequisites:**
{course.prerequisites or 'None specified'}

**Learning Outcomes:**
{outcomes_text}

**Course Structure:**
{structure_text}

**Grading Policy:**
{course.grading_policy or 'Standard completion-based grading'}

Create a comprehensive syllabus with:
1. Course overview and objectives
2. Week-by-week schedule based on the module structure
3. Grading breakdown and assessment information
4. Course policies and expectations
"""

    def _build_about_prompt(self, course: Course, language: str) -> str:
        """Build prompt for about page generation."""
        lang_instruction = ""
        if language.lower() != "english":
            lang_instruction = f"\n**IMPORTANT: Generate ALL content in {language}.**\n"

        # Build learning outcomes
        outcomes_lines = []
        for lo in course.learning_outcomes:
            full_outcome = f"{lo.audience} will be able to {lo.behavior}"
            if lo.condition:
                full_outcome += f" {lo.condition}"
            if lo.degree:
                full_outcome += f" {lo.degree}"
            outcomes_lines.append(f"- {full_outcome}")

        outcomes_text = "\n".join(outcomes_lines) if outcomes_lines else "No learning outcomes defined."

        # Count content
        total_modules = len(course.modules)
        total_lessons = sum(len(m.lessons) for m in course.modules)
        total_activities = sum(
            len(l.activities) for m in course.modules for l in m.lessons
        )

        return f"""{lang_instruction}
Generate an "About This Course" page for:

**Course Title:** {course.title}
**Description:** {course.description or 'Not provided'}
**Audience Level:** {course.audience_level}
**Duration:** {course.target_duration_minutes} minutes
**Modality:** {course.modality}

**Prerequisites:**
{course.prerequisites or 'None - suitable for beginners'}

**Learning Outcomes:**
{outcomes_text}

**Course Size:**
- {total_modules} modules
- {total_lessons} lessons
- {total_activities} activities

Create an engaging about page with:
1. Compelling course description
2. Who this course is for (target audience)
3. What learners will gain (key takeaways)
4. Prerequisites and recommended background
5. How the course is structured
"""

    def _build_resources_prompt(self, course: Course, language: str) -> str:
        """Build prompt for resources page generation."""
        lang_instruction = ""
        if language.lower() != "english":
            lang_instruction = f"\n**IMPORTANT: Generate ALL content in {language}.**\n"

        tools_text = ", ".join(course.tools) if course.tools else "No specific tools required"

        return f"""{lang_instruction}
Generate a "Course Resources" page for:

**Course Title:** {course.title}
**Description:** {course.description or 'Not provided'}
**Audience Level:** {course.audience_level}

**Tools & Technologies:**
{tools_text}

Create a comprehensive resources page with:
1. Required tools and how to set them up
2. Recommended additional resources
3. Community and support links (generic placeholders)
4. Tips for getting the most out of the course

For each tool, provide:
- Brief description of what it is
- Why it's needed for this course
- Where to download/access it (generic guidance)
"""

    def _schema_to_page(
        self,
        schema: Any,
        page_type: PageType,
        default_title: str
    ) -> CoursePage:
        """Convert a schema to a CoursePage model."""
        # Build markdown content from schema
        content_parts = []

        if hasattr(schema, 'introduction') and schema.introduction:
            content_parts.append(schema.introduction)
            content_parts.append("")

        for section in schema.sections:
            content_parts.append(f"## {section.title}")
            content_parts.append(section.content)
            content_parts.append("")

        # Handle syllabus-specific fields
        if hasattr(schema, 'weekly_schedule') and schema.weekly_schedule:
            content_parts.append("## Weekly Schedule")
            for week in schema.weekly_schedule:
                content_parts.append(f"### {week.title}")
                content_parts.append(week.content)
                content_parts.append("")

        if hasattr(schema, 'grading_breakdown') and schema.grading_breakdown:
            content_parts.append("## Grading")
            content_parts.append(schema.grading_breakdown)
            content_parts.append("")

        # Handle about-specific fields
        if hasattr(schema, 'key_takeaways') and schema.key_takeaways:
            content_parts.append("## Key Takeaways")
            for takeaway in schema.key_takeaways:
                content_parts.append(f"- {takeaway}")
            content_parts.append("")

        if hasattr(schema, 'target_audience') and schema.target_audience:
            content_parts.append("## Who This Course Is For")
            content_parts.append(schema.target_audience)
            content_parts.append("")

        # Handle resources-specific fields
        if hasattr(schema, 'tools') and schema.tools:
            content_parts.append("## Tools & Technologies")
            for tool in schema.tools:
                content_parts.append(f"### {tool.title}")
                content_parts.append(tool.content)
                content_parts.append("")

        if hasattr(schema, 'additional_resources') and schema.additional_resources:
            content_parts.append("## Additional Resources")
            for resource in schema.additional_resources:
                content_parts.append(f"### {resource.title}")
                content_parts.append(resource.content)
                content_parts.append("")

        if hasattr(schema, 'conclusion') and schema.conclusion:
            content_parts.append(schema.conclusion)

        # Build sections list
        sections = [{"title": s.title, "content": s.content} for s in schema.sections]

        return CoursePage(
            page_type=page_type,
            title=schema.title if hasattr(schema, 'title') else default_title,
            content="\n".join(content_parts),
            sections=sections,
            build_state=BuildState.GENERATED,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
