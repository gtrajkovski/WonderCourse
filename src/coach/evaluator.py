"""Coach evaluation engine with rubric-based assessment.

Evaluates student responses against 3-level rubric criteria using Claude AI
to provide formative feedback and track learning progress.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from anthropic import Anthropic
from src.config import Config


@dataclass
class EvaluationResult:
    """Result of evaluating a single student response.

    Attributes:
        level: Performance level ("developing" | "proficient" | "exemplary")
        score: Numeric score (1-3)
        criteria_met: List of evaluation criteria that were satisfied
        criteria_missing: List of criteria that were not satisfied
        feedback: Detailed feedback on the response
        strengths: Specific strengths identified in the response
        areas_for_improvement: Specific areas needing improvement
    """

    level: str
    score: int
    criteria_met: List[str]
    criteria_missing: List[str]
    feedback: str
    strengths: List[str]
    areas_for_improvement: List[str]

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "level": self.level,
            "score": self.score,
            "criteria_met": self.criteria_met,
            "criteria_missing": self.criteria_missing,
            "feedback": self.feedback,
            "strengths": self.strengths,
            "areas_for_improvement": self.areas_for_improvement
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EvaluationResult":
        """Deserialize from dictionary."""
        return cls(
            level=data["level"],
            score=data["score"],
            criteria_met=data["criteria_met"],
            criteria_missing=data["criteria_missing"],
            feedback=data["feedback"],
            strengths=data["strengths"],
            areas_for_improvement=data["areas_for_improvement"]
        )


@dataclass
class SessionEvaluation:
    """Overall evaluation of a complete coaching session.

    Attributes:
        overall_level: Overall performance level across session
        progress_trajectory: Learning trajectory ("improving" | "consistent" | "struggling")
        key_insights: Main learning insights from the session
        recommendations: Recommendations for continued learning
        time_spent: Total session duration in seconds
        turns_count: Number of conversation turns
    """

    overall_level: str
    progress_trajectory: str
    key_insights: List[str]
    recommendations: List[str]
    time_spent: int
    turns_count: int

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "overall_level": self.overall_level,
            "progress_trajectory": self.progress_trajectory,
            "key_insights": self.key_insights,
            "recommendations": self.recommendations,
            "time_spent": self.time_spent,
            "turns_count": self.turns_count
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SessionEvaluation":
        """Deserialize from dictionary."""
        return cls(
            overall_level=data["overall_level"],
            progress_trajectory=data["progress_trajectory"],
            key_insights=data["key_insights"],
            recommendations=data["recommendations"],
            time_spent=data["time_spent"],
            turns_count=data["turns_count"]
        )


class CoachEvaluator:
    """Evaluates student responses against coaching rubric criteria.

    Uses Claude AI to assess responses against 3-level rubric:
    - developing (1): Basic understanding, needs guidance
    - proficient (2): Solid understanding, applies concepts
    - exemplary (3): Deep understanding, extends concepts
    """

    def __init__(self, evaluation_criteria: List[str]):
        """Initialize evaluator with coaching rubric criteria.

        Args:
            evaluation_criteria: List of criteria from CoachSchema
        """
        self.evaluation_criteria = evaluation_criteria
        self.client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        self.model = Config.MODEL

    def evaluate_response(
        self,
        student_response: str,
        context: dict
    ) -> EvaluationResult:
        """Evaluate a single student response against rubric.

        Args:
            student_response: Student's response text
            context: Context dict with keys:
                - scenario: The coaching scenario
                - tasks: List of coaching tasks
                - conversation_history: Previous messages

        Returns:
            EvaluationResult with level, score, and feedback
        """
        # Build evaluation prompt
        prompt = self._build_evaluation_prompt(student_response, context)

        # Call Claude to evaluate
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse response text
            response_text = response.content[0].text

            # Extract evaluation components
            return self._parse_evaluation(response_text)

        except Exception as e:
            # Return default evaluation on error
            return EvaluationResult(
                level="developing",
                score=1,
                criteria_met=[],
                criteria_missing=self.evaluation_criteria,
                feedback=f"Unable to evaluate response: {str(e)}",
                strengths=[],
                areas_for_improvement=["Please try again"]
            )

    def evaluate_session(
        self,
        transcript: List,  # List[Message]
        started_at: str,
        ended_at: str
    ) -> SessionEvaluation:
        """Evaluate overall session performance.

        Args:
            transcript: List of Message objects from conversation
            started_at: ISO timestamp when session started
            ended_at: ISO timestamp when session ended

        Returns:
            SessionEvaluation with overall assessment
        """
        from datetime import datetime

        # Calculate time spent
        start_time = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(ended_at.replace('Z', '+00:00'))
        time_spent = int((end_time - start_time).total_seconds())

        # Count turns (user messages only)
        turns_count = sum(1 for msg in transcript if msg.role == "user")

        # Build session evaluation prompt
        prompt = self._build_session_evaluation_prompt(transcript)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text

            # Parse session evaluation
            return self._parse_session_evaluation(
                response_text,
                time_spent,
                turns_count
            )

        except Exception as e:
            # Return default evaluation on error
            return SessionEvaluation(
                overall_level="developing",
                progress_trajectory="consistent",
                key_insights=["Session completed"],
                recommendations=["Continue practicing"],
                time_spent=time_spent,
                turns_count=turns_count
            )

    def generate_summary(
        self,
        transcript: List,  # List[Message]
        evaluation: SessionEvaluation
    ) -> str:
        """Generate natural language summary of session.

        Args:
            transcript: List of Message objects from conversation
            evaluation: SessionEvaluation for the session

        Returns:
            Natural language summary text
        """
        # Build summary prompt
        prompt = f"""Generate a natural language summary of this coaching session.

