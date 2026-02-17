"""SCORM package parser for content import.

Parses SCORM 1.2 and 2004 packages using lxml for XML parsing.
Handles non-root manifest locations per RESEARCH.md guidance.
"""

from datetime import datetime
from typing import Union
import zipfile
import io
import os

try:
    from lxml import etree
    LXML_AVAILABLE = True
except ImportError:
    LXML_AVAILABLE = False

from .base_parser import BaseParser, ParseResult


class SCORMParser(BaseParser):
    """Parser for SCORM packages.

    Extracts course structure from imsmanifest.xml in SCORM ZIP files.
    Searches for manifest at any depth to handle wrapper folders.
    """

    # SCORM XML namespaces
    NAMESPACES = {
        'imscp': 'http://www.imsglobal.org/xsd/imscp_v1p1',
        'adlcp': 'http://www.adlnet.org/xsd/adlcp_v1p3',
        'imsmd': 'http://www.imsglobal.org/xsd/imsmd_v1p2'
    }

    def can_parse(self, source: Union[str, bytes], filename: str = None) -> bool:
        """Detect if source is a SCORM package.

        Args:
            source: ZIP file bytes
            filename: Optional filename for extension checking

        Returns:
            True if source is a ZIP with imsmanifest.xml
        """
        if not LXML_AVAILABLE:
            return False

        # Check filename extension
        if filename and filename.lower().endswith('.zip'):
            # Need to check contents for imsmanifest.xml
            pass

        # Check if it's a ZIP file
        if not isinstance(source, bytes):
            return False

        if len(source) < 4 or source[:2] != b'PK':
            return False

        # Check for imsmanifest.xml in ZIP
        try:
            zip_obj = zipfile.ZipFile(io.BytesIO(source))
            return self._find_manifest_path(zip_obj) is not None
        except (zipfile.BadZipFile, Exception):
            return False

    def parse(self, source: Union[str, bytes], filename: str = None) -> ParseResult:
        """Parse SCORM package into course structure.

        Args:
            source: SCORM ZIP file bytes
            filename: Optional filename for provenance

        Returns:
            ParseResult with course structure

        Raises:
            ValueError: If source cannot be parsed as SCORM
        """
        if not LXML_AVAILABLE:
            raise ValueError("lxml library not installed")

        if not isinstance(source, bytes):
            raise ValueError("Source must be bytes for SCORM parsing")

        warnings = []

        # Open ZIP
        try:
            zip_file = zipfile.ZipFile(io.BytesIO(source))
        except zipfile.BadZipFile:
            raise ValueError("Source is not a valid ZIP file")

        # Find manifest (may not be at root)
        manifest_path = self._find_manifest_path(zip_file)
        if not manifest_path:
            raise ValueError("No imsmanifest.xml found in SCORM package")

        # Calculate package root (directory containing manifest)
        package_root = os.path.dirname(manifest_path)
        if package_root:
            warnings.append(f"Non-standard structure: manifest at {manifest_path}")

        # Parse manifest XML
        manifest_xml = zip_file.read(manifest_path)
        try:
            tree = etree.fromstring(manifest_xml)
        except etree.XMLSyntaxError as e:
            raise ValueError(f"Invalid manifest XML: {e}")

        # Extract metadata
        metadata_elem = tree.find('.//imscp:metadata', self.NAMESPACES)
        schema_version = 'unknown'
        if metadata_elem is not None:
            version_elem = metadata_elem.find('.//adlcp:schemaversion', self.NAMESPACES)
            if version_elem is not None and version_elem.text:
                schema_version = version_elem.text.strip()

        # Extract organizations (course structure)
        orgs = tree.find('.//imscp:organizations', self.NAMESPACES)
        if orgs is None:
            raise ValueError("No organizations found in manifest")

        default_org = orgs.get('default')
        if not default_org:
            # Use first organization
            first_org = orgs.find('.//imscp:organization', self.NAMESPACES)
            if first_org is not None:
                default_org = first_org.get('identifier')

        org = None
        if default_org:
            org = orgs.find(f'.//imscp:organization[@identifier="{default_org}"]', self.NAMESPACES)
        if org is None:
            # Fallback: use first organization
            org = orgs.find('.//imscp:organization', self.NAMESPACES)

        if org is None:
            raise ValueError("No organization found in manifest")

        # Get organization title
        title_elem = org.find('.//imscp:title', self.NAMESPACES)
        course_title = title_elem.text if title_elem is not None and title_elem.text else 'Untitled Course'

        # Parse items (modules/lessons hierarchy)
        modules = self._parse_items(org, package_root)

        # Extract resources
        resources_elem = tree.find('.//imscp:resources', self.NAMESPACES)
        resources = {}
        if resources_elem is not None:
            for res in resources_elem.findall('.//imscp:resource', self.NAMESPACES):
                res_id = res.get('identifier')
                if res_id:
                    files = [f.get('href') for f in res.findall('.//imscp:file', self.NAMESPACES) if f.get('href')]
                    resources[res_id] = {
                        'type': res.get('type', 'unknown'),
                        'href': res.get('href', ''),
                        'files': files
                    }

        # Extract content from HTML resources
        content_html = self._extract_html_content(zip_file, resources, package_root)

        # Metadata
        metadata = {
            'scorm_version': schema_version,
            'module_count': len(modules),
            'resource_count': len(resources),
            'format': 'scorm',
            'package_root': package_root or '/'
        }

        content = {
            'title': course_title,
            'modules': modules,
            'resources': resources,
            'html_content': content_html
        }

        provenance = {
            'filename': filename or 'unknown.zip',
            'import_time': datetime.now().isoformat(),
            'original_format': 'scorm',
            'parser': 'SCORMParser',
            'manifest_path': manifest_path
        }

        return ParseResult(
            content_type='blueprint',
            content=content,
            metadata=metadata,
            warnings=warnings,
            provenance=provenance
        )

    def _find_manifest_path(self, zip_file):
        """Find imsmanifest.xml at any depth in ZIP.

        Args:
            zip_file: zipfile.ZipFile object

        Returns:
            Path to manifest, or None if not found
        """
        for name in zip_file.namelist():
            if name.endswith('imsmanifest.xml') and not name.startswith('__MACOSX'):
                return name
        return None

    def _parse_items(self, parent_elem, package_root, level=0):
        """Recursively parse item hierarchy.

        Args:
            parent_elem: Parent XML element
            package_root: Root directory of package
            level: Nesting level (for structure detection)

        Returns:
            List of module/lesson dictionaries
        """
        items = []
        for item in parent_elem.findall('.//imscp:item', self.NAMESPACES):
            # Only process direct children
            if item.getparent() != parent_elem:
                continue

            title_elem = item.find('.//imscp:title', self.NAMESPACES)
            title = title_elem.text if title_elem is not None and title_elem.text else 'Untitled'

            item_data = {
                'identifier': item.get('identifier', ''),
                'title': title,
                'resource_ref': item.get('identifierref', ''),
                'children': self._parse_items(item, package_root, level + 1)
            }

            items.append(item_data)

        return items

    def _extract_html_content(self, zip_file, resources, package_root):
        """Extract HTML content from resources.

        Args:
            zip_file: zipfile.ZipFile object
            resources: Resource dictionary
            package_root: Root directory of package

        Returns:
            Dictionary of resource_id to HTML content
        """
        content = {}
        for res_id, res_data in resources.items():
            if res_data['href'] and res_data['href'].endswith('.html'):
                # Adjust path relative to package root
                if package_root:
                    file_path = os.path.join(package_root, res_data['href']).replace('\\', '/')
                else:
                    file_path = res_data['href']

                try:
                    html_bytes = zip_file.read(file_path)
                    content[res_id] = html_bytes.decode('utf-8', errors='ignore')
                except (KeyError, UnicodeDecodeError):
                    pass  # Skip missing or unreadable files

        return content
