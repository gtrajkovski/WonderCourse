"""Context-aware autocomplete engine for inline text editing.

Provides ghost text suggestions based on course context and learning outcomes
using Claude Haiku for fast response times.
"""

from dataclasses import dataclass
from typing import Optional, Dict, List
from anthropic import Anthropic
from src.config import Config


@dataclass
class CompletionResult:
    """Result of autocomplete generation.

    Attributes:
        suggestion: The ghost text to display
        confidence: Confidence score (0.0 to 1.0)
        full_text: Original text + suggestion
    """
    suggestion: str
    confidence: float
    full_text: str


class AutocompleteEngine:
    """Generate context-aware autocomplete suggestions for text editing.

    Uses Claude Haiku for fast (<500ms target) response times with low token
    limits. Context from learning outcomes and course metadata affects suggestions.

    Example:
        engine = AutocompleteEngine()
        context = {
            "learning_outcomes": ["Explain REST API design"],
            "activity_title": "Introduction to APIs",
            "content_type": "reading"
        }
        result = engine.complete("REST APIs use HTTP verbs like", context)
        # result.suggestion = "GET, POST, PUT, and DELETE to perform CRUD operations."
    """

    def __init__(self, model: str = "claude-3-5-haiku-20241022"):
        """Initialize autocomplete engine with Haiku model.

        Args:
            model: Claude model ID (default: Haiku for speed per RESEARCH.md)
        """
        self.model = model
        try:
            self.client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)
            self.enabled = True
        except Exception:
            self.client = None
            self.enabled = False

    def complete(
        self,
        text: str,
        context: Optional[Dict] = None,
        max_tokens: int = 50
    ) -> CompletionResult:
        """Generate autocomplete suggestion for text.

        Args:
            text: Partial text to complete
            context: Optional context dict with:
                - learning_outcomes: List[str] - Course learning outcomes
                - activity_title: str - Current activity title
                - content_type: str - Type of content being edited
                - course_title: str - Course title
                - existing_content: str - Preceding paragraphs for context
            max_tokens: Maximum tokens to generate (default: 50 for speed)

        Returns:
            CompletionResult with suggestion, confidence, and full text

        Raises:
            RuntimeError: If AI client not initialized
            Exception: If API call fails
        """
        if not self.enabled:
            raise RuntimeError("Autocomplete engine not initialized (missing API key)")

        context = context or {}

        # Build system prompt with context awareness
        system_prompt = self._build_system_prompt(context)

        # Build user prompt
        user_prompt = self._build_user_prompt(text, context)

        # Call Claude API with low max_tokens for speed
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=0.7,  # Some creativity for natural suggestions
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )

            # Extract suggestion from response
            suggestion = response.content[0].text.strip()

            # Calculate confidence (higher for longer text that provides context)
            confidence = min(0.5 + (len(text) / 500), 0.95)

            # Combine original and suggestion
            full_text = text + " " + suggestion if not text.endswith(" ") else text + suggestion

            return CompletionResult(
                suggestion=suggestion,
                confidence=confidence,
                full_text=full_text
            )

        except Exception as e:
            raise Exception(f"Autocomplete API call failed: {str(e)}")

    def get_sentence_completion(
        self,
        text: str,
        context: Optional[Dict] = None
    ) -> str:
        """Convenience method to get just the suggestion text.

        Args:
            text: Partial text to complete
            context: Optional context dict

        Returns:
            Suggestion text only
        """
        result = self.complete(text, context)
        return result.suggestion

    def _build_system_prompt(self, context: Dict) -> str:
        """Build system prompt with context awareness.

        Args:
            context: Context dict with learning outcomes, content type, etc.

        Returns:
            System prompt string
        """
        prompt_parts = [
            "You are an intelligent autocomplete assistant for educational content.",
            "Complete the given sentence in a way that:",
            "1. Aligns with the learning outcomes",
            "2. Matches the content type and tone",
            "3. Keeps completion short (1-2 sentences maximum)",
            "4. Sounds natural and human-written",
            "",
            "IMPORTANT:",
            "- Only provide the completion text, not the original text",
            "- Do not add unnecessary punctuation at the start",
            "- Keep it concise and relevant"
        ]

        # Add learning outcomes if provided
        if context.get("learning_outcomes"):
            outcomes = context["learning_outcomes"]
            outcomes_text = "\n".join(f"  - {outcome}" for outcome in outcomes)
            prompt_parts.extend([
                "",
                "Learning Outcomes:",
                outcomes_text
            ])

        # Add content type context
        if context.get("content_type"):
            prompt_parts.extend([
                "",
                f"Content Type: {context['content_type']}"
            ])

        return "\n".join(prompt_parts)

    def _build_user_prompt(self, text: str, context: Dict) -> str:
        """Build user prompt with text and context.

        Args:
            text: Partial text to complete
            context: Context dict

        Returns:
            User prompt string
        """
        prompt_parts = []

        # Add existing content for context if provided
        if context.get("existing_content"):
            prompt_parts.extend([
                "Previous content:",
                context["existing_content"],
                ""
            ])

        # Add activity context if provided
        if context.get("activity_title"):
            prompt_parts.append(f"Activity: {context['activity_title']}")

        if context.get("course_title"):
            prompt_parts.append(f"Course: {context['course_title']}")

        if prompt_parts:
            prompt_parts.append("")  # Blank line before text

        # Add the text to complete
        prompt_parts.extend([
            "Complete this sentence:",
            f'"{text}"',
            "",
            "Completion:"
        ])

        return "\n".join(prompt_parts)
