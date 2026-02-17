"""Tests for advanced content import parsers (DOCX, HTML, SCORM, QTI)."""

import pytest
import io
import zipfile
from unittest.mock import patch, MagicMock

# Import parsers using importlib to avoid keyword issue
try:
    import importlib
    parsers = importlib.import_module('src.import.parsers')
    DOCXParser = parsers.DOCXParser
    HTMLParser = parsers.HTMLParser
    SCORMParser = parsers.SCORMParser
    QTIParser = parsers.QTIParser
    ParseResult = parsers.ParseResult
    PARSERS_AVAILABLE = True
except ImportError:
    PARSERS_AVAILABLE = False


@pytest.mark.skipif(not PARSERS_AVAILABLE, reason="Parsers not available")
class TestDOCXParser:
    """Tests for DOCX parser."""

    def test_can_parse_docx_filename(self):
        """Test DOCX detection from filename."""
        parser = DOCXParser()
        assert parser.can_parse(b'PK\x03\x04', filename='document.docx')

    def test_can_parse_docx_magic_bytes(self):
        """Test DOCX detection from magic bytes."""
        parser = DOCXParser()
        assert parser.can_parse(b'PK\x03\x04' + b'\x00' * 100)

    def test_cannot_parse_non_docx(self):
        """Test rejection of non-DOCX content."""
        parser = DOCXParser()
        assert not parser.can_parse(b'Not a DOCX file')
        assert not parser.can_parse('Plain text')

    @patch('src.import.parsers.docx_parser.DOCX_AVAILABLE', False)
    def test_unavailable_library(self):
        """Test graceful handling when libraries unavailable."""
        parser = DOCXParser()
        assert not parser.can_parse(b'PK\x03\x04', filename='test.docx')

        with pytest.raises(ValueError, match="not installed"):
            parser.parse(b'PK\x03\x04')

    @patch('src.import.parsers.docx_parser.Document')
    @patch('src.import.parsers.docx_parser.mammoth')
    def test_parse_simple_docx(self, mock_mammoth, mock_document):
        """Test parsing a simple DOCX document."""
        # Mock Document
        mock_doc = MagicMock()
        mock_doc.paragraphs = []

        mock_para = MagicMock()
        mock_para.text = 'Test paragraph'
        mock_para.style.name = 'Normal'
        mock_run = MagicMock()
        mock_run.text = 'Test paragraph'
        mock_run.bold = False
        mock_run.italic = False
        mock_run.underline = False
        mock_para.runs = [mock_run]

        mock_doc.paragraphs.append(mock_para)
        mock_doc.tables = []
        mock_doc.core_properties.author = 'Test Author'
        mock_doc.core_properties.title = 'Test Document'
        mock_doc.core_properties.created = None

        mock_document.return_value = mock_doc

        # Mock mammoth
        mock_result = MagicMock()
        mock_result.value = '<p>Test paragraph</p>'
        mock_result.messages = []
        mock_mammoth.convert_to_html.return_value = mock_result

        parser = DOCXParser()
        result = parser.parse(b'PK\x03\x04' + b'\x00' * 100, filename='test.docx')

        assert isinstance(result, ParseResult)
        assert result.content_type == 'reading'
        assert result.metadata['format'] == 'docx'
        assert result.metadata['author'] == 'Test Author'
        assert result.metadata['word_count'] == 2
        assert 'paragraphs' in result.content
        assert 'html' in result.content

    @patch('src.import.parsers.docx_parser.Document')
    @patch('src.import.parsers.docx_parser.mammoth')
    def test_detect_lab_content_type(self, mock_mammoth, mock_document):
        """Test detection of lab content type from numbered lists."""
        mock_doc = MagicMock()
        mock_doc.paragraphs = []

        # Add 5 numbered paragraphs (>30% of 10 total)
        for i in range(1, 6):
            mock_para = MagicMock()
            mock_para.text = f"{i}. Step {i}"
            mock_para.style.name = 'Normal'
            mock_run = MagicMock()
            mock_run.text = mock_para.text
            mock_run.bold = False
            mock_run.italic = False
            mock_run.underline = False
            mock_para.runs = [mock_run]
            mock_doc.paragraphs.append(mock_para)

        # Add 5 regular paragraphs
        for i in range(5):
            mock_para = MagicMock()
            mock_para.text = 'Regular paragraph'
            mock_para.style.name = 'Normal'
            mock_run = MagicMock()
            mock_run.text = mock_para.text
            mock_run.bold = False
            mock_run.italic = False
            mock_run.underline = False
            mock_para.runs = [mock_run]
            mock_doc.paragraphs.append(mock_para)

        mock_doc.tables = []
        mock_doc.core_properties.author = None
        mock_doc.core_properties.title = ''
        mock_doc.core_properties.created = None

        mock_document.return_value = mock_doc

        mock_result = MagicMock()
        mock_result.value = '<p>Test</p>'
        mock_result.messages = []
        mock_mammoth.convert_to_html.return_value = mock_result

        parser = DOCXParser()
        result = parser.parse(b'PK\x03\x04' + b'\x00' * 100)

        assert result.content_type == 'lab'


