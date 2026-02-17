"""Tests for CoherenceValidator with mocked Anthropic API.

Tests the 3 types of coherence checks:
1. _check_contradictions - LLM-based contradiction detection
2. _check_term_consistency - glossary term presence in text
3. _check_redundancy - duplicate headings and content overlap
"""

import pytest
from unittest.mock import MagicMock

from src.utils.coherence_validator import CoherenceValidator
from src.generators.schemas.textbook import TextbookSectionSchema, GlossaryTerm


# Helper to create test sections
def make_section(heading: str, content: str, key_concepts: list = None) -> TextbookSectionSchema:
    """Create a TextbookSectionSchema for testing."""
    return TextbookSectionSchema(
        heading=heading,
        content=content,
        key_concepts=key_concepts or ["concept1", "concept2"]
    )


# Helper to create test glossary terms
def make_term(term: str, definition: str = "A definition", context: str = "Used in chapter") -> GlossaryTerm:
    """Create a GlossaryTerm for testing."""
    return GlossaryTerm(
        term=term,
        definition=definition,
        context=context
    )


class TestCheckTermConsistency:
    """Tests for _check_term_consistency method."""

    def test_returns_empty_list_when_all_terms_found(self, mocker):
        """Test that no issues are returned when all glossary terms appear in text."""
        mock_client = mocker.MagicMock()
        mocker.patch('src.utils.coherence_validator.Anthropic', return_value=mock_client)

        validator = CoherenceValidator(api_key="test-key")

        sections = [
            make_section("Introduction", "This section covers machine learning and neural networks."),
            make_section("Deep Dive", "We explore convolutional neural networks in depth.")
        ]
        glossary_terms = [
            make_term("machine learning"),
            make_term("neural networks")
        ]

        issues = validator._check_term_consistency(sections, glossary_terms)

        assert issues == []

    def test_flags_missing_glossary_terms(self, mocker):
        """Test that missing glossary terms are flagged."""
        mock_client = mocker.MagicMock()
        mocker.patch('src.utils.coherence_validator.Anthropic', return_value=mock_client)

        validator = CoherenceValidator(api_key="test-key")

        sections = [
            make_section("Introduction", "This section covers machine learning concepts."),
        ]
        glossary_terms = [
            make_term("machine learning"),
            make_term("quantum computing"),  # Not in text
            make_term("blockchain")  # Not in text
        ]

        issues = validator._check_term_consistency(sections, glossary_terms)

        assert len(issues) == 2
        assert any("quantum computing" in issue for issue in issues)
        assert any("blockchain" in issue for issue in issues)

    def test_case_insensitive_matching(self, mocker):
        """Test that term matching is case-insensitive."""
        mock_client = mocker.MagicMock()
        mocker.patch('src.utils.coherence_validator.Anthropic', return_value=mock_client)

        validator = CoherenceValidator(api_key="test-key")

        sections = [
            make_section("Intro", "MACHINE LEARNING is important. Also Neural Networks."),
        ]
        glossary_terms = [
            make_term("machine learning"),
            make_term("neural networks")
        ]

        issues = validator._check_term_consistency(sections, glossary_terms)

        assert issues == []


class TestCheckRedundancy:
    """Tests for _check_redundancy method."""

    def test_returns_empty_list_for_unique_sections(self, mocker):
        """Test that no issues are returned for unique sections."""
        mock_client = mocker.MagicMock()
        mocker.patch('src.utils.coherence_validator.Anthropic', return_value=mock_client)

        validator = CoherenceValidator(api_key="test-key")

        sections = [
            make_section("Introduction", "This is the first section with unique content."),
            make_section("Methods", "This section describes the methods used."),
            make_section("Results", "Here are the results of our analysis.")
        ]

        issues = validator._check_redundancy(sections)

        assert issues == []

    def test_flags_duplicate_headings(self, mocker):
        """Test that duplicate headings are flagged."""
        mock_client = mocker.MagicMock()
        mocker.patch('src.utils.coherence_validator.Anthropic', return_value=mock_client)

        validator = CoherenceValidator(api_key="test-key")

        sections = [
            make_section("Introduction", "First intro content."),
            make_section("Methods", "Methods content."),
            make_section("Introduction", "Second intro content.")  # Duplicate heading
        ]

        issues = validator._check_redundancy(sections)

        assert len(issues) >= 1
        assert any("Introduction" in issue for issue in issues)

    def test_flags_high_content_overlap(self, mocker):
        """Test that sections with >50% word overlap are flagged."""
        mock_client = mocker.MagicMock()
        mocker.patch('src.utils.coherence_validator.Anthropic', return_value=mock_client)

        validator = CoherenceValidator(api_key="test-key")

        # These sections share most of their words
        shared_content = "Machine learning uses algorithms to learn from data and make predictions."
        sections = [
            make_section("Section A", shared_content),
            make_section("Section B", shared_content + " This is slightly different.")
        ]

        issues = validator._check_redundancy(sections)

        assert len(issues) >= 1
        assert any("overlap" in issue.lower() or "redundant" in issue.lower() for issue in issues)


