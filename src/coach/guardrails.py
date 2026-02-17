"""Guardrail engine for topic and structure enforcement in coach dialogues.

Ensures conversations stay on-topic and cover required dialogue sections.
"""

from dataclasses import dataclass
from typing import List, Dict


@dataclass
class CoverageResult:
    """Result of dialogue section coverage analysis.

    Tracks which sections have been addressed and which remain.

    Attributes:
        covered_sections: List of section names that have been covered
        remaining_sections: List of section names not yet covered
        coverage_percent: Percentage of sections covered (0-100)
        key_points_addressed: List of specific key points discussed
    """

    covered_sections: List[str]
    remaining_sections: List[str]
    coverage_percent: float
    key_points_addressed: List[str]

    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            "covered_sections": self.covered_sections,
            "remaining_sections": self.remaining_sections,
            "coverage_percent": self.coverage_percent,
            "key_points_addressed": self.key_points_addressed
        }


class GuardrailEngine:
    """Enforces topic boundaries and dialogue structure for coach conversations.

    Uses the dialogue structure from CoachSchema to guide conversations and
    keep them focused on learning objectives.
    """

    # Section names from CoachSchema structure
    DIALOGUE_SECTIONS = [
        "context_setting",
        "skill_introduction",
        "guided_practice",
        "formative_assessment",
        "reflection",
        "application",
        "wrap_up",
        "next_steps"
    ]

    def __init__(
        self,
        dialogue_structure: dict = None,
        learning_outcomes: List[str] = None,
        tasks: List[str] = None,
        evaluation_criteria: List[str] = None
    ):
        """Initialize guardrail engine.

        Args:
            dialogue_structure: Generated coach dialogue structure
            learning_outcomes: Course learning outcomes for topic validation
            tasks: Alternative to dialogue_structure - list of task strings
            evaluation_criteria: Alternative to learning_outcomes - criteria list
        """
        # Support both old and new parameter styles
        self.dialogue_structure = dialogue_structure or {}
        self.learning_outcomes = learning_outcomes or []

        # If tasks provided, use them as key points
        self.tasks = tasks or []
        self.evaluation_criteria = evaluation_criteria or []

        # Extract key points from dialogue structure or tasks
        if dialogue_structure:
            self.key_points = self._extract_key_points(dialogue_structure)
        else:
            self.key_points = self.tasks

    def build_system_prompt(self, persona) -> str:
        """Build system prompt with guardrails and persona.

        Args:
            persona: CoachPersona with personality and style settings

        Returns:
            str: Complete system prompt for Claude API
        """
        from src.coach.persona import PersonaBuilder

        # Get personality description
        personality_prompt = PersonaBuilder.get_personality_prompt(persona)

        # Build guardrails section
        guardrails = self._build_guardrails_section()

        # Combine into full prompt
        prompt = f"""{personality_prompt}

**Learning Boundaries:**
You are coaching students on these specific learning outcomes:
{self._format_learning_outcomes()}

**Dialogue Structure:**
Guide the conversation through these key sections:
{self._format_dialogue_sections()}

**Topic Guardrails:**
{guardrails}

**Off-Topic Handling:**
If a student goes off-topic, gently redirect them back to the learning objectives.
Use the configured handling style: {persona.off_topic_handling}
- strict: Immediately redirect with minimal acknowledgment
- moderate: Briefly acknowledge, then redirect
- flexible: Allow brief exploration if related, then redirect
"""

        return prompt

    def check_coverage(self, transcript: List) -> CoverageResult:
        """Check which dialogue sections have been covered in conversation.

        Args:
            transcript: List of Message objects from conversation

        Returns:
            CoverageResult: Analysis of section coverage
        """
        # Simple keyword matching for section detection
        # In production, this would use more sophisticated NLP

        covered = []
        key_points_discussed = []

        # Build combined text from transcript
        text = " ".join([msg.content.lower() for msg in transcript])

        # Check each section for keywords
        section_keywords = {
            "context_setting": ["context", "scenario", "situation", "background"],
            "skill_introduction": ["skill", "learn", "technique", "approach"],
            "guided_practice": ["practice", "try", "exercise", "apply"],
            "formative_assessment": ["assess", "evaluate", "check", "test"],
            "reflection": ["reflect", "think", "consider", "analyze"],
            "application": ["apply", "use", "implement", "transfer"],
            "wrap_up": ["summary", "conclusion", "wrap", "recap"],
            "next_steps": ["next", "forward", "continue", "advance"]
        }

        for section, keywords in section_keywords.items():
            if any(kw in text for kw in keywords):
                covered.append(section)

        # Check key points
        for point in self.key_points:
            if point.lower() in text:
                key_points_discussed.append(point)

        remaining = [s for s in self.DIALOGUE_SECTIONS if s not in covered]
        coverage = (len(covered) / len(self.DIALOGUE_SECTIONS)) * 100

        return CoverageResult(
            covered_sections=covered,
            remaining_sections=remaining,
            coverage_percent=coverage,
            key_points_addressed=key_points_discussed
        )

    def is_on_topic(self, message: str) -> bool:
        """Check if student message relates to learning outcomes.

        Args:
            message: Student message text

        Returns:
            bool: True if message is on-topic
        """
        message_lower = message.lower()

        # Check against learning outcomes
        for outcome in self.learning_outcomes:
            outcome_keywords = outcome.lower().split()
            # If any significant keyword from outcome appears, consider on-topic
            if any(kw in message_lower for kw in outcome_keywords if len(kw) > 4):
                return True

        # Check against key points
        for point in self.key_points:
            if any(kw in message_lower for kw in point.lower().split() if len(kw) > 4):
                return True

        return False

    def get_redirect_prompt(self, off_topic_message: str) -> str:
        """Generate gentle redirect prompt for off-topic message.

        Args:
            off_topic_message: The off-topic message from student

        Returns:
            str: Prompt to help AI redirect conversation
        """
        return f"""The student said: "{off_topic_message}"

This is off-topic. Generate a gentle redirect that:
1. Briefly acknowledges their point
2. Connects it (if possible) to our learning objectives
3. Redirects to one of the key topics we're covering

Learning objectives: {', '.join(self.learning_outcomes[:3])}
Key topics: {', '.join(self.key_points[:3])}
"""

    def _extract_key_points(self, dialogue_structure: dict) -> List[str]:
        """Extract key discussion points from dialogue structure.

        Args:
            dialogue_structure: Coach dialogue data

        Returns:
            List[str]: Key points to cover
        """
        key_points = []

        # Extract from learning objectives
        if "learning_objectives" in dialogue_structure:
            key_points.extend(dialogue_structure["learning_objectives"])

        # Extract from tasks
        if "tasks" in dialogue_structure:
            key_points.extend(dialogue_structure["tasks"])

        # Extract from evaluation criteria
        if "evaluation_criteria" in dialogue_structure:
            key_points.extend(dialogue_structure["evaluation_criteria"])

        return key_points

    def _format_learning_outcomes(self) -> str:
        """Format learning outcomes for system prompt."""
        return "\n".join([f"- {outcome}" for outcome in self.learning_outcomes])

    def _format_dialogue_sections(self) -> str:
        """Format dialogue sections for system prompt."""
        return "\n".join([f"{i+1}. {section.replace('_', ' ').title()}"
                         for i, section in enumerate(self.DIALOGUE_SECTIONS)])

    def _build_guardrails_section(self) -> str:
        """Build guardrails text for system prompt."""
        return f"""- Stay focused on the learning objectives listed above
- Guide students through the dialogue sections in sequence
- Address these key points: {', '.join(self.key_points[:5])}
- If conversation drifts off-topic, gently redirect
- Use Socratic questions to guide discovery
- Provide formative feedback, not just answers"""
