"""Integration tests for content generation API endpoints."""

import pytest
from unittest.mock import MagicMock, patch
import json

from src.core.models import ContentType, ActivityType, BuildState
from src.core.project_store import ProjectStore
from src.collab.models import Collaborator
from app import app as flask_app


def _load_course(course_id):
    """Helper to load course with owner_id lookup."""
    import app as app_module
    with flask_app.app_context():
        owner_id = Collaborator.get_course_owner_id(course_id)
    return app_module.project_store.load(owner_id, course_id)


def _save_course(course_id, course):
    """Helper to save course with owner_id lookup."""
    import app as app_module
    with flask_app.app_context():
        owner_id = Collaborator.get_course_owner_id(course_id)
    app_module.project_store.save(owner_id, course)


# Uses client fixture from conftest.py which includes authentication


@pytest.fixture
def setup_course_structure(client):
    """Create a course with module, lesson, and activities for testing.

    Returns:
        dict: IDs for course, module, lesson, and activities by type
    """
    # Create course
    resp = client.post('/api/courses', json={
        "title": "Test Course",
        "description": "Test course for content generation",
        "audience_level": "intermediate",
        "target_duration_minutes": 120
    })
    course_id = resp.get_json()["id"]

    # Create module
    resp = client.post(f'/api/courses/{course_id}/modules', json={
        "title": "Module 1",
        "description": "Test module"
    })
    module_id = resp.get_json()["id"]

    # Create lesson
    resp = client.post(f'/api/courses/{course_id}/modules/{module_id}/lessons', json={
        "title": "Lesson 1",
        "description": "Test lesson"
    })
    lesson_id = resp.get_json()["id"]

    # Create activities for different content types
    activities = {}

    # VIDEO activity
    resp = client.post(f'/api/courses/{course_id}/lessons/{lesson_id}/activities', json={
        "title": "Video 1",
        "content_type": "video",
        "activity_type": "video_lecture"
    })
    activities["video"] = resp.get_json()["id"]

    # READING activity
    resp = client.post(f'/api/courses/{course_id}/lessons/{lesson_id}/activities', json={
        "title": "Reading 1",
        "content_type": "reading",
        "activity_type": "reading_material"
    })
    activities["reading"] = resp.get_json()["id"]

    # QUIZ activity
    resp = client.post(f'/api/courses/{course_id}/lessons/{lesson_id}/activities', json={
        "title": "Quiz 1",
        "content_type": "quiz",
        "activity_type": "graded_quiz"
    })
    activities["quiz"] = resp.get_json()["id"]

    # RUBRIC activity
    resp = client.post(f'/api/courses/{course_id}/lessons/{lesson_id}/activities', json={
        "title": "Rubric 1",
        "content_type": "rubric",
        "activity_type": "peer_review"
    })
    activities["rubric"] = resp.get_json()["id"]

    # HOL activity
    resp = client.post(f'/api/courses/{course_id}/lessons/{lesson_id}/activities', json={
        "title": "HOL 1",
        "content_type": "hol",
        "activity_type": "hands_on_lab"
    })
    activities["hol"] = resp.get_json()["id"]

    # COACH activity
    resp = client.post(f'/api/courses/{course_id}/lessons/{lesson_id}/activities', json={
        "title": "Coach 1",
        "content_type": "coach",
        "activity_type": "coach_dialogue"
    })
    activities["coach"] = resp.get_json()["id"]

    # PRACTICE_QUIZ activity
    resp = client.post(f'/api/courses/{course_id}/lessons/{lesson_id}/activities', json={
        "title": "Practice Quiz 1",
        "content_type": "quiz",
        "activity_type": "practice_quiz"
    })
    activities["practice_quiz"] = resp.get_json()["id"]

    # LAB activity
    resp = client.post(f'/api/courses/{course_id}/lessons/{lesson_id}/activities', json={
        "title": "Lab 1",
        "content_type": "lab",
        "activity_type": "ungraded_lab"
    })
    activities["lab"] = resp.get_json()["id"]

    # DISCUSSION activity
    resp = client.post(f'/api/courses/{course_id}/lessons/{lesson_id}/activities', json={
        "title": "Discussion 1",
        "content_type": "discussion",
        "activity_type": "discussion_prompt"
    })
    activities["discussion"] = resp.get_json()["id"]

    # ASSIGNMENT activity
    resp = client.post(f'/api/courses/{course_id}/lessons/{lesson_id}/activities', json={
        "title": "Assignment 1",
        "content_type": "assignment",
        "activity_type": "assignment_submission"
    })
    activities["assignment"] = resp.get_json()["id"]

    # PROJECT activity
    resp = client.post(f'/api/courses/{course_id}/lessons/{lesson_id}/activities', json={
        "title": "Project 1",
        "content_type": "project",
        "activity_type": "project_milestone"
    })
    activities["project"] = resp.get_json()["id"]

    return {
        "course_id": course_id,
        "module_id": module_id,
        "lesson_id": lesson_id,
        "activities": activities
    }


