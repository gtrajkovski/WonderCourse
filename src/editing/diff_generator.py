"""Text diff generation for visualizing changes between original and modified text.

Uses Python's difflib for generating unified diffs, HTML table diffs,
and inline diffs with insertion/deletion markup.
"""

import difflib
from dataclasses import dataclass
from typing import List, Dict, Tuple
import html


@dataclass
class DiffResult:
    """Result of diff generation containing multiple diff formats.

    Attributes:
        original: Original text before changes
        modified: Modified text after changes
        unified_diff: Unified diff format (like git diff)
        html_diff: HTML table for side-by-side comparison
        changes: Structured list of changes with line numbers
    """
    original: str
    modified: str
    unified_diff: str
    html_diff: str
    changes: List[Dict[str, any]]


class DiffGenerator:
    """Generate visual diffs between original and modified text.

    Provides multiple diff formats for different use cases:
    - Unified diff for terminal/git-like display
    - HTML table diff for side-by-side comparison
    - Inline diff with <ins> and <del> tags for inline editing UI
    - Structured changes list for programmatic processing
    """

    def generate_diff(self, original: str, modified: str) -> DiffResult:
        """Generate comprehensive diff between original and modified text.

        Args:
            original: Original text before changes
            modified: Modified text after changes

        Returns:
            DiffResult containing all diff formats
        """
        # Split into lines for line-by-line diff
        original_lines = original.splitlines(keepends=True)
        modified_lines = modified.splitlines(keepends=True)

        # Generate unified diff
        unified_diff = self._generate_unified_diff(original_lines, modified_lines)

        # Generate HTML table diff
        html_diff = self._generate_html_diff(original_lines, modified_lines)

        # Generate structured changes
        changes = self._generate_changes(original_lines, modified_lines)

        return DiffResult(
            original=original,
            modified=modified,
            unified_diff=unified_diff,
            html_diff=html_diff,
            changes=changes
        )

    def generate_inline_diff(self, original: str, modified: str) -> str:
        """Generate inline diff with <ins> and <del> tags for inline display.

        Uses word-level diff for fine-grained change visualization.

        Args:
            original: Original text
            modified: Modified text

        Returns:
            HTML string with <ins> and <del> tags marking changes
        """
        # For inline diff, we'll use word-level comparison
        original_words = original.split()
        modified_words = modified.split()

        diff = difflib.SequenceMatcher(None, original_words, modified_words)
        result = []

        for opcode, i1, i2, j1, j2 in diff.get_opcodes():
            if opcode == 'equal':
                result.append(' '.join(original_words[i1:i2]))
            elif opcode == 'delete':
                deleted = ' '.join(original_words[i1:i2])
                result.append(f'<del>{html.escape(deleted)}</del>')
            elif opcode == 'insert':
                inserted = ' '.join(modified_words[j1:j2])
                result.append(f'<ins>{html.escape(inserted)}</ins>')
            elif opcode == 'replace':
                deleted = ' '.join(original_words[i1:i2])
                inserted = ' '.join(modified_words[j1:j2])
                result.append(f'<del>{html.escape(deleted)}</del>')
                result.append(f'<ins>{html.escape(inserted)}</ins>')

        return ' '.join(result)

    def _generate_unified_diff(self, original_lines: List[str], modified_lines: List[str]) -> str:
        """Generate unified diff format (like git diff).

        Args:
            original_lines: Original text split into lines
            modified_lines: Modified text split into lines

        Returns:
            Unified diff string
        """
        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile='original',
            tofile='modified',
            lineterm=''
        )
        return '\n'.join(diff)

    def _generate_html_diff(self, original_lines: List[str], modified_lines: List[str]) -> str:
        """Generate HTML table for side-by-side diff comparison.

        Args:
            original_lines: Original text split into lines
            modified_lines: Modified text split into lines

        Returns:
            HTML table string
        """
        diff = difflib.HtmlDiff()
        return diff.make_table(
            original_lines,
            modified_lines,
            fromdesc='Original',
            todesc='Modified',
            context=True,
            numlines=3
        )

    def _generate_changes(self, original_lines: List[str], modified_lines: List[str]) -> List[Dict[str, any]]:
        """Generate structured list of changes with line numbers.

        Args:
            original_lines: Original text split into lines
            modified_lines: Modified text split into lines

        Returns:
            List of change dictionaries with type, line numbers, and content
        """
        changes = []
        diff = difflib.SequenceMatcher(None, original_lines, modified_lines)

        for opcode, i1, i2, j1, j2 in diff.get_opcodes():
            if opcode == 'equal':
                # Skip unchanged lines
                continue
            elif opcode == 'delete':
                changes.append({
                    'type': 'delete',
                    'original_start': i1 + 1,
                    'original_end': i2,
                    'content': ''.join(original_lines[i1:i2]).strip()
                })
            elif opcode == 'insert':
                changes.append({
                    'type': 'insert',
                    'modified_start': j1 + 1,
                    'modified_end': j2,
                    'content': ''.join(modified_lines[j1:j2]).strip()
                })
            elif opcode == 'replace':
                changes.append({
                    'type': 'replace',
                    'original_start': i1 + 1,
                    'original_end': i2,
                    'modified_start': j1 + 1,
                    'modified_end': j2,
                    'original_content': ''.join(original_lines[i1:i2]).strip(),
                    'modified_content': ''.join(modified_lines[j1:j2]).strip()
                })

        return changes
