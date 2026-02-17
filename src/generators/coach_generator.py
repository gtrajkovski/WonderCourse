"""CoachGenerator for creating AI coach dialogue activities with 8-section structure."""

from typing import Tuple
from src.generators.base_generator import BaseGenerator
from src.generators.schemas.coach import CoachSchema, ConversationStarter, SampleResponse
from src.utils.content_metadata import ContentMetadata


class CoachGenerator(BaseGenerator[CoachSchema]):
    """Generator for creating AI coach dialogue activities.

    Produces structured conversational learning experiences with:
    - 8 required sections (learning objectives, scenario, tasks, conversation starters,
      sample responses, evaluation criteria, wrap-up, reflection prompts)
    - 3-level evaluation (exceeds, meets, needs_improvement)
    - Socratic dialogue approach focused on guiding rather than lecturing
    """

    @property
    def system_prompt(self) -> str:
        """Return system prompt for coach dialogue generation with 8-section structure."""
        return """You are an expert in AI-powered conversational coaching for education.

Your coach dialogues provide structured learning experiences that guide students through
realistic scenarios using Socratic questioning rather than direct instruction.

**Required 8-Section Structure:**

1. **Learning Objectives** (2-4 objectives)
   - Clear, measurable outcomes students will achieve
   - Focus on both knowledge and application

2. **Scenario**
   - Realistic, relatable context that students might encounter
   - Provides sufficient detail for meaningful engagement
   - Creates motivation for the learning experience

3. **Tasks** (2-5 specific tasks)
   - Concrete actions students must complete
   - Build progressively in complexity
   - Support the learning objectives

4. **Conversation Starters** (3-5 prompts)
   - Open-ended questions that elicit thinking
   - Each starter has a clear pedagogical purpose
   - Designed to reveal understanding and guide reflection

5. **Sample Responses** (exactly 3 examples)
   - One at each evaluation level: exceeds, meets, needs_improvement
   - Demonstrates quality expectations at different levels
   - Each includes constructive coaching feedback

6. **Evaluation Criteria** (3-5 criteria)
   - Clear standards for assessing student responses
   - Observable, actionable indicators of understanding
   - Aligned with learning objectives

7. **Wrap-Up**
   - Synthesizes key insights from the dialogue
   - Reinforces learning objectives
   - Provides closure and forward-looking perspective

8. **Reflection Prompts** (2-4 questions)
   - Deepen metacognitive awareness
   - Connect experience to broader contexts
   - Encourage transfer of learning

**Coaching Philosophy:**
- Ask, don't tell - use questions to guide discovery
- Provide formative feedback that supports growth
- Create safe space for exploration and mistakes
- Focus on thinking processes, not just answers
- Build on student responses with follow-up questions"""

    def build_user_prompt(
        self,
        learning_objective: str,
        topic: str,
        difficulty: str = "intermediate",
        audience_level: str = "intermediate",
        language: str = "English",
        standards_rules: str = ""
    ) -> str:
        """Build user prompt for coach dialogue generation.

        Args:
            learning_objective: The learning objective this dialogue addresses
            topic: Subject matter for the dialogue
            difficulty: Difficulty level (beginner, intermediate, advanced)
            language: Language for content generation (default: English)
            standards_rules: Pre-built standards rules from standards_loader (optional)

        Returns:
            str: Formatted user prompt
        """
        lang_instruction = ""
        if language.lower() != "english":
            lang_instruction = f"**IMPORTANT: Generate ALL content in {language}.**\n\n"

        standards_section = ""
        if standards_rules:
            standards_section = f"{standards_rules}\n\n"

        return f"""{lang_instruction}{standards_section}**CONTEXT:**
Learning Objective: {learning_objective}
Topic: {topic}
Difficulty: {difficulty}

**TASK:**
Create a complete AI coach dialogue activity with all 8 required sections.

**REQUIREMENTS:**
- All 8 sections must be present and substantive
- Sample responses must include exactly 3 examples at these evaluation levels:
  * "exceeds" - exceptional understanding and application
  * "meets" - solid understanding with minor gaps
  * "needs_improvement" - significant misconceptions or gaps
- Each sample response must include constructive coaching feedback
- Conversation starters should use Socratic questioning (ask, don't tell)
- Scenario should be realistic and relatable to students
- Tasks should build progressively in complexity
- Evaluation criteria should be observable and actionable

**COACHING APPROACH:**
Focus on guiding student thinking rather than providing answers. Use questions that reveal
understanding, challenge assumptions, and encourage deeper reflection. Feedback should be
formative and growth-oriented."""

    def extract_metadata(self, content: CoachSchema) -> dict:
        """Calculate metadata from generated coach dialogue.

        Args:
            content: The validated CoachSchema instance

        Returns:
            dict: Metadata with word counts and section counts
        """
        # Count words across all text fields
        word_count = 0

        # Title and scenario
        word_count += ContentMetadata.count_words(content.title)
        word_count += ContentMetadata.count_words(content.scenario)
        word_count += ContentMetadata.count_words(content.wrap_up)

        # Learning objectives
        for obj in content.learning_objectives:
            word_count += ContentMetadata.count_words(obj)

        # Tasks
        for task in content.tasks:
            word_count += ContentMetadata.count_words(task)

        # Conversation starters (text + purpose)
        for starter in content.conversation_starters:
            word_count += ContentMetadata.count_words(starter.starter_text)
            word_count += ContentMetadata.count_words(starter.purpose)

        # Sample responses (text + feedback)
        for response in content.sample_responses:
            word_count += ContentMetadata.count_words(response.response_text)
            word_count += ContentMetadata.count_words(response.feedback)

        # Evaluation criteria
        for criterion in content.evaluation_criteria:
            word_count += ContentMetadata.count_words(criterion)

        # Reflection prompts
        for prompt in content.reflection_prompts:
            word_count += ContentMetadata.count_words(prompt)

        return {
            "word_count": word_count,
            "num_conversation_starters": len(content.conversation_starters),
            "num_sample_responses": len(content.sample_responses),
            "num_evaluation_criteria": len(content.evaluation_criteria),
            "content_type": "coach"
        }

    def generate_dialogue(
        self,
        learning_objective: str,
        topic: str,
        difficulty: str = "intermediate"
    ) -> Tuple[CoachSchema, dict]:
        """Convenience method for generating a coach dialogue.

        Args:
            learning_objective: The learning objective this dialogue addresses
            topic: Subject matter for the dialogue
            difficulty: Difficulty level (default "intermediate")

        Returns:
            Tuple[CoachSchema, dict]: (dialogue, metadata)
        """
        return self.generate(
            schema=CoachSchema,
            learning_objective=learning_objective,
            topic=topic,
            difficulty=difficulty
        )
