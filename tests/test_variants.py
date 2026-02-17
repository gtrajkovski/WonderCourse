"""Tests for content variants (UDL) and depth layers."""

import pytest
import json
from datetime import datetime

from src.core.models import (
    VariantType, DepthLevel, ContentVariant, BuildState,
    Activity, ContentType, ActivityType
)
from src.generators.variant_generators import (
    TranscriptVariantGenerator, AudioNarrationGenerator, DepthAdapter, get_variant_generator
)
from src.api.variants import PREFERENCE_TO_VARIANTS
from src.core.models import LearningPreference
from src.config import Config


class TestVariantEnums:
    """Test VariantType and DepthLevel enums."""

    def test_variant_type_values(self):
        """Test all variant types exist."""
        assert VariantType.PRIMARY.value == "primary"
        assert VariantType.TRANSCRIPT.value == "transcript"
        assert VariantType.AUDIO_ONLY.value == "audio_only"
        assert VariantType.ILLUSTRATED.value == "illustrated"

    def test_depth_level_values(self):
        """Test all depth levels exist."""
        assert DepthLevel.ESSENTIAL.value == "essential"
        assert DepthLevel.STANDARD.value == "standard"
        assert DepthLevel.ADVANCED.value == "advanced"


class TestContentVariant:
    """Test ContentVariant dataclass."""

    def test_default_values(self):
        """Test ContentVariant default values."""
        variant = ContentVariant()
        assert variant.variant_type == VariantType.PRIMARY
        assert variant.depth_level == DepthLevel.STANDARD
        assert variant.build_state == BuildState.DRAFT
        assert variant.content == ""
        assert variant.word_count == 0
        assert variant.id.startswith("var_")

    def test_to_dict(self):
        """Test serialization to dict."""
        variant = ContentVariant(
            id="var_test123",
            variant_type=VariantType.TRANSCRIPT,
            depth_level=DepthLevel.ESSENTIAL,
            content='{"text": "test"}',
            build_state=BuildState.GENERATED,
            word_count=100,
            estimated_duration_minutes=5.0,
        )

        data = variant.to_dict()

        assert data["id"] == "var_test123"
        assert data["variant_type"] == "transcript"
        assert data["depth_level"] == "essential"
        assert data["build_state"] == "generated"
        assert data["word_count"] == 100

    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "id": "var_test123",
            "variant_type": "transcript",
            "depth_level": "essential",
            "content": '{"text": "test"}',
            "build_state": "generated",
            "word_count": 100,
            "estimated_duration_minutes": 5.0,
        }

        variant = ContentVariant.from_dict(data)

        assert variant.id == "var_test123"
        assert variant.variant_type == VariantType.TRANSCRIPT
        assert variant.depth_level == DepthLevel.ESSENTIAL
        assert variant.build_state == BuildState.GENERATED

    def test_from_dict_schema_evolution(self):
        """Test unknown fields are ignored."""
        data = {
            "id": "var_test",
            "variant_type": "primary",
            "unknown_field": "should be ignored",
            "another_unknown": 42,
        }

        variant = ContentVariant.from_dict(data)

        assert variant.id == "var_test"
        assert not hasattr(variant, "unknown_field")

    def test_from_dict_invalid_enum(self):
        """Test invalid enum values fallback to defaults."""
        data = {
            "variant_type": "invalid_type",
            "depth_level": "invalid_level",
            "build_state": "invalid_state",
        }

        variant = ContentVariant.from_dict(data)

        assert variant.variant_type == VariantType.PRIMARY
        assert variant.depth_level == DepthLevel.STANDARD
        assert variant.build_state == BuildState.DRAFT


