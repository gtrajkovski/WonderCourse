"""Base parser infrastructure for content import.

This module provides the abstract base class and result dataclass for all parsers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Union


@dataclass
class ParseResult:
    """Result of parsing content from an external source.

    Attributes:
        content_type: Detected content type (blueprint, video_script, reading, quiz, etc.)
        content: Parsed content in normalized dictionary format
        metadata: Source metadata (word_count, format, detected_structure, etc.)
        warnings: Non-fatal parsing issues encountered during extraction
        provenance: Source tracking information (filename, import_time, original_format)
    """
    content_type: str
    content: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert ParseResult to dictionary for serialization."""
        return {
            'content_type': self.content_type,
            'content': self.content,
            'metadata': self.metadata,
            'warnings': self.warnings,
            'provenance': self.provenance
        }


class BaseParser(ABC):
    """Abstract base class for content parsers.

    All parsers must implement:
    - can_parse(): Format detection
    - parse(): Content extraction
    """

    @abstractmethod
    def can_parse(self, source: Union[str, bytes], filename: str = None) -> bool:
        """Detect if this parser can handle the given source.

        Args:
            source: Content to parse (string or bytes)
            filename: Optional filename for extension-based detection

        Returns:
            True if this parser can handle the source format
        """
        pass

    @abstractmethod
    def parse(self, source: Union[str, bytes], filename: str = None) -> ParseResult:
        """Parse content from source into structured format.

        Args:
            source: Content to parse (string or bytes)
            filename: Optional filename for provenance tracking

        Returns:
            ParseResult with extracted content, metadata, and warnings

        Raises:
            ValueError: If source cannot be parsed by this parser
        """
        pass
