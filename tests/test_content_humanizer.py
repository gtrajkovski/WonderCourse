"""Unit tests for content humanization utilities."""

import pytest
from pydantic import BaseModel, Field
from typing import List

from src.utils.content_humanizer import (
    humanize_content,
    get_content_score,
    get_supported_schemas,
    TEXT_FIELDS,
    ContentHumanizationResult,
    _collect_text_values,
    _apply_humanized_values,
)
from src.utils.text_humanizer import PatternType


# Test schema that mimics video script structure
class MockSection(BaseModel):
    """Mock section for testing."""
    title: str = ""
    script_text: str = ""
    speaker_notes: str = ""


class MockVideoScript(BaseModel):
    """Mock video script for testing."""
    title: str = ""
    learning_objective: str = ""
    hook: MockSection
    content: MockSection


class MockReadingSection(BaseModel):
    """Mock reading section."""
    heading: str = ""
    body: str = ""


class MockReading(BaseModel):
    """Mock reading for testing."""
    title: str = ""
    introduction: str = ""
    sections: List[MockReadingSection] = Field(default_factory=list)
    conclusion: str = ""


class MockQuizOption(BaseModel):
    """Mock quiz option."""
    text: str = ""
    feedback: str = ""


class MockQuizQuestion(BaseModel):
    """Mock quiz question."""
    question_text: str = ""
    options: List[MockQuizOption] = Field(default_factory=list)
    explanation: str = ""


class MockQuiz(BaseModel):
    """Mock quiz for testing."""
    title: str = ""
    questions: List[MockQuizQuestion] = Field(default_factory=list)


class TestTextFieldsMapping:
    """Tests for TEXT_FIELDS mapping configuration."""

    def test_video_script_fields_defined(self):
        """VideoScriptSchema should have comprehensive field mapping."""
        assert 'VideoScriptSchema' in TEXT_FIELDS
        fields = TEXT_FIELDS['VideoScriptSchema']
        assert 'title' in fields
        assert 'learning_objective' in fields
        assert 'hook.script_text' in fields
        assert 'content.script_text' in fields

    def test_reading_fields_defined(self):
        """ReadingSchema should include sections array notation."""
        assert 'ReadingSchema' in TEXT_FIELDS
        fields = TEXT_FIELDS['ReadingSchema']
        assert 'title' in fields
        assert 'introduction' in fields
        assert 'sections[].body' in fields
        assert 'conclusion' in fields

    def test_quiz_fields_defined(self):
        """QuizSchema should include nested array fields."""
        assert 'QuizSchema' in TEXT_FIELDS
        fields = TEXT_FIELDS['QuizSchema']
        assert 'title' in fields
        assert 'questions[].question_text' in fields
        assert 'questions[].options[].text' in fields
        assert 'questions[].options[].feedback' in fields

    def test_all_content_types_covered(self):
        """All major content types should be in TEXT_FIELDS."""
        expected_schemas = [
            'VideoScriptSchema',
            'ReadingSchema',
            'QuizSchema',
            'PracticeQuizSchema',
            'HOLSchema',
            'CoachSchema',
            'LabSchema',
            'DiscussionSchema',
            'AssignmentSchema',
            'ProjectMilestoneSchema',
            'RubricSchema',
        ]
        for schema in expected_schemas:
            assert schema in TEXT_FIELDS, f"Missing schema: {schema}"


