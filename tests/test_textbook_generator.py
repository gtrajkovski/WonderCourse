"""Tests for TextbookGenerator with mocked Anthropic API."""

import json
import pytest
from unittest.mock import Mock, MagicMock, call
from src.generators.textbook_generator import TextbookGenerator
from src.generators.schemas.textbook import (
    TextbookChapterSchema,
    TextbookOutlineSchema,
    TextbookSectionSchema,
    SectionOutline,
    GlossaryTerm,
    ImagePlaceholder
)
from src.generators.schemas.reading import Reference


# Sample data as dicts
SAMPLE_OUTLINE_DATA = {
    "chapter_title": "Understanding Neural Networks",
    "introduction_summary": "This introduction will provide context for neural networks and their importance in modern AI.",
    "sections": [
        {"title": "History of Neural Networks", "description": "Overview of the development of neural networks from the 1950s to present.", "estimated_words": 450},
        {"title": "Basic Architecture", "description": "Introduction to neurons, layers, and connections in neural networks.", "estimated_words": 500},
        {"title": "Activation Functions", "description": "Explanation of common activation functions and their purposes.", "estimated_words": 400},
        {"title": "Training Process", "description": "How neural networks learn through backpropagation and gradient descent.", "estimated_words": 550},
        {"title": "Applications", "description": "Real-world applications of neural networks across industries.", "estimated_words": 500}
    ],
    "conclusion_summary": "The conclusion will summarize key concepts and point to further learning resources.",
    "estimated_total_words": 2600
}

SAMPLE_SECTION_DATA = {
    "heading": "History of Neural Networks",
    "content": "Neural networks have a rich history dating back to the 1940s when Warren McCulloch and Walter Pitts created a computational model for neural networks. The field experienced significant growth in the 1980s with the development of backpropagation algorithms. Today, deep learning has revolutionized AI capabilities across numerous domains.",
    "key_concepts": ["Perceptron", "Backpropagation", "Deep Learning"]
}

SAMPLE_CHAPTER_DATA = {
    "chapter_number": 1,
    "title": "Understanding Neural Networks",
    "introduction": "Neural networks are the backbone of modern artificial intelligence. This chapter introduces the fundamental concepts and architecture of neural networks, providing a foundation for understanding how machines learn.",
    "sections": [
        {"heading": "History of Neural Networks", "content": "Neural networks have a rich history dating back to the 1940s when Warren McCulloch and Walter Pitts created a computational model for neural networks. The field experienced significant growth in the 1980s with the development of backpropagation algorithms.", "key_concepts": ["Perceptron", "Backpropagation"]},
        {"heading": "Basic Architecture", "content": "A neural network consists of layers of interconnected nodes or neurons. The input layer receives data, hidden layers process it, and the output layer produces results. Each connection has an associated weight that is adjusted during training.", "key_concepts": ["Layers", "Neurons", "Weights"]},
        {"heading": "Activation Functions", "content": "Activation functions determine whether a neuron should be activated. Common functions include ReLU, sigmoid, and tanh. Each has different properties that make them suitable for different types of problems.", "key_concepts": ["ReLU", "Sigmoid", "Tanh"]},
        {"heading": "Training Process", "content": "Neural networks learn through a process called backpropagation. During training, the network makes predictions, calculates the error, and adjusts weights to minimize this error. This process is repeated many times until the network achieves acceptable performance.", "key_concepts": ["Backpropagation", "Gradient Descent", "Loss Function"]},
        {"heading": "Applications", "content": "Neural networks power many modern applications including image recognition, natural language processing, and autonomous vehicles. Their ability to learn complex patterns makes them invaluable across industries from healthcare to finance.", "key_concepts": ["Computer Vision", "NLP", "Autonomous Systems"]}
    ],
    "conclusion": "Neural networks represent a powerful approach to machine learning that mimics aspects of biological neural processing. Understanding their architecture and training process is essential for anyone working in AI and data science.",
    "references": [
        {"citation": "LeCun, Y., Bengio, Y., & Hinton, G. (2015). Deep learning. Nature, 521(7553), 436-444.", "url": "https://doi.org/10.1038/nature14539"},
        {"citation": "Goodfellow, I., Bengio, Y., & Courville, A. (2016). Deep Learning. MIT Press.", "url": "https://www.deeplearningbook.org"},
        {"citation": "Rosenblatt, F. (1958). The perceptron: A probabilistic model for information storage and organization in the brain. Psychological Review, 65(6), 386-408.", "url": "https://doi.org/10.1037/h0042519"}
    ],
    "glossary_terms": [
        {"term": "Neural Network", "definition": "A computing system inspired by biological neural networks that can learn to perform tasks by considering examples.", "context": "Neural networks are the backbone of modern AI."},
        {"term": "Backpropagation", "definition": "An algorithm for training neural networks by propagating error backwards through the network.", "context": "Neural networks learn through a process called backpropagation."},
        {"term": "Activation Function", "definition": "A mathematical function that determines the output of a neural network node.", "context": "Activation functions determine whether a neuron should be activated."},
        {"term": "Deep Learning", "definition": "A subset of machine learning using neural networks with many layers.", "context": "Today, deep learning has revolutionized AI capabilities."},
        {"term": "Gradient Descent", "definition": "An optimization algorithm used to minimize the loss function during training.", "context": "Training uses gradient descent to adjust weights."}
    ],
    "image_placeholders": [
        {"figure_number": "Figure 1.1", "caption": "Basic architecture of a neural network showing input, hidden, and output layers.", "alt_text": "Diagram showing interconnected layers of neurons in a neural network", "suggested_type": "diagram", "placement_after": "A neural network consi"},
        {"figure_number": "Figure 1.2", "caption": "Common activation functions: ReLU, sigmoid, and tanh.", "alt_text": "Graph comparing three activation function curves", "suggested_type": "chart", "placement_after": "Activation functions de"}
    ],
    "learning_outcome_id": "lo_123"
}


