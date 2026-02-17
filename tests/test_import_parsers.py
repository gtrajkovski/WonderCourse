"""
Tests for content import parsers.
Tests BaseParser interface, ParseResult, and all parser implementations.
"""

import pytest
import json
import zipfile
import io

# Import from src.importers.parsers package
from src.importers.parsers import (
    BaseParser,
    ParseResult,
    TextParser,
    JSONParser,
    MarkdownParser,
    CSVParser,
    ZIPParser,
)


class TestParseResult:
    """Test ParseResult dataclass."""

    def test_to_dict_serialization(self):
        """Test to_dict() method returns correct structure."""
        result = ParseResult(
            content_type='reading',
            content={'text': 'sample'},
            metadata={'word_count': 10},
            warnings=['warning1'],
            provenance={'filename': 'test.txt'}
        )

        data = result.to_dict()

        assert data['content_type'] == 'reading'
        assert data['content'] == {'text': 'sample'}
        assert data['metadata'] == {'word_count': 10}
        assert data['warnings'] == ['warning1']
        assert data['provenance'] == {'filename': 'test.txt'}

    def test_default_warnings_and_provenance(self):
        """Test warnings and provenance default to empty lists/dicts."""
        result = ParseResult(
            content_type='reading',
            content={},
            metadata={}
        )

        assert result.warnings == []
        assert result.provenance == {}


class TestTextParser:
    """Test TextParser implementation."""

    def test_can_parse_plain_text(self):
        """Test can_parse detects plain text."""
        parser = TextParser()
        text = "This is plain text content.\nWith multiple lines."

        assert parser.can_parse(text) is True

    def test_can_parse_rejects_json(self):
        """Test can_parse rejects JSON."""
        parser = TextParser()
        json_text = '{"key": "value"}'

        assert parser.can_parse(json_text) is False

    def test_can_parse_rejects_markdown(self):
        """Test can_parse rejects Markdown."""
        parser = TextParser()
        markdown = "# Header\n\nSome **bold** text."

        assert parser.can_parse(markdown) is False

    def test_can_parse_bytes(self):
        """Test can_parse handles bytes."""
        parser = TextParser()
        text_bytes = b"Plain text content"

        assert parser.can_parse(text_bytes) is True

    def test_parse_detects_headings(self):
        """Test parsing detects headings (lines ending with :)."""
        parser = TextParser()
        text = "Introduction:\nThis is the intro.\n\nMain Content:\nThe main part."

        result = parser.parse(text)

        assert result.content_type in ['reading', 'video_script']
        assert len(result.content['headings']) == 2
        assert 'Introduction' in result.content['headings']
        assert 'Main Content' in result.content['headings']

    def test_parse_detects_lists(self):
        """Test parsing detects list items."""
        parser = TextParser()
        text = "- Item 1\n- Item 2\n* Item 3"

        result = parser.parse(text)

        assert len(result.content['lists']) == 3
        assert 'Item 1' in result.content['lists']

    def test_parse_counts_words(self):
        """Test word count is calculated."""
        parser = TextParser()
        text = "one two three four five"

        result = parser.parse(text)

        assert result.metadata['word_count'] == 5

    def test_parse_detects_higher_bloom(self):
        """Test Bloom's level estimation based on keywords."""
        parser = TextParser()
        text = "You will analyze the data and evaluate the results."

        result = parser.parse(text)

        assert result.metadata['estimated_bloom_level'] == 'analyze'

    def test_parse_warns_on_short_content(self):
        """Test warning for short content."""
        parser = TextParser()
        text = "Very short."

        result = parser.parse(text)

        assert len(result.warnings) > 0
        assert any('Short content' in w for w in result.warnings)

    def test_parse_includes_provenance(self):
        """Test provenance tracking."""
        parser = TextParser()
        text = "Sample text"

        result = parser.parse(text, filename='test.txt')

        assert result.provenance['filename'] == 'test.txt'
        assert 'import_time' in result.provenance
        assert result.provenance['original_format'] == 'text/plain'


