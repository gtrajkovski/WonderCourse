"""Tests for validation API endpoints."""
import pytest
import json
from src.core.models import (
    Course, Module, Lesson, Activity, LearningOutcome,
    ContentType, BloomLevel, BuildState
)


@pytest.fixture
def test_store(client):
    """Get the project store used by the client fixture."""
    import app as app_module
    return app_module.project_store


@pytest.fixture
def valid_course(test_store, client):
    """Create a course that passes most validation."""
    from src.collab.decorators import ensure_owner_collaborator
    import app as app_module

    course = Course(title="Valid Course", target_duration_minutes=60)

    # Add 2 modules with 3 lessons each, 2 activities each
    for m_idx in range(2):
        module = Module(title=f"Module {m_idx+1}")
        for l_idx in range(3):
            lesson = Lesson(title=f"Lesson {l_idx+1}")
            for a_idx in range(2):
                bloom = [BloomLevel.UNDERSTAND, BloomLevel.APPLY, BloomLevel.ANALYZE][l_idx % 3]
                activity = Activity(
                    title=f"Activity {a_idx+1}",
                    content_type=ContentType.VIDEO if a_idx == 0 else ContentType.READING,
                    bloom_level=bloom,
                    estimated_duration_minutes=5.0
                )
                lesson.activities.append(activity)
            module.lessons.append(lesson)
        course.modules.append(module)

    # User ID 1 is the authenticated test user from conftest.py
    test_store.save(1, course)

    # Create owner collaborator record in database
    with app_module.app.app_context():
        ensure_owner_collaborator(course.id, 1)

    return course


@pytest.fixture
def invalid_course(test_store, client):
    """Create a course that fails validation."""
    from src.collab.decorators import ensure_owner_collaborator
    import app as app_module

    course = Course(title="Invalid Course")
    # Only 1 module (needs 2-3)
    course.modules = [Module(title="Only One")]
    # User ID 1 is the authenticated test user from conftest.py
    test_store.save(1, course)

    # Create owner collaborator record in database
    with app_module.app.app_context():
        ensure_owner_collaborator(course.id, 1)

    return course


class TestValidateEndpoint:
    def test_validate_returns_report(self, client, valid_course):
        response = client.get(f'/api/courses/{valid_course.id}/validate')
        assert response.status_code == 200

        data = response.get_json()
        assert "is_publishable" in data
        assert "validators" in data
        assert "summary" in data
        assert "CourseValidator" in data["validators"]
        assert "OutcomeValidator" in data["validators"]
        assert "BloomsValidator" in data["validators"]
        assert "DistractorValidator" in data["validators"]

    def test_validate_returns_errors_for_invalid(self, client, invalid_course):
        response = client.get(f'/api/courses/{invalid_course.id}/validate')
        assert response.status_code == 200

        data = response.get_json()
        assert data["is_publishable"] is False
        assert data["summary"]["total_errors"] > 0

    def test_validate_course_not_found(self, client):
        response = client.get('/api/courses/nonexistent/validate')
        assert response.status_code == 404

    def test_validate_returns_summary_counts(self, client, valid_course):
        response = client.get(f'/api/courses/{valid_course.id}/validate')
        assert response.status_code == 200

        data = response.get_json()
        summary = data["summary"]
        assert "total_errors" in summary
        assert "total_warnings" in summary
        assert "total_suggestions" in summary
        assert isinstance(summary["total_errors"], int)
        assert isinstance(summary["total_warnings"], int)
        assert isinstance(summary["total_suggestions"], int)

    def test_validate_returns_validator_results(self, client, valid_course):
        response = client.get(f'/api/courses/{valid_course.id}/validate')
        assert response.status_code == 200

        data = response.get_json()
        for validator_name, result in data["validators"].items():
            assert "is_valid" in result
            assert "errors" in result
            assert "warnings" in result
            assert "suggestions" in result
            assert "metrics" in result


class TestPublishableEndpoint:
    def test_publishable_quick_check(self, client, valid_course):
        response = client.get(f'/api/courses/{valid_course.id}/publishable')
        assert response.status_code == 200

        data = response.get_json()
        assert "is_publishable" in data
        assert "error_count" in data

    def test_publishable_returns_false_for_invalid(self, client, invalid_course):
        response = client.get(f'/api/courses/{invalid_course.id}/publishable')
        assert response.status_code == 200

        data = response.get_json()
        assert data["is_publishable"] is False
        assert data["error_count"] > 0

    def test_publishable_course_not_found(self, client):
        response = client.get('/api/courses/nonexistent/publishable')
        assert response.status_code == 404


class TestBuildStatePublishingGate:
    def test_publish_blocked_for_invalid_course(self, client, invalid_course, test_store):
        # Create an activity in APPROVED state
        lesson = Lesson(title="L1")
        activity = Activity(
            title="A1",
            build_state=BuildState.APPROVED,
            estimated_duration_minutes=60
        )
        lesson.activities.append(activity)
        invalid_course.modules[0].lessons.append(lesson)
        test_store.save(1, invalid_course)

        # Try to publish - should fail due to validation
        response = client.put(
            f'/api/courses/{invalid_course.id}/activities/{activity.id}/state',
            json={"build_state": "published"}
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "validation" in data["error"].lower()

    def test_publish_allowed_for_valid_course(self, client, valid_course, test_store):
        # Get an activity and move it to APPROVED state
        activity = valid_course.modules[0].lessons[0].activities[0]
        activity.build_state = BuildState.APPROVED
        test_store.save(1, valid_course)

        # Try to publish - should succeed
        response = client.put(
            f'/api/courses/{valid_course.id}/activities/{activity.id}/state',
            json={"build_state": "published"}
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["build_state"] == "published"

    def test_publish_error_includes_hint(self, client, invalid_course, test_store):
        # Create an activity in APPROVED state
        lesson = Lesson(title="L1")
        activity = Activity(
            title="A1",
            build_state=BuildState.APPROVED,
            estimated_duration_minutes=60
        )
        lesson.activities.append(activity)
        invalid_course.modules[0].lessons.append(lesson)
        test_store.save(1, invalid_course)

        # Try to publish
        response = client.put(
            f'/api/courses/{invalid_course.id}/activities/{activity.id}/state',
            json={"build_state": "published"}
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "hint" in data
        assert "/validate" in data["hint"]
