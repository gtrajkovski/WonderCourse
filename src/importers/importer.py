"""
Import pipeline orchestrating format detection, parsing, and analysis.
"""

from dataclasses import dataclass
from typing import Union, Optional, Dict, Any
from .parsers import (
    BaseParser, ParseResult,
    TextParser, JSONParser, MarkdownParser, CSVParser,
    ZIPParser, DOCXParser, HTMLParser, SCORMParser, QTIParser
)
from .analyzer import ContentAnalyzer, AnalysisResult


@dataclass
class ImportResult:
    """Result of complete import pipeline execution.

    Attributes:
        parse_result: Parsed content from appropriate parser
        analysis: Optional AI-powered content analysis
        format_detected: Detected format string (text, json, markdown, etc.)
    """
    parse_result: ParseResult
    analysis: Optional[AnalysisResult]
    format_detected: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'parse_result': self.parse_result.to_dict(),
            'analysis': self.analysis.to_dict() if self.analysis else None,
            'format_detected': self.format_detected
        }


class ImportPipeline:
    """Orchestrates content import from detection through analysis."""

    def __init__(self):
        """Initialize import pipeline with all parsers and analyzer."""
        # Register parsers in priority order
        # More specific parsers first (SCORM before ZIP, etc.)
        self.parsers: Dict[str, BaseParser] = {
            'scorm': SCORMParser(),
            'qti': QTIParser(),
            'docx': DOCXParser(),
            'html': HTMLParser(),
            'json': JSONParser(),
            'markdown': MarkdownParser(),
            'csv': CSVParser(),
            'zip': ZIPParser(),
            'text': TextParser(),  # Most generic, try last
        }

        self.analyzer = ContentAnalyzer()

    def detect_format(
        self,
        source: Union[str, bytes],
        filename: Optional[str] = None
    ) -> Optional[str]:
        """
        Auto-detect content format by trying parsers in priority order.

        Args:
            source: Content to detect
            filename: Optional filename for extension hints

        Returns:
            Format string (json, markdown, text, etc.) or None if no parser can handle it
        """
        # Use filename extension as hint if available
        if filename:
            ext = filename.lower().rsplit('.', 1)[-1] if '.' in filename else ''

            # Try parser matching extension first
            ext_map = {
                'json': 'json',
                'md': 'markdown',
                'markdown': 'markdown',
                'csv': 'csv',
                'zip': 'zip',
                'docx': 'docx',
                'html': 'html',
                'htm': 'html',
                'txt': 'text',
                'xml': 'qti',  # QTI is XML-based
            }

            if ext in ext_map:
                parser_name = ext_map[ext]
                if parser_name in self.parsers:
                    parser = self.parsers[parser_name]
                    if parser.can_parse(source, filename):
                        return parser_name

        # Try each parser in priority order
        for format_name, parser in self.parsers.items():
            if parser.can_parse(source, filename):
                return format_name

        return None

    def import_content(
        self,
        source: Union[str, bytes],
        filename: Optional[str] = None,
        format_hint: Optional[str] = None,
        analyze: bool = True
    ) -> ImportResult:
        """
        Import content: detect format, parse, and optionally analyze.

        Args:
            source: Content to import (string or bytes)
            filename: Optional filename for provenance and format hints
            format_hint: Optional format override (json, markdown, text, etc.)
            analyze: Whether to run AI analysis (default True)

        Returns:
            ImportResult with parsed content and optional analysis

        Raises:
            ValueError: If format cannot be detected or parsing fails
        """
        # Detect format
        if format_hint and format_hint in self.parsers:
            detected_format = format_hint
        else:
            detected_format = self.detect_format(source, filename)

        if not detected_format:
            raise ValueError(
                "Could not detect content format. "
                "Supported formats: json, markdown, csv, docx, html, scorm, qti, zip, text"
            )

        # Parse with appropriate parser
        parser = self.parsers[detected_format]
        try:
            parse_result = parser.parse(source, filename)
        except Exception as e:
            raise ValueError(f"Failed to parse {detected_format} content: {str(e)}")

        # Analyze content if requested
        analysis = None
        if analyze:
            try:
                analysis = self.analyzer.analyze(parse_result.content, use_ai=True)
            except Exception:
                # Analysis is optional, continue without it if it fails
                pass

        return ImportResult(
            parse_result=parse_result,
            analysis=analysis,
            format_detected=detected_format
        )