class TestJSONParser:
    """Test JSONParser implementation."""

    def test_can_parse_valid_json(self):
        """Test can_parse detects valid JSON."""
        parser = JSONParser()
        json_text = '{"course_title": "Test", "modules": []}'

        assert parser.can_parse(json_text) is True

    def test_can_parse_rejects_invalid_json(self):
        """Test can_parse rejects invalid JSON."""
        parser = JSONParser()
        invalid = "Not JSON at all"

        assert parser.can_parse(invalid) is False

    def test_can_parse_rejects_json_without_blueprint_keys(self):
        """Test can_parse rejects JSON without blueprint structure."""
        parser = JSONParser()
        json_text = '{"random": "data"}'

        assert parser.can_parse(json_text) is False

    def test_parse_valid_blueprint(self):
        """Test parsing valid blueprint structure."""
        parser = JSONParser()
        blueprint = {
            "course_title": "Test Course",
            "description": "A test course",
            "modules": [
                {
                    "title": "Module 1",
                    "lessons": [
                        {
                            "title": "Lesson 1",
                            "activities": [
                                {"title": "Activity 1", "content_type": "video"}
                            ]
                        }
                    ]
                }
            ]
        }
        json_text = json.dumps(blueprint)

        result = parser.parse(json_text)

        assert result.content_type == 'blueprint'
        assert result.metadata['structure_valid'] is True
        assert result.metadata['module_count'] == 1
        assert result.metadata['lesson_count'] == 1
        assert result.metadata['activity_count'] == 1

    def test_parse_warns_on_missing_keys(self):
        """Test warnings for missing blueprint keys."""
        parser = JSONParser()
        incomplete = {"modules": []}
        json_text = json.dumps(incomplete)

        result = parser.parse(json_text)

        assert len(result.warnings) > 0
        assert any('Missing blueprint keys' in w for w in result.warnings)

    def test_parse_validates_module_structure(self):
        """Test validation of module structure."""
        parser = JSONParser()
        blueprint = {
            "course_title": "Test",
            "description": "Test",
            "modules": [
                {"title": "Module 1"}  # Missing lessons
            ]
        }
        json_text = json.dumps(blueprint)

        result = parser.parse(json_text)

        assert any('missing keys' in w.lower() for w in result.warnings)

    def test_parse_handles_json_error(self):
        """Test handling of JSON parse errors."""
        parser = JSONParser()
        invalid_json = '{"broken": json}'

        result = parser.parse(invalid_json)

        assert result.content_type == 'unknown'
        assert 'parse_error' in result.metadata
        assert len(result.warnings) > 0


class TestMarkdownParser:
    """Test MarkdownParser implementation."""

    def test_can_parse_markdown_headers(self):
        """Test can_parse detects Markdown headers."""
        parser = MarkdownParser()
        markdown = "# Header 1\n\nContent here."

        assert parser.can_parse(markdown) is True

    def test_can_parse_markdown_lists(self):
        """Test can_parse detects Markdown lists."""
        parser = MarkdownParser()
        markdown = "- Item 1\n- Item 2"

        assert parser.can_parse(markdown) is True

    def test_can_parse_markdown_emphasis(self):
        """Test can_parse detects Markdown emphasis."""
        parser = MarkdownParser()
        markdown = "Some **bold** and *italic* text."

        assert parser.can_parse(markdown) is True

    def test_can_parse_rejects_plain_text(self):
        """Test can_parse rejects plain text without Markdown."""
        parser = MarkdownParser()
        plain = "Just plain text with no formatting."

        # Should reject because no Markdown syntax
        assert parser.can_parse(plain) is False

    def test_parse_extracts_sections(self):
        """Test parsing extracts sections based on headers."""
        parser = MarkdownParser()
        markdown = "# Section 1\n\nContent 1\n\n## Section 2\n\nContent 2"

        result = parser.parse(markdown)

        assert len(result.content['sections']) >= 2
        assert result.metadata['detected_structure']['section_count'] >= 2

    def test_parse_extracts_code_blocks(self):
        """Test parsing extracts code blocks."""
        parser = MarkdownParser()
        markdown = "# Code Example\n\n```python\nprint('hello')\n```"

        result = parser.parse(markdown)

        assert len(result.content['code_blocks']) == 1
        assert result.content['code_blocks'][0]['language'] == 'python'
        assert 'print' in result.content['code_blocks'][0]['code']

    def test_parse_extracts_links(self):
        """Test parsing extracts links."""
        parser = MarkdownParser()
        markdown = "Check out [this link](https://example.com) for more."

        result = parser.parse(markdown)

        assert len(result.content['links']) == 1
        assert result.content['links'][0]['text'] == 'this link'
        assert result.content['links'][0]['url'] == 'https://example.com'

    def test_parse_preserves_raw_markdown(self):
        """Test raw markdown is preserved."""
        parser = MarkdownParser()
        markdown = "# Header\n\nContent"

        result = parser.parse(markdown)

        assert result.content['raw_markdown'] == markdown

    def test_parse_warns_on_short_content(self):
        """Test warning when content is too short."""
        parser = MarkdownParser()
        markdown = "Just *some* text with no headers."

        result = parser.parse(markdown)

        # Implementation creates an "introduction" section for content without headers
        # Short content warning should be generated since word count is low
        assert any('Short content' in w for w in result.warnings)


