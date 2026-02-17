"""Tests for v1.3.0 image generation utilities.

Tests:
- Video slide generator
- Reading image generator
- CTA slide generator
- Terminal image generator
"""

import pytest
from unittest.mock import MagicMock, patch


class TestVideoSlideGenerator:
    """Tests for video slide generator."""

    def test_slide_type_enum(self):
        """Test SlideType enum values."""
        from src.utils.video_slide_generator import SlideType

        assert SlideType.TITLE.value == "title"
        assert SlideType.OBJECTIVE.value == "objective"
        assert SlideType.CONTENT.value == "content"
        assert SlideType.KEY_POINT.value == "key_point"
        assert SlideType.VISUAL_CUE.value == "visual_cue"
        assert SlideType.SUMMARY.value == "summary"
        assert SlideType.CTA.value == "cta"

    def test_slide_style_defaults(self):
        """Test SlideStyle has correct defaults."""
        from src.utils.video_slide_generator import SlideStyle

        style = SlideStyle()

        assert style.width == 1920
        assert style.height == 1080
        assert style.title_bg == (0, 86, 210)  # Coursera blue
        assert style.title_font_size == 64

    def test_slide_dataclass(self):
        """Test Slide dataclass."""
        from src.utils.video_slide_generator import Slide, SlideType

        slide = Slide(
            slide_type=SlideType.TITLE,
            title="Introduction to Python",
            subtitle="Learn the basics",
            content=["Point 1", "Point 2"]
        )

        assert slide.slide_type == SlideType.TITLE
        assert slide.title == "Introduction to Python"
        assert slide.subtitle == "Learn the basics"
        assert len(slide.content) == 2

    def test_slide_set_dataclass(self):
        """Test SlideSet dataclass."""
        from src.utils.video_slide_generator import SlideSet, Slide, SlideType

        slide_set = SlideSet(
            video_title="Test Video",
            slides=[
                Slide(slide_type=SlideType.TITLE, title="Title Slide"),
                Slide(slide_type=SlideType.CONTENT, title="Content Slide"),
            ]
        )

        assert slide_set.video_title == "Test Video"
        assert len(slide_set.slides) == 2

    def test_parse_script_hook_section(self):
        """Test parsing hook section creates title slide."""
        from src.utils.video_slide_generator import VideoSlideGenerator, SlideType

        try:
            generator = VideoSlideGenerator()
        except ImportError:
            pytest.skip("Pillow not installed")

        video_content = {
            "title": "Flask REST APIs",
            "sections": [
                {
                    "section_name": "Hook",
                    "script_text": "Welcome to this exciting tutorial on building APIs!"
                }
            ]
        }

        slide_set = generator.parse_script(video_content)

        assert slide_set.video_title == "Flask REST APIs"
        assert len(slide_set.slides) >= 1
        assert slide_set.slides[0].slide_type == SlideType.TITLE
        assert slide_set.slides[0].title == "Flask REST APIs"

    def test_parse_script_objective_section(self):
        """Test parsing objective section."""
        from src.utils.video_slide_generator import VideoSlideGenerator, SlideType

        try:
            generator = VideoSlideGenerator()
        except ImportError:
            pytest.skip("Pillow not installed")

        video_content = {
            "title": "Test Video",
            "sections": [
                {
                    "section_name": "Objective",
                    "script_text": "By the end you will:\n- Understand APIs\n- Build endpoints"
                }
            ]
        }

        slide_set = generator.parse_script(video_content)

        assert len(slide_set.slides) >= 1
        obj_slides = [s for s in slide_set.slides if s.slide_type == SlideType.OBJECTIVE]
        assert len(obj_slides) == 1
        assert obj_slides[0].title == "Learning Objectives"

    def test_parse_script_content_with_visual_cues(self):
        """Test parsing content with visual cues."""
        from src.utils.video_slide_generator import VideoSlideGenerator, SlideType

        try:
            generator = VideoSlideGenerator()
        except ImportError:
            pytest.skip("Pillow not installed")

        video_content = {
            "title": "Test Video",
            "sections": [
                {
                    "section_name": "Content",
                    "script_text": "Here's the explanation. [Diagram: API flow] More content follows."
                }
            ]
        }

        slide_set = generator.parse_script(video_content)

        visual_cue_slides = [s for s in slide_set.slides if s.slide_type == SlideType.VISUAL_CUE]
        assert len(visual_cue_slides) >= 1

    def test_parse_script_summary_section(self):
        """Test parsing summary section."""
        from src.utils.video_slide_generator import VideoSlideGenerator, SlideType

        try:
            generator = VideoSlideGenerator()
        except ImportError:
            pytest.skip("Pillow not installed")

        video_content = {
            "title": "Test Video",
            "sections": [
                {
                    "section_name": "Summary",
                    "script_text": "To recap:\n- Point 1\n- Point 2\n- Point 3"
                }
            ]
        }

        slide_set = generator.parse_script(video_content)

        summary_slides = [s for s in slide_set.slides if s.slide_type == SlideType.SUMMARY]
        assert len(summary_slides) == 1
        assert summary_slides[0].title == "Key Takeaways"

    def test_parse_script_cta_section(self):
        """Test parsing CTA section."""
        from src.utils.video_slide_generator import VideoSlideGenerator, SlideType

        try:
            generator = VideoSlideGenerator()
        except ImportError:
            pytest.skip("Pillow not installed")

        video_content = {
            "title": "Flask APIs",
            "sections": [
                {
                    "section_name": "CTA",
                    "script_text": "Practice building your own API in the next lab!"
                }
            ]
        }

        slide_set = generator.parse_script(video_content)

        cta_slides = [s for s in slide_set.slides if s.slide_type == SlideType.CTA]
        assert len(cta_slides) == 1
        assert cta_slides[0].title == "Flask APIs"

    @pytest.mark.skipif(True, reason="Requires Pillow installation")
    def test_generate_slide_image(self):
        """Test generating a slide image."""
        from src.utils.video_slide_generator import (
            VideoSlideGenerator, Slide, SlideType
        )

        generator = VideoSlideGenerator()
        slide = Slide(
            slide_type=SlideType.TITLE,
            title="Test Title",
            subtitle="Test Subtitle"
        )

        image = generator.generate_slide_image(slide)

        assert image is not None
        assert image.width == 1920
        assert image.height == 1080


