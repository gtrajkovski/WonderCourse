"""Interactive coach conversation engine package.

This package provides the conversation management, guardrails, and persona
functionality for AI-guided coach dialogues.
"""

from src.coach.conversation import ConversationManager, Message
from src.coach.guardrails import GuardrailEngine, CoverageResult
from src.coach.persona import CoachPersona, PersonaBuilder
from src.coach.evaluator import CoachEvaluator, EvaluationResult, SessionEvaluation
from src.coach.transcript import TranscriptStore, Transcript

__all__ = [
    "ConversationManager",
    "Message",
    "GuardrailEngine",
    "CoverageResult",
    "CoachPersona",
    "PersonaBuilder",
    "CoachEvaluator",
    "EvaluationResult",
    "SessionEvaluation",
    "TranscriptStore",
    "Transcript"
]