class TestActivityVariants:
    """Test Activity variant-related functionality."""

    def test_activity_has_content_variants_field(self):
        """Test Activity has content_variants field."""
        activity = Activity(title="Test")
        assert hasattr(activity, "content_variants")
        assert activity.content_variants == []

    def test_activity_has_default_depth_level(self):
        """Test Activity has default_depth_level field."""
        activity = Activity(title="Test")
        assert hasattr(activity, "default_depth_level")
        assert activity.default_depth_level is None

    def test_get_variant_primary_standard(self):
        """Test get_variant returns virtual variant for primary/standard."""
        activity = Activity(
            title="Test",
            content='{"test": true}',
            build_state=BuildState.GENERATED,
            word_count=100,
        )

        variant = activity.get_variant(VariantType.PRIMARY, DepthLevel.STANDARD)

        assert variant is not None
        assert variant.variant_type == VariantType.PRIMARY
        assert variant.depth_level == DepthLevel.STANDARD
        assert variant.content == '{"test": true}'
        assert variant.word_count == 100

    def test_get_variant_from_list(self):
        """Test get_variant finds variant in content_variants list."""
        activity = Activity(title="Test")

        transcript = ContentVariant(
            variant_type=VariantType.TRANSCRIPT,
            depth_level=DepthLevel.STANDARD,
            content="transcript text",
            build_state=BuildState.GENERATED,
        )
        activity.content_variants.append(transcript)

        found = activity.get_variant(VariantType.TRANSCRIPT, DepthLevel.STANDARD)

        assert found is not None
        assert found.variant_type == VariantType.TRANSCRIPT

    def test_get_variant_not_found(self):
        """Test get_variant returns None when not found."""
        activity = Activity(title="Test")

        found = activity.get_variant(VariantType.TRANSCRIPT, DepthLevel.STANDARD)

        assert found is None

    def test_get_available_variants(self):
        """Test get_available_variants lists all variants."""
        activity = Activity(
            title="Test",
            build_state=BuildState.GENERATED,
        )
        activity.content_variants.append(ContentVariant(
            variant_type=VariantType.TRANSCRIPT,
            depth_level=DepthLevel.STANDARD,
            build_state=BuildState.GENERATED,
        ))

        variants = activity.get_available_variants()

        assert len(variants) == 2
        assert (VariantType.PRIMARY, DepthLevel.STANDARD, BuildState.GENERATED) in variants
        assert (VariantType.TRANSCRIPT, DepthLevel.STANDARD, BuildState.GENERATED) in variants

    def test_activity_to_dict_with_variants(self):
        """Test Activity serialization includes variants."""
        activity = Activity(title="Test")
        activity.content_variants.append(ContentVariant(
            id="var_test",
            variant_type=VariantType.TRANSCRIPT,
        ))

        data = activity.to_dict()

        assert "content_variants" in data
        assert len(data["content_variants"]) == 1
        assert data["content_variants"][0]["id"] == "var_test"

    def test_activity_from_dict_with_variants(self):
        """Test Activity deserialization includes variants."""
        data = {
            "id": "act_test",
            "title": "Test",
            "content_type": "video",
            "content_variants": [
                {
                    "id": "var_test",
                    "variant_type": "transcript",
                    "depth_level": "standard",
                }
            ],
        }

        activity = Activity.from_dict(data)

        assert len(activity.content_variants) == 1
        assert activity.content_variants[0].id == "var_test"
        assert activity.content_variants[0].variant_type == VariantType.TRANSCRIPT


class TestTranscriptVariantGenerator:
    """Test TranscriptVariantGenerator."""

    def test_source_target_types(self):
        """Test generator source and target types."""
        gen = TranscriptVariantGenerator()
        assert gen.source_variant_type == VariantType.PRIMARY
        assert gen.target_variant_type == VariantType.TRANSCRIPT

    def test_transform_video_script(self):
        """Test transforming video script to transcript."""
        gen = TranscriptVariantGenerator()

        video_script = json.dumps({
            "title": "Test Video",
            "hook": {
                "title": "Introduction",
                "script_text": "Welcome to this video about testing."
            },
            "objective": {
                "title": "Learning Goal",
                "script_text": "By the end, you will understand testing."
            },
            "content": {
                "title": "Main Content",
                "script_text": "Testing is important for software quality."
            },
            "ivq": {
                "title": "Check",
                "script_text": "What is the main purpose of testing?"
            },
            "summary": {
                "title": "Summary",
                "script_text": "We learned about testing."
            },
            "cta": {
                "title": "Next Steps",
                "script_text": "Practice writing tests."
            },
            "learning_objective": "Understand testing"
        })

        result_json, metadata = gen.transform(video_script)
        result = json.loads(result_json)

        assert result["title"] == "Test Video"
        assert "Welcome to this video" in result["content"]
        assert "Testing is important" in result["content"]
        assert metadata["word_count"] > 0

    def test_transform_invalid_json(self):
        """Test handling invalid JSON input."""
        gen = TranscriptVariantGenerator()

        result_json, metadata = gen.transform("not valid json")

        assert result_json == "not valid json"
        assert "word_count" in metadata

    def test_generate_variant(self):
        """Test generating ContentVariant from source."""
        gen = TranscriptVariantGenerator()

        source = ContentVariant(
            id="var_source",
            variant_type=VariantType.PRIMARY,
            content=json.dumps({"title": "Test", "content": {"script_text": "Hello"}}),
            build_state=BuildState.GENERATED,
        )

        result = gen.generate_variant(source)

        assert result.variant_type == VariantType.TRANSCRIPT
        assert result.build_state == BuildState.GENERATED
        assert result.generated_from_variant_id == "var_source"