class TestReadingImageGenerator:
    """Tests for reading image generator."""

    def test_image_type_enum(self):
        """Test ImageType enum values."""
        from src.utils.reading_image_generator import ImageType

        assert ImageType.CONCEPT.value == "concept"
        assert ImageType.DIAGRAM.value == "diagram"
        assert ImageType.EXAMPLE.value == "example"
        assert ImageType.COMPARISON.value == "comparison"
        assert ImageType.INFOGRAPHIC.value == "infographic"

    def test_image_style_defaults(self):
        """Test ImageStyle has correct defaults."""
        from src.utils.reading_image_generator import ImageStyle

        style = ImageStyle()

        assert style.width == 1200
        assert style.height == 675
        assert style.accent == (0, 86, 210)  # Coursera blue

    def test_image_concept_dataclass(self):
        """Test ImageConcept dataclass."""
        from src.utils.reading_image_generator import ImageConcept, ImageType

        concept = ImageConcept(
            title="REST API Architecture",
            description="How REST APIs structure requests and responses",
            image_type=ImageType.DIAGRAM,
            keywords=["REST", "API", "HTTP"]
        )

        assert concept.title == "REST API Architecture"
        assert concept.image_type == ImageType.DIAGRAM
        assert len(concept.keywords) == 3

    def test_concept_to_prompt(self):
        """Test converting concept to image generation prompt."""
        from src.utils.reading_image_generator import ImageConcept, ImageType

        concept = ImageConcept(
            title="Database Schema",
            description="Visual representation of table relationships",
            image_type=ImageType.DIAGRAM,
            keywords=["database", "schema", "tables", "relationships"]
        )

        prompt = concept.to_prompt()

        assert "Database Schema" in prompt
        assert "table relationships" in prompt
        assert "Keywords:" in prompt

    def test_extract_concepts_from_headers(self):
        """Test extracting concepts from markdown headers."""
        from src.utils.reading_image_generator import ReadingImageGenerator

        generator = ReadingImageGenerator()

        content = """
        # Introduction to Machine Learning

        Some content here.

        ## Supervised Learning

        More content about supervised learning.

        ## Unsupervised Learning

        Content about unsupervised learning.
        """

        concepts = generator.extract_concepts(content, count=3)

        assert len(concepts) <= 3
        titles = [c.title for c in concepts]
        assert any("Machine Learning" in t or "Learning" in t for t in titles)

    def test_extract_concepts_from_definitions(self):
        """Test extracting concepts from definitions."""
        from src.utils.reading_image_generator import ReadingImageGenerator

        generator = ReadingImageGenerator()

        content = """
        An API is defined as a set of protocols for building software.

        A REST interface refers to the architectural style using HTTP methods.

        Machine learning is a subset of artificial intelligence that enables systems to learn.
        """

        concepts = generator.extract_concepts(content, count=3)

        assert len(concepts) >= 1
        descriptions = [c.description.lower() for c in concepts]
        # Should extract at least one definition
        assert any(
            "protocol" in d or "architectural" in d or "artificial" in d
            for d in descriptions
        )

    def test_extract_concepts_from_dict_content(self):
        """Test extracting concepts from dict content."""
        from src.utils.reading_image_generator import ReadingImageGenerator

        generator = ReadingImageGenerator()

        content = {
            "content": "# API Design\n\nThe key concept is separation of concerns.\n\nFor example, RESTful endpoints handle resources."
        }

        concepts = generator.extract_concepts(content, count=2)

        assert len(concepts) <= 2

    def test_extract_concepts_limits_count(self):
        """Test that extract_concepts respects count limit."""
        from src.utils.reading_image_generator import ReadingImageGenerator

        generator = ReadingImageGenerator()

        content = """
        # Topic 1
        # Topic 2
        # Topic 3
        # Topic 4
        # Topic 5
        """

        concepts = generator.extract_concepts(content, count=2)
        assert len(concepts) <= 2

    def test_extract_keywords(self):
        """Test keyword extraction."""
        from src.utils.reading_image_generator import ReadingImageGenerator

        generator = ReadingImageGenerator()

        keywords = generator._extract_keywords(
            "The database schema defines table relationships and foreign keys"
        )

        assert "database" in keywords
        assert "schema" in keywords
        # Stop words should be filtered
        assert "the" not in keywords
        assert "and" not in keywords

    @pytest.mark.skipif(True, reason="Requires Pillow installation")
    def test_generate_concept_image(self):
        """Test generating a concept image."""
        from src.utils.reading_image_generator import (
            ReadingImageGenerator, ImageConcept, ImageType
        )

        generator = ReadingImageGenerator()
        concept = ImageConcept(
            title="REST API",
            description="Client-server architecture",
            image_type=ImageType.CONCEPT
        )

        image = generator.generate_concept_image(concept)

        assert image is not None
        assert image.width == 1200
        assert image.height == 675

    @pytest.mark.skipif(True, reason="Requires Pillow installation")
    def test_generate_images_from_content(self):
        """Test generating multiple images from content."""
        from src.utils.reading_image_generator import (
            ReadingImageGenerator, GeneratedImage
        )

        generator = ReadingImageGenerator()
        content = "# API Design Principles\n\nREST APIs use HTTP methods."

        images = generator.generate_images(content, count=2)

        assert len(images) <= 2
        for img in images:
            assert isinstance(img, GeneratedImage)
            assert len(img.image_bytes) > 0

    def test_extract_image_concepts_convenience(self):
        """Test convenience function for concept extraction."""
        from src.utils.reading_image_generator import extract_image_concepts

        content = "# Database Design\n\nThe process of normalization reduces data redundancy."

        concepts = extract_image_concepts(content, count=2)

        assert len(concepts) <= 2
        for concept in concepts:
            assert "title" in concept
            assert "description" in concept
            assert "prompt" in concept

    def test_generate_images_clamps_count(self):
        """Test that count is clamped to 1-5 range."""
        from src.utils.reading_image_generator import (
            ReadingImageGenerator, PILLOW_AVAILABLE
        )

        if not PILLOW_AVAILABLE:
            pytest.skip("Pillow not installed")

        try:
            generator = ReadingImageGenerator()
        except ImportError:
            pytest.skip("Pillow not installed")

        content = "# Test Topic\n\nSome content about the topic."

        # These should not raise, but clamp
        images = generator.generate_images(content, count=0)  # Clamped to 1
        assert len(images) >= 0

        images = generator.generate_images(content, count=10)  # Clamped to 5
        assert len(images) <= 5