def _mock_tool_response(mock_client, data):
    """Helper to create properly structured tool_use response mock."""
    mock_response = MagicMock()
    mock_tool_use = MagicMock()
    mock_tool_use.type = "tool_use"
    mock_tool_use.input = data if isinstance(data, dict) else json.loads(data)
    mock_response.content = [mock_tool_use]
    mock_client.messages.create.return_value = mock_response


def test_generate_returns_valid_schema(mocker):
    """Test that generate() returns a valid TextbookChapterSchema instance."""
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_CHAPTER_DATA)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    generator = TextbookGenerator()
    chapter, metadata = generator.generate(
        schema=TextbookChapterSchema,
        learning_objective="Understand neural network fundamentals",
        topic="Neural Networks",
        audience_level="intermediate"
    )

    assert isinstance(chapter, TextbookChapterSchema)
    assert chapter.title == "Understanding Neural Networks"
    assert len(chapter.sections) == 5
    assert len(chapter.references) == 3
    assert len(chapter.glossary_terms) == 5
    assert len(chapter.image_placeholders) == 2


def test_system_prompt_contains_textbook_and_apa7(mocker):
    """Test that system prompt includes textbook and APA 7 citation guidance."""
    mock_client = MagicMock()
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    generator = TextbookGenerator()
    system_prompt = generator.system_prompt

    # Check for textbook reference
    assert "textbook" in system_prompt.lower()
    # Check for APA 7 reference
    assert "APA 7" in system_prompt or "APA-7" in system_prompt


def test_build_user_prompt_includes_all_parameters(mocker):
    """Test that build_user_prompt includes all parameters."""
    mock_client = MagicMock()
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    generator = TextbookGenerator()

    user_prompt = generator.build_user_prompt(
        learning_objective="Understand neural networks",
        topic="Neural Network Architecture",
        audience_level="advanced"
    )

    assert "neural networks" in user_prompt.lower() or "neural network" in user_prompt.lower()
    assert "architecture" in user_prompt.lower() or "advanced" in user_prompt.lower()