class TestGetVariantGenerator:
    """Test variant generator registry."""

    def test_get_transcript_generator(self):
        """Test getting transcript generator."""
        gen = get_variant_generator(VariantType.PRIMARY, VariantType.TRANSCRIPT)
        assert gen is not None
        assert isinstance(gen, TranscriptVariantGenerator)

    def test_get_unsupported_generator(self):
        """Test getting unsupported generator returns None."""
        gen = get_variant_generator(VariantType.PRIMARY, VariantType.INFOGRAPHIC)
        assert gen is None

    def test_get_audio_generator(self):
        """Test getting audio narration generator."""
        gen = get_variant_generator(VariantType.PRIMARY, VariantType.AUDIO_ONLY)
        assert gen is not None
        assert isinstance(gen, AudioNarrationGenerator)


class TestAudioNarrationGenerator:
    """Test AudioNarrationGenerator."""

    def test_source_target_types(self):
        """Test generator source and target types."""
        gen = AudioNarrationGenerator()
        assert gen.source_variant_type == VariantType.PRIMARY
        assert gen.target_variant_type == VariantType.AUDIO_ONLY

    def test_extract_text_video_script(self):
        """Test text extraction from video script format."""
        gen = AudioNarrationGenerator()

        video_script = {
            "title": "Test Video",
            "hook": {"script_text": "Welcome to the lesson."},
            "content": {"script_text": "Here is the main content."},
            "summary": {"script_text": "In summary, we learned..."},
        }

        text = gen._extract_text(video_script)

        assert "Test Video" in text
        assert "Welcome to the lesson" in text
        assert "main content" in text
        assert "we learned" in text

    def test_extract_text_reading_content(self):
        """Test text extraction from reading format."""
        gen = AudioNarrationGenerator()

        reading_content = {
            "title": "Test Reading",
            "introduction": "This is the introduction.",
            "sections": [
                {"heading": "Section 1", "body": "Content of section 1."},
                {"title": "Section 2", "content": "Content of section 2."},
            ],
            "conclusion": "This is the conclusion.",
        }

        text = gen._extract_text(reading_content)

        assert "Test Reading" in text
        assert "introduction" in text
        assert "Section 1" in text
        assert "Content of section 1" in text
        assert "Section 2" in text
        assert "conclusion" in text

    def test_extract_text_plain_string(self):
        """Test text extraction from plain string."""
        gen = AudioNarrationGenerator()

        text = gen._extract_text("Just a simple string")
        assert text == "Just a simple string"

    @pytest.mark.skipif(
        "sk-ant-test" in (Config.ANTHROPIC_API_KEY or ""),
        reason="Requires real API key for integration test"
    )
    def test_generate_variant(self):
        """Test generating ContentVariant from source (integration test)."""
        gen = AudioNarrationGenerator()

        source = ContentVariant(
            id="var_source",
            variant_type=VariantType.PRIMARY,
            content=json.dumps({"title": "Test", "hook": {"script_text": "Hello world"}}),
            build_state=BuildState.GENERATED,
        )

        result = gen.generate_variant(source)

        assert result.variant_type == VariantType.AUDIO_ONLY
        assert result.build_state == BuildState.GENERATED
        assert result.generated_from_variant_id == "var_source"


class TestPreferenceToVariants:
    """Test learner preference to variant mapping."""

    def test_visual_preference_mapping(self):
        """Test visual preference maps to illustrated/infographic variants."""
        variants = PREFERENCE_TO_VARIANTS[LearningPreference.VISUAL]
        assert VariantType.ILLUSTRATED in variants
        assert VariantType.INFOGRAPHIC in variants

    def test_auditory_preference_mapping(self):
        """Test auditory preference maps to audio_only variant."""
        variants = PREFERENCE_TO_VARIANTS[LearningPreference.AUDITORY]
        assert VariantType.AUDIO_ONLY in variants

    def test_reading_preference_mapping(self):
        """Test reading preference maps to transcript variant."""
        variants = PREFERENCE_TO_VARIANTS[LearningPreference.READING]
        assert VariantType.TRANSCRIPT in variants

    def test_hands_on_preference_mapping(self):
        """Test hands-on preference maps to guided/challenge variants."""
        variants = PREFERENCE_TO_VARIANTS[LearningPreference.HANDS_ON]
        assert VariantType.GUIDED in variants
        assert VariantType.CHALLENGE in variants

    def test_mixed_preference_mapping(self):
        """Test mixed preference maps to primary variant."""
        variants = PREFERENCE_TO_VARIANTS[LearningPreference.MIXED]
        assert VariantType.PRIMARY in variants

    def test_all_mappings_have_primary_fallback(self):
        """Test all preference mappings include PRIMARY as fallback."""
        for pref, variants in PREFERENCE_TO_VARIANTS.items():
            assert VariantType.PRIMARY in variants, f"{pref} should include PRIMARY"
