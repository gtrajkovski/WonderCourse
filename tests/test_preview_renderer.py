"""Tests for preview renderer utility."""

import pytest
import json

from src.utils.preview_renderer import PreviewRenderer, render_learner_preview


@pytest.fixture
def renderer():
    """Create PreviewRenderer instance."""
    return PreviewRenderer()


class TestVideoScriptRendering:
    """Tests for video script preview rendering."""

    def test_render_video_with_title(self, renderer):
        """Should render video script title."""
        content = {'title': 'Introduction to Python'}
        html = renderer.render_video_script(content)

        assert 'Introduction to Python' in html
        assert '<h1' in html

    def test_render_video_with_learning_objective(self, renderer):
        """Should render learning objective."""
        content = {
            'title': 'Test Video',
            'learning_objective': 'Learn Python basics'
        }
        html = renderer.render_video_script(content)

        assert 'Learn Python basics' in html
        assert 'Learning Objective' in html

    def test_render_video_wwhaa_sections(self, renderer):
        """Should render WWHAA sections without speaker notes."""
        content = {
            'title': 'Test',
            'hook': {
                'script_text': 'Welcome to the course!',
                'speaker_notes': 'Be enthusiastic'
            },
            'content': {
                'script_text': 'Main content here',
                'speaker_notes': 'Slow down for this part'
            }
        }
        html = renderer.render_video_script(content)

        # Should include script text
        assert 'Welcome to the course!' in html
        assert 'Main content here' in html

        # Should NOT include speaker notes (author-only)
        assert 'Be enthusiastic' not in html
        assert 'Slow down for this part' not in html

    def test_render_video_string_sections(self, renderer):
        """Should handle string section values."""
        content = {
            'hook': 'Simple hook text',
            'summary': 'Simple summary'
        }
        html = renderer.render_video_script(content)

        assert 'Simple hook text' in html
        assert 'Simple summary' in html


class TestReadingRendering:
    """Tests for reading preview rendering."""

    def test_render_reading_with_sections(self, renderer):
        """Should render reading sections."""
        content = {
            'title': 'Understanding APIs',
            'introduction': 'APIs are everywhere.',
            'sections': [
                {'heading': 'What is an API?', 'body': 'An API is...'},
                {'heading': 'REST APIs', 'body': 'REST stands for...'}
            ],
            'conclusion': 'Now you understand APIs.'
        }
        html = renderer.render_reading(content)

        assert 'Understanding APIs' in html
        assert 'APIs are everywhere.' in html
        assert 'What is an API?' in html
        assert 'An API is...' in html
        assert 'REST APIs' in html
        assert 'Now you understand APIs.' in html

    def test_render_reading_with_references(self, renderer):
        """Should render references."""
        content = {
            'title': 'Test',
            'references': [
                {'citation': 'Smith, 2023', 'url': 'https://example.com'},
                {'citation': 'Jones, 2022'}
            ]
        }
        html = renderer.render_reading(content)

        assert 'Smith, 2023' in html
        assert 'https://example.com' in html
        assert 'Jones, 2022' in html

    def test_render_reading_alternate_format(self, renderer):
        """Should handle alternate section format."""
        content = {
            'title': 'Test',
            'sections': [
                {'title': 'Section Title', 'content': 'Section content'}
            ]
        }
        html = renderer.render_reading(content)

        assert 'Section Title' in html
        assert 'Section content' in html


class TestQuizRendering:
    """Tests for quiz preview rendering."""

    def test_render_quiz_without_answers(self, renderer):
        """Should render quiz with feedback in hidden divs (revealed on click)."""
        content = {
            'title': 'Python Quiz',
            'passing_score_percentage': 70,
            'questions': [
                {
                    'question_text': 'What is Python?',
                    'options': [
                        {'text': 'A snake', 'is_correct': False, 'feedback': 'Wrong!'},
                        {'text': 'A programming language', 'is_correct': True, 'feedback': 'Correct!'},
                        {'text': 'A food', 'is_correct': False}
                    ],
                    'explanation': 'Python is a programming language.'
                }
            ]
        }
        html = renderer.render_quiz(content)

        # Should include question and options
        assert 'Python Quiz' in html
        assert 'What is Python?' in html
        assert 'A snake' in html
        assert 'A programming language' in html
        assert 'A food' in html

        # Feedback is in hidden divs, revealed on click via JavaScript
        assert 'class="option-feedback hidden"' in html
        # data-correct attribute is used for JavaScript interaction
        assert 'data-correct=' in html

    def test_render_quiz_with_radio_buttons(self, renderer):
        """Should render with radio button inputs."""
        content = {
            'questions': [
                {
                    'question_text': 'Test?',
                    'options': [
                        {'text': 'Option A'},
                        {'text': 'Option B'}
                    ]
                }
            ]
        }
        html = renderer.render_quiz(content)

        assert 'type="radio"' in html
        assert 'Option A' in html
        assert 'Option B' in html


