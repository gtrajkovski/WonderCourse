"""Shared pytest fixtures for all tests."""

import os
import tempfile
import pytest
from pathlib import Path

from src.core.project_store import ProjectStore
from src.core.models import Course
from app import app as flask_app


@pytest.fixture
def tmp_store(tmp_path):
    """Create a temporary ProjectStore for isolated testing.

    Args:
        tmp_path: pytest's built-in temporary directory fixture.

    Returns:
        ProjectStore instance using temporary directory.
    """
    return ProjectStore(tmp_path / "projects")


@pytest.fixture
def auth_app(tmp_path, monkeypatch):
    """Create Flask app configured for testing with auth support.

    Sets up isolated database and project store for each test.
    Disables rate limiting.

    Returns:
        Configured Flask app instance.
    """
    from src.auth.db import init_db
    from src.auth.routes import init_auth_bp

    # Create temporary database
    db_fd, db_path = tempfile.mkstemp()

    # Create temporary projects directory
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir(parents=True, exist_ok=True)

    # Patch the project_store base_dir
    import app as app_module
    monkeypatch.setattr(app_module.project_store, 'base_dir', projects_dir)

    # Re-initialize blueprints with the patched project_store
    from src.api.modules import init_modules_bp
    from src.api.lessons import init_lessons_bp
    from src.api.activities import init_activities_bp
    from src.api.learning_outcomes import init_learning_outcomes_bp
    from src.api.blueprint import init_blueprint_bp
    from src.api.content import init_content_bp
    from src.api.build_state import init_build_state_bp
    from src.api.textbook import init_textbook_bp
    from src.api.validation import init_validation_bp
    from src.api.export import init_export_bp
    from src.api.import_bp import init_import_bp
    from src.api.coach_bp import init_coach_bp
    from src.api.learner_profiles import init_learner_profiles_bp
    from src.api.duration import init_duration_bp
    from src.core.taxonomy_store import TaxonomyStore
    from src.api.taxonomies import init_taxonomies_bp

    init_modules_bp(app_module.project_store)
    init_lessons_bp(app_module.project_store)
    init_activities_bp(app_module.project_store)
    init_learning_outcomes_bp(app_module.project_store)
    init_blueprint_bp(app_module.project_store)
    init_content_bp(app_module.project_store)
    init_build_state_bp(app_module.project_store)
    init_textbook_bp(app_module.project_store)
    init_validation_bp(app_module.project_store)
    init_export_bp(app_module.project_store)
    init_import_bp(app_module.project_store)
    init_coach_bp(app_module.project_store)
    init_learner_profiles_bp(tmp_path / "learner_profiles")
    init_duration_bp(app_module.project_store)
    taxonomy_store = TaxonomyStore(tmp_path / "taxonomies")
    init_taxonomies_bp(taxonomy_store, app_module.project_store)

    # Configure Flask app for testing
    flask_app.config.update({
        'TESTING': True,
        'DATABASE': db_path,
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False,
    })

    # Re-init auth blueprint AFTER setting TESTING=True to disable rate limiter
    init_auth_bp(flask_app)

    # Initialize database
    with flask_app.app_context():
        init_db()
        # Seed collaboration permissions for tests
        from src.collab.permissions import seed_permissions
        from src.auth.db import get_db
        seed_permissions(get_db())

    yield flask_app

    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def authenticated_client(auth_app):
    """Create a test client with a logged-in user.

    Creates a test user and logs them in.

    Returns:
        Flask test client with authenticated session.
    """
    client = auth_app.test_client()

    # Register a test user
    client.post('/api/auth/register', json={
        'email': 'test@example.com',
        'password': 'testpassword123',
        'name': 'Test User'
    })

    # Log in the test user
    client.post('/api/auth/login', json={
        'email': 'test@example.com',
        'password': 'testpassword123'
    })

    return client


@pytest.fixture
def sample_course():
    """Create a sample Course object for testing.

    Returns:
        Course instance with test data (no modules/lessons/activities).
    """
    return Course(
        title="Introduction to Python",
        description="Learn Python fundamentals",
        audience_level="beginner",
        target_duration_minutes=120,
        modality="online"
    )


