"""TDD tests for SCORMPackageExporter - SCORM 1.2 compliant packages."""

import pytest
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import tempfile
import shutil

from src.exporters.scorm_package import SCORMPackageExporter
from src.exporters.base_exporter import BaseExporter
from src.core.models import (
    Course, Module, Lesson, Activity,
    ContentType, BuildState, ActivityType
)


@pytest.fixture
def exporter(tmp_path):
    """Create SCORMPackageExporter with temp output directory."""
    return SCORMPackageExporter(output_dir=tmp_path)


@pytest.fixture
def simple_course():
    """Create a simple course with one module, one lesson, one activity."""
    course = Course(
        id="course_scorm_test",
        title="SCORM Test Course",
        description="A test course for SCORM export",
    )
    module = Module(id="mod_1", title="Introduction Module", order=0)
    lesson = Lesson(id="les_1", title="Getting Started", order=0)
    activity = Activity(
        id="act_1",
        title="Welcome Video",
        content_type=ContentType.VIDEO,
        activity_type=ActivityType.VIDEO_LECTURE,
        content="Welcome to the course! This is the introductory video content.",
        build_state=BuildState.APPROVED,
        order=0,
    )
    lesson.activities.append(activity)
    module.lessons.append(lesson)
    course.modules.append(module)
    return course


@pytest.fixture
def multi_module_course():
    """Create a course with multiple modules and lessons."""
    course = Course(
        id="course_multi",
        title="Multi-Module Course",
        description="Course with multiple modules for SCORM testing",
    )

    # Module 1: Introduction
    mod1 = Module(id="mod_1", title="Introduction", order=0)
    les1_1 = Lesson(id="les_1_1", title="Overview", order=0)
    les1_1.activities.append(Activity(
        id="act_1_1",
        title="Course Overview",
        content_type=ContentType.VIDEO,
        content="Overview video content here.",
        build_state=BuildState.APPROVED,
        order=0,
    ))
    les1_2 = Lesson(id="les_1_2", title="Prerequisites", order=1)
    les1_2.activities.append(Activity(
        id="act_1_2",
        title="Prerequisites Reading",
        content_type=ContentType.READING,
        content="You should know basic concepts before starting.",
        build_state=BuildState.APPROVED,
        order=0,
    ))
    mod1.lessons.extend([les1_1, les1_2])

    # Module 2: Core Concepts
    mod2 = Module(id="mod_2", title="Core Concepts", order=1)
    les2_1 = Lesson(id="les_2_1", title="Fundamentals", order=0)
    les2_1.activities.append(Activity(
        id="act_2_1",
        title="Fundamentals Video",
        content_type=ContentType.VIDEO,
        content="Core fundamentals explained here.",
        build_state=BuildState.APPROVED,
        order=0,
    ))
    les2_1.activities.append(Activity(
        id="act_2_2",
        title="Practice Quiz",
        content_type=ContentType.QUIZ,
        activity_type=ActivityType.PRACTICE_QUIZ,
        content="Quiz content with questions.",
        build_state=BuildState.APPROVED,
        order=1,
    ))
    mod2.lessons.append(les2_1)

    course.modules.extend([mod1, mod2])
    return course


class TestSCORMPackageExporterInheritance:
    """Tests for class structure and inheritance."""

    def test_inherits_from_base_exporter(self, exporter):
        """SCORMPackageExporter should inherit from BaseExporter."""
        assert isinstance(exporter, BaseExporter)

    def test_format_name_property(self, exporter):
        """format_name should return 'SCORM 1.2 Package'."""
        assert exporter.format_name == "SCORM 1.2 Package"

    def test_file_extension_property(self, exporter):
        """file_extension should return '.zip'."""
        assert exporter.file_extension == ".zip"