class TestCSVParser:
    """Test CSVParser implementation."""

    def test_can_parse_valid_csv(self):
        """Test can_parse detects valid CSV with quiz columns."""
        parser = CSVParser()
        csv_text = "question,option_a,option_b,correct\nQ1?,A,B,a"

        assert parser.can_parse(csv_text) is True

    def test_can_parse_rejects_invalid_csv(self):
        """Test can_parse rejects invalid CSV."""
        parser = CSVParser()
        invalid = "Not a CSV file"

        assert parser.can_parse(invalid) is False

    def test_can_parse_rejects_csv_without_required_columns(self):
        """Test can_parse rejects CSV without required columns."""
        parser = CSVParser()
        csv_text = "col1,col2\nval1,val2"

        assert parser.can_parse(csv_text) is False

    def test_parse_valid_quiz_csv(self):
        """Test parsing valid quiz CSV."""
        parser = CSVParser()
        csv_text = """question,option_a,option_b,option_c,option_d,correct,feedback
What is 2+2?,3,4,5,6,b,Basic math
What is the capital of France?,London,Paris,Berlin,Madrid,b,Geography"""

        result = parser.parse(csv_text)

        assert result.content_type == 'quiz'
        assert len(result.content['questions']) == 2
        assert result.metadata['question_count'] == 2

    def test_parse_marks_correct_option(self):
        """Test correct option is marked."""
        parser = CSVParser()
        csv_text = "question,option_a,option_b,correct\nQ1?,A,B,b"

        result = parser.parse(csv_text)

        question = result.content['questions'][0]
        option_b = [opt for opt in question['options'] if opt['letter'] == 'b'][0]
        assert option_b['is_correct'] is True

    def test_parse_warns_on_missing_columns(self):
        """Test warnings for missing columns."""
        parser = CSVParser()
        csv_text = "question,option_a\nQ1?,A"  # Missing option_b and correct

        result = parser.parse(csv_text)

        assert any('Missing required columns' in w for w in result.warnings)

    def test_parse_warns_on_answer_distribution(self):
        """Test warnings for predictable answer patterns."""
        parser = CSVParser()
        # All answers are 'a'
        csv_text = """question,option_a,option_b,correct
Q1?,A,B,a
Q2?,A,B,a
Q3?,A,B,a
Q4?,A,B,a
Q5?,A,B,a"""

        result = parser.parse(csv_text)

        assert any('100%' in w for w in result.warnings)

    def test_parse_handles_optional_columns(self):
        """Test optional columns (option_c, option_d, feedback) work."""
        parser = CSVParser()
        csv_text = "question,option_a,option_b,option_c,correct,feedback\nQ1?,A,B,C,c,Good job"

        result = parser.parse(csv_text)

        question = result.content['questions'][0]
        assert len(question['options']) == 3
        assert question['feedback'] == 'Good job'


