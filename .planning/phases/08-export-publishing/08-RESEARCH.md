# Phase 8: Export & Publishing - Research

**Researched:** 2026-02-06
**Domain:** Document generation, archive packaging, LMS interoperability
**Confidence:** HIGH (core libraries verified via official docs)

## Summary

Phase 8 implements four export formats: instructor ZIP bundles, LMS JSON manifests, DOCX textbooks, and SCORM 1.2 packages. The research confirms Python's standard library handles ZIP creation (zipfile) while python-docx (v1.2.0) provides mature DOCX generation capabilities. SCORM 1.2 requires generating an imsmanifest.xml file following the IMS Content Packaging specification, which can be done with standard XML generation (no special library needed).

The Flask send_file pattern with BytesIO enables in-memory file streaming to avoid disk I/O during export. The existing validation system (ValidationReport) provides the pre-export content verification infrastructure.

**Primary recommendation:** Use python-docx for DOCX, standard zipfile for ZIP/SCORM packages, generate imsmanifest.xml using Python's xml.etree.ElementTree, and serve downloads via Flask send_file with BytesIO.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python-docx | 1.2.0 | DOCX file generation | Industry standard for Python Word document creation. Supports headings, paragraphs, tables, images, styles. Official docs at python-docx.readthedocs.io |
| zipfile | stdlib | ZIP archive creation | Python standard library. Supports compression, in-memory creation with BytesIO, streaming writes |
| xml.etree.ElementTree | stdlib | imsmanifest.xml generation | Python standard library. Sufficient for SCORM manifest XML creation without external dependencies |
| io.BytesIO | stdlib | In-memory file buffers | Required for streaming downloads without disk I/O. Works with Flask send_file |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Flask send_file | (Flask) | HTTP file downloads | Serve generated exports to browser with proper Content-Disposition headers |
| json | stdlib | LMS manifest generation | Standard JSON serialization for LMS manifest format |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| python-docx | docxtpl (python-docx-template) | docxtpl adds Jinja2 templating, but we're generating programmatically, not from templates |
| xml.etree.ElementTree | lxml | lxml offers better XPath/validation, but overkill for simple manifest generation |
| Custom SCORM generator | SCORM Cloud API | Cloud API requires external service; we need offline/local package creation |

**Installation:**
```bash
pip install python-docx==1.2.0
```

## Architecture Patterns

### Recommended Project Structure

```
src/
├── exporters/               # Export functionality
│   ├── __init__.py
│   ├── base_exporter.py     # Abstract base class
│   ├── instructor_package.py # ZIP with syllabus, rubrics, quizzes
│   ├── lms_manifest.py      # JSON course hierarchy
│   ├── docx_textbook.py     # DOCX textbook generation
│   ├── scorm_package.py     # SCORM 1.2 package
│   └── export_validator.py  # Pre-export content verification
├── api/
│   └── export.py            # Export API blueprint
```

### Pattern 1: Exporter Base Class

**What:** Abstract base with common validation, progress tracking, and error handling
**When to use:** All exporters inherit from this base
**Example:**
```python
# Source: Pattern derived from existing BaseGenerator
from abc import ABC, abstractmethod
from typing import Tuple, Dict, Any
from io import BytesIO

class BaseExporter(ABC):
    """Base class for all export formats."""

    @abstractmethod
    def export(self, course: Course) -> Tuple[BytesIO, str]:
        """Export course to format.

        Returns:
            Tuple of (file_buffer, filename)
        """
        pass

    def validate_content(self, course: Course) -> List[str]:
        """Check all referenced content exists before export.

        Returns:
            List of missing content descriptions (empty if valid)
        """
        missing = []
        for module in course.modules:
            for lesson in module.lessons:
                for activity in lesson.activities:
                    if not activity.content:
                        missing.append(f"{module.title}/{lesson.title}/{activity.title}")
        return missing
```

