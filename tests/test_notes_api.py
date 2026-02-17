"""Tests for developer notes API endpoints."""

import pytest
from unittest.mock import MagicMock, patch
from flask import Flask
from flask_login import LoginManager

from src.api.notes import notes_bp, init_notes_bp
from src.core.models import Course, Module, Lesson, Activity, DeveloperNote, ContentType


@pytest.fixture
def app():
    """Create Flask app for testing."""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test-secret'
    app.config['TESTING'] = True
    app.config['LOGIN_DISABLED'] = True

    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        user = MagicMock()
        user.id = int(user_id)
        user.name = 'Test User'
        user.email = 'test@example.com'
        user.is_authenticated = True
        return user

    return app


@pytest.fixture
def mock_project_store():
    """Create mock project store."""
    return MagicMock()


@pytest.fixture
def sample_course():
    """Create sample course with notes."""
    course = Course(id='course-1', title='Test Course')

    # Add a course-level note
    course.developer_notes.append(
        DeveloperNote(
            id='note-course-1',
            content='Course-level note',
            author_id=1,
            author_name='Test User'
        )
    )

    module = Module(id='module-1', title='Module 1')
    module.developer_notes.append(
        DeveloperNote(
            id='note-module-1',
            content='Module note',
            author_id=1,
            author_name='Test User'
        )
    )

    lesson = Lesson(id='lesson-1', title='Lesson 1')
    lesson.developer_notes.append(
        DeveloperNote(
            id='note-lesson-1',
            content='Lesson note',
            author_id=1,
            author_name='Test User'
        )
    )

    activity = Activity(
        id='activity-1',
        title='Activity 1',
        content_type=ContentType.VIDEO
    )
    activity.developer_notes.append(
        DeveloperNote(
            id='note-activity-1',
            content='Activity note',
            author_id=1,
            author_name='Test User',
            pinned=True
        )
    )

    lesson.activities.append(activity)
    module.lessons.append(lesson)
    course.modules.append(module)

    return course


@pytest.fixture
def client(app, mock_project_store, sample_course):
    """Create test client with mocked dependencies."""
    init_notes_bp(mock_project_store)
    app.register_blueprint(notes_bp)

    # Mock Collaborator.get_course_owner_id in both modules
    with patch('src.api.notes.Collaborator') as mock_collab:
        mock_collab.get_course_owner_id.return_value = 1
        mock_project_store.load.return_value = sample_course

        # Mock current_user
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.name = 'Test User'
        mock_user.email = 'test@example.com'
        mock_user.is_authenticated = True

        with patch('src.api.notes.current_user', mock_user):
            # Also mock the decorator's current_user
            with patch('src.collab.decorators.current_user', mock_user):
                # Mock Collaborator in decorators module (for require_permission)
                with patch('src.collab.decorators.Collaborator') as mock_dec_collab:
                    mock_dec_collab.get_course_owner_id.return_value = 1
                    # Mock has_permission to always return True
                    with patch('src.collab.decorators.has_permission', return_value=True):
                        with app.test_client() as client:
                            yield client


class TestListAllNotes:
    """Tests for list_all_notes endpoint."""

    def test_list_all_notes_success(self, client, mock_project_store):
        """Should return all notes grouped by entity type."""
        response = client.get('/api/courses/course-1/notes')

        assert response.status_code == 200
        data = response.get_json()

        assert 'course' in data
        assert len(data['course']) == 1
        assert data['course'][0]['content'] == 'Course-level note'

        assert 'modules' in data
        assert 'module-1' in data['modules']

        assert 'lessons' in data
        assert 'lesson-1' in data['lessons']

        assert 'activities' in data
        assert 'activity-1' in data['activities']

    def test_list_all_notes_course_not_found(self, client, mock_project_store):
        """Should return 404 if course not found."""
        with patch('src.api.notes.Collaborator') as mock_collab:
            mock_collab.get_course_owner_id.return_value = None

            response = client.get('/api/courses/invalid-course/notes')
            assert response.status_code == 404


class TestCreateCourseNote:
    """Tests for create_course_note endpoint."""

    def test_create_course_note_success(self, client, mock_project_store, sample_course):
        """Should create a note at course level."""
        response = client.post(
            '/api/courses/course-1/notes',
            json={'content': 'New course note'}
        )

        assert response.status_code == 201
        data = response.get_json()

        assert data['content'] == 'New course note'
        assert 'id' in data
        assert data['author_name'] == 'Test User'

        mock_project_store.save.assert_called_once()

    def test_create_course_note_empty_content(self, client):
        """Should reject empty content."""
        response = client.post(
            '/api/courses/course-1/notes',
            json={'content': '   '}
        )

        assert response.status_code == 400
        assert 'required' in response.get_json()['error'].lower()


