"""SCORM 1.2 package exporter for Course Builder Studio.

Generates SCORM 1.2 compliant packages with:
- imsmanifest.xml with proper schema references
- HTML content pages for each lesson
- Shared CSS stylesheet
"""

import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Optional
from html import escape as html_escape

from src.exporters.base_exporter import BaseExporter
from src.core.models import Course, Module, Lesson, Activity


class SCORMPackageExporter(BaseExporter):
    """Export course content as SCORM 1.2 compliant package.

    Creates a zip file containing:
    - imsmanifest.xml (SCORM 1.2 manifest with adlcp:scormtype="sco")
    - content/module_X/lesson_Y.html (HTML pages for each lesson)
    - shared/style.css (shared stylesheet)
    """

    # XML namespace URIs for SCORM 1.2
    NS_IMS = "http://www.imsproject.org/xsd/imscp_rootv1p1p2"
    NS_ADLCP = "http://www.adlnet.org/xsd/adlcp_rootv1p2"
    NS_XSI = "http://www.w3.org/2001/XMLSchema-instance"

    @property
    def format_name(self) -> str:
        """Human-readable name of the export format."""
        return "SCORM 1.2 Package"

    @property
    def file_extension(self) -> str:
        """File extension for exported files."""
        return ".zip"

    def export(self, course: Course, filename: Optional[str] = None) -> Path:
        """Export course as SCORM 1.2 package.

        Args:
            course: Course object to export.
            filename: Optional filename (without extension). If None, uses course title.

        Returns:
            Path to the exported zip file.

        Raises:
            ValueError: If course has no modules.
        """
        if not course.modules:
            raise ValueError("Cannot export course with no modules")

        output_path = self.get_output_path(course, filename)

        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Generate and add manifest
            manifest_xml = self._generate_manifest(course)
            zf.writestr("imsmanifest.xml", manifest_xml)

            # Generate and add content pages
            self._add_content_pages(zf, course)

            # Add shared stylesheet
            css_content = self._generate_stylesheet()
            zf.writestr("shared/style.css", css_content)

        return output_path

    def _generate_manifest(self, course: Course) -> str:
        """Generate imsmanifest.xml content.

        Args:
            course: Course to generate manifest for.

        Returns:
            XML string for imsmanifest.xml.
        """
        # Register namespaces to avoid ns0/ns1 prefixes
        ET.register_namespace('', self.NS_IMS)
        ET.register_namespace('adlcp', self.NS_ADLCP)
        ET.register_namespace('xsi', self.NS_XSI)

        # Root manifest element - use QName for proper namespace handling
        # Note: register_namespace handles xmlns declarations during serialization
        root = ET.Element('{%s}manifest' % self.NS_IMS, {
            'identifier': course.id,
            'version': '1.0',
            '{%s}schemaLocation' % self.NS_XSI: (
                f"{self.NS_IMS} imscp_rootv1p1p2.xsd "
                f"{self.NS_ADLCP} adlcp_rootv1p2.xsd"
            ),
        })

        # Metadata section
        metadata = ET.SubElement(root, 'metadata')
        schema = ET.SubElement(metadata, 'schema')
        schema.text = 'ADL SCORM'
        schemaversion = ET.SubElement(metadata, 'schemaversion')
        schemaversion.text = '1.2'

        # Add course title in lom metadata
        lom = ET.SubElement(metadata, 'lom')
        general = ET.SubElement(lom, 'general')
        title_elem = ET.SubElement(general, 'title')
        langstring = ET.SubElement(title_elem, 'langstring')
        langstring.set('xml:lang', 'en')
        langstring.text = course.title

        if course.description:
            desc_elem = ET.SubElement(general, 'description')
            desc_langstring = ET.SubElement(desc_elem, 'langstring')
            desc_langstring.set('xml:lang', 'en')
            desc_langstring.text = course.description

        # Organizations section
        organizations = ET.SubElement(root, 'organizations', {
            'default': f'org_{course.id}'
        })

        organization = ET.SubElement(organizations, 'organization', {
            'identifier': f'org_{course.id}'
        })
        org_title = ET.SubElement(organization, 'title')
        org_title.text = course.title

        # Build organization structure and collect resources
        resources_list = []

        for mod_idx, module in enumerate(course.modules):
            mod_item = ET.SubElement(organization, 'item', {
                'identifier': f'item_{module.id}'
            })
            mod_title = ET.SubElement(mod_item, 'title')
            mod_title.text = module.title

            for les_idx, lesson in enumerate(module.lessons):
                resource_id = f'res_module_{mod_idx}_lesson_{les_idx}'
                les_item = ET.SubElement(mod_item, 'item', {
                    'identifier': f'item_{lesson.id}',
                    'identifierref': resource_id
                })
                les_title = ET.SubElement(les_item, 'title')
                les_title.text = lesson.title

                # Track resource for later
                html_path = f'content/module_{mod_idx}/lesson_{les_idx}.html'
                resources_list.append({
                    'identifier': resource_id,
                    'href': html_path,
                    'lesson': lesson,
                })

        # Resources section
        resources = ET.SubElement(root, 'resources')

        for res_info in resources_list:
            resource = ET.SubElement(resources, 'resource', {
                'identifier': res_info['identifier'],
                'type': 'webcontent',
                '{%s}scormtype' % self.NS_ADLCP: 'sco',
                'href': res_info['href'],
            })
            # Add file reference
            file_elem = ET.SubElement(resource, 'file', {
                'href': res_info['href']
            })

        # Convert to string with XML declaration
        xml_str = ET.tostring(root, encoding='unicode', method='xml')
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str

    def _add_content_pages(self, zf: zipfile.ZipFile, course: Course) -> None:
        """Add HTML content pages for each lesson.

        Args:
            zf: ZipFile object to add pages to.
            course: Course to generate pages for.
        """
        for mod_idx, module in enumerate(course.modules):
            for les_idx, lesson in enumerate(module.lessons):
                html_content = self._generate_lesson_html(lesson, module, mod_idx)
                html_path = f'content/module_{mod_idx}/lesson_{les_idx}.html'
                zf.writestr(html_path, html_content)

    def _generate_lesson_html(
        self,
        lesson: Lesson,
        module: Module,
        module_index: int
    ) -> str:
        """Generate HTML page for a lesson.

        Args:
            lesson: Lesson to generate page for.
            module: Parent module.
            module_index: Index of module (for path calculation).

        Returns:
            HTML string for the lesson page.
        """
        # Escape title for HTML
        lesson_title = html_escape(lesson.title)
        module_title = html_escape(module.title)

        # Build activity content sections
        activity_sections = []
        for activity in lesson.activities:
            activity_title = html_escape(activity.title)
            # Escape content, preserve basic structure
            activity_content = html_escape(activity.content) if activity.content else ""
            content_type = activity.content_type.value.title()

            activity_sections.append(f'''
        <section class="activity">
            <h3>{activity_title}</h3>
            <p class="activity-type">{content_type}</p>
            <div class="activity-content">
                {activity_content}
            </div>
        </section>''')

        activities_html = '\n'.join(activity_sections)

        # Generate complete HTML page
        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{lesson_title}</title>
    <link rel="stylesheet" href="../../shared/style.css">