def test_generate_video_content(client, setup_course_structure, mocker):
    """Test generating video script content."""
    course_id = setup_course_structure["course_id"]
    activity_id = setup_course_structure["activities"]["video"]

    # Mock VideoScriptGenerator
    mock_content = MagicMock()
    mock_content.model_dump.return_value = {
        "hook": {"script_text": "Hook text"},
        "objective": {"script_text": "Objective text"},
        "content": {"script_text": "Content text"},
        "ivq": {"script_text": "IVQ text"},
        "summary": {"script_text": "Summary text"},
        "cta": {"script_text": "CTA text"}
    }
    mock_content.model_dump_json.return_value = json.dumps(mock_content.model_dump.return_value)

    mock_metadata = {
        "word_count": 1200,
        "estimated_duration_minutes": 8.0,
        "content_type": "video"
    }

    mock_generator = mocker.patch("src.api.content.VideoScriptGenerator")
    mock_generator.return_value.generate.return_value = (mock_content, mock_metadata)

    # Generate content
    resp = client.post(f'/api/courses/{course_id}/activities/{activity_id}/generate', json={
        "learning_objective": "Understand variables",
        "topic": "Python variables",
        "audience_level": "beginner",
        "duration_minutes": 8
    })

    assert resp.status_code == 200
    data = resp.get_json()
    assert "content" in data
    assert "metadata" in data
    assert data["metadata"]["word_count"] == 1200
    assert data["metadata"]["estimated_duration_minutes"] == 8.0
    assert data["build_state"] == "generated"


def test_generate_reading_content(client, setup_course_structure, mocker):
    """Test generating reading material content."""
    course_id = setup_course_structure["course_id"]
    activity_id = setup_course_structure["activities"]["reading"]

    # Mock ReadingGenerator
    mock_content = MagicMock()
    mock_content.model_dump.return_value = {
        "title": "Test Reading",
        "sections": [{"heading": "Section 1", "content": "Content"}]
    }
    mock_content.model_dump_json.return_value = json.dumps(mock_content.model_dump.return_value)

    mock_metadata = {
        "word_count": 800,
        "estimated_duration_minutes": 3.4,
        "content_type": "reading"
    }

    mock_generator = mocker.patch("src.api.content.ReadingGenerator")
    mock_generator.return_value.generate.return_value = (mock_content, mock_metadata)

    # Generate content
    resp = client.post(f'/api/courses/{course_id}/activities/{activity_id}/generate', json={
        "learning_objective": "Understand loops",
        "topic": "Python loops"
    })

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["metadata"]["word_count"] == 800
    assert data["build_state"] == "generated"


def test_generate_quiz_content(client, setup_course_structure, mocker):
    """Test generating quiz content."""
    course_id = setup_course_structure["course_id"]
    activity_id = setup_course_structure["activities"]["quiz"]

    # Mock QuizGenerator
    mock_content = MagicMock()
    mock_content.model_dump.return_value = {
        "title": "Test Quiz",
        "questions": [
            {"question_text": "Q1", "options": [{"text": "A", "is_correct": True}]}
        ]
    }
    mock_content.model_dump_json.return_value = json.dumps(mock_content.model_dump.return_value)

    mock_metadata = {
        "word_count": 200,
        "estimated_duration_minutes": 7.5,
        "question_count": 5,
        "content_type": "quiz"
    }

    mock_generator = mocker.patch("src.api.content.QuizGenerator")
    mock_generator.return_value.generate.return_value = (mock_content, mock_metadata)

    # Generate content
    resp = client.post(f'/api/courses/{course_id}/activities/{activity_id}/generate', json={
        "learning_objective": "Apply conditionals",
        "topic": "Python if statements",
        "bloom_level": "apply",
        "num_questions": 5
    })

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["metadata"]["question_count"] == 5
    assert data["build_state"] == "generated"