class TestHOLRendering:
    """Tests for hands-on lab preview rendering."""

    def test_render_hol_with_parts(self, renderer):
        """Should render HOL with parts."""
        content = {
            'title': 'Build a REST API',
            'scenario': 'You are building an API for...',
            'parts': [
                {
                    'part_number': 1,
                    'title': 'Setup',
                    'estimated_minutes': 15,
                    'instructions': 'First, install the dependencies.'
                },
                {
                    'part_number': 2,
                    'title': 'Build',
                    'estimated_minutes': 30,
                    'instructions': 'Create the routes.'
                }
            ],
            'submission_criteria': 'Submit the code.'
        }
        html = renderer.render_hol(content)

        assert 'Build a REST API' in html
        assert 'You are building an API' in html
        assert 'Part 1: Setup' in html
        assert '15 minutes' in html
        assert 'Part 2: Build' in html
        assert 'Submit the code' in html


class TestCoachRendering:
    """Tests for coach dialogue preview rendering."""

    def test_render_coach_excludes_author_elements(self, renderer):
        """Should exclude sample responses and evaluation criteria."""
        content = {
            'title': 'Leadership Coaching',
            'scenario': 'Practice leading a team meeting.',
            'tasks': ['Introduce the agenda', 'Facilitate discussion'],
            'conversation_starters': [
                {'starter_text': 'Hello team!', 'purpose': 'Greeting'}
            ],
            'sample_responses': [
                {
                    'response_text': 'This is how to respond...',
                    'evaluation_level': 'meets',
                    'feedback': 'Good job!'
                }
            ],
            'evaluation_criteria': ['Clarity', 'Engagement'],
            'wrap_up': 'Great session!'
        }
        html = renderer.render_coach(content)

        # Should include learner-facing content
        assert 'Leadership Coaching' in html
        assert 'Practice leading a team' in html
        assert 'Introduce the agenda' in html
        assert 'Hello team!' in html
        assert 'Great session!' in html

        # Should NOT include author-only content
        assert 'This is how to respond' not in html
        assert 'meets' not in html
        assert 'Good job!' not in html
        assert 'Clarity' not in html
        assert 'Engagement' not in html


class TestLabRendering:
    """Tests for lab preview rendering."""

    def test_render_lab_with_exercises(self, renderer):
        """Should render lab with exercises."""
        content = {
            'title': 'Docker Lab',
            'overview': 'Learn Docker basics.',
            'estimated_minutes': 45,
            'prerequisites': ['Linux basics', 'Command line'],
            'learning_objectives': ['Build images', 'Run containers'],
            'lab_exercises': ['Build a Dockerfile', 'Run the container']
        }
        html = renderer.render_lab(content)

        assert 'Docker Lab' in html
        assert 'Learn Docker basics' in html
        assert '45 minutes' in html
        assert 'Linux basics' in html
        assert 'Build images' in html
        assert 'Build a Dockerfile' in html


class TestDiscussionRendering:
    """Tests for discussion preview rendering."""

    def test_render_discussion(self, renderer):
        """Should render discussion prompt and questions."""
        content = {
            'title': 'Ethics in AI',
            'main_prompt': 'What are the ethical implications of AI?',
            'facilitation_questions': [
                'How should we regulate AI?',
                'What role does consent play?'
            ],
            'engagement_hooks': ['Consider real-world examples']
        }
        html = renderer.render_discussion(content)

        assert 'Ethics in AI' in html
        assert 'What are the ethical implications' in html
        assert 'How should we regulate AI?' in html
        assert 'Consider real-world examples' in html


class TestAssignmentRendering:
    """Tests for assignment preview rendering."""

    def test_render_assignment_with_deliverables(self, renderer):
        """Should render assignment with deliverables and points."""
        content = {
            'title': 'Final Project',
            'overview': 'Build a web application.',
            'total_points': 100,
            'estimated_hours': 10,
            'deliverables': [
                {'item': 'Code repository', 'points': 50},
                {'item': 'Documentation', 'points': 30},
                {'item': 'Presentation', 'points': 20}
            ],
            'grading_criteria': ['Code quality', 'Documentation'],
            'submission_checklist': [
                {'item': 'Source code', 'required': True},
                {'item': 'Bonus features', 'required': False}
            ]
        }
        html = renderer.render_assignment(content)

        assert 'Final Project' in html
        assert 'Build a web application' in html
        assert '100' in html  # points
        assert '10 hours' in html
        assert 'Code repository' in html
        assert '50 points' in html
        assert 'Source code' in html
        assert 'optional' in html.lower()