Evaluation:
- Overall level: {evaluation.overall_level}
- Progress: {evaluation.progress_trajectory}
- Turns: {evaluation.turns_count}
- Duration: {evaluation.time_spent} seconds

Key insights:
{chr(10).join(f"- {insight}" for insight in evaluation.key_insights)}

Recommendations:
{chr(10).join(f"- {rec}" for rec in evaluation.recommendations)}

Create a 2-3 paragraph summary that:
1. Describes the student's engagement and performance
2. Highlights key learning moments
3. Provides encouraging next steps

Write in a supportive, educational tone."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}]
            )

            return response.content[0].text.strip()

        except Exception as e:
            # Return simple summary on error
            return f"Session completed with {evaluation.turns_count} turns. Overall performance: {evaluation.overall_level}."

    def _build_evaluation_prompt(
        self,
        student_response: str,
        context: dict
    ) -> str:
        """Build prompt for evaluating single response."""
        criteria_text = "\n".join(
            f"{i+1}. {criterion}"
            for i, criterion in enumerate(self.evaluation_criteria)
        )

        return f"""Evaluate this student response against the coaching rubric.

Scenario: {context.get('scenario', 'N/A')}

Evaluation Criteria:
{criteria_text}

Student Response:
{student_response}

Assess the response using this 3-level rubric:
- developing (1): Basic understanding, needs guidance
- proficient (2): Solid understanding, applies concepts
- exemplary (3): Deep understanding, extends concepts

Provide your evaluation in this format:

LEVEL: [developing|proficient|exemplary]
SCORE: [1|2|3]

CRITERIA MET:
- [criterion that was satisfied]
- [criterion that was satisfied]

CRITERIA MISSING:
- [criterion not satisfied]
- [criterion not satisfied]

STRENGTHS:
- [specific strength]
- [specific strength]

AREAS FOR IMPROVEMENT:
- [specific area]
- [specific area]

FEEDBACK:
[2-3 sentences of formative feedback]"""

    def _build_session_evaluation_prompt(self, transcript: List) -> str:
        """Build prompt for evaluating entire session."""
        # Format conversation for evaluation
        conversation_text = "\n\n".join([
            f"{msg.role.upper()}: {msg.content}"
            for msg in transcript
        ])

        criteria_text = "\n".join(
            f"{i+1}. {criterion}"
            for i, criterion in enumerate(self.evaluation_criteria)
        )

        return f"""Evaluate this complete coaching session.

Evaluation Criteria:
{criteria_text}

Conversation:
{conversation_text}

Assess the overall session performance:

1. Overall level (developing/proficient/exemplary)
2. Progress trajectory (improving/consistent/struggling)
3. Key insights (2-4 main learning points)
4. Recommendations (2-4 next steps)

Provide evaluation in this format:

OVERALL LEVEL: [developing|proficient|exemplary]

PROGRESS TRAJECTORY: [improving|consistent|struggling]

KEY INSIGHTS:
- [insight 1]
- [insight 2]
- [insight 3]

RECOMMENDATIONS:
- [recommendation 1]
- [recommendation 2]
- [recommendation 3]"""

    def _parse_evaluation(self, response_text: str) -> EvaluationResult:
        """Parse Claude response into EvaluationResult."""
        lines = response_text.strip().split("\n")

        level = "developing"
        score = 1
        criteria_met = []
        criteria_missing = []
        strengths = []
        areas_for_improvement = []
        feedback = ""

        current_section = None

        for line in lines:
            line = line.strip()

            if line.startswith("LEVEL:"):
                level = line.split(":", 1)[1].strip().lower()
            elif line.startswith("SCORE:"):
                try:
                    score = int(line.split(":", 1)[1].strip())
                except ValueError:
                    score = 1
            elif line.startswith("CRITERIA MET:"):
                current_section = "criteria_met"
            elif line.startswith("CRITERIA MISSING:"):
                current_section = "criteria_missing"
            elif line.startswith("STRENGTHS:"):
                current_section = "strengths"
            elif line.startswith("AREAS FOR IMPROVEMENT:"):
                current_section = "areas"
            elif line.startswith("FEEDBACK:"):
                current_section = "feedback"
            elif line.startswith("-") and current_section:
                item = line[1:].strip()
                if current_section == "criteria_met":
                    criteria_met.append(item)
                elif current_section == "criteria_missing":
                    criteria_missing.append(item)
                elif current_section == "strengths":
                    strengths.append(item)
                elif current_section == "areas":
                    areas_for_improvement.append(item)
            elif current_section == "feedback" and line:
                feedback += line + " "

        return EvaluationResult(
            level=level,
            score=score,
            criteria_met=criteria_met,
            criteria_missing=criteria_missing,
            feedback=feedback.strip(),
            strengths=strengths,
            areas_for_improvement=areas_for_improvement
        )

    def _parse_session_evaluation(
        self,
        response_text: str,
        time_spent: int,
        turns_count: int
    ) -> SessionEvaluation:
        """Parse Claude response into SessionEvaluation."""
        lines = response_text.strip().split("\n")

        overall_level = "developing"
        progress_trajectory = "consistent"
        key_insights = []
        recommendations = []

        current_section = None

        for line in lines:
            line = line.strip()

            if line.startswith("OVERALL LEVEL:"):
                overall_level = line.split(":", 1)[1].strip().lower()
            elif line.startswith("PROGRESS TRAJECTORY:"):
                progress_trajectory = line.split(":", 1)[1].strip().lower()
            elif line.startswith("KEY INSIGHTS:"):
                current_section = "insights"
            elif line.startswith("RECOMMENDATIONS:"):
                current_section = "recommendations"
            elif line.startswith("-") and current_section:
                item = line[1:].strip()
                if current_section == "insights":
                    key_insights.append(item)
                elif current_section == "recommendations":
                    recommendations.append(item)

        return SessionEvaluation(
            overall_level=overall_level,
            progress_trajectory=progress_trajectory,
            key_insights=key_insights,
            recommendations=recommendations,
            time_spent=time_spent,
            turns_count=turns_count
        )