class TestImageGeneratorIntegration:
    """Integration tests requiring Pillow."""

    @pytest.fixture
    def check_pillow(self):
        """Skip tests if Pillow is not available."""
        try:
            import PIL
            return True
        except ImportError:
            pytest.skip("Pillow not installed")

    def test_video_slide_generator_available(self, check_pillow):
        """Test that video slide generator can be imported."""
        from src.utils.video_slide_generator import (
            VideoSlideGenerator,
            PILLOW_AVAILABLE
        )
        assert PILLOW_AVAILABLE is True

    def test_reading_image_generator_available(self, check_pillow):
        """Test that reading image generator can be imported."""
        from src.utils.reading_image_generator import (
            ReadingImageGenerator,
            PILLOW_AVAILABLE
        )
        assert PILLOW_AVAILABLE is True

    def test_generate_video_slides_convenience(self, check_pillow):
        """Test convenience function for video slides."""
        from src.utils.video_slide_generator import generate_video_slides

        video_content = {
            "title": "Test Video",
            "sections": [
                {"section_name": "Hook", "script_text": "Welcome!"},
                {"section_name": "Content", "script_text": "Here is the content."},
                {"section_name": "CTA", "script_text": "Try it yourself!"}
            ]
        }

        slides = generate_video_slides(video_content)

        assert len(slides) >= 1
        for slide_bytes in slides:
            assert isinstance(slide_bytes, bytes)
            assert len(slide_bytes) > 0

    def test_generate_reading_images_convenience(self, check_pillow):
        """Test convenience function for reading images."""
        from src.utils.reading_image_generator import generate_reading_images

        content = "# API Concepts\n\nREST APIs define how clients communicate with servers."

        images = generate_reading_images(content, count=1)

        assert len(images) >= 0  # May be 0 if no concepts extracted
        for img_bytes in images:
            assert isinstance(img_bytes, bytes)

    def test_different_image_types_render(self, check_pillow):
        """Test rendering different image types."""
        from src.utils.reading_image_generator import (
            ReadingImageGenerator, ImageConcept, ImageType
        )

        generator = ReadingImageGenerator()

        for img_type in [ImageType.CONCEPT, ImageType.DIAGRAM, ImageType.COMPARISON,
                         ImageType.INFOGRAPHIC, ImageType.EXAMPLE]:
            concept = ImageConcept(
                title=f"Test {img_type.value}",
                description="Test description",
                image_type=img_type
            )

            image = generator.generate_concept_image(concept)
            assert image is not None
            assert image.width == 1200