class TestSCORMPackageExport:
    """Tests for export functionality."""

    def test_export_creates_zip_file(self, exporter, simple_course, tmp_path):
        """export() should create a .zip file in output directory."""
        result_path = exporter.export(simple_course)

        assert result_path.exists()
        assert result_path.suffix == ".zip"
        assert zipfile.is_zipfile(result_path)

    def test_export_returns_path_in_output_dir(self, exporter, simple_course, tmp_path):
        """Exported file should be in the configured output directory."""
        result_path = exporter.export(simple_course)

        assert result_path.parent == tmp_path

    def test_export_uses_course_title_as_filename(self, exporter, simple_course):
        """Default filename should be based on course title."""
        result_path = exporter.export(simple_course)

        # Title is "SCORM Test Course"
        assert "SCORM_Test_Course" in result_path.stem or "SCORM Test Course" in result_path.stem

    def test_export_uses_custom_filename(self, exporter, simple_course):
        """Custom filename parameter should be used."""
        result_path = exporter.export(simple_course, filename="my_custom_package")

        assert result_path.stem == "my_custom_package"


class TestIMSManifest:
    """Tests for imsmanifest.xml generation."""

    def test_manifest_exists_in_package(self, exporter, simple_course):
        """Package should contain imsmanifest.xml at root."""
        result_path = exporter.export(simple_course)

        with zipfile.ZipFile(result_path, 'r') as zf:
            assert "imsmanifest.xml" in zf.namelist()

    def test_manifest_is_valid_xml(self, exporter, simple_course):
        """imsmanifest.xml should be valid XML."""
        result_path = exporter.export(simple_course)

        with zipfile.ZipFile(result_path, 'r') as zf:
            manifest_bytes = zf.read("imsmanifest.xml")
            # Should not raise exception
            root = ET.fromstring(manifest_bytes)
            assert root is not None

    def test_manifest_has_scorm_1_2_schema(self, exporter, simple_course):
        """Manifest should reference SCORM 1.2 schema with schemaversion 1.2."""
        result_path = exporter.export(simple_course)

        with zipfile.ZipFile(result_path, 'r') as zf:
            manifest_bytes = zf.read("imsmanifest.xml")
            manifest_str = manifest_bytes.decode('utf-8')

            # Check for SCORM 1.2 identifiers
            assert "ADL SCORM" in manifest_str or "adlcp" in manifest_str.lower()
            # schemaversion should be "1.2"
            assert "<schemaversion>1.2</schemaversion>" in manifest_str

    def test_manifest_has_course_identifier(self, exporter, simple_course):
        """Manifest should include course identifier."""
        result_path = exporter.export(simple_course)

        with zipfile.ZipFile(result_path, 'r') as zf:
            manifest_bytes = zf.read("imsmanifest.xml")
            manifest_str = manifest_bytes.decode('utf-8')

            # Course ID should appear in manifest
            assert simple_course.id in manifest_str

    def test_manifest_has_course_title(self, exporter, simple_course):
        """Manifest should include course title in metadata."""
        result_path = exporter.export(simple_course)

        with zipfile.ZipFile(result_path, 'r') as zf:
            manifest_bytes = zf.read("imsmanifest.xml")
            manifest_str = manifest_bytes.decode('utf-8')

            assert simple_course.title in manifest_str

    def test_manifest_has_organizations_element(self, exporter, simple_course):
        """Manifest should have organizations element with course structure."""
        result_path = exporter.export(simple_course)

        with zipfile.ZipFile(result_path, 'r') as zf:
            manifest_bytes = zf.read("imsmanifest.xml")
            root = ET.fromstring(manifest_bytes)

            # Find organizations element (may need namespace handling)
            orgs = root.find('.//{http://www.imsproject.org/xsd/imscp_rootv1p1p2}organizations')
            if orgs is None:
                # Try without namespace
                orgs = root.find('.//organizations')

            assert orgs is not None

    def test_manifest_has_resources_element(self, exporter, simple_course):
        """Manifest should have resources element."""
        result_path = exporter.export(simple_course)

        with zipfile.ZipFile(result_path, 'r') as zf:
            manifest_bytes = zf.read("imsmanifest.xml")
            root = ET.fromstring(manifest_bytes)

            # Find resources element
            resources = root.find('.//{http://www.imsproject.org/xsd/imscp_rootv1p1p2}resources')
            if resources is None:
                resources = root.find('.//resources')

            assert resources is not None

    def test_manifest_resources_have_scormtype_sco(self, exporter, simple_course):
        """Resource elements should have adlcp:scormtype='sco'."""
        result_path = exporter.export(simple_course)

        with zipfile.ZipFile(result_path, 'r') as zf:
            manifest_bytes = zf.read("imsmanifest.xml")
            manifest_str = manifest_bytes.decode('utf-8')

            # Check for scormtype="sco" (lowercase 't' per SCORM 1.2 spec)
            assert 'scormtype="sco"' in manifest_str.lower() or "scormtype='sco'" in manifest_str.lower()