</head>
<body>
    <header>
        <nav class="breadcrumb">
            <span class="module">{module_title}</span> &gt;
            <span class="lesson">{lesson_title}</span>
        </nav>
    </header>

    <main>
        <h1>{lesson_title}</h1>
        {activities_html}
    </main>

    <footer>
        <p>Generated by Course Builder Studio</p>
    </footer>
</body>
</html>'''

        return html

    def _generate_stylesheet(self) -> str:
        """Generate shared CSS stylesheet.

        Returns:
            CSS string for shared/style.css.
        """
        return '''/* SCORM Package Stylesheet - Course Builder Studio */

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
    line-height: 1.6;
    color: #333;
    background-color: #f5f5f5;
    padding: 20px;
    max-width: 900px;
    margin: 0 auto;
}

header {
    margin-bottom: 30px;
    padding-bottom: 15px;
    border-bottom: 1px solid #ddd;
}

.breadcrumb {
    font-size: 0.9em;
    color: #666;
}

.breadcrumb .module {
    font-weight: 600;
    color: #444;
}

main {
    background: #fff;
    padding: 30px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

h1 {
    font-size: 1.8em;
    margin-bottom: 25px;
    color: #222;
}

h3 {
    font-size: 1.2em;
    margin-bottom: 10px;
    color: #333;
}

.activity {
    margin-bottom: 30px;
    padding-bottom: 20px;
    border-bottom: 1px solid #eee;
}

.activity:last-child {
    border-bottom: none;
    margin-bottom: 0;
    padding-bottom: 0;
}

.activity-type {
    font-size: 0.85em;
    color: #666;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 12px;
}

.activity-content {
    background: #fafafa;
    padding: 15px;
    border-radius: 4px;
    white-space: pre-wrap;
}

footer {
    margin-top: 30px;
    padding-top: 15px;
    border-top: 1px solid #ddd;
    text-align: center;
    font-size: 0.85em;
    color: #888;
}
'''