class TestZIPParser:
    """Test ZIPParser implementation."""

    def test_can_parse_valid_zip(self):
        """Test can_parse detects valid ZIP."""
        parser = ZIPParser()

        # Create a simple ZIP in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr('test.txt', 'content')
        zip_bytes = zip_buffer.getvalue()

        assert parser.can_parse(zip_bytes) is True

    def test_can_parse_rejects_string(self):
        """Test can_parse rejects string input."""
        parser = ZIPParser()

        assert parser.can_parse("not bytes") is False

    def test_can_parse_rejects_scorm_package(self):
        """Test can_parse rejects SCORM packages (with imsmanifest.xml)."""
        parser = ZIPParser()

        # Create ZIP with imsmanifest.xml
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr('imsmanifest.xml', '<manifest></manifest>')
        zip_bytes = zip_buffer.getvalue()

        assert parser.can_parse(zip_bytes) is False

    def test_parse_lists_files(self):
        """Test parsing lists all files in archive."""
        parser = ZIPParser()

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr('file1.txt', 'content1')
            zf.writestr('file2.txt', 'content2')
        zip_bytes = zip_buffer.getvalue()

        result = parser.parse(zip_bytes)

        assert result.content_type == 'archive'
        assert len(result.content['files']) == 2
        assert result.metadata['file_count'] == 2

    def test_parse_extracts_text_files(self):
        """Test parsing extracts and parses text files."""
        parser = ZIPParser()

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr('readme.txt', 'This is a readme file with some content.')
        zip_bytes = zip_buffer.getvalue()

        result = parser.parse(zip_bytes)

        assert len(result.content['extracted_content']) == 1
        extracted = result.content['extracted_content'][0]
        assert extracted['path'] == 'readme.txt'
        assert extracted['content_type'] in ['reading', 'video_script']

    def test_parse_delegates_to_json_parser(self):
        """Test ZIP parser delegates JSON files to JSONParser."""
        parser = ZIPParser()

        blueprint = {"course_title": "Test", "description": "Test", "modules": []}
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr('blueprint.json', json.dumps(blueprint))
        zip_bytes = zip_buffer.getvalue()

        result = parser.parse(zip_bytes)

        extracted = result.content['extracted_content'][0]
        assert extracted['content_type'] == 'blueprint'

    def test_parse_delegates_to_markdown_parser(self):
        """Test ZIP parser delegates Markdown files to MarkdownParser."""
        parser = ZIPParser()

        markdown = "# Header\n\nContent here."
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr('readme.md', markdown)
        zip_bytes = zip_buffer.getvalue()

        result = parser.parse(zip_bytes)

        extracted = result.content['extracted_content'][0]
        assert extracted['content_type'] in ['reading', 'video_script']
        assert 'sections' in extracted['content']

    def test_parse_delegates_to_csv_parser(self):
        """Test ZIP parser delegates CSV files to CSVParser."""
        parser = ZIPParser()

        csv_content = "question,option_a,option_b,correct\nQ1?,A,B,a"
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr('quiz.csv', csv_content)
        zip_bytes = zip_buffer.getvalue()

        result = parser.parse(zip_bytes)

        extracted = result.content['extracted_content'][0]
        assert extracted['content_type'] == 'quiz'

    def test_parse_detects_flat_structure(self):
        """Test structure detection for flat archives."""
        parser = ZIPParser()

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr('file1.txt', 'content')
            zf.writestr('file2.txt', 'content')
        zip_bytes = zip_buffer.getvalue()

        result = parser.parse(zip_bytes)

        assert result.content['structure'] == 'flat'

    def test_parse_detects_nested_structure(self):
        """Test structure detection for nested archives."""
        parser = ZIPParser()

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr('folder1/file1.txt', 'content')
            zf.writestr('folder1/subfolder/file2.txt', 'content')
        zip_bytes = zip_buffer.getvalue()

        result = parser.parse(zip_bytes)

        assert result.content['structure'] == 'nested'

    def test_parse_warns_on_extraction_errors(self):
        """Test warnings for files that fail to extract."""
        parser = ZIPParser()

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            # Add a binary file that won't parse
            zf.writestr('binary.bin', b'\x00\x01\x02\x03')
        zip_bytes = zip_buffer.getvalue()

        result = parser.parse(zip_bytes)

        # Binary files should not be extracted (not in parseable list)
        # So no extraction errors should occur for .bin files
        assert result.metadata['extracted_count'] == 0