def test_generate_rubric_content(client, setup_course_structure, mocker):
    """Test generating rubric content."""
    course_id = setup_course_structure["course_id"]
    activity_id = setup_course_structure["activities"]["rubric"]

    # Mock RubricGenerator
    mock_content = MagicMock()
    mock_content.model_dump.return_value = {
        "title": "Test Rubric",
        "criteria": [{"name": "Quality", "description": "Code quality"}]
    }
    mock_content.model_dump_json.return_value = json.dumps(mock_content.model_dump.return_value)

    mock_metadata = {
        "word_count": 500,
        "estimated_duration_minutes": 2.1,
        "content_type": "rubric"
    }

    mock_generator = mocker.patch("src.api.content.RubricGenerator")
    mock_generator.return_value.generate.return_value = (mock_content, mock_metadata)

    # Generate content
    resp = client.post(f'/api/courses/{course_id}/activities/{activity_id}/generate', json={
        "learning_objective": "Evaluate code quality",
        "topic": "Python project assessment"
    })

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["metadata"]["word_count"] == 500
    assert data["build_state"] == "generated"


def test_generate_hol_content(client, setup_course_structure, mocker):
    """Test generating HOL content."""
    course_id = setup_course_structure["course_id"]
    activity_id = setup_course_structure["activities"]["hol"]

    # Mock HOLGenerator
    mock_content = MagicMock()
    mock_content.model_dump.return_value = {
        "title": "Test HOL",
        "parts": [{"title": "Foundation", "estimated_minutes": 15}]
    }
    mock_content.model_dump_json.return_value = json.dumps(mock_content.model_dump.return_value)

    mock_metadata = {
        "word_count": 600,
        "estimated_duration_minutes": 45.0,
        "content_type": "hol"
    }

    mock_generator = mocker.patch("src.api.content.HOLGenerator")
    mock_generator.return_value.generate.return_value = (mock_content, mock_metadata)

    # Generate content
    resp = client.post(f'/api/courses/{course_id}/activities/{activity_id}/generate', json={
        "learning_objective": "Complete hands-on lab",
        "topic": "Docker containers"
    })

    assert resp.status_code == 200
    data = resp.get_json()
    assert "content" in data
    assert "metadata" in data
    assert data["metadata"]["word_count"] == 600
    assert data["build_state"] == "generated"


def test_generate_sets_build_state(client, setup_course_structure, mocker):
    """Test that generate correctly transitions build state."""
    course_id = setup_course_structure["course_id"]
    activity_id = setup_course_structure["activities"]["video"]

    # Mock generator
    mock_content = MagicMock()
    mock_content.model_dump.return_value = {"hook": {"script_text": "test"}}
    mock_content.model_dump_json.return_value = "{}"
    mock_metadata = {"word_count": 100, "estimated_duration_minutes": 1.0}

    mock_generator = mocker.patch("src.api.content.VideoScriptGenerator")
    mock_generator.return_value.generate.return_value = (mock_content, mock_metadata)

    # Verify initial state is DRAFT
    resp = client.get(f'/api/courses/{course_id}')
    course = resp.get_json()
    activity = None
    for module in course["modules"]:
        for lesson in module["lessons"]:
            for act in lesson["activities"]:
                if act["id"] == activity_id:
                    activity = act
                    break

    assert activity["build_state"] == "draft"

    # Generate content
    resp = client.post(f'/api/courses/{course_id}/activities/{activity_id}/generate', json={})
    assert resp.status_code == 200
    assert resp.get_json()["build_state"] == "generated"

    # Verify state persisted
    resp = client.get(f'/api/courses/{course_id}')
    course = resp.get_json()
    for module in course["modules"]:
        for lesson in module["lessons"]:
            for act in lesson["activities"]:
                if act["id"] == activity_id:
                    assert act["build_state"] == "generated"


