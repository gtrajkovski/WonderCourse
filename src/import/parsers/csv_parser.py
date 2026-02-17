"""
CSV parser for quiz question import.
Parses CSV files into quiz question format with validation.
"""

import csv
import io
from typing import Union, List, Dict
from datetime import datetime
from .base_parser import BaseParser, ParseResult


class CSVParser(BaseParser):
    """Parser for CSV quiz questions."""

    # Required columns for quiz CSV
    REQUIRED_COLUMNS = {'question', 'option_a', 'option_b', 'correct'}
    OPTIONAL_COLUMNS = {'option_c', 'option_d', 'feedback'}

    def can_parse(self, source: Union[str, bytes], filename: str = None) -> bool:
        """
        Detect if this is valid CSV with quiz question columns.

        Args:
            source: Content to check
            filename: Optional filename

        Returns:
            True if valid CSV with required columns
        """
        if isinstance(source, bytes):
            try:
                source = source.decode('utf-8')
            except UnicodeDecodeError:
                return False

        if not source or not source.strip():
            return False

        try:
            # Try parsing as CSV
            reader = csv.DictReader(io.StringIO(source))
            fieldnames = set(reader.fieldnames or [])

            # Check for required columns
            if self.REQUIRED_COLUMNS.issubset(fieldnames):
                return True

        except (csv.Error, Exception):
            return False

        return False

    def parse(self, source: Union[str, bytes], filename: str = None) -> ParseResult:
        """
        Parse CSV into quiz questions.

        Expected columns:
        - question (required)
        - option_a (required)
        - option_b (required)
        - option_c (optional)
        - option_d (optional)
        - correct (required): 'a', 'b', 'c', or 'd'
        - feedback (optional)

        Args:
            source: CSV content to parse
            filename: Optional filename for provenance

        Returns:
            ParseResult with quiz questions
        """
        if isinstance(source, bytes):
            source = source.decode('utf-8')

        warnings = []
        questions = []

        try:
            reader = csv.DictReader(io.StringIO(source))
            fieldnames = set(reader.fieldnames or [])

            # Validate columns
            missing = self.REQUIRED_COLUMNS - fieldnames
            if missing:
                warnings.append(f'Missing required columns: {", ".join(missing)}')

            # Parse each row
            for i, row in enumerate(reader, start=1):
                question_data = self._parse_question_row(row, i, warnings)
                if question_data:
                    questions.append(question_data)

        except csv.Error as e:
            warnings.append(f'CSV parsing error: {str(e)}')
            return ParseResult(
                content_type='quiz',
                content={'questions': []},
                metadata={'format': 'csv', 'parse_error': str(e)},
                warnings=warnings,
                provenance={
                    'filename': filename,
                    'import_time': datetime.utcnow().isoformat() + 'Z',
                    'original_format': 'text/csv'
                }
            )

        # Validate answer distribution
        self._validate_answer_distribution(questions, warnings)

        # Build content
        content = {
            'questions': questions
        }

        # Build metadata
        metadata = {
            'format': 'csv',
            'question_count': len(questions),
            'detected_structure': {
                'has_feedback': any('feedback' in q for q in questions),
                'option_counts': self._count_options(questions)
            }
        }

        # Build provenance
        provenance = {
            'filename': filename,
            'import_time': datetime.utcnow().isoformat() + 'Z',
            'original_format': 'text/csv'
        }

        return ParseResult(
            content_type='quiz',
            content=content,
            metadata=metadata,
            warnings=warnings,
            provenance=provenance
        )

    def _parse_question_row(self, row: Dict[str, str], row_num: int, warnings: List[str]) -> Dict:
        """
        Parse a single question row.

        Args:
            row: CSV row data
            row_num: Row number for error reporting
            warnings: List to append warnings to

        Returns:
            Question dictionary or None if invalid
        """
        question_text = row.get('question', '').strip()
        if not question_text:
            warnings.append(f'Row {row_num}: Empty question text')
            return None

        # Parse options
        options = []
        for letter in ['a', 'b', 'c', 'd']:
            option_text = row.get(f'option_{letter}', '').strip()
            if option_text:
                options.append({
                    'letter': letter,
                    'text': option_text
                })

        if len(options) < 2:
            warnings.append(f'Row {row_num}: Need at least 2 options')
            return None

        # Parse correct answer
        correct = row.get('correct', '').strip().lower()
        if correct not in [opt['letter'] for opt in options]:
            warnings.append(f'Row {row_num}: Correct answer "{correct}" not in available options')
            return None

        # Mark correct option
        for opt in options:
            opt['is_correct'] = (opt['letter'] == correct)

        # Parse feedback
        feedback = row.get('feedback', '').strip()

        question_data = {
            'question': question_text,
            'options': options,
            'correct_answer': correct
        }

        if feedback:
            question_data['feedback'] = feedback

        return question_data

    def _validate_answer_distribution(self, questions: List[Dict], warnings: List[str]):
        """
        Validate that correct answers are distributed (not all same letter).

        Args:
            questions: List of parsed questions
            warnings: List to append warnings to
        """
        if not questions:
            return

        correct_answers = [q['correct_answer'] for q in questions]
        answer_counts = {}

        for answer in correct_answers:
            answer_counts[answer] = answer_counts.get(answer, 0) + 1

        # Check if any answer is used too frequently
        total = len(questions)
        for answer, count in answer_counts.items():
            percentage = (count / total) * 100
            if percentage > 60:
                warnings.append(f'Correct answer "{answer}" used {percentage:.0f}% of the time (may be predictable)')

    def _count_options(self, questions: List[Dict]) -> Dict[str, int]:
        """
        Count how many options each question has.

        Args:
            questions: List of parsed questions

        Returns:
            Dictionary mapping option count to number of questions
        """
        counts = {}
        for question in questions:
            option_count = len(question['options'])
            counts[str(option_count)] = counts.get(str(option_count), 0) + 1
        return counts