### Pattern 2: In-Memory ZIP Creation

**What:** Create ZIP archives entirely in memory using BytesIO + zipfile
**When to use:** All ZIP-based exports (instructor package, SCORM)
**Example:**
```python
# Source: Python official docs + Flask community patterns
from io import BytesIO
import zipfile

def create_zip_buffer(files: Dict[str, bytes]) -> BytesIO:
    """Create ZIP archive in memory.

    Args:
        files: Dict mapping archive paths to file contents

    Returns:
        BytesIO buffer positioned at start
    """
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for path, content in files.items():
            zf.writestr(path, content)
    buffer.seek(0)  # CRITICAL: Reset position for reading
    return buffer
```

### Pattern 3: Flask File Download

**What:** Stream in-memory files to browser with proper headers
**When to use:** All export download endpoints
**Example:**
```python
# Source: Flask official documentation
from flask import send_file
from io import BytesIO

@export_bp.route('/api/courses/<course_id>/export/instructor', methods=['GET'])
def download_instructor_package(course_id):
    """Download instructor package as ZIP."""
    buffer = exporter.export(course)  # Returns BytesIO
    return send_file(
        buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'{course.title}_instructor.zip'
    )
```

### Pattern 4: DOCX Document Structure

**What:** Use python-docx styles for consistent formatting
**When to use:** Textbook DOCX generation
**Example:**
```python
# Source: python-docx official documentation
from docx import Document
from docx.shared import Inches, Pt

def create_textbook_docx(chapters: List[TextbookChapter]) -> BytesIO:
    """Generate DOCX textbook from chapters."""
    doc = Document()

    for chapter in chapters:
        # Chapter title as Heading 1
        doc.add_heading(chapter.title, level=1)

        # Introduction paragraph
        doc.add_paragraph(chapter.introduction)

        # Sections with Heading 2
        for section in chapter.sections:
            doc.add_heading(section['heading'], level=2)
            doc.add_paragraph(section['content'])

        # Page break between chapters
        doc.add_page_break()

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer
```

### Anti-Patterns to Avoid

- **Writing to disk then reading:** Always use BytesIO for in-memory generation. Disk I/O is slower and creates cleanup issues.
- **Not seeking BytesIO to start:** After writing to BytesIO, position is at end. Must call `buffer.seek(0)` before sending.
- **Forgetting ZipFile close:** Always use `with` statement. ZipFile writes central directory on close.
- **Hardcoded file paths in SCORM:** All paths in imsmanifest.xml must be relative to package root.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| DOCX generation | Custom XML manipulation | python-docx | OOXML is complex; python-docx handles styles, sections, headers properly |
| ZIP compression | Manual file concatenation | zipfile stdlib | ZIP format has specific headers, CRC checks, central directory |
| XML generation | String concatenation | xml.etree.ElementTree | Proper escaping, encoding, well-formed output |
| Content-Type headers | Manual header construction | Flask send_file | Handles MIME types, Content-Disposition, streaming automatically |

**Key insight:** Export formats (DOCX, ZIP, SCORM) have strict specifications. Hand-rolling produces files that work in some readers but fail in others. Use established libraries.

## Common Pitfalls

### Pitfall 1: SCORM 1.2 vs 2004 Confusion

**What goes wrong:** Using SCORM 2004 attributes/elements in a 1.2 manifest causes LMS import failures
**Why it happens:** Documentation often mixes versions; developers copy-paste wrong examples
**How to avoid:**
- Use `adlcp:scormtype="sco"` (lowercase 't') for SCORM 1.2
- Don't use SCORM 2004 completion_status variables
- Schema version must be exactly "1.2"
**Warning signs:** LMS import errors mentioning "invalid attribute" or "schema validation failed"

### Pitfall 2: BytesIO Position Not Reset

