"""DiscussionGenerator for creating discussion prompts with facilitation questions and engagement hooks."""

from typing import Tuple
from src.generators.base_generator import BaseGenerator
from src.generators.schemas.discussion import DiscussionSchema
from src.utils.content_metadata import ContentMetadata


class DiscussionGenerator(BaseGenerator[DiscussionSchema]):
    """Generator for creating discussion prompts with facilitation support.

    Produces discussion activities with:
    - Open-ended main prompt that encourages diverse perspectives
    - 3-5 facilitation questions to deepen discussion
    - 2-3 engagement hooks connecting to real-world contexts
    - Clear connection to learning objective
    """

    @property
    def system_prompt(self) -> str:
        """Return system prompt for discussion generation with peer learning guidelines."""
        return """You are an expert in facilitating online discussions in educational settings.

Your discussion prompts follow these principles:

**Prompt Design:**
- Open-ended questions that spark diverse perspectives
- No single "right answer" - invite exploration and debate
- Connect abstract concepts to concrete experiences
- Encourage students to build on each other's ideas
- Balance accessibility (everyone can contribute) with depth (expert insights welcome)

**Peer Learning Focus (CRITICAL):**
- Design for peer interaction, not just instructor response
- Prompts should invite students to engage with classmates' perspectives
- Create opportunities for collaborative knowledge construction
- Encourage respectful disagreement and perspective-taking
- Foster dialogue that extends beyond initial posts

**Facilitation Questions:**
- Guide instructors in deepening the conversation
- Target common misconceptions or surface-level thinking
- Connect discussion to broader course themes
- Suggest ways to challenge or extend student thinking
- 3-5 questions that scaffold progressively deeper analysis

**Engagement Hooks:**
- Real-world connections that make the topic personally relevant
- Current events, case studies, or scenarios students can relate to
- Questions that tap into students' prior experiences or interests
- 2-3 hooks that spark initial curiosity and investment

**Quality Standards:**
- Discussions should advance the learning objective through dialogue
- Avoid yes/no questions or prompts with obvious answers
- Create cognitive dissonance or interesting dilemmas
- Make space for multiple valid viewpoints"""

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
        """Build user prompt for discussion generation.

        Args:
            learning_objective: The learning objective this discussion supports
            topic: Subject matter for the discussion
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
Generate a discussion prompt that advances the learning objective through peer dialogue and reflection.

**REQUIREMENTS:**
- Create an open-ended main prompt that invites diverse perspectives
- Include 3-5 facilitation questions that help instructors deepen the conversation
- Include 2-3 engagement hooks that connect to real-world contexts or experiences
- Explain how this discussion advances the learning objective
- Design for peer interaction, not just instructor-student Q&A

**DISCUSSION FOCUS:**
The main prompt should encourage students to engage with each other's ideas, not just respond to the instructor. Create opportunities for collaborative exploration of the topic at the '{difficulty}' level."""

    def extract_metadata(self, content: DiscussionSchema) -> dict:
        """Calculate metadata from generated discussion.

        Args:
            content: The validated DiscussionSchema instance

        Returns:
            dict: Metadata with word_count, num_facilitation_questions, num_engagement_hooks, content_type
        """
        # Count words in all text fields
        word_count = 0

        # Count words in title and main prompt
        word_count += ContentMetadata.count_words(content.title)
        word_count += ContentMetadata.count_words(content.main_prompt)

        # Count words in all facilitation questions
        for question in content.facilitation_questions:
            word_count += ContentMetadata.count_words(question)

        # Count words in all engagement hooks
        for hook in content.engagement_hooks:
            word_count += ContentMetadata.count_words(hook)

        # Count words in connection to objective
        word_count += ContentMetadata.count_words(content.connection_to_objective)

        return {
            "word_count": word_count,
            "num_facilitation_questions": len(content.facilitation_questions),
            "num_engagement_hooks": len(content.engagement_hooks),
            "content_type": "discussion"
        }

    def generate_discussion(
        self,
        learning_objective: str,
        topic: str,
        difficulty: str = "intermediate"
    ) -> Tuple[DiscussionSchema, dict]:
        """Convenience method for generating a discussion prompt.

        Args:
            learning_objective: The learning objective this discussion supports
            topic: Subject matter for the discussion
            difficulty: Difficulty level (default "intermediate")

        Returns:
            Tuple[DiscussionSchema, dict]: (discussion, metadata)
        """
        return self.generate(
            schema=DiscussionSchema,
            learning_objective=learning_objective,
            topic=topic,
            difficulty=difficulty
        )