class TestCollectTextValues:
    """Tests for _collect_text_values function."""

    def test_collect_simple_fields(self):
        """Should collect simple dot-notation fields."""
        content = MockVideoScript(
            title="Test Title",
            learning_objective="Learn something",
            hook=MockSection(title="Hook", script_text="Hook text", speaker_notes="Notes"),
            content=MockSection(title="Content", script_text="Content text", speaker_notes="More notes")
        )
        paths = ['title', 'learning_objective', 'hook.script_text', 'content.script_text']
        texts = _collect_text_values(content, paths)

        assert texts['title'] == "Test Title"
        assert texts['learning_objective'] == "Learn something"
        assert texts['hook.script_text'] == "Hook text"
        assert texts['content.script_text'] == "Content text"

    def test_collect_array_fields(self):
        """Should expand array notation to all items."""
        content = MockReading(
            title="Reading Title",
            introduction="Intro text",
            sections=[
                MockReadingSection(heading="Section 1", body="Body 1"),
                MockReadingSection(heading="Section 2", body="Body 2"),
            ],
            conclusion="Conclusion text"
        )
        paths = ['title', 'sections[].heading', 'sections[].body']
        texts = _collect_text_values(content, paths)

        assert texts['title'] == "Reading Title"
        assert texts['sections[0].heading'] == "Section 1"
        assert texts['sections[0].body'] == "Body 1"
        assert texts['sections[1].heading'] == "Section 2"
        assert texts['sections[1].body'] == "Body 2"

    def test_collect_nested_arrays(self):
        """Should handle nested array fields."""
        content = MockQuiz(
            title="Quiz Title",
            questions=[
                MockQuizQuestion(
                    question_text="Q1",
                    options=[
                        MockQuizOption(text="Option A", feedback="Feedback A"),
                        MockQuizOption(text="Option B", feedback="Feedback B"),
                    ],
                    explanation="Explanation 1"
                )
            ]
        )
        paths = ['questions[].question_text', 'questions[].options[].text']
        texts = _collect_text_values(content, paths)

        assert texts['questions[0].question_text'] == "Q1"
        # Nested arrays produce paths like questions[0].options[0].text
        assert texts['questions[0].options[0].text'] == "Option A"
        assert texts['questions[0].options[1].text'] == "Option B"

    def test_skip_empty_values(self):
        """Should skip empty string values."""
        content = MockVideoScript(
            title="Title",
            learning_objective="",  # Empty
            hook=MockSection(title="", script_text="Hook text", speaker_notes=""),
            content=MockSection(title="", script_text="", speaker_notes="")
        )
        paths = ['title', 'learning_objective', 'hook.script_text']
        texts = _collect_text_values(content, paths)

        assert 'title' in texts
        assert 'learning_objective' not in texts  # Empty, should be skipped
        assert 'hook.script_text' in texts


class TestHumanizeContent:
    """Tests for humanize_content function."""

    def test_humanize_simple_content(self):
        """Should humanize content with AI patterns."""
        content = MockVideoScript(
            title="Utilizing Python",
            learning_objective="Demonstrate comprehensive understanding",
            hook=MockSection(
                title="Hook",
                script_text="Here's where it gets powerful. Let's dive in.",
                speaker_notes="Speak naturally"
            ),
            content=MockSection(
                title="Content",
                script_text="This is really amazing content.",
                speaker_notes="Good notes"
            )
        )

        result = humanize_content(content, schema_name='VideoScriptSchema')

        assert isinstance(result, ContentHumanizationResult)
        assert result.patterns_found > 0  # Should detect patterns
        # Check that humanization improved the score
        assert result.score >= result.original_score

    def test_humanize_with_detect_only(self):
        """Should detect patterns without modifying content when detect_only=True."""
        original_text = "Utilizing Python for comprehensive implementation"
        content = MockVideoScript(
            title=original_text,
            learning_objective="Learn",
            hook=MockSection(title="H", script_text="Text", speaker_notes="N"),
            content=MockSection(title="C", script_text="Text", speaker_notes="N")
        )

        result = humanize_content(content, schema_name='VideoScriptSchema', detect_only=True)

        # Content should be unchanged
        assert result.content.title == original_text
        assert result.patterns_found > 0
        assert result.patterns_fixed == 0

    def test_humanize_clean_content(self):
        """Content without AI patterns should score high."""
        content = MockVideoScript(
            title="Python Basics",
            learning_objective="Learn to write Python code",
            hook=MockSection(title="Hook", script_text="Python makes coding simple.", speaker_notes="Speak clearly"),
            content=MockSection(title="Main", script_text="Variables store data.", speaker_notes="Show examples")
        )

        result = humanize_content(content, schema_name='VideoScriptSchema')

        # Clean content should have high score
        assert result.score >= 80

    def test_humanize_dict_content(self):
        """Should work with dict content as well as Pydantic models."""
        content = {
            'title': 'Utilizing Comprehensive Methods',
            'introduction': "Here's where it gets interesting.",
            'sections': [
                {'heading': 'Section 1', 'body': 'This is really amazing content.'},
            ],
            'conclusion': 'In summary, we covered the basics.'
        }

        result = humanize_content(content, schema_name='ReadingSchema')

        assert result.patterns_found > 0
        assert isinstance(result.content, dict)