@pytest.fixture
def sample_course_with_content():
    """Create a sample Course with modules, lessons, and activities for testing.

    Returns:
        Course instance with complete content hierarchy.
    """
    from src.core.models import Module, Lesson, Activity, ContentType

    course = Course(
        title="Introduction to Python",
        description="Learn Python fundamentals",
        audience_level="beginner",
        target_duration_minutes=120,
        modality="online"
    )

    activity = Activity(
        title="Introduction Video",
        content_type=ContentType.VIDEO
    )

    lesson = Lesson(title="Getting Started")
    lesson.activities.append(activity)

    module = Module(title="Python Basics", description="Learn the fundamentals")
    module.lessons.append(lesson)

    course.modules.append(module)

    return course


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Create Flask test client with temporary ProjectStore and authenticated user.

    Sets up isolated database and project store, creates and logs in a test user.

    Args:
        tmp_path: pytest's built-in temporary directory fixture.
        monkeypatch: pytest fixture for modifying objects.

    Returns:
        Flask test client with authenticated session.
    """
    from src.auth.db import init_db
    from src.auth.routes import init_auth_bp

    # Create temporary database
    db_fd, db_path = tempfile.mkstemp()

    # Create temporary projects directory
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir(parents=True, exist_ok=True)

    # Patch the module-level project_store in app module
    from src.config import Config
    monkeypatch.setattr(Config, 'PROJECTS_DIR', projects_dir)

    # Import app and patch its project_store
    import app as app_module
    app_module.project_store = ProjectStore(projects_dir)
    monkeypatch.setattr(app_module.project_store, 'base_dir', projects_dir)

    # Re-initialize all blueprints with the test project_store
    from src.api.modules import init_modules_bp
    from src.api.lessons import init_lessons_bp
    from src.api.activities import init_activities_bp
    from src.api.learning_outcomes import init_learning_outcomes_bp
    from src.api.blueprint import init_blueprint_bp
    from src.api.content import init_content_bp
    from src.api.build_state import init_build_state_bp
    from src.api.textbook import init_textbook_bp
    from src.api.validation import init_validation_bp
    from src.api.export import init_export_bp
    from src.api.coach_bp import init_coach_bp
    from src.core.taxonomy_store import TaxonomyStore
    from src.api.taxonomies import init_taxonomies_bp

    init_modules_bp(app_module.project_store)
    init_lessons_bp(app_module.project_store)
    init_activities_bp(app_module.project_store)
    init_learning_outcomes_bp(app_module.project_store)
    init_blueprint_bp(app_module.project_store)
    init_content_bp(app_module.project_store)
    init_build_state_bp(app_module.project_store)
    init_textbook_bp(app_module.project_store)
    init_validation_bp(app_module.project_store)
    init_export_bp(app_module.project_store)
    init_coach_bp(app_module.project_store)
    taxonomy_store = TaxonomyStore(tmp_path / "taxonomies")
    init_taxonomies_bp(taxonomy_store, app_module.project_store)

    # Configure Flask app for testing with auth support
    flask_app.config.update({
        'TESTING': True,
        'DATABASE': db_path,
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False,
    })

    # Re-init auth blueprint AFTER setting TESTING=True to disable rate limiter
    init_auth_bp(flask_app)

    # Initialize database
    with flask_app.app_context():
        init_db()
        # Seed collaboration permissions for tests
        from src.collab.permissions import seed_permissions
        from src.auth.db import get_db
        seed_permissions(get_db())

    # Create test client
    test_client = flask_app.test_client()

    # Register and login a test user
    test_client.post('/api/auth/register', json={
        'email': 'test@example.com',
        'password': 'testpassword123',
        'name': 'Test User'
    })
    test_client.post('/api/auth/login', json={
        'email': 'test@example.com',
        'password': 'testpassword123'
    })

    yield test_client

    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)