@pytest.mark.skipif(not PARSERS_AVAILABLE, reason="Parsers not available")
class TestHTMLParser:
    """Tests for HTML parser."""

    def test_can_parse_html_filename(self):
        """Test HTML detection from filename."""
        parser = HTMLParser()
        assert parser.can_parse('<html></html>', filename='page.html')
        assert parser.can_parse('<html></html>', filename='page.htm')

    def test_can_parse_html_content(self):
        """Test HTML detection from content."""
        parser = HTMLParser()
        assert parser.can_parse('<html><body>Content</body></html>')
        assert parser.can_parse('<div>Test</div>')
        assert parser.can_parse('<p>Paragraph</p>')

    def test_cannot_parse_non_html(self):
        """Test rejection of non-HTML content."""
        parser = HTMLParser()
        assert not parser.can_parse('Plain text without tags')
        assert not parser.can_parse(b'Binary data')

    @patch('src.import.parsers.html_parser.HTML_AVAILABLE', False)
    def test_unavailable_library(self):
        """Test graceful handling when libraries unavailable."""
        parser = HTMLParser()
        assert not parser.can_parse('<html></html>')

        with pytest.raises(ValueError, match="not installed"):
            parser.parse('<html></html>')

    def test_parse_simple_html(self):
        """Test parsing simple HTML."""
        parser = HTMLParser()
        html = '<html><body><h1>Title</h1><p>Paragraph 1</p><p>Paragraph 2</p></body></html>'
        result = parser.parse(html, filename='test.html')

        assert isinstance(result, ParseResult)
        assert result.content_type == 'reading'
        assert result.metadata['format'] == 'html'
        assert result.metadata['paragraph_count'] == 3
        assert len(result.content['paragraphs']) == 3
        assert result.content['paragraphs'][0]['tag'] == 'h1'

    def test_sanitize_malicious_html(self):
        """Test sanitization of scripts and unsafe tags."""
        parser = HTMLParser()
        html = '''
        <html>
            <head><script>alert("XSS")</script></head>
            <body>
                <p>Safe content</p>
                <script>alert("More XSS")</script>
                <style>body { color: red; }</style>
            </body>
        </html>
        '''
        result = parser.parse(html)

        # Scripts and styles should be removed
        assert 'alert' not in result.content['html']
        assert '<script>' not in result.content['html']
        assert '<style>' not in result.content['html']
        assert 'Safe content' in result.content['html']

    def test_parse_html_lists(self):
        """Test extraction of HTML lists."""
        parser = HTMLParser()
        html = '''
        <html><body>
            <ul><li>Item 1</li><li>Item 2</li></ul>
            <ol><li>Step 1</li><li>Step 2</li></ol>
        </body></html>
        '''
        result = parser.parse(html)

        assert result.metadata['list_count'] == 2
        assert len(result.content['lists']) == 2
        assert result.content['lists'][0]['type'] == 'ul'
        assert len(result.content['lists'][0]['items']) == 2
        assert result.content['lists'][1]['type'] == 'ol'

    def test_detect_lab_from_ordered_lists(self):
        """Test detection of lab content from ordered lists."""
        parser = HTMLParser()
        html = '''
        <html><body>
            <h1>Lab Instructions</h1>
            <ol><li>Step 1</li><li>Step 2</li><li>Step 3</li></ol>
        </body></html>
        '''
        result = parser.parse(html)

        assert result.content_type == 'lab'


