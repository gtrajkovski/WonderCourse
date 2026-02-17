"""
Markdown parser for structured content import.
Converts Markdown syntax to structured reading/video_script format.
"""

import re
from typing import Union, List, Dict
from datetime import datetime, timezone
from .base_parser import BaseParser, ParseResult


class MarkdownParser(BaseParser):
    """Parser for Markdown content."""

    def can_parse(self, source: Union[str, bytes], filename: str = None) -> bool:
        """
        Detect if this is Markdown (has headers, lists, or emphasis).

        Args:
            source: Content to check
            filename: Optional filename

        Returns:
            True if contains Markdown syntax
        """
        if isinstance(source, bytes):
            try:
                source = source.decode('utf-8')
            except UnicodeDecodeError:
                return False

        if not source or not source.strip():
            return False

        # Check for Markdown headers
        if re.search(r'^#{1,6}\s+', source, re.MULTILINE):
            return True

        # Check for lists
        if re.search(r'^[\*\-\+]\s+', source, re.MULTILINE):
            return True

        # Check for emphasis (bold, italic, code)
        if re.search(r'\*\*[^*]+\*\*|__[^_]+__|`[^`]+`|\*[^*]+\*|_[^_]+_', source):
            return True

        # Check for links
        if re.search(r'\[([^\]]+)\]\(([^)]+)\)', source):
            return True

        return False

    def parse(self, source: Union[str, bytes], filename: str = None) -> ParseResult:
        """
        Parse Markdown into structured sections.

        Detects:
        - Headers (# ## ###)
        - Lists (- * +)
        - Code blocks (```)
        - Emphasis (**bold**, *italic*, `code`)
        - Links

        Args:
            source: Markdown content to parse
            filename: Optional filename for provenance

        Returns:
            ParseResult with structured content
        """
        if isinstance(source, bytes):
            source = source.decode('utf-8')

        # Extract structure
        sections = self._extract_sections(source)
        code_blocks = self._extract_code_blocks(source)
        links = self._extract_links(source)

        # Count words (excluding code blocks)
        text_without_code = re.sub(r'```[^`]*```', '', source)
        word_count = len(text_without_code.split())

        # Detect content type
        content_type = self._detect_content_type(sections, word_count)

        # Build content dictionary
        content = {
            'sections': sections,
            'code_blocks': code_blocks,
            'links': links,
            'raw_markdown': source  # Preserve original for reference
        }

        # Build metadata
        metadata = {
            'word_count': word_count,
            'format': 'markdown',
            'detected_structure': {
                'section_count': len(sections),
                'code_block_count': len(code_blocks),
                'link_count': len(links)
            }
        }

        # Build provenance
        provenance = {
            'filename': filename,
            'import_time': datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            'original_format': 'text/markdown'
        }

        warnings = []

        # Add warnings
        if not sections:
            warnings.append('No sections detected (no headers found)')

        if word_count < 100:
            warnings.append(f'Short content ({word_count} words) may not provide enough detail')

        return ParseResult(
            content_type=content_type,
            content=content,
            metadata=metadata,
            warnings=warnings,
            provenance=provenance
        )

    def _extract_sections(self, source: str) -> List[Dict[str, any]]:
        """
        Extract sections based on headers.

        Args:
            source: Markdown source

        Returns:
            List of sections with level, title, and content
        """
        sections = []
        lines = source.split('\n')

        current_section = None

        for line in lines:
            # Check for header
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if header_match:
                # Save previous section
                if current_section:
                    sections.append(current_section)

                # Start new section
                level = len(header_match.group(1))
                title = header_match.group(2).strip()
                current_section = {
                    'level': level,
                    'title': title,
                    'content': []
                }
            elif current_section is not None:
                current_section['content'].append(line)
            else:
                # Content before first header (introduction)
                if not sections and line.strip():
                    if current_section is None:
                        current_section = {
                            'level': 0,
                            'title': 'Introduction',
                            'content': []
                        }
                    current_section['content'].append(line)

        # Save final section
        if current_section:
            current_section['content'] = '\n'.join(current_section['content']).strip()
            sections.append(current_section)

        return sections

    def _extract_code_blocks(self, source: str) -> List[Dict[str, str]]:
        """
        Extract code blocks from Markdown.

        Args:
            source: Markdown source

        Returns:
            List of code blocks with language and content
        """
        code_blocks = []
        pattern = r'```(\w*)\n(.*?)```'

        for match in re.finditer(pattern, source, re.DOTALL):
            language = match.group(1) or 'text'
            code = match.group(2).strip()
            code_blocks.append({
                'language': language,
                'code': code
            })

        return code_blocks

    def _extract_links(self, source: str) -> List[Dict[str, str]]:
        """
        Extract links from Markdown.

        Args:
            source: Markdown source

        Returns:
            List of links with text and URL
        """
        links = []
        pattern = r'\[([^\]]+)\]\(([^)]+)\)'

        for match in re.finditer(pattern, source):
            text = match.group(1)
            url = match.group(2)
            links.append({
                'text': text,
                'url': url
            })

        return links

    def _detect_content_type(self, sections: List[Dict], word_count: int) -> str:
        """
        Detect likely content type based on structure.

        Args:
            sections: Extracted sections
            word_count: Total word count

        Returns:
            Detected content type string
        """
        # Video scripts have specific section patterns
        if sections:
            titles_lower = [s['title'].lower() for s in sections]
            video_keywords = ['hook', 'objective', 'summary', 'call to action']
            if any(keyword in ' '.join(titles_lower) for keyword in video_keywords):
                return 'video_script'

        # Readings are longer with multiple sections
        if len(sections) >= 3 and word_count > 500:
            return 'reading'

        # Default to reading
        return 'reading'
