"""Tests for multi-language content generation support.

Verifies that all 11 content generators properly handle the language parameter
and include language instructions in prompts for non-English content.
"""

import pytest


class TestGeneratorLanguageParameter:
    """Test that all generators accept and use the language parameter."""

    def test_video_script_generator_language_param(self):
        """VideoScriptGenerator includes language instruction for non-English."""
        from src.generators.video_script_generator import VideoScriptGenerator
        generator = VideoScriptGenerator()

        # English prompt should NOT have language instruction
        prompt_en = generator.build_user_prompt(
            learning_objective="Learn Python",
            topic="Variables",
            audience_level="beginner",
            language="English"
        )
        assert "IMPORTANT: Generate ALL content in" not in prompt_en

        # Spanish prompt SHOULD have language instruction
        prompt_es = generator.build_user_prompt(
            learning_objective="Learn Python",
            topic="Variables",
            audience_level="beginner",
            language="Spanish"
        )
        assert "IMPORTANT: Generate ALL content in Spanish" in prompt_es

    def test_reading_generator_language_param(self):
        """ReadingGenerator includes language instruction for non-English."""
        from src.generators.reading_generator import ReadingGenerator
        generator = ReadingGenerator()

        prompt_en = generator.build_user_prompt(
            learning_objective="Understand APIs",
            topic="REST APIs",
            audience_level="intermediate",
            language="English"
        )
        assert "IMPORTANT: Generate ALL content in" not in prompt_en

        prompt_fr = generator.build_user_prompt(
            learning_objective="Understand APIs",
            topic="REST APIs",
            audience_level="intermediate",
            language="French"
        )
        assert "IMPORTANT: Generate ALL content in French" in prompt_fr

    def test_quiz_generator_language_param(self):
        """QuizGenerator includes language instruction for non-English."""
        from src.generators.quiz_generator import QuizGenerator
        generator = QuizGenerator()

        prompt_en = generator.build_user_prompt(
            learning_objective="Evaluate code",
            topic="Testing",
            bloom_level="apply",
            language="English"
        )
        assert "IMPORTANT: Generate ALL content in" not in prompt_en

        prompt_de = generator.build_user_prompt(
            learning_objective="Evaluate code",
            topic="Testing",
            bloom_level="apply",
            language="German"
        )
        assert "IMPORTANT: Generate ALL content in German" in prompt_de

    def test_practice_quiz_generator_language_param(self):
        """PracticeQuizGenerator includes language instruction for non-English."""
        from src.generators.practice_quiz_generator import PracticeQuizGenerator
        generator = PracticeQuizGenerator()

        prompt_en = generator.build_user_prompt(
            learning_objective="Practice loops",
            topic="For loops",
            bloom_level="understand",
            language="English"
        )
        assert "IMPORTANT: Generate ALL content in" not in prompt_en

        prompt_pt = generator.build_user_prompt(
            learning_objective="Practice loops",
            topic="For loops",
            bloom_level="understand",
            language="Portuguese"
        )
        assert "IMPORTANT: Generate ALL content in Portuguese" in prompt_pt

    def test_rubric_generator_language_param(self):
        """RubricGenerator includes language instruction for non-English."""
        from src.generators.rubric_generator import RubricGenerator
        generator = RubricGenerator()

        prompt_en = generator.build_user_prompt(
            learning_objective="Create a project",
            activity_title="Final Project",
            activity_type="project",
            language="English"
        )
        assert "IMPORTANT: Generate ALL content in" not in prompt_en

        prompt_zh = generator.build_user_prompt(
            learning_objective="Create a project",
            activity_title="Final Project",
            activity_type="project",
            language="Chinese"
        )
        assert "IMPORTANT: Generate ALL content in Chinese" in prompt_zh

    def test_hol_generator_language_param(self):
        """HOLGenerator includes language instruction for non-English."""
        from src.generators.hol_generator import HOLGenerator
        generator = HOLGenerator()

        prompt_en = generator.build_user_prompt(
            learning_objective="Build an API",
            topic="REST API development",
            language="English"
        )
        assert "IMPORTANT: Generate ALL content in" not in prompt_en

        prompt_ja = generator.build_user_prompt(
            learning_objective="Build an API",
            topic="REST API development",
            language="Japanese"
        )
        assert "IMPORTANT: Generate ALL content in Japanese" in prompt_ja

    def test_coach_generator_language_param(self):
        """CoachGenerator includes language instruction for non-English."""
        from src.generators.coach_generator import CoachGenerator
        generator = CoachGenerator()

        prompt_en = generator.build_user_prompt(
            learning_objective="Debug code",
            topic="Debugging techniques",
            language="English"
        )
        assert "IMPORTANT: Generate ALL content in" not in prompt_en

        prompt_ko = generator.build_user_prompt(
            learning_objective="Debug code",
            topic="Debugging techniques",
            language="Korean"
        )
        assert "IMPORTANT: Generate ALL content in Korean" in prompt_ko

    def test_lab_generator_language_param(self):
        """LabGenerator includes language instruction for non-English."""
        from src.generators.lab_generator import LabGenerator
        generator = LabGenerator()

        prompt_en = generator.build_user_prompt(
            learning_objective="Configure environment",
            topic="Development setup",
            language="English"
        )
        assert "IMPORTANT: Generate ALL content in" not in prompt_en

        prompt_ar = generator.build_user_prompt(
            learning_objective="Configure environment",
            topic="Development setup",
            language="Arabic"
        )
        assert "IMPORTANT: Generate ALL content in Arabic" in prompt_ar

    def test_discussion_generator_language_param(self):
        """DiscussionGenerator includes language instruction for non-English."""
        from src.generators.discussion_generator import DiscussionGenerator
        generator = DiscussionGenerator()

        prompt_en = generator.build_user_prompt(
            learning_objective="Analyze trends",
            topic="Industry trends",
            language="English"
        )
        assert "IMPORTANT: Generate ALL content in" not in prompt_en

        prompt_hi = generator.build_user_prompt(
            learning_objective="Analyze trends",
            topic="Industry trends",
            language="Hindi"
        )
        assert "IMPORTANT: Generate ALL content in Hindi" in prompt_hi

    def test_assignment_generator_language_param(self):
        """AssignmentGenerator includes language instruction for non-English."""
        from src.generators.assignment_generator import AssignmentGenerator
        generator = AssignmentGenerator()

        prompt_en = generator.build_user_prompt(
            learning_objective="Complete analysis",
            topic="Data analysis",
            language="English"
        )
        assert "IMPORTANT: Generate ALL content in" not in prompt_en

        prompt_es = generator.build_user_prompt(
            learning_objective="Complete analysis",
            topic="Data analysis",
            language="Spanish"
        )
        assert "IMPORTANT: Generate ALL content in Spanish" in prompt_es

    def test_project_generator_language_param(self):
        """ProjectMilestoneGenerator includes language instruction for non-English."""
        from src.generators.project_generator import ProjectMilestoneGenerator
        generator = ProjectMilestoneGenerator()

        prompt_en = generator.build_user_prompt(
            learning_objective="Build application",
            topic="Web development",
            language="English"
        )
        assert "IMPORTANT: Generate ALL content in" not in prompt_en

        prompt_fr = generator.build_user_prompt(
            learning_objective="Build application",
            topic="Web development",
            language="French"
        )
        assert "IMPORTANT: Generate ALL content in French" in prompt_fr