**What goes wrong:** Flask sends empty file; browser downloads 0-byte file
**Why it happens:** After writing to BytesIO, read position is at end. `send_file` reads from current position.
**How to avoid:** Always call `buffer.seek(0)` before returning buffer
**Warning signs:** Empty downloads, correct Content-Length but no content

### Pitfall 3: UTF-8 Filename Issues in ZIP

**What goes wrong:** Files with non-ASCII names cause extraction errors
**Why it happens:** ZIP format originally used CP437 encoding; UTF-8 support varies
**How to avoid:**
- Sanitize filenames to ASCII-safe characters
- Replace spaces with underscores
- Remove special characters
**Warning signs:** "Invalid filename" errors on extraction, garbled filenames

### Pitfall 4: Missing Content in Export

**What goes wrong:** Export contains empty placeholders or missing files
**Why it happens:** Activities with DRAFT build_state have no generated content
**How to avoid:**
- Pre-validate that all activities have content
- Warn user of missing content before export
- Use existing ValidationReport.is_publishable() check
**Warning signs:** Empty sections in DOCX, missing resource files in SCORM

### Pitfall 5: SCORM Suspend Data Size

**What goes wrong:** Course progress doesn't save; "suspend_data exceeds maximum" errors
**Why it happens:** SCORM 1.2 limits suspend_data to 4096 characters
**How to avoid:** Keep SCO simple; don't try to store detailed progress in suspend_data
**Warning signs:** LMS errors about "LMSSetValue" or "suspend_data"

### Pitfall 6: python-docx Image Path Issues

**What goes wrong:** Images fail to embed or appear broken
**Why it happens:** Image paths must be valid at generation time
**How to avoid:**
- TextbookChapter uses image_placeholders with figure numbers and captions
- Generate placeholder text or skip images for now
- If implementing image support later, use absolute paths or embed base64
**Warning signs:** "File not found" errors, broken image icons in DOCX

## Code Examples

Verified patterns from official sources:

### SCORM 1.2 imsmanifest.xml Generation

```python
# Source: SCORM.com specification examples
import xml.etree.ElementTree as ET
from xml.dom import minidom

def generate_scorm_manifest(course: Course, resources: List[str]) -> str:
    """Generate SCORM 1.2 imsmanifest.xml.

    Args:
        course: Course object
        resources: List of file paths relative to package root

    Returns:
        XML string for imsmanifest.xml
    """
    # Namespaces
    NSMAP = {
        '': 'http://www.imsproject.org/xsd/imscp_rootv1p1p2',
        'adlcp': 'http://www.adlnet.org/xsd/adlcp_rootv1p2',
        'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
    }

    # Create manifest root
    manifest = ET.Element('manifest')
    manifest.set('identifier', f'course_{course.id}')
    manifest.set('version', '1')
    manifest.set('xmlns', NSMAP[''])
    manifest.set('xmlns:adlcp', NSMAP['adlcp'])
    manifest.set('xmlns:xsi', NSMAP['xsi'])

    # Metadata
    metadata = ET.SubElement(manifest, 'metadata')
    schema = ET.SubElement(metadata, 'schema')
    schema.text = 'ADL SCORM'
    schemaversion = ET.SubElement(metadata, 'schemaversion')
    schemaversion.text = '1.2'

    # Organizations
    organizations = ET.SubElement(manifest, 'organizations')
    organizations.set('default', 'org_default')

    org = ET.SubElement(organizations, 'organization')
    org.set('identifier', 'org_default')

    title = ET.SubElement(org, 'title')
    title.text = course.title

    # Create items for each module
    for module in course.modules:
        item = ET.SubElement(org, 'item')
        item.set('identifier', f'item_{module.id}')
        item.set('identifierref', f'res_{module.id}')
        item_title = ET.SubElement(item, 'title')
        item_title.text = module.title

    # Resources
    resources_elem = ET.SubElement(manifest, 'resources')
    for module in course.modules:
        resource = ET.SubElement(resources_elem, 'resource')
        resource.set('identifier', f'res_{module.id}')
        resource.set('type', 'webcontent')
        resource.set('adlcp:scormtype', 'sco')
        resource.set('href', f'modules/{module.id}/index.html')

    # Format with indentation
    xml_str = ET.tostring(manifest, encoding='unicode')
    dom = minidom.parseString(xml_str)
    return dom.toprettyxml(indent='  ')
```

