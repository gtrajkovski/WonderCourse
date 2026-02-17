"""Conversation management with token budget tracking.

Manages multi-turn coach conversations with automatic history compaction
when approaching token limits.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime, timezone
import uuid


@dataclass
class Message:
    """Single message in a conversation.

    Attributes:
        role: Message role ("user" | "assistant" | "system")
        content: Message text content
        timestamp: ISO 8601 timestamp when message was created
        token_count: Estimated token count for this message
    """

    role: str
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    token_count: int = 0

    def to_dict(self) -> dict:
        """Serialize message to dictionary."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "token_count": self.token_count
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        """Deserialize message from dictionary."""
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            token_count=data.get("token_count", 0)
        )


class ConversationManager:
    """Manages conversation history with token budget tracking.

    Automatically compacts history when approaching token limits by:
    - Keeping recent messages (last 5)
    - Summarizing older messages into context summaries
    - Maintaining full transcript for instructor review

    Token counting uses simple word-based estimation (words * 1.3) which
    approximates tokenization without requiring external libraries.
    """

    def __init__(self, max_tokens: int = 8000, session_id: Optional[str] = None):
        """Initialize conversation manager.

        Args:
            max_tokens: Maximum token budget before compaction (default 8000)
            session_id: Optional session identifier for persistence
        """
        self.max_tokens = max_tokens
        self.session_id = session_id or f"session_{uuid.uuid4().hex[:8]}"
        self.messages: List[Message] = []
        self.summaries: List[str] = []
        self._cumulative_tokens = 0

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation.

        Automatically counts tokens and triggers compaction if budget
        approaches limit (80% capacity).

        Args:
            role: Message role ("user" | "assistant" | "system")
            content: Message text content
        """
        # Count tokens using simple word-based estimation
        token_count = self._estimate_tokens(content)

        # Create message
        message = Message(
            role=role,
            content=content,
            token_count=token_count
        )

        self.messages.append(message)
        self._cumulative_tokens += token_count

        # Check if compaction needed (80% capacity)
        if self._cumulative_tokens > self.max_tokens * 0.8:
            self.compact_history()

    def get_context(self) -> List[dict]:
        """Get conversation context for Claude API.

        Returns messages in Claude API format with summaries prepended
        as system context if available.

        Returns:
            List[dict]: Messages in [{"role": str, "content": str}] format
        """
        context = []

        # Add summaries as system context if available
        if self.summaries:
            summary_text = "\n\n".join([
                f"**Previous conversation summary:**\n{summary}"
                for summary in self.summaries
            ])
            context.append({
                "role": "system",
                "content": summary_text
            })

        # Add current messages
        for msg in self.messages:
            context.append({
                "role": msg.role,
                "content": msg.content
            })

        return context

    def compact_history(self) -> None:
        """Compact conversation history to stay within token budget.

        Keeps the most recent 5 messages and creates a summary of older
        messages. Summary is stored for later inclusion in context.

        Note: In production, this would use Claude API to generate summaries.
        For now, we create a simple text summary of the older messages.
        """
        if len(self.messages) <= 5:
            return  # Nothing to compact

        # Keep most recent 5 messages
        recent = self.messages[-5:]
        older = self.messages[:-5]

        # Create summary of older messages
        # TODO: Use Claude API to generate intelligent summary
        summary_parts = []
        for msg in older:
            summary_parts.append(f"{msg.role}: {msg.content[:100]}...")

        summary = "\n".join(summary_parts)
        self.summaries.append(summary)

        # Reset messages to recent only
        self.messages = recent

        # Recalculate token count
        self._cumulative_tokens = sum(msg.token_count for msg in self.messages)

    def get_full_transcript(self) -> List[Message]:
        """Get full conversation transcript including summarized messages.

        Returns:
            List[Message]: All messages in chronological order
        """
        # In production, this would reconstruct from stored transcript
        # For now, return current messages (summaries are separate)
        return self.messages.copy()

    def save_transcript(self) -> dict:
        """Export full transcript for storage.

        Returns:
            dict: Serialized transcript with metadata
        """
        return {
            "session_id": self.session_id,
            "max_tokens": self.max_tokens,
            "messages": [msg.to_dict() for msg in self.messages],
            "summaries": self.summaries,
            "cumulative_tokens": self._cumulative_tokens,
            "saved_at": datetime.now(timezone.utc).isoformat()
        }

    def load_transcript(self, data: dict) -> None:
        """Restore conversation from saved state.

        Args:
            data: Serialized transcript from save_transcript()
        """
        self.session_id = data.get("session_id", self.session_id)
        self.max_tokens = data.get("max_tokens", self.max_tokens)
        self.messages = [Message.from_dict(msg) for msg in data.get("messages", [])]
        self.summaries = data.get("summaries", [])
        self._cumulative_tokens = data.get("cumulative_tokens", 0)

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count from text.

        Uses simple word-based estimation: word_count * 1.3
        This approximates tokenization without external dependencies.

        Args:
            text: Text to estimate tokens for

        Returns:
            int: Estimated token count
        """
        word_count = len(text.split())
        return int(word_count * 1.3)