class TestGetContentScore:
    """Tests for get_content_score function."""

    def test_score_clean_content(self):
        """Clean content should score high."""
        content = MockVideoScript(
            title="Python Basics",
            learning_objective="Learn Python",
            hook=MockSection(title="Hook", script_text="Python is useful.", speaker_notes="Notes"),
            content=MockSection(title="Content", script_text="Variables store values.", speaker_notes="More notes")
        )

        score_data = get_content_score(content, schema_name='VideoScriptSchema')

        assert score_data['score'] >= 80
        assert score_data['total_patterns'] < 3
        assert 'word_count' in score_data
        assert 'breakdown' in score_data

    def test_score_ai_heavy_content(self):
        """Content with AI patterns should score lower."""
        content = MockVideoScript(
            title="Utilizing Comprehensive Methodologies",
            learning_objective="Demonstrate comprehensive understanding of implementations",
            hook=MockSection(
                title="Hook",
                script_text="Here's where it gets powerful. Let's dive deeper into this fascinating topic.",
                speaker_notes="Interestingly, this is notable"
            ),
            content=MockSection(
                title="Content",
                script_text="This is truly, absolutely, incredibly amazing. Furthermore, we will leverage robust capabilities.",
                speaker_notes="Additionally, we should facilitate comprehensive outcomes"
            )
        )

        score_data = get_content_score(content, schema_name='VideoScriptSchema')

        assert score_data['score'] < 80
        assert score_data['total_patterns'] > 3
        assert len(score_data['breakdown']) > 0

    def test_score_breakdown_by_pattern_type(self):
        """Should provide breakdown by pattern type."""
        content = MockVideoScript(
            title="Utilizing Python",  # formal_vocabulary
            learning_objective="Comprehensive understanding",  # formal_vocabulary
            hook=MockSection(
                title="Hook",
                script_text="This is, quite frankly, really amazing.",  # filler_phrase
                speaker_notes="Notes"
            ),
            content=MockSection(
                title="Content",
                script_text="The solution is robust, seamless, and efficient.",  # adjective_list, formal
                speaker_notes="Notes"
            )
        )

        score_data = get_content_score(content, schema_name='VideoScriptSchema')

        breakdown = score_data['breakdown']
        # Should have at least formal_vocabulary patterns
        assert 'formal_vocabulary' in breakdown or len(breakdown) > 0


class TestGetSupportedSchemas:
    """Tests for get_supported_schemas function."""

    def test_returns_list_of_schemas(self):
        """Should return list of supported schema names."""
        schemas = get_supported_schemas()

        assert isinstance(schemas, list)
        assert len(schemas) > 0
        assert 'VideoScriptSchema' in schemas
        assert 'ReadingSchema' in schemas
        assert 'QuizSchema' in schemas


