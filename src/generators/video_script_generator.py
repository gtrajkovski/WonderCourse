"""Video script generator with WWHAA structure.

Generates instructional video scripts following the WWHAA framework:
- Hook (10%): Engage with relatable problem
- Objective (10%): State measurable learning goal
- Content (60%): Teach with concrete examples
- IVQ (5%): In-video question to check understanding
- Summary (10%): Reinforce key takeaways
- CTA (5%): Call to action directing to next activity
"""

from anthropic import Anthropic
from src.generators.base_generator import BaseGenerator
from src.generators.schemas.video_script import VideoScriptSchema
from src.utils.content_metadata import ContentMetadata


class VideoScriptGenerator(BaseGenerator[VideoScriptSchema]):
    """Generator for WWHAA-structured video scripts.

    Extends BaseGenerator to produce VideoScriptSchema instances with all 6
    required WWHAA sections. Calculates metadata including word counts and
    estimated duration based on 150 WPM speaking rate.
    """

    @property
    def system_prompt(self) -> str:
        """Return system instructions for video script generation.

        Returns:
            str: System prompt with WWHAA structure and percentage guidelines
        """
        return """You are an expert instructional video scriptwriter for online courses.

Your task is to create engaging, pedagogically sound video scripts following the WWHAA framework:

**WWHAA Structure (with target proportions):**

1. **Hook (10%)**: Open with a relatable problem, surprising fact, or thought-provoking question that captures attention and establishes relevance.

2. **Objective (10%)**: Clearly state the measurable learning goal. What will learners be able to do after watching this video?

3. **Content (60%)**: Deliver the main teaching content with:
   - Clear explanations of concepts
   - Concrete, realistic examples
   - Step-by-step demonstrations where appropriate
   - Visual cues (mention what should appear on screen)

4. **IVQ - In-Video Question (5%)**: Pose a question that checks understanding of a key concept. Include both the question and the answer/explanation.

5. **Summary (10%)**: Reinforce the key takeaways. Briefly recap the most important points covered.

6. **CTA - Call to Action (5%)**: Direct learners to the next activity (practice exercise, reading, quiz) to apply what they learned.

**Writing Guidelines:**

- Write in a conversational, approachable tone
- Use "you" to address learners directly
- Keep sentences clear and concise for easy delivery
- Include speaker notes for delivery guidance (pacing, emphasis, visual cues)
- Avoid jargon unless teaching technical concepts (then define terms clearly)
- Target the specified audience level (beginner/intermediate/advanced)
- Aim for the target duration, keeping in mind 150 words per minute speaking rate

**Quality Criteria:**

- Each section must have a clear purpose and flow logically to the next
- Examples must be concrete, realistic, and relevant to learners
- Language should match the specified audience level
- Script should be deliverable naturally (avoid overly complex sentences)
- Speaker notes should provide actionable delivery guidance"""

    def build_user_prompt(
        self,
        learning_objective: str,
        topic: str,
        audience_level: str,
        duration_minutes: int = 8,
        language: str = "English",
        standards_rules: str = "",
        feedback: str = "",
        target_duration_minutes: float = None,
        speaking_wpm: int = 120
    ) -> str:
        """Build user prompt from video script parameters.

        Args:
            learning_objective: What learners will be able to do after the video
            topic: The subject matter to be taught
            audience_level: Target audience (beginner/intermediate/advanced)
            duration_minutes: Target video duration in minutes (default: 8)
            language: Language for content generation (default: English)
            standards_rules: Pre-built standards rules from standards_loader (optional)
            feedback: User feedback to incorporate in regeneration (optional)
            target_duration_minutes: Override duration for regeneration (optional)
            speaking_wpm: Words per minute speaking rate (default: 120)

        Returns:
            str: Formatted user prompt for Claude API
        """
        lang_instruction = ""
        if language.lower() != "english":
            lang_instruction = f"\n**IMPORTANT: Generate ALL content in {language}.**\n"

        standards_section = ""
        if standards_rules:
            standards_section = f"\n{standards_rules}\n"

        # Calculate actual target duration and word count
        actual_duration = target_duration_minutes if target_duration_minutes else duration_minutes
        target_words = int(actual_duration * speaking_wpm)

        # Build length constraint section
        length_section = f"""
**LENGTH REQUIREMENTS (STRICT):**
- Target duration: {actual_duration} minutes
- Speaking rate: {speaking_wpm} words per minute
- Target total words: {target_words} (stay within ±10%)
- Distribute words across WWHAA sections proportionally
"""

        # Build feedback section if provided
        feedback_section = ""
        if feedback:
            feedback_section = f"""
**USER FEEDBACK TO ADDRESS:**
{feedback}

Please incorporate this feedback while maintaining the WWHAA structure and meeting length requirements.
"""

        return f"""{lang_instruction}{standards_section}{length_section}{feedback_section}Generate a video script for an online course.

**CONTEXT:**
- Topic: {topic}
- Audience Level: {audience_level}

**LEARNING OBJECTIVE:**
{learning_objective}

**TASK:**
Create a complete WWHAA-structured video script that:
1. Hooks learners with a relatable opening
2. States the learning objective clearly
3. Teaches the content with concrete examples
4. Includes an in-video question to check understanding
5. Summarizes the key takeaways
6. Directs learners to practice with a call to action

Remember to:
- Match the {audience_level} level in language and depth
- Include speaker notes for delivery guidance
- Keep the script natural and conversational
- Target exactly {target_words} words total ({actual_duration} minutes at {speaking_wpm} WPM)"""

    def extract_metadata(self, content: VideoScriptSchema) -> dict:
        """Calculate metadata from generated video script.

        Extracts word counts from all 6 WWHAA sections and calculates
        video duration based on 150 WPM speaking rate.

        Args:
            content: The validated VideoScriptSchema instance

        Returns:
            dict: Metadata with word_count, estimated_duration_minutes,
                  content_type, and section_word_counts
        """
        # Calculate word count for each section
        section_word_counts = {
            "hook": ContentMetadata.count_words(content.hook.script_text),
            "objective": ContentMetadata.count_words(content.objective.script_text),
            "content": ContentMetadata.count_words(content.content.script_text),
            "ivq": ContentMetadata.count_words(content.ivq.script_text),
            "summary": ContentMetadata.count_words(content.summary.script_text),
            "cta": ContentMetadata.count_words(content.cta.script_text),
        }

        # Calculate total word count
        total_word_count = sum(section_word_counts.values())

        # Calculate estimated duration at 150 WPM
        estimated_duration = ContentMetadata.estimate_video_duration(total_word_count)

        # Calculate per-section timing in minutes (150 WPM)
        section_timings = {
            section: round(wc / 150, 2)
            for section, wc in section_word_counts.items()
        }

        return {
            "word_count": total_word_count,
            "estimated_duration_minutes": estimated_duration,
            "content_type": "video",
            "section_word_counts": section_word_counts,
            "section_timings": section_timings,
        }

    def generate_script(
        self,
        learning_objective: str,
        topic: str,
        audience_level: str,
        duration_minutes: int = 8
    ) -> tuple[VideoScriptSchema, dict]:
        """Convenience method for generating video scripts.

        Wraps the generate() method with a cleaner API specifically for
        video script generation.

        Args:
            learning_objective: What learners will be able to do
            topic: The subject matter to be taught
            audience_level: Target audience (beginner/intermediate/advanced)
            duration_minutes: Target video duration in minutes (default: 8)

        Returns:
            tuple: (VideoScriptSchema, metadata_dict)
        """
        return self.generate(
            schema=VideoScriptSchema,
            learning_objective=learning_objective,
            topic=topic,
            audience_level=audience_level,
            duration_minutes=duration_minutes
        )