class TestHTMLContentPages:
    """Tests for HTML content page generation."""

    def test_html_pages_exist_for_each_lesson(self, exporter, simple_course):
        """Package should contain HTML page for each lesson."""
        result_path = exporter.export(simple_course)

        with zipfile.ZipFile(result_path, 'r') as zf:
            names = zf.namelist()

            # Should have content/module_1/lesson_1.html pattern
            html_files = [n for n in names if n.endswith('.html')]
            assert len(html_files) >= 1

    def test_html_pages_in_module_directories(self, exporter, multi_module_course):
        """HTML pages should be organized in content/module_X directories."""
        result_path = exporter.export(multi_module_course)

        with zipfile.ZipFile(result_path, 'r') as zf:
            names = zf.namelist()

            # Check for module directory structure
            content_files = [n for n in names if n.startswith('content/')]
            assert len(content_files) >= 2  # Multiple modules

            # Check for module directories
            module_dirs = set()
            for f in content_files:
                parts = f.split('/')
                if len(parts) >= 2:
                    module_dirs.add(parts[1])
            assert len(module_dirs) >= 2  # module_1, module_2

    def test_html_page_contains_lesson_title(self, exporter, simple_course):
        """HTML page should contain the lesson title."""
        result_path = exporter.export(simple_course)

        with zipfile.ZipFile(result_path, 'r') as zf:
            # Find HTML files
            html_files = [n for n in zf.namelist() if n.endswith('.html')]
            assert len(html_files) >= 1

            html_content = zf.read(html_files[0]).decode('utf-8')
            assert "Getting Started" in html_content

    def test_html_page_contains_activity_content(self, exporter, simple_course):
        """HTML page should contain activity content."""
        result_path = exporter.export(simple_course)

        with zipfile.ZipFile(result_path, 'r') as zf:
            html_files = [n for n in zf.namelist() if n.endswith('.html')]
            html_content = zf.read(html_files[0]).decode('utf-8')

            # Activity content should be present
            assert "Welcome to the course" in html_content or "introductory video" in html_content

    def test_html_page_is_valid_html(self, exporter, simple_course):
        """HTML pages should be valid HTML with doctype."""
        result_path = exporter.export(simple_course)

        with zipfile.ZipFile(result_path, 'r') as zf:
            html_files = [n for n in zf.namelist() if n.endswith('.html')]
            html_content = zf.read(html_files[0]).decode('utf-8')

            assert "<!DOCTYPE html>" in html_content or "<!doctype html>" in html_content.lower()
            assert "<html" in html_content
            assert "</html>" in html_content
            assert "<head>" in html_content
            assert "<body>" in html_content


class TestSharedStylesheet:
    """Tests for shared CSS stylesheet."""

    def test_stylesheet_exists_in_package(self, exporter, simple_course):
        """Package should contain shared/style.css."""
        result_path = exporter.export(simple_course)

        with zipfile.ZipFile(result_path, 'r') as zf:
            assert "shared/style.css" in zf.namelist()

    def test_html_pages_reference_stylesheet(self, exporter, simple_course):
        """HTML pages should reference the shared stylesheet."""
        result_path = exporter.export(simple_course)

        with zipfile.ZipFile(result_path, 'r') as zf:
            html_files = [n for n in zf.namelist() if n.endswith('.html')]
            html_content = zf.read(html_files[0]).decode('utf-8')

            # Should have link to stylesheet (relative path)
            assert "style.css" in html_content

    def test_stylesheet_has_basic_styles(self, exporter, simple_course):
        """Stylesheet should contain basic CSS rules."""
        result_path = exporter.export(simple_course)

        with zipfile.ZipFile(result_path, 'r') as zf:
            css_content = zf.read("shared/style.css").decode('utf-8')

            # Should have some basic CSS
            assert "body" in css_content
            assert "{" in css_content and "}" in css_content


