"""Coherence validator for textbook chapter content.

Performs post-generation quality checks on textbook chapters:
1. Contradiction detection (LLM-based)
2. Glossary term consistency (terms used in text)
3. Redundancy detection (duplicate headings, content overlap)
"""

from typing import List
from anthropic import Anthropic

from src.config import Config
from src.generators.schemas.textbook import TextbookSectionSchema, GlossaryTerm


class CoherenceValidator:
    """Validates coherence of textbook chapter content.

    Uses a combination of LLM-based analysis and pure Python checks
    to detect issues in generated textbook content before returning
    it to the user.

    Attributes:
        client: Anthropic API client for LLM-based checks
        model: Model to use for LLM calls
    """

    def __init__(self, api_key: str = None, model: str = None):
        """Initialize validator with Anthropic client.

        Args:
            api_key: Optional API key override. Defaults to Config.ANTHROPIC_API_KEY.
            model: Optional model override. Defaults to Config.MODEL.
        """
        self.client = Anthropic(api_key=api_key or Config.ANTHROPIC_API_KEY)
        self.model = model or Config.MODEL

    def check_consistency(
        self,
        sections: List[TextbookSectionSchema],
        glossary_terms: List[GlossaryTerm]
    ) -> List[str]:
        """Run all coherence checks and return combined issues.

        Args:
            sections: List of textbook sections to check
            glossary_terms: List of glossary terms that should appear in text

        Returns:
            List of issue descriptions. Empty list = no issues found.
        """
        issues = []

        # Run all 3 checks
        issues.extend(self._check_contradictions(sections))
        issues.extend(self._check_term_consistency(sections, glossary_terms))
        issues.extend(self._check_redundancy(sections))

        return issues

    def _check_contradictions(self, sections: List[TextbookSectionSchema]) -> List[str]:
        """Check for contradictory statements across sections using LLM.

        Args:
            sections: List of textbook sections to analyze

        Returns:
            List of contradiction descriptions. Empty list if none found.
        """
        if not sections:
            return []

        # Build section content for LLM
        section_texts = []
        for i, section in enumerate(sections, 1):
            section_texts.append(f"Section {i} ({section.heading}):\n{section.content}")

        all_content = "\n\n".join(section_texts)

        prompt = f"""Review these textbook sections for factual contradictions.
Look for statements that directly contradict each other across different sections.

{all_content}

If you find contradictions, list each one on a separate line, describing what contradicts what.
If no contradictions are found, respond with exactly: NO_CONTRADICTIONS"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = response.content[0].text.strip()

        # Parse response
        if "NO_CONTRADICTIONS" in response_text:
            return []

        # Split by newlines and filter empty lines
        issues = [line.strip() for line in response_text.split("\n") if line.strip()]
        return issues

    def _check_term_consistency(
        self,
        sections: List[TextbookSectionSchema],
        glossary_terms: List[GlossaryTerm]
    ) -> List[str]:
        """Check that all glossary terms appear in section content.

        Args:
            sections: List of textbook sections
            glossary_terms: List of glossary terms to verify

        Returns:
            List of issues for missing terms.
        """
        issues = []

        # Combine all section content for searching
        all_content = " ".join(section.content for section in sections).lower()

        for term in glossary_terms:
            term_lower = term.term.lower()
            if term_lower not in all_content:
                issues.append(f"Glossary term '{term.term}' not found in chapter text")

        return issues

    def _check_redundancy(self, sections: List[TextbookSectionSchema]) -> List[str]:
        """Check for redundant content between sections.

        Checks for:
        1. Duplicate section headings
        2. High content overlap (>50% word overlap)

        Args:
            sections: List of textbook sections

        Returns:
            List of redundancy warnings.
        """
        issues = []

        # Check for duplicate headings
        headings = [section.heading for section in sections]
        seen_headings = set()
        for heading in headings:
            if heading in seen_headings:
                issues.append(f"Duplicate section heading: '{heading}'")
            seen_headings.add(heading)

        # Check for content overlap between sections
        for i, section_a in enumerate(sections):
            words_a = set(section_a.content.lower().split())
            for j, section_b in enumerate(sections[i + 1:], i + 1):
                words_b = set(section_b.content.lower().split())

                # Calculate overlap
                if not words_a or not words_b:
                    continue

                overlap = len(words_a & words_b)
                min_words = min(len(words_a), len(words_b))

                if min_words > 0 and overlap / min_words > 0.5:
                    issues.append(
                        f"High content overlap between '{section_a.heading}' and '{section_b.heading}' "
                        f"(>50% word overlap detected)"
                    )

        return issues