def test_generate_conflict_when_generating(client, setup_course_structure, mocker):
    """Test that generating while already generating returns 409."""
    course_id = setup_course_structure["course_id"]
    activity_id = setup_course_structure["activities"]["video"]

    # Set activity to GENERATING state
    # First, get the activity to modify it directly via activities API
    # We'll use the update endpoint to set build_state (though this is a bit of a hack)
    # Actually, we need to load and modify through the API, but there's no direct
    # build_state setter in activities API. Let's directly modify via internal state.

    # Import and modify directly for this test
    course = _load_course(course_id)
    for module in course.modules:
        for lesson in module.lessons:
            for act in lesson.activities:
                if act.id == activity_id:
                    act.build_state = BuildState.GENERATING
                    _save_course(course_id, course)
                    break

    # Try to generate
    resp = client.post(f'/api/courses/{course_id}/activities/{activity_id}/generate', json={})

    assert resp.status_code == 409
    data = resp.get_json()
    assert "already in progress" in data["error"]


def test_regenerate_preserves_previous(client, setup_course_structure, mocker):
    """Test that regenerate preserves previous content."""
    course_id = setup_course_structure["course_id"]
    activity_id = setup_course_structure["activities"]["video"]

    # Mock generator
    mock_content = MagicMock()
    mock_content.model_dump.return_value = {"hook": {"script_text": "test"}}
    mock_content.model_dump_json.return_value = '{"hook": {"script_text": "test"}}'
    mock_metadata = {"word_count": 100, "estimated_duration_minutes": 1.0}

    mock_generator = mocker.patch("src.api.content.VideoScriptGenerator")
    mock_generator.return_value.generate.return_value = (mock_content, mock_metadata)

    # Generate initial content
    resp = client.post(f'/api/courses/{course_id}/activities/{activity_id}/generate', json={})
    assert resp.status_code == 200
    initial_content = resp.get_json()["content"]

    # Regenerate with different content
    mock_content.model_dump_json.return_value = '{"hook": {"script_text": "new test"}}'
    mock_metadata["word_count"] = 150

    resp = client.post(f'/api/courses/{course_id}/activities/{activity_id}/regenerate', json={
        "feedback": "Make it longer"
    })

    assert resp.status_code == 200

    # Verify previous content was preserved
    course = _load_course(course_id)
    for module in course.modules:
        for lesson in module.lessons:
            for act in lesson.activities:
                if act.id == activity_id:
                    assert "previous_content" in act.metadata
                    assert len(act.metadata["previous_content"]) == 1
                    assert act.metadata["previous_content"][0]["word_count"] == 100


def test_regenerate_requires_existing_content(client, setup_course_structure):
    """Test that regenerate on DRAFT activity returns 400."""
    course_id = setup_course_structure["course_id"]
    activity_id = setup_course_structure["activities"]["video"]

    # Try to regenerate without generating first
    resp = client.post(f'/api/courses/{course_id}/activities/{activity_id}/regenerate', json={})

    assert resp.status_code == 400
    data = resp.get_json()
    assert "No existing content" in data["error"]


def test_edit_content_inline(client, setup_course_structure):
    """Test editing content via PUT endpoint."""
    course_id = setup_course_structure["course_id"]
    activity_id = setup_course_structure["activities"]["video"]

    # Edit content
    new_content = "This is edited content"
    resp = client.put(f'/api/courses/{course_id}/activities/{activity_id}/content', json={
        "content": new_content,
        "build_state": "reviewed"
    })

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["content"] == new_content
    assert data["build_state"] == "reviewed"


def test_edit_content_recalculates_word_count(client, setup_course_structure):
    """Test that editing content recalculates word count."""
    course_id = setup_course_structure["course_id"]
    activity_id = setup_course_structure["activities"]["video"]

    # Edit with known word count
    new_content = "one two three four five"  # 5 words
    resp = client.put(f'/api/courses/{course_id}/activities/{activity_id}/content', json={
        "content": new_content
    })

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["word_count"] == 5


def test_generate_404_course_not_found(client):
    """Test that generate with bad course_id returns 404."""
    resp = client.post('/api/courses/bad_course_id/activities/bad_activity_id/generate', json={})

    assert resp.status_code == 404
    data = resp.get_json()
    assert "Course not found" in data["error"]


def test_generate_404_activity_not_found(client, setup_course_structure):
    """Test that generate with bad activity_id returns 404."""
    course_id = setup_course_structure["course_id"]

    resp = client.post(f'/api/courses/{course_id}/activities/bad_activity_id/generate', json={})

    assert resp.status_code == 404
    data = resp.get_json()
    assert "Activity not found" in data["error"]