class TestCreateActivityNote:
    """Tests for create_activity_note endpoint."""

    def test_create_activity_note_success(self, client, mock_project_store):
        """Should create a note on an activity."""
        response = client.post(
            '/api/courses/course-1/activities/activity-1/notes',
            json={'content': 'New activity note', 'pinned': True}
        )

        assert response.status_code == 201
        data = response.get_json()

        assert data['content'] == 'New activity note'
        assert data['pinned'] is True

    def test_create_activity_note_not_found(self, client, mock_project_store, sample_course):
        """Should return 404 if activity not found."""
        response = client.post(
            '/api/courses/course-1/activities/invalid-activity/notes',
            json={'content': 'Note'}
        )

        assert response.status_code == 404


class TestUpdateNote:
    """Tests for update_note endpoint."""

    def test_update_note_content(self, client, mock_project_store):
        """Should update note content."""
        response = client.put(
            '/api/courses/course-1/notes/note-activity-1',
            json={'content': 'Updated content'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['content'] == 'Updated content'

    def test_update_note_pinned(self, client, mock_project_store):
        """Should update note pinned status."""
        response = client.put(
            '/api/courses/course-1/notes/note-activity-1',
            json={'pinned': False}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['pinned'] is False

    def test_update_note_not_found(self, client, mock_project_store):
        """Should return 404 if note not found."""
        response = client.put(
            '/api/courses/course-1/notes/invalid-note',
            json={'content': 'Updated'}
        )

        assert response.status_code == 404

    def test_update_note_empty_content(self, client):
        """Should reject empty content."""
        response = client.put(
            '/api/courses/course-1/notes/note-activity-1',
            json={'content': ''}
        )

        assert response.status_code == 400


class TestDeleteNote:
    """Tests for delete_note endpoint."""

    def test_delete_note_success(self, client, mock_project_store, sample_course):
        """Should delete note."""
        # Get initial count
        initial_count = len(sample_course.modules[0].lessons[0].activities[0].developer_notes)

        response = client.delete('/api/courses/course-1/notes/note-activity-1')

        assert response.status_code == 200
        assert 'deleted' in response.get_json()['message'].lower()

        # Verify note was removed
        final_count = len(sample_course.modules[0].lessons[0].activities[0].developer_notes)
        assert final_count == initial_count - 1

    def test_delete_note_not_found(self, client, mock_project_store):
        """Should return 404 if note not found."""
        response = client.delete('/api/courses/course-1/notes/invalid-note')
        assert response.status_code == 404


class TestListActivityNotes:
    """Tests for list_activity_notes endpoint."""

    def test_list_activity_notes_success(self, client, mock_project_store):
        """Should return notes for specific activity."""
        response = client.get('/api/courses/course-1/activities/activity-1/notes')

        assert response.status_code == 200
        data = response.get_json()

        assert 'notes' in data
        assert len(data['notes']) == 1
        assert data['notes'][0]['content'] == 'Activity note'

    def test_list_activity_notes_sorted(self, client, mock_project_store, sample_course):
        """Should return notes with pinned first."""
        # Add an unpinned note
        activity = sample_course.modules[0].lessons[0].activities[0]
        activity.developer_notes.append(
            DeveloperNote(
                id='note-activity-2',
                content='Second note',
                author_id=1,
                author_name='Test User',
                pinned=False
            )
        )

        response = client.get('/api/courses/course-1/activities/activity-1/notes')

        assert response.status_code == 200
        data = response.get_json()

        # Pinned note should be first
        assert data['notes'][0]['pinned'] is True


class TestModuleNotes:
    """Tests for module-level notes."""

    def test_list_module_notes(self, client):
        """Should return notes for specific module."""
        response = client.get('/api/courses/course-1/modules/module-1/notes')

        assert response.status_code == 200
        data = response.get_json()

        assert 'notes' in data
        assert len(data['notes']) == 1
        assert data['notes'][0]['content'] == 'Module note'

    def test_create_module_note(self, client, mock_project_store):
        """Should create note on module."""
        response = client.post(
            '/api/courses/course-1/modules/module-1/notes',
            json={'content': 'New module note'}
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['content'] == 'New module note'


class TestLessonNotes:
    """Tests for lesson-level notes."""

    def test_list_lesson_notes(self, client):
        """Should return notes for specific lesson."""
        response = client.get('/api/courses/course-1/lessons/lesson-1/notes')

        assert response.status_code == 200
        data = response.get_json()

        assert 'notes' in data
        assert len(data['notes']) == 1
        assert data['notes'][0]['content'] == 'Lesson note'

    def test_create_lesson_note(self, client, mock_project_store):
        """Should create note on lesson."""
        response = client.post(
            '/api/courses/course-1/lessons/lesson-1/notes',
            json={'content': 'New lesson note'}
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['content'] == 'New lesson note'
