"""AI-powered text suggestion engine for inline editing.

Provides multiple suggestion actions (improve, expand, simplify, rewrite, etc.)
with context-aware prompting using Claude API.
"""

from dataclasses import dataclass
from typing import Iterator, Optional, Dict, List
from anthropic import Anthropic
from src.config import Config
from src.editing.diff_generator import DiffGenerator, DiffResult


@dataclass
class Suggestion:
    """Result of AI suggestion generation.

    Attributes:
        original: Original text that was improved
        suggestion: AI-generated suggested text
        action: The action type that was applied
        diff: Diff visualization of changes
        explanation: Why this change was made
    """
    original: str
    suggestion: str
    action: str
    diff: DiffResult
    explanation: str


class SuggestionEngine:
    """Generate AI-powered text suggestions with multiple action types.

    Supports 10 action types:
    - improve: Enhance clarity and flow without changing meaning
    - expand: Add detail, examples, or elaboration
    - simplify: Reduce complexity, shorter sentences
    - rewrite: Complete rewrite maintaining meaning
    - fix_grammar: Fix grammatical errors only
    - make_academic: More formal, scholarly tone
    - make_conversational: Casual, friendly tone
    - summarize: Condense to key points
    - add_examples: Insert concrete examples
    - custom: Use context['prompt'] for custom instruction

    Context dict supports:
    - learning_outcomes: List[str] - for alignment
    - content_type: str - video_script, reading, etc.
    - bloom_level: str - target cognitive level
    - tone: str - tone preset
    - prompt: str - custom prompt for 'custom' action
    """

    # Action type prompts
    ACTION_PROMPTS = {
        'improve': """Enhance the clarity and flow of this text without changing its core meaning.
Focus on:
- Stronger word choices
- Better sentence structure
- Smoother transitions
- Eliminating redundancy

Avoid AI telltales like em-dashes, three-adjective lists, and overly parallel structures.""",

        'expand': """Add detail, examples, or elaboration to this text.
Focus on:
- Concrete examples that illustrate concepts
- Additional context or background
- Practical applications
- Supporting details

Keep the expansion natural and relevant.""",

        'simplify': """Simplify this text for easier understanding.
Focus on:
- Shorter sentences
- Simpler vocabulary
- Clearer structure
- Removing jargon where possible

Maintain the key information.""",

        'rewrite': """Completely rewrite this text while maintaining its core meaning and purpose.
Focus on:
- Fresh perspective and phrasing
- Different structure or approach
- Natural, human-written tone
- Preserving key information

Avoid the original phrasing patterns.""",

        'fix_grammar': """Fix grammatical errors in this text.
Focus on:
- Subject-verb agreement
- Verb tense consistency
- Pronoun usage
- Punctuation
- Spelling

Make minimal changes - only fix errors, don't restyle.""",

        'make_academic': """Transform this text into a more formal, scholarly tone.
Focus on:
- Formal vocabulary and structure
- Third-person perspective
- Objective, evidence-based language
- Academic conventions

Avoid overly casual expressions.""",

        'make_conversational': """Transform this text into a casual, friendly tone.
Focus on:
- Conversational vocabulary
- Personal pronouns (you, we)
- Active voice
- Natural speech patterns

Avoid overly formal or stiff language.""",

        'summarize': """Condense this text to its key points.
Focus on:
- Main ideas and conclusions
- Essential information only
- Concise expression
- Logical flow

Remove redundancy and minor details.""",

        'add_examples': """Add concrete, practical examples to illustrate the concepts in this text.
Focus on:
- Real-world scenarios
- Specific instances
- Practical applications
- Relatable situations

Examples should clarify and enhance understanding.""",

        'custom': """Follow the custom instruction provided below."""
    }

    def __init__(self, model: str = None):
        """Initialize suggestion engine with Anthropic client.

        Args:
            model: Optional model override. Defaults to Config.MODEL.
        """
        if not Config.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not set in environment")

        self.client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        self.model = model or Config.MODEL
        self.diff_generator = DiffGenerator()

    def suggest(
        self,
        text: str,
        action: str,
        context: Optional[Dict] = None
    ) -> Suggestion:
        """Generate a suggestion for the given text and action.

        Args:
            text: The text to improve/modify
            action: Action type (improve, expand, simplify, etc.)
            context: Optional context dict with learning outcomes, content type, etc.

        Returns:
            Suggestion with original text, suggested text, diff, and explanation

        Raises:
            ValueError: If action type is invalid or custom action without prompt
            anthropic.APIError: If API request fails
        """
        if action not in self.ACTION_PROMPTS:
            raise ValueError(f"Invalid action type: {action}. Must be one of {list(self.ACTION_PROMPTS.keys())}")

        context = context or {}

        # Validate custom action has prompt
        if action == 'custom' and 'prompt' not in context:
            raise ValueError("Custom action requires 'prompt' in context")

        # Build system prompt
        system_prompt = self._build_system_prompt(action, context)

        # Build user prompt
        user_prompt = self._build_user_prompt(text, action, context)

        # Call Claude API
        response = self.client.messages.create(
            model=self.model,
            max_tokens=Config.MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        # Extract response text
        full_response = response.content[0].text.strip()

        # Parse response (expecting format: SUGGESTION:\n...\n\nEXPLANATION:\n...)
        suggestion_text, explanation = self._parse_response(full_response)

        # Generate diff
        diff = self.diff_generator.generate_diff(text, suggestion_text)

        return Suggestion(
            original=text,
            suggestion=suggestion_text,
            action=action,
            diff=diff,
            explanation=explanation
        )

    def stream_suggest(
        self,
        text: str,
        action: str,
        context: Optional[Dict] = None
    ) -> Iterator[str]:
        """Stream suggestion generation in real-time.

        Args:
            text: The text to improve/modify
            action: Action type (improve, expand, simplify, etc.)
            context: Optional context dict

        Yields:
            Text chunks as they arrive from the API

        Raises:
            ValueError: If action type is invalid or custom action without prompt
            anthropic.APIError: If API request fails
        """
        if action not in self.ACTION_PROMPTS:
            raise ValueError(f"Invalid action type: {action}")

        context = context or {}

        # Validate custom action has prompt
        if action == 'custom' and 'prompt' not in context:
            raise ValueError("Custom action requires 'prompt' in context")

        # Build prompts
        system_prompt = self._build_system_prompt(action, context)
        user_prompt = self._build_user_prompt(text, action, context)

        # Stream response
        with self.client.messages.stream(
            model=self.model,
            max_tokens=Config.MAX_TOKENS,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        ) as stream:
            for text_chunk in stream.text_stream:
                yield text_chunk

    def _build_system_prompt(self, action: str, context: Dict) -> str:
        """Build system prompt with action instructions and context.

        Args:
            action: Action type
            context: Context dict

        Returns:
            System prompt string
        """
        prompt = "You are an expert content editor specializing in educational material.\n\n"

        # Add action-specific instructions
        if action == 'custom' and 'prompt' in context:
            prompt += f"{context['prompt']}\n\n"
        else:
            prompt += f"{self.ACTION_PROMPTS[action]}\n\n"

        # Add context-specific instructions
        if context.get('content_type'):
            prompt += f"Content type: {context['content_type']}\n"

        if context.get('learning_outcomes'):
            outcomes = '\n'.join(f"- {lo}" for lo in context['learning_outcomes'])
            prompt += f"\nLearning outcomes to align with:\n{outcomes}\n"

        if context.get('bloom_level'):
            prompt += f"\nTarget Bloom's taxonomy level: {context['bloom_level']}\n"

        if context.get('tone'):
            prompt += f"\nDesired tone: {context['tone']}\n"

        prompt += "\nProvide your response in this exact format:\n"
        prompt += "SUGGESTION:\n[your suggested text here]\n\n"
        prompt += "EXPLANATION:\n[brief explanation of what you changed and why]"

        return prompt

    def _build_user_prompt(self, text: str, action: str, context: Dict) -> str:
        """Build user prompt with the text to modify.

        Args:
            text: Text to modify
            action: Action type
            context: Context dict

        Returns:
            User prompt string
        """
        return f"Please {action} the following text:\n\n{text}"

    def _parse_response(self, response: str) -> tuple[str, str]:
        """Parse Claude response into suggestion text and explanation.

        Args:
            response: Full response from Claude

        Returns:
            Tuple of (suggestion_text, explanation)
        """
        # Look for SUGGESTION: and EXPLANATION: markers
        if 'SUGGESTION:' in response and 'EXPLANATION:' in response:
            parts = response.split('EXPLANATION:', 1)
            suggestion_part = parts[0].replace('SUGGESTION:', '').strip()
            explanation = parts[1].strip()
            return suggestion_part, explanation

        # Fallback: if format not followed, treat entire response as suggestion
        return response, "No explanation provided"

    def get_available_actions(self) -> List[Dict[str, str]]:
        """Get list of available action types with descriptions.

        Returns:
            List of dicts with 'action' and 'description' keys
        """
        return [
            {'action': 'improve', 'description': 'Enhance clarity and flow'},
            {'action': 'expand', 'description': 'Add detail and examples'},
            {'action': 'simplify', 'description': 'Reduce complexity'},
            {'action': 'rewrite', 'description': 'Complete rewrite'},
            {'action': 'fix_grammar', 'description': 'Fix grammatical errors'},
            {'action': 'make_academic', 'description': 'Formal, scholarly tone'},
            {'action': 'make_conversational', 'description': 'Casual, friendly tone'},
            {'action': 'summarize', 'description': 'Condense to key points'},
            {'action': 'add_examples', 'description': 'Insert concrete examples'},
            {'action': 'custom', 'description': 'Custom instruction'}
        ]