def test_generate_coach_content(client, setup_course_structure, mocker):
    """Test generating coach dialogue content."""
    course_id = setup_course_structure["course_id"]
    activity_id = setup_course_structure["activities"]["coach"]

    # Mock CoachGenerator
    mock_content = MagicMock()
    mock_content.model_dump.return_value = {
        "title": "Test Coach",
        "conversation_starters": [{"text": "Let's discuss..."}]
    }
    mock_content.model_dump_json.return_value = json.dumps(mock_content.model_dump.return_value)

    mock_metadata = {
        "word_count": 500,
        "estimated_duration_minutes": 10.0,
        "content_type": "coach"
    }

    mock_generator = mocker.patch("src.api.content.CoachGenerator")
    mock_generator.return_value.generate.return_value = (mock_content, mock_metadata)

    # Generate content
    resp = client.post(f'/api/courses/{course_id}/activities/{activity_id}/generate', json={
        "learning_objective": "Understand design patterns",
        "topic": "Singleton pattern"
    })

    assert resp.status_code == 200
    data = resp.get_json()
    assert "content" in data
    assert data["metadata"]["word_count"] == 500
    assert data["build_state"] == "generated"


def test_generate_practice_quiz_content(client, setup_course_structure, mocker):
    """Test generating practice quiz content with hints."""
    course_id = setup_course_structure["course_id"]
    activity_id = setup_course_structure["activities"]["practice_quiz"]

    # Mock PracticeQuizGenerator
    mock_content = MagicMock()
    mock_content.model_dump.return_value = {
        "title": "Test Practice Quiz",
        "questions": [{"question_text": "Q1", "options": [{"text": "A", "hint": "Think about..."}]}]
    }
    mock_content.model_dump_json.return_value = json.dumps(mock_content.model_dump.return_value)

    mock_metadata = {
        "word_count": 300,
        "estimated_duration_minutes": 10.0,
        "question_count": 5,
        "content_type": "practice_quiz"
    }

    mock_generator = mocker.patch("src.api.content.PracticeQuizGenerator")
    mock_generator.return_value.generate.return_value = (mock_content, mock_metadata)

    # Generate content
    resp = client.post(f'/api/courses/{course_id}/activities/{activity_id}/generate', json={
        "learning_objective": "Practice Python basics",
        "topic": "Variables and types",
        "num_questions": 5
    })

    assert resp.status_code == 200
    data = resp.get_json()
    assert "content" in data
    assert data["metadata"]["question_count"] == 5
    assert data["build_state"] == "generated"


def test_practice_quiz_dispatches_to_correct_generator(client, setup_course_structure, mocker):
    """Test that practice quiz (QUIZ + PRACTICE_QUIZ) dispatches to PracticeQuizGenerator not QuizGenerator."""
    course_id = setup_course_structure["course_id"]
    activity_id = setup_course_structure["activities"]["practice_quiz"]

    # Mock both generators
    mock_content = MagicMock()
    mock_content.model_dump.return_value = {"title": "Test"}
    mock_content.model_dump_json.return_value = json.dumps(mock_content.model_dump.return_value)
    mock_metadata = {"word_count": 100, "estimated_duration_minutes": 5.0}

    mock_practice_quiz = mocker.patch("src.api.content.PracticeQuizGenerator")
    mock_practice_quiz.return_value.generate.return_value = (mock_content, mock_metadata)

    mock_quiz = mocker.patch("src.api.content.QuizGenerator")

    # Generate content
    resp = client.post(f'/api/courses/{course_id}/activities/{activity_id}/generate', json={})

    assert resp.status_code == 200
    # Verify PracticeQuizGenerator was called
    mock_practice_quiz.assert_called_once()
    # Verify QuizGenerator was NOT called
    mock_quiz.assert_not_called()


def test_generate_lab_content(client, setup_course_structure, mocker):
    """Test generating lab content with setup instructions."""
    course_id = setup_course_structure["course_id"]
    activity_id = setup_course_structure["activities"]["lab"]

    # Mock LabGenerator
    mock_content = MagicMock()
    mock_content.model_dump.return_value = {
        "title": "Test Lab",
        "setup_steps": [{"instruction": "Install Docker", "expected_result": "docker --version works"}]
    }
    mock_content.model_dump_json.return_value = json.dumps(mock_content.model_dump.return_value)

    mock_metadata = {
        "word_count": 700,
        "estimated_duration_minutes": 60.0,
        "content_type": "lab"
    }

    mock_generator = mocker.patch("src.api.content.LabGenerator")
    mock_generator.return_value.generate.return_value = (mock_content, mock_metadata)

    # Generate content
    resp = client.post(f'/api/courses/{course_id}/activities/{activity_id}/generate', json={
        "learning_objective": "Set up development environment",
        "topic": "Docker basics"
    })

    assert resp.status_code == 200
    data = resp.get_json()
    assert "content" in data
    assert data["metadata"]["word_count"] == 700
    assert data["build_state"] == "generated"