### Instructor Package Contents

```python
# Source: Architecture based on course content types
def create_instructor_package(course: Course) -> Dict[str, bytes]:
    """Create files for instructor package ZIP.

    Returns:
        Dict mapping archive paths to file contents
    """
    files = {}

    # Syllabus (course overview)
    files['syllabus.txt'] = generate_syllabus(course).encode('utf-8')

    # Lesson plans (one per lesson)
    for module in course.modules:
        for lesson in module.lessons:
            path = f'lesson_plans/{module.title}/{lesson.title}.txt'
            files[path] = generate_lesson_plan(lesson).encode('utf-8')

    # Rubrics (for graded activities)
    for module in course.modules:
        for lesson in module.lessons:
            for activity in lesson.activities:
                if activity.content_type == ContentType.RUBRIC:
                    path = f'rubrics/{activity.title}.txt'
                    content = json.loads(activity.content)
                    files[path] = format_rubric(content).encode('utf-8')

    # Quizzes with answer keys
    for module in course.modules:
        for lesson in module.lessons:
            for activity in lesson.activities:
                if activity.content_type == ContentType.QUIZ:
                    quiz = json.loads(activity.content)
                    # Quiz questions (student version)
                    files[f'quizzes/{activity.title}_questions.txt'] = \
                        format_quiz_questions(quiz).encode('utf-8')
                    # Answer key (instructor only)
                    files[f'answer_keys/{activity.title}_key.txt'] = \
                        format_quiz_answers(quiz).encode('utf-8')

    # Textbook (assembled from chapters)
    if course.textbook_chapters:
        textbook_buffer = create_textbook_docx(course.textbook_chapters)
        files['textbook.docx'] = textbook_buffer.getvalue()

    return files
```

### LMS Manifest JSON Structure

```python
# Source: Derived from course model hierarchy
def generate_lms_manifest(course: Course) -> Dict[str, Any]:
    """Generate LMS manifest as structured JSON.

    Provides complete course hierarchy for LMS import.
    """
    return {
        "version": "1.0",
        "course": {
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "audience_level": course.audience_level,
            "duration_minutes": course.target_duration_minutes,
            "learning_outcomes": [
                {
                    "id": lo.id,
                    "behavior": lo.behavior,
                    "bloom_level": lo.bloom_level.value,
                    "mapped_activities": lo.mapped_activity_ids
                }
                for lo in course.learning_outcomes
            ],
            "modules": [
                {
                    "id": module.id,
                    "title": module.title,
                    "order": module.order,
                    "lessons": [
                        {
                            "id": lesson.id,
                            "title": lesson.title,
                            "order": lesson.order,
                            "activities": [
                                {
                                    "id": activity.id,
                                    "title": activity.title,
                                    "content_type": activity.content_type.value,
                                    "activity_type": activity.activity_type.value,
                                    "duration_minutes": activity.estimated_duration_minutes,
                                    "bloom_level": activity.bloom_level.value if activity.bloom_level else None
                                }
                                for activity in lesson.activities
                            ]
                        }
                        for lesson in module.lessons
                    ]
                }
                for module in course.modules
            ]
        }
    }
```

### Export Preview Data