class TestCheckContradictions:
    """Tests for _check_contradictions method."""

    def test_calls_llm_with_section_content(self, mocker):
        """Test that LLM is called with all section content."""
        mock_client = mocker.MagicMock()
        mock_response = mocker.MagicMock()
        mock_response.content = [mocker.MagicMock(text="NO_CONTRADICTIONS")]
        mock_client.messages.create.return_value = mock_response
        mocker.patch('src.utils.coherence_validator.Anthropic', return_value=mock_client)

        validator = CoherenceValidator(api_key="test-key")

        sections = [
            make_section("Intro", "Python is a programming language."),
            make_section("Details", "Python supports object-oriented programming.")
        ]

        validator._check_contradictions(sections)

        # Verify LLM was called
        mock_client.messages.create.assert_called_once()

        # Verify section content was included in the prompt
        call_kwargs = mock_client.messages.create.call_args
        messages = call_kwargs[1]["messages"]
        user_message = messages[0]["content"]
        assert "Python is a programming language" in user_message
        assert "Python supports object-oriented programming" in user_message

    def test_returns_empty_list_for_no_contradictions(self, mocker):
        """Test that empty list is returned when LLM finds no contradictions."""
        mock_client = mocker.MagicMock()
        mock_response = mocker.MagicMock()
        mock_response.content = [mocker.MagicMock(text="NO_CONTRADICTIONS")]
        mock_client.messages.create.return_value = mock_response
        mocker.patch('src.utils.coherence_validator.Anthropic', return_value=mock_client)

        validator = CoherenceValidator(api_key="test-key")

        sections = [
            make_section("Intro", "Python is a programming language."),
        ]

        issues = validator._check_contradictions(sections)

        assert issues == []

    def test_returns_contradiction_descriptions(self, mocker):
        """Test that contradiction descriptions are parsed from LLM response."""
        mock_client = mocker.MagicMock()
        mock_response = mocker.MagicMock()
        mock_response.content = [mocker.MagicMock(text="""Section 1 says Python is slow, but Section 2 says it's fast.
Section 3 claims the sky is green, contradicting Section 4 which says it's blue.""")]
        mock_client.messages.create.return_value = mock_response
        mocker.patch('src.utils.coherence_validator.Anthropic', return_value=mock_client)

        validator = CoherenceValidator(api_key="test-key")

        sections = [
            make_section("Section 1", "Python is slow."),
            make_section("Section 2", "Python is fast.")
        ]

        issues = validator._check_contradictions(sections)

        assert len(issues) == 2
        assert any("slow" in issue and "fast" in issue for issue in issues)


class TestCheckConsistency:
    """Tests for check_consistency method (combines all 3 checks)."""

    def test_returns_empty_list_for_coherent_content(self, mocker):
        """Test that empty list is returned for fully coherent content."""
        mock_client = mocker.MagicMock()
        mock_response = mocker.MagicMock()
        mock_response.content = [mocker.MagicMock(text="NO_CONTRADICTIONS")]
        mock_client.messages.create.return_value = mock_response
        mocker.patch('src.utils.coherence_validator.Anthropic', return_value=mock_client)

        validator = CoherenceValidator(api_key="test-key")

        sections = [
            make_section("Introduction", "Machine learning uses algorithms to analyze data."),
            make_section("Methods", "We apply deep learning techniques to the dataset.")
        ]
        glossary_terms = [
            make_term("machine learning"),
            make_term("deep learning")
        ]

        issues = validator.check_consistency(sections, glossary_terms)

        assert issues == []

    def test_combines_all_check_results(self, mocker):
        """Test that check_consistency combines issues from all 3 checks."""
        mock_client = mocker.MagicMock()
        mock_response = mocker.MagicMock()
        # Return a contradiction
        mock_response.content = [mocker.MagicMock(text="Section 1 contradicts Section 2 on the speed claim.")]
        mock_client.messages.create.return_value = mock_response
        mocker.patch('src.utils.coherence_validator.Anthropic', return_value=mock_client)

        validator = CoherenceValidator(api_key="test-key")

        # Create content with multiple issues:
        # 1. Missing glossary term
        # 2. Duplicate heading
        # 3. Contradiction (from mock)
        sections = [
            make_section("Introduction", "Python is slow."),
            make_section("Introduction", "Python is fast.")  # Duplicate heading
        ]
        glossary_terms = [
            make_term("quantum computing")  # Not in text
        ]

        issues = validator.check_consistency(sections, glossary_terms)

        # Should have issues from all 3 checks
        assert len(issues) >= 3
        # Check for term consistency issue
        assert any("quantum computing" in issue for issue in issues)
        # Check for redundancy issue
        assert any("Introduction" in issue for issue in issues)
        # Check for contradiction issue
        assert any("contradicts" in issue.lower() for issue in issues)


class TestCoherenceValidatorInit:
    """Tests for CoherenceValidator initialization."""

    def test_creates_anthropic_client(self, mocker):
        """Test that Anthropic client is created on init."""
        mock_anthropic = mocker.MagicMock()
        mocker.patch('src.utils.coherence_validator.Anthropic', mock_anthropic)

        validator = CoherenceValidator(api_key="test-key")

        mock_anthropic.assert_called_once_with(api_key="test-key")
        assert validator.client is not None

    def test_uses_default_model(self, mocker):
        """Test that default model is used when not specified."""
        mock_client = mocker.MagicMock()
        mocker.patch('src.utils.coherence_validator.Anthropic', return_value=mock_client)

        validator = CoherenceValidator(api_key="test-key")

        from src.config import Config
        assert validator.model == Config.MODEL

    def test_accepts_custom_model(self, mocker):
        """Test that custom model can be specified."""
        mock_client = mocker.MagicMock()
        mocker.patch('src.utils.coherence_validator.Anthropic', return_value=mock_client)

        validator = CoherenceValidator(api_key="test-key", model="custom-model")

        assert validator.model == "custom-model"
