"""
ZIP archive parser for generic archive import.
Lists files and delegates parsing to appropriate parsers.
Note: SCORM packages (with imsmanifest.xml) are handled by SCORMParser.
"""

import zipfile
import io
from typing import Union, List, Dict
from datetime import datetime
from .base_parser import BaseParser, ParseResult


class ZIPParser(BaseParser):
    """Parser for generic ZIP archives."""

    def __init__(self):
        """Initialize with parser registry."""
        # Import parsers here to avoid circular imports
        from .text_parser import TextParser
        from .json_parser import JSONParser
        from .markdown_parser import MarkdownParser
        from .csv_parser import CSVParser

        self.parsers = [
            JSONParser(),
            CSVParser(),  # CSVParser before MarkdownParser (more specific)
            MarkdownParser(),
            TextParser()  # TextParser should be last (most permissive)
        ]

    def can_parse(self, source: Union[str, bytes], filename: str = None) -> bool:
        """
        Detect if this is a valid ZIP (not SCORM).

        Args:
            source: Content to check (must be bytes for ZIP)
            filename: Optional filename

        Returns:
            True if valid ZIP without imsmanifest.xml
        """
        if isinstance(source, str):
            # ZIP must be bytes
            return False

        if not source:
            return False

        try:
            # Try opening as ZIP
            zip_buffer = io.BytesIO(source)
            with zipfile.ZipFile(zip_buffer, 'r') as zf:
                # Check if this is a SCORM package
                if 'imsmanifest.xml' in zf.namelist():
                    # This is SCORM, should be handled by SCORMParser
                    return False
                return True
        except (zipfile.BadZipFile, Exception):
            return False

    def parse(self, source: Union[str, bytes], filename: str = None) -> ParseResult:
        """
        Parse ZIP archive: list files and extract content.

        Detects:
        - Archive structure (flat vs nested)
        - File list with paths and sizes
        - Extracted content from text/markdown/JSON/CSV files

        Args:
            source: ZIP archive bytes
            filename: Optional filename for provenance

        Returns:
            ParseResult with file list and extracted content
        """
        if isinstance(source, str):
            # ZIP must be bytes
            return ParseResult(
                content_type='archive',
                content={},
                metadata={'format': 'zip', 'parse_error': 'ZIP content must be bytes'},
                warnings=['ZIP content must be bytes, not string'],
                provenance={
                    'filename': filename,
                    'import_time': datetime.utcnow().isoformat() + 'Z',
                    'original_format': 'application/zip'
                }
            )

        warnings = []
        files = []
        extracted_content = []

        try:
            zip_buffer = io.BytesIO(source)
            with zipfile.ZipFile(zip_buffer, 'r') as zf:
                # List all files
                for info in zf.infolist():
                    if info.is_dir():
                        continue

                    file_info = {
                        'path': info.filename,
                        'size': info.file_size,
                        'compressed_size': info.compress_size
                    }
                    files.append(file_info)

                    # Try to extract and parse content from text-based files
                    if self._is_parseable_file(info.filename):
                        try:
                            file_content = zf.read(info.filename)
                            parse_result = self._parse_file_content(file_content, info.filename)

                            if parse_result:
                                extracted_content.append({
                                    'path': info.filename,
                                    'content_type': parse_result.content_type,
                                    'content': parse_result.content,
                                    'metadata': parse_result.metadata,
                                    'warnings': parse_result.warnings
                                })
                        except Exception as e:
                            warnings.append(f'Failed to extract {info.filename}: {str(e)}')

                # Detect archive structure
                structure = self._detect_structure(files)

        except zipfile.BadZipFile as e:
            warnings.append(f'Invalid ZIP archive: {str(e)}')
            return ParseResult(
                content_type='archive',
                content={},
                metadata={'format': 'zip', 'parse_error': str(e)},
                warnings=warnings,
                provenance={
                    'filename': filename,
                    'import_time': datetime.utcnow().isoformat() + 'Z',
                    'original_format': 'application/zip'
                }
            )

        # Build content
        content = {
            'files': files,
            'extracted_content': extracted_content,
            'structure': structure
        }

        # Build metadata
        metadata = {
            'format': 'zip',
            'file_count': len(files),
            'extracted_count': len(extracted_content),
            'total_size': sum(f['size'] for f in files),
            'compressed_size': sum(f['compressed_size'] for f in files)
        }

        # Build provenance
        provenance = {
            'filename': filename,
            'import_time': datetime.utcnow().isoformat() + 'Z',
            'original_format': 'application/zip'
        }

        return ParseResult(
            content_type='archive',
            content=content,
            metadata=metadata,
            warnings=warnings,
            provenance=provenance
        )

    def _is_parseable_file(self, filename: str) -> bool:
        """
        Check if file is a text-based format we can parse.

        Args:
            filename: File path

        Returns:
            True if we should try parsing this file
        """
        text_extensions = ['.txt', '.md', '.json', '.csv', '.html', '.xml']
        return any(filename.lower().endswith(ext) for ext in text_extensions)

    def _parse_file_content(self, content: bytes, filename: str):
        """
        Try to parse file content with appropriate parser.

        Args:
            content: File content bytes
            filename: File path

        Returns:
            ParseResult or None if no parser can handle it
        """
        # Try each parser in order
        for parser in self.parsers:
            if parser.can_parse(content, filename):
                try:
                    return parser.parse(content, filename)
                except Exception:
                    # Parser failed, try next one
                    continue

        return None

    def _detect_structure(self, files: List[Dict]) -> str:
        """
        Detect archive structure (flat vs nested).

        Args:
            files: List of file info dictionaries

        Returns:
            Structure description string
        """
        if not files:
            return 'empty'

        # Check for nested folders
        has_folders = any('/' in f['path'] for f in files)

        if not has_folders:
            return 'flat'

        # Count folder depth
        max_depth = max(f['path'].count('/') for f in files)

        if max_depth == 1:
            return 'single_level'
        else:
            return 'nested'