class TestProjectRendering:
    """Tests for project preview rendering."""

    def test_render_project_with_milestones(self, renderer):
        """Should render project with milestones."""
        content = {
            'title': 'Capstone Project',
            'overview': 'Apply everything you learned.',
            'learning_objectives': ['Integrate skills', 'Present work'],
            'milestones': [
                {'title': 'Planning', 'description': 'Create project plan'},
                {'title': 'Implementation', 'description': 'Build the solution'},
                {'title': 'Presentation', 'description': 'Present results'}
            ],
            'grading_criteria': ['Completeness', 'Quality']
        }
        html = renderer.render_project(content)

        assert 'Capstone Project' in html
        assert 'Apply everything' in html
        assert 'Integrate skills' in html
        assert 'Milestone 1: Planning' in html
        assert 'Create project plan' in html
        assert 'Milestone 2: Implementation' in html


class TestGenericRendering:
    """Tests for generic content rendering."""

    def test_render_generic_content(self, renderer):
        """Should render unknown content types as generic sections."""
        content = {
            'title': 'Unknown Content',
            'description': 'Some description',
            'items': ['Item 1', 'Item 2']
        }
        html = renderer.render_generic(content)

        assert 'Unknown Content' in html
        assert 'Some description' in html
        assert 'Item 1' in html
        assert 'Item 2' in html


class TestRenderContent:
    """Tests for content dispatch method."""

    def test_dispatch_to_video_renderer(self, renderer):
        """Should dispatch video content to video renderer."""
        content = {'title': 'Video Title', 'hook': 'Hook text'}
        html = renderer.render_content('video', content)

        assert 'Video Title' in html
        assert 'Hook text' in html

    def test_dispatch_to_reading_renderer(self, renderer):
        """Should dispatch reading content to reading renderer."""
        content = {'title': 'Reading Title', 'introduction': 'Intro text'}
        html = renderer.render_content('reading', content)

        assert 'Reading Title' in html
        assert 'Intro text' in html

    def test_dispatch_to_quiz_renderer(self, renderer):
        """Should dispatch quiz content to quiz renderer."""
        content = {'title': 'Quiz', 'questions': []}
        html = renderer.render_content('quiz', content)

        assert 'Quiz' in html

    def test_parse_json_string(self, renderer):
        """Should parse JSON string content."""
        content = json.dumps({'title': 'JSON Title'})
        html = renderer.render_content('video', content)

        assert 'JSON Title' in html

    def test_handle_invalid_json(self, renderer):
        """Should handle invalid JSON gracefully."""
        content = 'Plain text content'
        html = renderer.render_content('video', content)

        assert 'Plain text content' in html

    def test_unknown_content_type(self, renderer):
        """Should fall back to generic renderer for unknown types."""
        content = {'title': 'Unknown', 'field': 'value'}
        html = renderer.render_content('unknown_type', content)

        assert 'Unknown' in html


class TestModuleFunction:
    """Tests for module-level convenience function."""

    def test_render_learner_preview(self):
        """Should use module-level function."""
        content = {'title': 'Test Video'}
        html = render_learner_preview('video', content)

        assert 'Test Video' in html


class TestHTMLEscaping:
    """Tests for HTML escaping."""

    def test_escape_html_in_content(self, renderer):
        """Should escape HTML special characters."""
        content = {
            'title': '<script>alert("XSS")</script>',
            'introduction': 'Text with <b>tags</b> & special chars'
        }
        html = renderer.render_reading(content)

        # Should escape HTML
        assert '&lt;script&gt;' in html
        assert '&lt;b&gt;' in html
        assert '&amp;' in html

        # Should not contain raw HTML
        assert '<script>' not in html
        assert '<b>' not in html


class TestEmptyContent:
    """Tests for empty content handling."""

    def test_empty_video_content(self, renderer):
        """Should handle empty video content."""
        html = renderer.render_video_script({})
        assert 'No content' in html or html.strip() == ''

    def test_empty_reading_content(self, renderer):
        """Should handle empty reading content."""
        html = renderer.render_reading({})
        assert 'No content' in html or html.strip() == ''

    def test_empty_quiz_content(self, renderer):
        """Should handle empty quiz content gracefully."""
        html = renderer.render_quiz({})
        # Quiz renderer includes JS/CSS boilerplate even for empty content
        # No actual question divs should be present (just the styles/scripts)
        assert '<div class="quiz-question"' not in html