def test_extract_metadata_calculates_correctly(mocker):
    """Test that extract_metadata calculates word count and duration correctly."""
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_CHAPTER_DATA)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    generator = TextbookGenerator()
    chapter, metadata = generator.generate(
        schema=TextbookChapterSchema,
        learning_objective="Test",
        topic="Test",
        audience_level="beginner"
    )

    # Check metadata structure
    assert "word_count" in metadata
    assert "estimated_duration_minutes" in metadata
    assert "content_type" in metadata
    assert metadata["content_type"] == "textbook_chapter"

    # Check counts
    assert "section_count" in metadata
    assert "reference_count" in metadata
    assert "glossary_count" in metadata
    assert "image_count" in metadata

    assert metadata["section_count"] == 5
    assert metadata["reference_count"] == 3
    assert metadata["glossary_count"] == 5
    assert metadata["image_count"] == 2


def test_metadata_duration_uses_238_wpm(mocker):
    """Test that duration calculation uses 238 WPM reading rate."""
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_CHAPTER_DATA)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    generator = TextbookGenerator()
    chapter, metadata = generator.generate(
        schema=TextbookChapterSchema,
        learning_objective="Test",
        topic="Test",
        audience_level="beginner"
    )

    # Calculate expected duration manually
    expected_duration = round(metadata["word_count"] / 238, 1)

    assert metadata["estimated_duration_minutes"] == expected_duration


def test_api_called_with_tools(mocker):
    """Test that API is called with tools parameter for structured output."""
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_CHAPTER_DATA)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    generator = TextbookGenerator()
    generator.generate(
        schema=TextbookChapterSchema,
        learning_objective="Test",
        topic="Test",
        audience_level="beginner"
    )

    # Verify API was called with tools
    mock_client.messages.create.assert_called()
    call_kwargs = mock_client.messages.create.call_args[1]

    assert "tools" in call_kwargs
    assert len(call_kwargs["tools"]) == 1
    assert call_kwargs["tools"][0]["name"] == "output_structured"
    assert "tool_choice" in call_kwargs


def _create_tool_response(data):
    """Create a tool_use response mock for base generate() method."""
    mock_response = MagicMock()
    mock_tool_use = MagicMock()
    mock_tool_use.type = "tool_use"
    mock_tool_use.input = data if isinstance(data, dict) else json.loads(data)
    mock_response.content = [mock_tool_use]
    return mock_response


def _create_text_response(data):
    """Create a text response mock for output_config methods (generate_outline, generate_section, generate_chapter).

    These methods use output_config parameter which returns JSON in response.content[0].text
    """
    mock_response = MagicMock()
    mock_text_block = MagicMock()
    mock_text_block.text = json.dumps(data) if isinstance(data, dict) else data
    mock_response.content = [mock_text_block]
    return mock_response


def test_generate_chapter_orchestrates_multiple_api_calls(mocker):
    """Test that generate_chapter orchestrates outline + sections + assembly (3+ API calls)."""
    mock_client = MagicMock()
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    # Return different responses for sequential calls:
    # 1st call: outline, 2nd-6th calls: sections (5 sections), 7th call: final assembly
    # These methods use output_config which returns text, not tool_use
    mock_client.messages.create.side_effect = [
        _create_text_response(SAMPLE_OUTLINE_DATA),
        _create_text_response(SAMPLE_SECTION_DATA),
        _create_text_response(SAMPLE_SECTION_DATA),
        _create_text_response(SAMPLE_SECTION_DATA),
        _create_text_response(SAMPLE_SECTION_DATA),
        _create_text_response(SAMPLE_SECTION_DATA),
        _create_text_response(SAMPLE_CHAPTER_DATA)
    ]

    generator = TextbookGenerator()
    chapter, metadata = generator.generate_chapter(
        learning_objective="Understand neural networks",
        topic="Neural Networks",
        audience_level="intermediate"
    )

    # Should have called API multiple times (1 outline + 5 sections + 1 assembly = 7)
    assert mock_client.messages.create.call_count >= 3
    assert isinstance(chapter, TextbookChapterSchema)


