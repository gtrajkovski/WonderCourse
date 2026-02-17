"""HTML parser for content import.

Uses BeautifulSoup4 for parsing and bleach for sanitization.
"""

from datetime import datetime
from typing import Union

try:
    from bs4 import BeautifulSoup
    import bleach
    HTML_AVAILABLE = True
except ImportError:
    HTML_AVAILABLE = False

from .base_parser import BaseParser, ParseResult


class HTMLParser(BaseParser):
    """Parser for HTML content.

    Sanitizes HTML and extracts clean structured content.
    Removes scripts, styles, and unsafe tags.
    """

    # Allowed HTML tags after sanitization
    ALLOWED_TAGS = [
        'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li',
        'strong', 'em', 'a', 'br',
        'table', 'tr', 'td', 'th', 'thead', 'tbody'
    ]

    ALLOWED_ATTRS = {
        'a': ['href', 'title'],
        '*': ['id', 'class']
    }

    def can_parse(self, source: Union[str, bytes], filename: str = None) -> bool:
        """Detect if source is HTML.

        Args:
            source: HTML string or bytes
            filename: Optional filename for extension checking

        Returns:
            True if source appears to be HTML
        """
        if not HTML_AVAILABLE:
            return False

        # Check filename extension
        if filename and filename.lower().endswith(('.html', '.htm')):
            return True

        # Check for HTML tags
        if isinstance(source, bytes):
            source = source.decode('utf-8', errors='ignore')

        if isinstance(source, str):
            source_lower = source.lower()
            return '<' in source and '>' in source and (
                '<html' in source_lower or
                '<body' in source_lower or
                '<div' in source_lower or
                '<p' in source_lower or
                '<h1' in source_lower
            )

        return False

    def parse(self, source: Union[str, bytes], filename: str = None) -> ParseResult:
        """Parse HTML content into structured format.

        Args:
            source: HTML string or bytes
            filename: Optional filename for provenance

        Returns:
            ParseResult with sanitized content

        Raises:
            ValueError: If source cannot be parsed as HTML
        """
        if not HTML_AVAILABLE:
            raise ValueError("beautifulsoup4 and bleach libraries not installed")

        if not self.can_parse(source, filename):
            raise ValueError("Source is not valid HTML")

        # Convert bytes to string
        if isinstance(source, bytes):
            html_str = source.decode('utf-8', errors='ignore')
        else:
            html_str = source

        warnings = []

        # Parse with BeautifulSoup
        soup = BeautifulSoup(html_str, 'html.parser')

        # Remove script and style tags
        for tag in soup(['script', 'style', 'meta', 'link']):
            tag.decompose()

        # Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, str) and text.strip().startswith('<!--')):
            comment.extract()

        # Sanitize with bleach
        cleaned_html = bleach.clean(
            str(soup),
            tags=self.ALLOWED_TAGS,
            attributes=self.ALLOWED_ATTRS,
            strip=True
        )

        # Extract structured content
        soup_clean = BeautifulSoup(cleaned_html, 'html.parser')

        # Extract text while preserving structure
        paragraphs = []
        for tag in soup_clean.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            text = tag.get_text().strip()
            if text:
                paragraphs.append({
                    'text': text,
                    'tag': tag.name,
                    'html': str(tag)
                })

        # Extract lists
        lists = []
        for ul in soup_clean.find_all(['ul', 'ol']):
            items = [li.get_text().strip() for li in ul.find_all('li')]
            lists.append({
                'type': ul.name,
                'items': items
            })

        # Extract tables
        tables = []
        for table in soup_clean.find_all('table'):
            rows = []
            for tr in table.find_all('tr'):
                cells = [cell.get_text().strip() for cell in tr.find_all(['td', 'th'])]
                rows.append(cells)
            if rows:
                tables.append(rows)

        # Metadata
        word_count = sum(len(p['text'].split()) for p in paragraphs)
        metadata = {
            'word_count': word_count,
            'paragraph_count': len(paragraphs),
            'list_count': len(lists),
            'table_count': len(tables),
            'format': 'html'
        }

        # Detect content type
        content_type = self._detect_content_type(paragraphs, lists)

        content = {
            'html': cleaned_html,
            'paragraphs': paragraphs,
            'lists': lists,
            'tables': tables,
            'title': paragraphs[0]['text'][:100] if paragraphs else ''
        }

        provenance = {
            'filename': filename or 'unknown.html',
            'import_time': datetime.now().isoformat(),
            'original_format': 'html',
            'parser': 'HTMLParser'
        }

        return ParseResult(
            content_type=content_type,
            content=content,
            metadata=metadata,
            warnings=warnings,
            provenance=provenance
        )

    def _detect_content_type(self, paragraphs, lists):
        """Detect content type from HTML structure.

        Args:
            paragraphs: List of paragraph dictionaries
            lists: List of extracted lists

        Returns:
            Detected content type string
        """
        if not paragraphs:
            return 'reading'

        # Count headings
        heading_count = sum(1 for p in paragraphs if p['tag'].startswith('h'))

        # Check for ordered lists (instructions)
        ordered_lists = sum(1 for l in lists if l['type'] == 'ol')

        # Heuristics
        if ordered_lists > 0 and ordered_lists >= len(lists) * 0.5:
            return 'lab'  # Instructions with ordered lists
        elif heading_count > len(paragraphs) * 0.3:
            return 'reading'  # Structured content
        else:
            return 'reading'  # Default