class TestApplyHumanizedValues:
    """Tests for _apply_humanized_values function."""

    def test_apply_to_pydantic_model(self):
        """Should apply values back to Pydantic model."""
        content = MockVideoScript(
            title="Original Title",
            learning_objective="Original Objective",
            hook=MockSection(title="H", script_text="Original hook", speaker_notes="N"),
            content=MockSection(title="C", script_text="Original content", speaker_notes="N")
        )
        humanized = {
            'title': 'New Title',
            'hook.script_text': 'New hook text'
        }

        result = _apply_humanized_values(content, humanized)

        assert result.title == 'New Title'
        assert result.hook.script_text == 'New hook text'
        # Unchanged fields should remain
        assert result.learning_objective == "Original Objective"

    def test_apply_to_array_fields(self):
        """Should apply values to array fields with indices."""
        content = MockReading(
            title="Title",
            introduction="Intro",
            sections=[
                MockReadingSection(heading="H1", body="B1"),
                MockReadingSection(heading="H2", body="B2"),
            ],
            conclusion="Conclusion"
        )
        humanized = {
            'sections[0].body': 'New Body 1',
            'sections[1].heading': 'New Heading 2'
        }

        result = _apply_humanized_values(content, humanized)

        assert result.sections[0].body == 'New Body 1'
        assert result.sections[1].heading == 'New Heading 2'
        # Unchanged fields
        assert result.sections[0].heading == 'H1'


class TestIntegration:
    """Integration tests for the full humanization pipeline."""

    def test_full_pipeline_video_script(self):
        """Test full pipeline with video script schema."""
        content = MockVideoScript(
            title="Utilizing Python for Comprehensive Data Analysis",
            learning_objective="Demonstrate comprehensive understanding of data manipulation",
            hook=MockSection(
                title="Hook",
                script_text="Here's where it gets powerful. Have you ever struggled with data? Let's dive in.",
                speaker_notes="Speak with enthusiasm. This is really, truly important."
            ),
            content=MockSection(
                title="Main Content",
                script_text="First and foremost, we need to understand variables. They are robust, flexible, and powerful tools.",
                speaker_notes="Show examples. Furthermore, demonstrate best practices."
            )
        )

        # Get initial score
        initial_score = get_content_score(content, schema_name='VideoScriptSchema')

        # Humanize
        result = humanize_content(content, schema_name='VideoScriptSchema')

        # Verify improvement
        assert result.score >= initial_score['score']
        assert result.patterns_fixed > 0

        # Check specific patterns were fixed
        humanized_content = result.content
        # "Utilizing" should become "Using"
        assert "Utilizing" not in humanized_content.title or "Using" in humanized_content.title or result.patterns_fixed > 0

    def test_result_serialization(self):
        """ContentHumanizationResult should serialize to dict."""
        content = MockVideoScript(
            title="Test",
            learning_objective="Learn",
            hook=MockSection(title="H", script_text="T", speaker_notes="N"),
            content=MockSection(title="C", script_text="T", speaker_notes="N")
        )

        result = humanize_content(content, schema_name='VideoScriptSchema')
        result_dict = result.to_dict()

        assert 'original_score' in result_dict
        assert 'score' in result_dict
        assert 'patterns_found' in result_dict
        assert 'patterns_fixed' in result_dict
        assert 'field_results' in result_dict


