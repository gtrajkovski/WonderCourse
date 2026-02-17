"""
Plain text parser for content import.
Detects structure from text formatting and estimates content type.
"""

import re
from typing import Union
from datetime import datetime, timezone
from .base_parser import BaseParser, ParseResult


class TextParser(BaseParser):
    """Parser for plain text content."""

    # Keywords indicating higher Bloom's levels
    HIGHER_BLOOM_KEYWORDS = {
        'analyze', 'evaluate', 'create', 'design', 'develop',
        'compare', 'contrast', 'critique', 'synthesize', 'propose'
    }

    def can_parse(self, source: Union[str, bytes], filename: str = None) -> bool:
        """
        Detect if this is plain text (no JSON/Markdown markers).

        Args:
            source: Content to check
            filename: Optional filename

        Returns:
            True if plain text without special markers
        """
        if isinstance(source, bytes):
            try:
                source = source.decode('utf-8')
            except UnicodeDecodeError:
                return False

        if not source or not source.strip():
            return False

        # Reject if it looks like JSON
        stripped = source.strip()
        if (stripped.startswith('{') or stripped.startswith('[')):
            return False

        # Reject if it has Markdown headers
        if re.search(r'^#{1,6}\s+', source, re.MULTILINE):
            return False

        # Reject if it has strong Markdown emphasis patterns
        if re.search(r'\*\*[^*]+\*\*|__[^_]+__|`[^`]+`', source):
            return False

        return True

    def parse(self, source: Union[str, bytes], filename: str = None) -> ParseResult:
        """
        Parse plain text into structured content.

        Detects:
        - Headings (lines ending with :)
        - Paragraphs (blocks of text)
        - Lists (lines starting with - or *)
        - Bloom's level based on keywords

        Args:
            source: Text content to parse
            filename: Optional filename for provenance

        Returns:
            ParseResult with detected structure
        """
        if isinstance(source, bytes):
            source = source.decode('utf-8')

        lines = source.split('\n')

        # Detect structure
        headings = []
        paragraphs = []
        lists = []
        current_paragraph = []

        for line in lines:
            stripped = line.strip()

            if not stripped:
                if current_paragraph:
                    paragraphs.append(' '.join(current_paragraph))
                    current_paragraph = []
                continue

            # Check for heading (ends with :)
            if stripped.endswith(':') and len(stripped) > 1:
                if current_paragraph:
                    paragraphs.append(' '.join(current_paragraph))
                    current_paragraph = []
                headings.append(stripped[:-1])
            # Check for list item
            elif stripped.startswith('-') or stripped.startswith('*'):
                if current_paragraph:
                    paragraphs.append(' '.join(current_paragraph))
                    current_paragraph = []
                lists.append(stripped[1:].strip())
            else:
                current_paragraph.append(stripped)

        # Add final paragraph if exists
        if current_paragraph:
            paragraphs.append(' '.join(current_paragraph))

        # Count words
        word_count = len(source.split())

        # Estimate Bloom's level based on keywords
        text_lower = source.lower()
        has_higher_bloom = any(keyword in text_lower for keyword in self.HIGHER_BLOOM_KEYWORDS)
        estimated_bloom = 'apply' if not has_higher_bloom else 'analyze'

        # Detect content type based on structure
        content_type = self._detect_content_type(headings, paragraphs, lists, word_count)

        # Build content dictionary
        content = {
            'raw_text': source,
            'headings': headings,
            'paragraphs': paragraphs,
            'lists': lists
        }

        # Build metadata
        metadata = {
            'word_count': word_count,
            'format': 'text',
            'detected_structure': {
                'heading_count': len(headings),
                'paragraph_count': len(paragraphs),
                'list_count': len(lists)
            },
            'estimated_bloom_level': estimated_bloom
        }

        # Build provenance
        provenance = {
            'filename': filename,
            'import_time': datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            'original_format': 'text/plain'
        }

        warnings = []

        # Add warnings for structure issues
        if not headings and not lists:
            warnings.append('No clear structure detected (no headings or lists)')

        if word_count < 50:
            warnings.append(f'Short content ({word_count} words) may not provide enough detail')

        return ParseResult(
            content_type=content_type,
            content=content,
            metadata=metadata,
            warnings=warnings,
            provenance=provenance
        )

    def _detect_content_type(self, headings: list, paragraphs: list, lists: list, word_count: int) -> str:
        """
        Detect likely content type based on structure.

        Args:
            headings: Detected headings
            paragraphs: Detected paragraphs
            lists: Detected list items
            word_count: Total word count

        Returns:
            Detected content type string
        """
        # Video scripts tend to be shorter with structured sections
        if headings and 300 <= word_count <= 800:
            return 'video_script'

        # Readings are longer with multiple paragraphs
        if len(paragraphs) >= 3 and word_count > 500:
            return 'reading'

        # Lists suggest quiz or checklist
        if lists and len(lists) >= 3:
            if word_count < 200:
                return 'quiz'
            return 'checklist'

        # Default to reading
        return 'reading'