def test_generate_discussion_content(client, setup_course_structure, mocker):
    """Test generating discussion content with facilitation."""
    course_id = setup_course_structure["course_id"]
    activity_id = setup_course_structure["activities"]["discussion"]

    # Mock DiscussionGenerator
    mock_content = MagicMock()
    mock_content.model_dump.return_value = {
        "title": "Test Discussion",
        "prompt": "Discuss the tradeoffs...",
        "facilitation_questions": ["What do you think about..."]
    }
    mock_content.model_dump_json.return_value = json.dumps(mock_content.model_dump.return_value)

    mock_metadata = {
        "word_count": 400,
        "estimated_duration_minutes": 15.0,
        "content_type": "discussion"
    }

    mock_generator = mocker.patch("src.api.content.DiscussionGenerator")
    mock_generator.return_value.generate.return_value = (mock_content, mock_metadata)

    # Generate content
    resp = client.post(f'/api/courses/{course_id}/activities/{activity_id}/generate', json={
        "learning_objective": "Evaluate design choices",
        "topic": "Microservices vs monoliths"
    })

    assert resp.status_code == 200
    data = resp.get_json()
    assert "content" in data
    assert data["metadata"]["word_count"] == 400
    assert data["build_state"] == "generated"


def test_generate_assignment_content(client, setup_course_structure, mocker):
    """Test generating assignment content with checklists."""
    course_id = setup_course_structure["course_id"]
    activity_id = setup_course_structure["activities"]["assignment"]

    # Mock AssignmentGenerator
    mock_content = MagicMock()
    mock_content.model_dump.return_value = {
        "title": "Test Assignment",
        "deliverables": [{"description": "Submit code", "points": 10, "checklist": []}]
    }
    mock_content.model_dump_json.return_value = json.dumps(mock_content.model_dump.return_value)

    mock_metadata = {
        "word_count": 800,
        "estimated_duration_minutes": 120.0,
        "num_deliverables": 3,
        "content_type": "assignment"
    }

    mock_generator = mocker.patch("src.api.content.AssignmentGenerator")
    mock_generator.return_value.generate.return_value = (mock_content, mock_metadata)

    # Generate content
    resp = client.post(f'/api/courses/{course_id}/activities/{activity_id}/generate', json={
        "learning_objective": "Build a web application",
        "topic": "Full-stack development"
    })

    assert resp.status_code == 200
    data = resp.get_json()
    assert "content" in data
    assert data["metadata"]["num_deliverables"] == 3
    assert data["build_state"] == "generated"


def test_generate_project_content(client, setup_course_structure, mocker):
    """Test generating project milestone content."""
    course_id = setup_course_structure["course_id"]
    activity_id = setup_course_structure["activities"]["project"]

    # Mock ProjectMilestoneGenerator
    mock_content = MagicMock()
    mock_content.model_dump.return_value = {
        "title": "Test Project Milestone",
        "milestone_type": "A1",
        "deliverables": [{"description": "Submit proposal", "milestone": "A1"}]
    }
    mock_content.model_dump_json.return_value = json.dumps(mock_content.model_dump.return_value)

    mock_metadata = {
        "word_count": 900,
        "estimated_duration_minutes": 180.0,
        "milestone_type": "A1",
        "content_type": "project"
    }

    mock_generator = mocker.patch("src.api.content.ProjectMilestoneGenerator")
    mock_generator.return_value.generate.return_value = (mock_content, mock_metadata)

    # Generate content
    resp = client.post(f'/api/courses/{course_id}/activities/{activity_id}/generate', json={
        "learning_objective": "Complete project proposal",
        "topic": "Capstone project",
        "milestone_type": "A1"
    })

    assert resp.status_code == 200
    data = resp.get_json()
    assert "content" in data
    assert data["metadata"]["milestone_type"] == "A1"
    assert data["build_state"] == "generated"