class TestLanguageCaseInsensitivity:
    """Test that language comparison is case-insensitive."""

    def test_english_lowercase(self):
        """Lowercase 'english' should not add language instruction."""
        from src.generators.video_script_generator import VideoScriptGenerator
        generator = VideoScriptGenerator()

        prompt = generator.build_user_prompt(
            learning_objective="Learn",
            topic="Topic",
            audience_level="beginner",
            language="english"  # lowercase
        )
        assert "IMPORTANT: Generate ALL content in" not in prompt

    def test_english_uppercase(self):
        """Uppercase 'ENGLISH' should not add language instruction."""
        from src.generators.reading_generator import ReadingGenerator
        generator = ReadingGenerator()

        prompt = generator.build_user_prompt(
            learning_objective="Learn",
            topic="Topic",
            audience_level="beginner",
            language="ENGLISH"  # uppercase
        )
        assert "IMPORTANT: Generate ALL content in" not in prompt


class TestLanguageDefaultValue:
    """Test that language parameter defaults to English."""

    def test_video_script_default_language(self):
        """VideoScriptGenerator defaults to English when language not specified."""
        from src.generators.video_script_generator import VideoScriptGenerator
        generator = VideoScriptGenerator()

        # Call without language parameter
        prompt = generator.build_user_prompt(
            learning_objective="Learn",
            topic="Topic",
            audience_level="beginner"
        )
        # Should not have language instruction since default is English
        assert "IMPORTANT: Generate ALL content in" not in prompt

    def test_all_generators_default_to_english(self):
        """All generators should default to English when language not specified."""
        from src.generators.video_script_generator import VideoScriptGenerator
        from src.generators.reading_generator import ReadingGenerator
        from src.generators.quiz_generator import QuizGenerator
        from src.generators.practice_quiz_generator import PracticeQuizGenerator
        from src.generators.rubric_generator import RubricGenerator
        from src.generators.hol_generator import HOLGenerator
        from src.generators.coach_generator import CoachGenerator
        from src.generators.lab_generator import LabGenerator
        from src.generators.discussion_generator import DiscussionGenerator
        from src.generators.assignment_generator import AssignmentGenerator
        from src.generators.project_generator import ProjectMilestoneGenerator
        import inspect

        generators = [
            VideoScriptGenerator(),
            ReadingGenerator(),
            QuizGenerator(),
            PracticeQuizGenerator(),
            RubricGenerator(),
            HOLGenerator(),
            CoachGenerator(),
            LabGenerator(),
            DiscussionGenerator(),
            AssignmentGenerator(),
            ProjectMilestoneGenerator(),
        ]

        for gen in generators:
            sig = inspect.signature(gen.build_user_prompt)
            lang_param = sig.parameters.get('language')
            assert lang_param is not None, f"{type(gen).__name__} missing language parameter"
            assert lang_param.default == "English", f"{type(gen).__name__} language default is not 'English'"