class TestMultiModuleCourse:
    """Tests for courses with multiple modules and lessons."""

    def test_all_modules_have_content_directories(self, exporter, multi_module_course):
        """Each module should have its own content directory."""
        result_path = exporter.export(multi_module_course)

        with zipfile.ZipFile(result_path, 'r') as zf:
            names = zf.namelist()

            # Check for module directories
            module_1_files = [n for n in names if 'module_1' in n or 'module_0' in n]
            module_2_files = [n for n in names if 'module_2' in n or 'module_1' in n]

            assert len(module_1_files) >= 1
            assert len(module_2_files) >= 1

    def test_all_lessons_have_html_files(self, exporter, multi_module_course):
        """Each lesson should have an HTML file."""
        result_path = exporter.export(multi_module_course)

        with zipfile.ZipFile(result_path, 'r') as zf:
            html_files = [n for n in zf.namelist() if n.endswith('.html')]

            # multi_module_course has 3 lessons total
            assert len(html_files) >= 3

    def test_manifest_reflects_full_structure(self, exporter, multi_module_course):
        """Manifest organizations should reflect complete course structure."""
        result_path = exporter.export(multi_module_course)

        with zipfile.ZipFile(result_path, 'r') as zf:
            manifest_str = zf.read("imsmanifest.xml").decode('utf-8')

            # All module titles should be in manifest
            assert "Introduction" in manifest_str
            assert "Core Concepts" in manifest_str

            # All lesson titles should be in manifest
            assert "Overview" in manifest_str
            assert "Prerequisites" in manifest_str
            assert "Fundamentals" in manifest_str


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_export_empty_course_raises_error(self, exporter):
        """Exporting course with no modules should raise ValueError."""
        empty_course = Course(id="empty", title="Empty Course")

        with pytest.raises(ValueError) as exc_info:
            exporter.export(empty_course)

        assert "no modules" in str(exc_info.value).lower() or "empty" in str(exc_info.value).lower()

    def test_special_characters_in_title_handled(self, exporter, tmp_path):
        """Course titles with special characters should be handled."""
        course = Course(
            id="course_special",
            title="Test: A <Course> & More!",  # Special chars
        )
        module = Module(id="mod_1", title="Module 1")
        lesson = Lesson(id="les_1", title="Lesson 1")
        activity = Activity(
            id="act_1",
            title="Activity 1",
            content_type=ContentType.VIDEO,
            content="Content here",
            build_state=BuildState.APPROVED,
        )
        lesson.activities.append(activity)
        module.lessons.append(lesson)
        course.modules.append(module)

        # Should not raise
        result_path = exporter.export(course)
        assert result_path.exists()

        # Manifest should properly escape special chars in XML
        with zipfile.ZipFile(result_path, 'r') as zf:
            manifest_str = zf.read("imsmanifest.xml").decode('utf-8')
            # Should be valid XML (special chars escaped)
            ET.fromstring(manifest_str.encode('utf-8'))

    def test_unicode_content_handled(self, exporter, tmp_path):
        """Unicode content should be properly handled."""
        course = Course(
            id="course_unicode",
            title="Unicode Course",
        )
        module = Module(id="mod_1", title="Module 1")
        lesson = Lesson(id="les_1", title="Lesson 1")
        activity = Activity(
            id="act_1",
            title="Activity with Unicode",
            content_type=ContentType.VIDEO,
            content="Content with unicode: cafe, resume, naive, and symbols",
            build_state=BuildState.APPROVED,
        )
        lesson.activities.append(activity)
        module.lessons.append(lesson)
        course.modules.append(module)

        result_path = exporter.export(course)
        assert result_path.exists()

        # Content should be readable
        with zipfile.ZipFile(result_path, 'r') as zf:
            html_files = [n for n in zf.namelist() if n.endswith('.html')]
            html_content = zf.read(html_files[0]).decode('utf-8')
            assert "unicode" in html_content.lower()
