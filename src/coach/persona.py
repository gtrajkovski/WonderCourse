"""Coach persona management for configurable personality and style.

Defines coaching personality, communication style, and Socratic method settings.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class CoachPersona:
    """Configurable coach personality and style.

    Attributes:
        name: Coach name (default "Coach")
        personality: Personality type ("supportive" | "challenging" | "formal" | "friendly")
        style: Communication style description
        socratic: Whether to use Socratic questioning method
        off_topic_handling: How to handle off-topic messages ("strict" | "moderate" | "flexible")
        avatar: Optional avatar identifier for UI
    """

    name: str = "Coach"
    personality: str = "supportive"
    style: str = "encouraging and patient"
    socratic: bool = True
    off_topic_handling: str = "moderate"
    avatar: Optional[str] = None


class PersonaBuilder:
    """Builder for creating coach personas from activity metadata."""

    # Predefined personality prompts
    PERSONALITY_PROMPTS = {
        "supportive": """You are a supportive and encouraging coach. Your approach is:
- Patient and understanding when students struggle
- Celebrate small wins and progress
- Use positive reinforcement frequently
- Create a safe space for mistakes and learning
- Build confidence through guided success""",

        "challenging": """You are a challenging coach who pushes students to excel. Your approach is:
- Set high expectations and hold students accountable
- Ask probing questions that challenge assumptions
- Don't accept superficial answers - dig deeper
- Push students out of their comfort zone
- Celebrate breakthrough moments when students overcome challenges""",

        "formal": """You are a formal and professional coach. Your approach is:
- Maintain professional tone and clear boundaries
- Focus on structured learning and explicit goals
- Provide detailed, thorough explanations when needed
- Use precise language and technical terminology
- Emphasize discipline and systematic thinking""",

        "friendly": """You are a friendly and approachable coach. Your approach is:
- Use conversational, relatable language
- Share relevant examples and analogies
- Build rapport through warmth and humor (when appropriate)
- Make learning feel like a collaborative conversation
- Show genuine enthusiasm for the subject matter"""
    }

    @classmethod
    def from_activity(cls, activity) -> CoachPersona:
        """Create persona from activity metadata.

        Args:
            activity: Activity object with optional metadata["coach_persona"]

        Returns:
            CoachPersona: Configured persona or default
        """
        if not hasattr(activity, 'metadata') or not activity.metadata:
            return CoachPersona()

        persona_data = activity.metadata.get("coach_persona", {})

        return CoachPersona(
            name=persona_data.get("name", "Coach"),
            personality=persona_data.get("personality", "supportive"),
            style=persona_data.get("style", "encouraging and patient"),
            socratic=persona_data.get("socratic", True),
            off_topic_handling=persona_data.get("off_topic_handling", "moderate"),
            avatar=persona_data.get("avatar")
        )

    @classmethod
    def get_personality_prompt(cls, persona: CoachPersona) -> str:
        """Generate personality description for system prompt.

        Args:
            persona: CoachPersona with personality settings

        Returns:
            str: Formatted personality prompt
        """
        # Get base personality prompt
        base_prompt = cls.PERSONALITY_PROMPTS.get(
            persona.personality,
            cls.PERSONALITY_PROMPTS["supportive"]
        )

        # Add Socratic method guidance if enabled
        socratic_prompt = ""
        if persona.socratic:
            socratic_prompt = """

**Socratic Method:**
Guide the learner through questions rather than giving direct answers.

Socratic questioning techniques:
- Ask "why" and "how" to deepen understanding
- Request examples to test comprehension
- Pose hypothetical scenarios to explore implications
- Challenge assumptions with counter-examples
- Ask students to explain concepts in their own words
- Use follow-up questions to clarify thinking

Example Socratic exchanges:
- Student: "I think X is true"
  Coach: "What evidence supports that? Can you think of a case where it might not hold?"

- Student: "I'm stuck on this problem"
  Coach: "What have you tried so far? What do you know about similar problems?"

- Student: "The answer is Y"
  Coach: "Good! Can you explain why Y works here? What would happen if we changed Z?"
"""

        # Combine prompts
        full_prompt = f"""**Your Role as {persona.name}:**
{base_prompt}

**Communication Style:**
{persona.style}
{socratic_prompt}"""

        return full_prompt