@pytest.mark.skipif(not PARSERS_AVAILABLE, reason="Parsers not available")
class TestSCORMParser:
    """Tests for SCORM parser."""

    def create_mock_scorm_zip(self, manifest_path='imsmanifest.xml'):
        """Create a mock SCORM package ZIP."""
        manifest_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
        <manifest xmlns="http://www.imsglobal.org/xsd/imscp_v1p1"
                  xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_v1p3">
            <metadata>
                <schema>ADL SCORM</schema>
                <adlcp:schemaversion>1.2</adlcp:schemaversion>
            </metadata>
            <organizations default="org1">
                <organization identifier="org1">
                    <title>Test Course</title>
                    <item identifier="item1" identifierref="res1">
                        <title>Module 1</title>
                    </item>
                </organization>
            </organizations>
            <resources>
                <resource identifier="res1" type="webcontent" href="content.html">
                    <file href="content.html"/>
                </resource>
            </resources>
        </manifest>'''

        content_html = '<html><body><h1>Lesson Content</h1></body></html>'

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr(manifest_path, manifest_xml)
            # Add content file in same directory as manifest
            content_path = manifest_path.replace('imsmanifest.xml', 'content.html')
            zf.writestr(content_path, content_html)

        return zip_buffer.getvalue()

    def test_can_parse_scorm_zip(self):
        """Test SCORM detection from ZIP with manifest."""
        parser = SCORMParser()
        scorm_zip = self.create_mock_scorm_zip()
        assert parser.can_parse(scorm_zip, filename='course.zip')

    def test_cannot_parse_non_scorm_zip(self):
        """Test rejection of ZIP without manifest."""
        parser = SCORMParser()
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr('readme.txt', 'Not a SCORM package')

        assert not parser.can_parse(zip_buffer.getvalue())

    def test_cannot_parse_non_zip(self):
        """Test rejection of non-ZIP content."""
        parser = SCORMParser()
        assert not parser.can_parse(b'Not a ZIP file')

    @patch('src.import.parsers.scorm_parser.LXML_AVAILABLE', False)
    def test_unavailable_library(self):
        """Test graceful handling when lxml unavailable."""
        parser = SCORMParser()
        assert not parser.can_parse(b'PK\x03\x04')

    def test_parse_scorm_root_manifest(self):
        """Test parsing SCORM with manifest at root."""
        parser = SCORMParser()
        scorm_zip = self.create_mock_scorm_zip('imsmanifest.xml')
        result = parser.parse(scorm_zip, filename='course.zip')

        assert isinstance(result, ParseResult)
        assert result.content_type == 'blueprint'
        assert result.metadata['format'] == 'scorm'
        assert result.metadata['scorm_version'] == '1.2'
        assert result.content['title'] == 'Test Course'
        assert len(result.content['modules']) == 1
        assert result.content['modules'][0]['title'] == 'Module 1'
        assert len(result.warnings) == 0  # No warning for root manifest

    def test_parse_scorm_nested_manifest(self):
        """Test parsing SCORM with manifest in subfolder."""
        parser = SCORMParser()
        scorm_zip = self.create_mock_scorm_zip('course/imsmanifest.xml')
        result = parser.parse(scorm_zip)

        assert result.content_type == 'blueprint'
        assert result.metadata['package_root'] == 'course'
        # Should have warning about non-standard structure
        assert any('Non-standard' in w for w in result.warnings)

    def test_invalid_manifest_xml(self):
        """Test error handling for invalid XML."""
        parser = SCORMParser()

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr('imsmanifest.xml', 'Invalid XML <>')

        with pytest.raises(ValueError, match="Invalid manifest XML"):
            parser.parse(zip_buffer.getvalue())


@pytest.mark.skipif(not PARSERS_AVAILABLE, reason="Parsers not available")
class TestQTIParser:
    """Tests for QTI parser."""

    def test_can_parse_qti_content(self):
        """Test QTI detection from XML content."""
        parser = QTIParser()
        qti_xml = '<assessmentItem><choiceInteraction></choiceInteraction></assessmentItem>'
        assert parser.can_parse(qti_xml)
        assert parser.can_parse('<assessmentTest></assessmentTest>')

    def test_can_parse_qti_filename(self):
        """Test QTI detection from filename."""
        parser = QTIParser()
        assert parser.can_parse('<assessmentItem></assessmentItem>', filename='quiz.xml')

    def test_cannot_parse_non_qti(self):
        """Test rejection of non-QTI content."""
        parser = QTIParser()
        assert not parser.can_parse('Plain text')
        assert not parser.can_parse('<html><body></body></html>')

    @patch('src.import.parsers.qti_parser.LXML_AVAILABLE', False)
    def test_unavailable_library(self):
        """Test graceful handling when lxml unavailable."""
        parser = QTIParser()
        assert not parser.can_parse('<assessmentItem></assessmentItem>')

    def test_parse_simple_qti(self):
        """Test parsing simple QTI question."""
        parser = QTIParser()
        qti_xml = '''<?xml version="1.0"?>
        <assessmentItem identifier="q1" title="Sample Question">
            <itemBody>
                <choiceInteraction responseIdentifier="RESPONSE">
                    <prompt>What is 2+2?</prompt>
                    <simpleChoice identifier="A">3</simpleChoice>
                    <simpleChoice identifier="B">4</simpleChoice>
                    <simpleChoice identifier="C">5</simpleChoice>
                </choiceInteraction>
            </itemBody>
            <responseDeclaration identifier="RESPONSE">
                <correctResponse>
                    <value>B</value>
                </correctResponse>
            </responseDeclaration>
        </assessmentItem>'''

        result = parser.parse(qti_xml, filename='quiz.xml')

        assert isinstance(result, ParseResult)
        assert result.content_type == 'quiz'
        assert result.metadata['format'] == 'qti'
        assert len(result.content['questions']) == 1

        question = result.content['questions'][0]
        assert question['identifier'] == 'q1'
        assert 'What is 2+2?' in question['prompt']
        assert len(question['options']) == 3
        assert question['correct_answer'] == 'B'

    def test_parse_qti_no_namespace(self):
        """Test parsing QTI without namespace prefix."""
        parser = QTIParser()
        qti_xml = '''<?xml version="1.0"?>
        <assessmentItem>
            <itemBody>
                <choiceInteraction>
                    <simpleChoice identifier="A">Option A</simpleChoice>
                </choiceInteraction>
            </itemBody>
        </assessmentItem>'''

        result = parser.parse(qti_xml)
        assert len(result.content['questions']) == 1

    def test_qti_version_detection(self):
        """Test QTI version detection."""
        parser = QTIParser()
        qti_21 = '<assessmentItem xmlns="http://www.imsglobal.org/xsd/imsqti_v2p1"></assessmentItem>'
        qti_22 = '<assessmentItem xmlns="http://www.imsglobal.org/xsd/imsqti_v2p2"></assessmentItem>'

        result_21 = parser.parse(qti_21)
        assert result_21.metadata['version'] == '2.1'

        result_22 = parser.parse(qti_22)
        assert result_22.metadata['version'] == '2.2'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
