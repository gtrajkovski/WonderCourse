"""QTI quiz parser for content import.

Parses QTI 2.1 XML for quiz questions and assessments.
"""

from datetime import datetime
from typing import Union

try:
    from lxml import etree
    LXML_AVAILABLE = True
except ImportError:
    LXML_AVAILABLE = False

from .base_parser import BaseParser, ParseResult


class QTIParser(BaseParser):
    """Parser for QTI (Question & Test Interoperability) files.

    Extracts quiz questions from QTI 2.1 XML format.
    Handles assessmentItem elements and choiceInteraction for MCQ.
    """

    # QTI XML namespaces
    NAMESPACES = {
        'qti': 'http://www.imsglobal.org/xsd/imsqti_v2p1',
        'qti2': 'http://www.imsglobal.org/xsd/imsqti_v2p2'
    }

    def can_parse(self, source: Union[str, bytes], filename: str = None) -> bool:
        """Detect if source is QTI XML.

        Args:
            source: XML string or bytes
            filename: Optional filename for extension checking

        Returns:
            True if source appears to be QTI XML
        """
        if not LXML_AVAILABLE:
            return False

        # Check filename extension
        if filename and filename.lower().endswith('.xml'):
            pass

        # Convert bytes to string
        if isinstance(source, bytes):
            source = source.decode('utf-8', errors='ignore')

        if not isinstance(source, str):
            return False

        # Check for QTI markers
        source_lower = source.lower()
        return (
            'assessmentitem' in source_lower or
            'assessmenttest' in source_lower or
            'qti' in source_lower
        ) and '<' in source and '>' in source

    def parse(self, source: Union[str, bytes], filename: str = None) -> ParseResult:
        """Parse QTI XML into quiz questions.

        Args:
            source: QTI XML string or bytes
            filename: Optional filename for provenance

        Returns:
            ParseResult with quiz questions

        Raises:
            ValueError: If source cannot be parsed as QTI
        """
        if not LXML_AVAILABLE:
            raise ValueError("lxml library not installed")

        if not self.can_parse(source, filename):
            raise ValueError("Source is not valid QTI XML")

        # Convert bytes to string
        if isinstance(source, bytes):
            xml_str = source.decode('utf-8', errors='ignore')
        else:
            xml_str = source

        warnings = []

        # Parse XML
        try:
            tree = etree.fromstring(xml_str.encode('utf-8'))
        except etree.XMLSyntaxError as e:
            raise ValueError(f"Invalid QTI XML: {e}")

        questions = []

        # Check if root element itself is an assessmentItem
        if tree.tag.endswith('assessmentItem') or tree.tag == 'assessmentItem':
            question = self._parse_assessment_item(tree, {}, '')
            if question:
                questions.append(question)

        # Try both QTI 2.1 and 2.2 namespaces for descendant items
        if not questions:
            for ns_key, ns_url in self.NAMESPACES.items():
                ns = {ns_key: ns_url}

                # Find all assessmentItem elements (descendants)
                items = tree.xpath(f'.//{ns_key}:assessmentItem', namespaces=ns)
                if not items:
                    # Try without namespace prefix
                    items = tree.xpath('.//assessmentItem')

                for item in items:
                    question = self._parse_assessment_item(item, ns, ns_key)
                    if question:
                        questions.append(question)

                if questions:
                    break  # Found questions, stop trying other namespaces

        # If no items found, try finding choiceInteraction directly
        if not questions:
            interactions = tree.xpath('.//choiceInteraction')
            for interaction in interactions:
                question = self._parse_choice_interaction(interaction, {})
                if question:
                    questions.append(question)

        if not questions:
            warnings.append("No quiz questions found in QTI XML")

        # Metadata
        metadata = {
            'question_count': len(questions),
            'format': 'qti',
            'version': self._detect_qti_version(xml_str)
        }

        content = {
            'questions': questions,
            'title': self._extract_title(tree, self.NAMESPACES)
        }

        provenance = {
            'filename': filename or 'unknown.xml',
            'import_time': datetime.now().isoformat(),
            'original_format': 'qti',
            'parser': 'QTIParser'
        }

        return ParseResult(
            content_type='quiz',
            content=content,
            metadata=metadata,
            warnings=warnings,
            provenance=provenance
        )

    def _parse_assessment_item(self, item_elem, namespaces, ns_key):
        """Parse a single assessmentItem element.

        Args:
            item_elem: assessmentItem XML element
            namespaces: XML namespace dict
            ns_key: Namespace key to use

        Returns:
            Question dictionary or None
        """
        # Get identifier and title from item element
        identifier = item_elem.get('identifier', '')
        title = item_elem.get('title', '')

        # Extract prompt
        prompt = ''
        if ns_key and namespaces:
            prompt_elem = item_elem.xpath(f'.//{ns_key}:prompt', namespaces=namespaces)
        else:
            prompt_elem = item_elem.xpath('.//prompt')

        if prompt_elem:
            prompt = self._get_text_content(prompt_elem[0])

        # Extract choiceInteraction
        if ns_key and namespaces:
            choice_elem = item_elem.xpath(f'.//{ns_key}:choiceInteraction', namespaces=namespaces)
        else:
            choice_elem = item_elem.xpath('.//choiceInteraction')

        options = []
        if choice_elem:
            interaction_data = self._parse_choice_interaction(choice_elem[0], namespaces)
            if interaction_data:
                options = interaction_data.get('options', [])

        # Extract correct answer from responseDeclaration
        response_id = choice_elem[0].get('responseIdentifier') if choice_elem else None
        correct_answer = ''
        if response_id:
            if ns_key and namespaces:
                response_decl = item_elem.xpath(f'.//{ns_key}:responseDeclaration[@identifier="{response_id}"]', namespaces=namespaces)
            else:
                response_decl = item_elem.xpath(f'.//responseDeclaration[@identifier="{response_id}"]')

            if response_decl:
                if ns_key and namespaces:
                    correct_elem = response_decl[0].xpath(f'.//{ns_key}:correctResponse/{ns_key}:value', namespaces=namespaces)
                else:
                    correct_elem = response_decl[0].xpath('.//correctResponse/value')

                if correct_elem:
                    correct_answer = correct_elem[0].text.strip() if correct_elem[0].text else ''

        # Extract feedback
        if ns_key and namespaces:
            feedback_elem = item_elem.xpath(f'.//{ns_key}:modalFeedback', namespaces=namespaces)
        else:
            feedback_elem = item_elem.xpath('.//modalFeedback')

        feedback = ''
        if feedback_elem:
            feedback = self._get_text_content(feedback_elem[0])

        # Build complete question
        question = {
            'identifier': identifier,
            'title': title,
            'prompt': prompt,
            'options': options,
            'correct_answer': correct_answer,
            'feedback': feedback
        }

        return question if prompt or options else None

    def _parse_choice_interaction(self, choice_elem, namespaces):
        """Parse choiceInteraction element.

        Args:
            choice_elem: choiceInteraction XML element
            namespaces: XML namespace dict

        Returns:
            Dictionary with options list
        """
        options = []

        # Find all simpleChoice elements
        choices = choice_elem.xpath('.//simpleChoice')

        for choice in choices:
            option = {
                'identifier': choice.get('identifier', ''),
                'text': self._get_text_content(choice)
            }
            options.append(option)

        return {'options': options} if options else None

    def _get_text_content(self, elem):
        """Extract text content from XML element, handling nested elements.

        Args:
            elem: XML element

        Returns:
            Text content as string
        """
        text_parts = []
        if elem.text:
            text_parts.append(elem.text.strip())

        for child in elem:
            child_text = self._get_text_content(child)
            if child_text:
                text_parts.append(child_text)
            if child.tail:
                text_parts.append(child.tail.strip())

        return ' '.join(text_parts).strip()

    def _detect_qti_version(self, xml_str):
        """Detect QTI version from XML.

        Args:
            xml_str: XML string

        Returns:
            Version string
        """
        if 'imsqti_v2p2' in xml_str:
            return '2.2'
        elif 'imsqti_v2p1' in xml_str:
            return '2.1'
        elif 'imsqti' in xml_str:
            return '2.x'
        else:
            return 'unknown'

    def _extract_title(self, tree, namespaces):
        """Extract assessment title.

        Args:
            tree: XML tree
            namespaces: XML namespace dict

        Returns:
            Title string
        """
        # Try to find assessmentTest title
        for ns_key in namespaces.keys():
            ns = {ns_key: namespaces[ns_key]}
            test_elem = tree.xpath(f'//{ns_key}:assessmentTest', namespaces=ns)
            if test_elem and test_elem[0].get('title'):
                return test_elem[0].get('title')

        # Fallback to first assessmentItem title
        items = tree.xpath('.//assessmentItem')
        if items and items[0].get('title'):
            return items[0].get('title')

        return 'Imported Quiz'
