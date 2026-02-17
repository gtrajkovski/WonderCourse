"""One-shot AI client for stateless batch generation tasks."""

from typing import Optional
import anthropic

from src.config import Config


def generate(
    system_prompt: str,
    user_prompt: str,
    max_tokens: Optional[int] = None,
    temperature: float = 0.3
) -> str:
    """Generate a one-shot response without maintaining state.

    Simple stateless wrapper around Anthropic API for batch generation tasks
    like generating demo code, slides, or other course assets.

    Args:
        system_prompt: System instructions for the AI
        user_prompt: The user's prompt
        max_tokens: Optional token limit (defaults to Config.MAX_TOKENS)
        temperature: Sampling temperature (0.0-1.0, default 0.3)

    Returns:
        The assistant's response text

    Raises:
        ValueError: If ANTHROPIC_API_KEY is not set
        anthropic.APIError: If API request fails
        anthropic.APIConnectionError: If connection to API fails
        anthropic.RateLimitError: If rate limit is exceeded
    """
    if not Config.ANTHROPIC_API_KEY:
        raise ValueError(
            "ANTHROPIC_API_KEY not set. Copy .env.example to .env and add your key."
        )

    client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)

    try:
        response = client.messages.create(
            model=Config.MODEL,
            max_tokens=max_tokens or Config.MAX_TOKENS,
            temperature=temperature,
            system=system_prompt,
            messages=[{
                "role": "user",
                "content": user_prompt
            }]
        )

        return response.content[0].text

    except Exception as e:
        raise