def test_generate_chapter_calls_progress_callback(mocker):
    """Test that generate_chapter calls progress_callback at each step when provided."""
    mock_client = MagicMock()
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    # These methods use output_config which returns text, not tool_use
    mock_client.messages.create.side_effect = [
        _create_text_response(SAMPLE_OUTLINE_DATA),
        _create_text_response(SAMPLE_SECTION_DATA),
        _create_text_response(SAMPLE_SECTION_DATA),
        _create_text_response(SAMPLE_SECTION_DATA),
        _create_text_response(SAMPLE_SECTION_DATA),
        _create_text_response(SAMPLE_SECTION_DATA),
        _create_text_response(SAMPLE_CHAPTER_DATA)
    ]

    # Create a mock callback
    progress_callback = Mock()

    generator = TextbookGenerator()
    chapter, metadata = generator.generate_chapter(
        learning_objective="Understand neural networks",
        topic="Neural Networks",
        audience_level="intermediate",
        progress_callback=progress_callback
    )

    # Callback should be called multiple times
    assert progress_callback.call_count >= 3  # At least: outline, assembly, and at least one section

    # Check that callback was called with float progress and string description
    for call_args in progress_callback.call_args_list:
        args = call_args[0]
        assert isinstance(args[0], float)  # progress value
        assert isinstance(args[1], str)    # step description


def test_generate_chapter_works_without_progress_callback(mocker):
    """Test that generate_chapter works without progress_callback (backward compatible)."""
    mock_client = MagicMock()
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    # These methods use output_config which returns text, not tool_use
    mock_client.messages.create.side_effect = [
        _create_text_response(SAMPLE_OUTLINE_DATA),
        _create_text_response(SAMPLE_SECTION_DATA),
        _create_text_response(SAMPLE_SECTION_DATA),
        _create_text_response(SAMPLE_SECTION_DATA),
        _create_text_response(SAMPLE_SECTION_DATA),
        _create_text_response(SAMPLE_SECTION_DATA),
        _create_text_response(SAMPLE_CHAPTER_DATA)
    ]

    generator = TextbookGenerator()

    # Should not raise without progress_callback
    chapter, metadata = generator.generate_chapter(
        learning_objective="Understand neural networks",
        topic="Neural Networks",
        audience_level="intermediate"
        # No progress_callback - should work fine
    )

    assert isinstance(chapter, TextbookChapterSchema)
    assert "word_count" in metadata


def test_generate_outline_returns_valid_schema(mocker):
    """Test that generate_outline returns valid TextbookOutlineSchema."""
    mock_client = MagicMock()
    # generate_outline uses output_config which returns text, not tool_use
    mock_client.messages.create.return_value = _create_text_response(SAMPLE_OUTLINE_DATA)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    generator = TextbookGenerator()
    outline = generator.generate_outline(
        learning_objective="Understand neural networks",
        topic="Neural Networks",
        audience_level="intermediate"
    )

    assert isinstance(outline, TextbookOutlineSchema)
    assert outline.chapter_title == "Understanding Neural Networks"
    assert len(outline.sections) == 5
    assert all(isinstance(s, SectionOutline) for s in outline.sections)


def test_generate_section_returns_valid_schema(mocker):
    """Test that generate_section returns valid TextbookSectionSchema."""
    mock_client = MagicMock()
    # generate_section uses output_config which returns text, not tool_use
    mock_client.messages.create.return_value = _create_text_response(SAMPLE_SECTION_DATA)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    # First create an outline to get a section_outline
    outline_data = {
        "title": "History of Neural Networks",
        "description": "Overview of the development of neural networks.",
        "estimated_words": 450
    }
    section_outline = SectionOutline(**outline_data)

    generator = TextbookGenerator()
    section = generator.generate_section(
        section_outline=section_outline,
        chapter_context="This chapter covers neural network fundamentals.",
        covered_concepts=["Basic Architecture"]
    )

    assert isinstance(section, TextbookSectionSchema)
    assert section.heading == "History of Neural Networks"
    assert len(section.key_concepts) >= 2