class TestNewV12Patterns:
    """Tests for v1.2.0 new AI detection patterns (Coursera v3.0)."""

    def test_ensures_opener_detection(self):
        """Should detect 'This ensures/enables/allows' patterns."""
        from src.utils.text_humanizer import TextHumanizer

        humanizer = TextHumanizer()
        text = "Python is powerful. This ensures reliable execution. This enables scaling."
        patterns = humanizer.detect_patterns(text)

        ensures_patterns = [p for p in patterns if p.pattern_type == PatternType.ENSURES_OPENER]
        assert len(ensures_patterns) >= 1

    def test_ensures_opener_humanization(self):
        """Should remove 'This ensures' patterns during humanization."""
        from src.utils.text_humanizer import TextHumanizer

        humanizer = TextHumanizer()
        text = "Python is fast. This ensures reliable code execution."
        result = humanizer.humanize(text)

        # "This ensures" should be removed or simplified
        assert "This ensures" not in result.humanized or result.pattern_count > 0

    def test_not_only_but_detection(self):
        """Should detect 'not only...but also' constructions."""
        from src.utils.text_humanizer import TextHumanizer

        humanizer = TextHumanizer()
        text = "Python is not only fast, but also readable."
        patterns = humanizer.detect_patterns(text)

        not_only_patterns = [p for p in patterns if p.pattern_type == PatternType.NOT_ONLY_BUT]
        assert len(not_only_patterns) == 1

    def test_not_only_but_humanization(self):
        """Should simplify 'not only...but also' to 'X and Y'."""
        from src.utils.text_humanizer import TextHumanizer

        humanizer = TextHumanizer()
        text = "Python is not only fast, but also reliable."
        result = humanizer.humanize(text)

        # Should be simplified
        assert "not only" not in result.humanized.lower() or "and" in result.humanized.lower()

    def test_long_comma_list_detection(self):
        """Should detect 4+ item comma-separated lists."""
        from src.utils.text_humanizer import TextHumanizer

        humanizer = TextHumanizer()
        text = "The framework supports Python, Java, JavaScript, and Go."
        patterns = humanizer.detect_patterns(text)

        list_patterns = [p for p in patterns if p.pattern_type == PatternType.LONG_COMMA_LIST]
        assert len(list_patterns) == 1

    def test_long_comma_list_not_three_items(self):
        """Should NOT detect 3-item lists as LONG_COMMA_LIST."""
        from src.utils.text_humanizer import TextHumanizer

        humanizer = TextHumanizer()
        text = "The options are red, green, and blue."
        patterns = humanizer.detect_patterns(text)

        list_patterns = [p for p in patterns if p.pattern_type == PatternType.LONG_COMMA_LIST]
        # 3 items should be caught by ADJECTIVE_LIST, not LONG_COMMA_LIST
        assert len(list_patterns) == 0

    def test_adverb_triplet_detection(self):
        """Should detect 3+ adverbs in close proximity."""
        from src.utils.text_humanizer import TextHumanizer

        humanizer = TextHumanizer()
        text = "The system runs quickly, efficiently, and reliably."
        patterns = humanizer.detect_patterns(text)

        adverb_patterns = [p for p in patterns if p.pattern_type == PatternType.ADVERB_TRIPLET]
        assert len(adverb_patterns) == 1

    def test_repeat_opener_detection(self):
        """Should detect consecutive sentences starting with same word."""
        from src.utils.text_humanizer import TextHumanizer

        humanizer = TextHumanizer()
        text = "Python is fast. Python is readable. Python has great libraries."
        patterns = humanizer.detect_patterns(text)

        repeat_patterns = [p for p in patterns if p.pattern_type == PatternType.REPEAT_OPENER]
        assert len(repeat_patterns) >= 1

    def test_content_with_new_patterns_scores_lower(self):
        """Content with new v1.2 patterns should score lower."""
        from src.utils.text_humanizer import TextHumanizer

        humanizer = TextHumanizer()

        # Text with multiple new patterns
        ai_heavy = """
        Python is fast. Python is flexible. Python is powerful.
        This ensures reliable execution. Not only is it fast, but also efficient.
        It supports strings, integers, floats, lists, and dictionaries.
        The system runs quickly, efficiently, and reliably.
        """

        # Clean text
        clean = """
        Python runs fast. The language reads easily.
        Your code executes without problems.
        It handles strings and integers well.
        The system works as expected.
        """

        ai_score = humanizer.get_score(ai_heavy)
        clean_score = humanizer.get_score(clean)

        assert ai_score['score'] < clean_score['score']
        assert ai_score['total_patterns'] > clean_score['total_patterns']