```python
# Source: Derived from export requirements
def generate_export_preview(course: Course, format: str) -> Dict[str, Any]:
    """Generate preview of export contents before download.

    Args:
        course: Course to preview
        format: Export format (instructor, lms, docx, scorm)

    Returns:
        Preview data including file list and validation status
    """
    preview = {
        "format": format,
        "course_id": course.id,
        "course_title": course.title,
        "files": [],
        "warnings": [],
        "errors": []
    }

    # Check content completeness
    missing = validate_content_exists(course)
    if missing:
        preview["errors"].extend([f"Missing content: {m}" for m in missing])

    # Check validation status
    from src.validators.validation_report import ValidationReport
    validator = ValidationReport()
    if not validator.is_publishable(course):
        preview["warnings"].append("Course has validation issues")

    # List files that would be generated
    if format == "instructor":
        preview["files"] = list_instructor_package_files(course)
    elif format == "scorm":
        preview["files"] = list_scorm_package_files(course)
    elif format == "docx":
        preview["files"] = [f"{course.title}_textbook.docx"]
    elif format == "lms":
        preview["files"] = [f"{course.title}_manifest.json"]

    preview["ready"] = len(preview["errors"]) == 0

    return preview
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SCORM 1.2 only | SCORM 2004 / xAPI | ~2013+ | Modern LMS support both; 1.2 still most compatible |
| Disk-based file generation | In-memory streaming | Python 3.x | Better performance, no temp file cleanup |
| Custom XML strings | ElementTree / lxml | Long established | Proper escaping, encoding, well-formedness |
| DOC format | DOCX format | Word 2007+ | OOXML is open standard, python-docx supports |

**Deprecated/outdated:**
- SCORM 1.1: Superseded by 1.2; minimal LMS support
- AICC: Legacy standard; SCORM replaced it
- Binary DOC format: Use DOCX (OOXML) instead

## Open Questions

Things that couldn't be fully resolved:

1. **Image embedding in DOCX**
   - What we know: python-docx supports add_picture() with file paths or BytesIO
   - What's unclear: TextbookChapter has image_placeholders but no actual image data
   - Recommendation: Generate placeholder text "[Figure X: caption]" for v1; image embedding can be Phase 12 polish

2. **SCORM Content HTML Generation**
   - What we know: SCORM packages need launchable HTML content, not just manifest
   - What's unclear: Should we generate static HTML views of content or simple wrapper?
   - Recommendation: Generate minimal HTML wrapper that displays content; full SCORM player is out of scope for v1

3. **LMS Manifest Standard Format**
   - What we know: No universal JSON LMS import format; SCORM uses XML
   - What's unclear: Which LMS systems (Canvas, Moodle, Blackboard) accept JSON imports?
   - Recommendation: Create custom JSON format documenting structure; can add IMS Common Cartridge in v2

## Sources

### Primary (HIGH confidence)

- [python-docx 1.2.0 documentation](https://python-docx.readthedocs.io/) - Document creation, styles, paragraphs, headings
- [Python zipfile documentation](https://docs.python.org/3/library/zipfile.html) - ZIP archive creation
- [SCORM.com Content Packaging](https://scorm.com/scorm-explained/technical-scorm/content-packaging/) - Manifest structure specification
- [SCORM 1.2 imsmanifest.xml example](https://scorm.com/wp-content/assets/golf_examples/Examples/ContentPackagingSingleSCO/SCORM%201.2/imsmanifest.xml) - Official SCORM example

### Secondary (MEDIUM confidence)

- [Flask send_file patterns](https://gist.github.com/dmitru/05b7efb94fd23637a451) - In-memory ZIP streaming
- [SCORM troubleshooting guide](https://doctorelearning.com/blog/guide-for-troubleshooting-scorm/) - Common validation errors

### Tertiary (LOW confidence)

- LMS JSON import format: No authoritative standard found; custom format recommended

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Official documentation verified for all libraries
- Architecture: HIGH - Patterns derived from existing codebase and official Flask/python-docx docs
- Pitfalls: MEDIUM - Synthesized from multiple troubleshooting sources and SCORM specification

**Research date:** 2026-02-06
**Valid until:** 2026-03-06 (30 days - stable libraries)
