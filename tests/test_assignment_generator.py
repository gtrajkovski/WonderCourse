"""Tests for AssignmentGenerator using TDD with mocked Anthropic API."""

import json
import pytest
from unittest.mock import Mock, MagicMock
from src.generators.assignment_generator import AssignmentGenerator
from src.generators.schemas.assignment import AssignmentSchema, AssignmentDeliverable, ChecklistItem


# Sample assignment data as dict
SAMPLE_ASSIGNMENT_DATA = {
    "title": "Database Design Project",
    "overview": "Design and implement a normalized relational database for a small business scenario. This assignment assesses your ability to apply database normalization principles and create a working schema.",
    "deliverables": [
        {
            "item": "Entity-Relationship Diagram (ERD) showing all entities, relationships, and cardinalities",
            "points": 30
        },
        {
            "item": "Normalized database schema (3NF) with CREATE TABLE statements",
            "points": 40
        },
        {
            "item": "Sample queries demonstrating CRUD operations",
            "points": 20
        },
        {
            "item": "Written justification of normalization decisions",
            "points": 10
        }
    ],
    "grading_criteria": [
        "ERD accurately represents business requirements with correct notation",
        "Schema achieves 3NF with no anomalies",
        "SQL statements are syntactically correct and follow best practices",
        "Justification demonstrates understanding of normalization principles"
    ],
    "submission_checklist": [
        {
            "item": "ERD exported as PDF or PNG image",
            "required": True
        },
        {
            "item": "SQL file contains all CREATE TABLE statements",
            "required": True
        },
        {
            "item": "SQL file contains at least 5 sample queries",
            "required": True
        },
        {
            "item": "Written justification is 300-500 words",
            "required": True
        },
        {
            "item": "All files are named according to convention (lastname_firstname_assignment)",
            "required": True
        },
        {
            "item": "Optional: Include sample data INSERT statements",
            "required": False
        }
    ],
    "total_points": 100,
    "estimated_hours": 5,
    "learning_objective": "Students will design normalized relational databases that eliminate data anomalies"
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
    """Test that generate() returns a valid AssignmentSchema instance."""
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_ASSIGNMENT_DATA)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    # Generate assignment
    generator = AssignmentGenerator()
    assignment, metadata = generator.generate(
        schema=AssignmentSchema,
        learning_objective="Design normalized relational databases",
        topic="Database Design",
        total_points=100,
        estimated_hours=5,
        difficulty="intermediate"
    )

    # Verify it's a valid AssignmentSchema
    assert isinstance(assignment, AssignmentSchema)
    assert assignment.title == "Database Design Project"
    assert len(assignment.deliverables) >= 1
    assert len(assignment.submission_checklist) >= 3


def test_deliverables_have_points(mocker):
    """Test that each deliverable has points >= 0."""
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_ASSIGNMENT_DATA)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    # Generate assignment
    generator = AssignmentGenerator()
    assignment, _ = generator.generate(
        schema=AssignmentSchema,
        learning_objective="Design normalized relational databases",
        topic="Database Design",
        total_points=100,
        estimated_hours=5
    )

    # Verify each deliverable has points >= 0
    for deliverable in assignment.deliverables:
        assert deliverable.points >= 0, f"Deliverable '{deliverable.item}' has negative points"


def test_checklist_has_required_field(mocker):
    """Test that each checklist item has required boolean."""
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_ASSIGNMENT_DATA)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    # Generate assignment
    generator = AssignmentGenerator()
    assignment, _ = generator.generate(
        schema=AssignmentSchema,
        learning_objective="Design normalized relational databases",
        topic="Database Design",
        total_points=100,
        estimated_hours=5
    )

    # Verify each checklist item has required field
    for checklist_item in assignment.submission_checklist:
        assert isinstance(checklist_item.required, bool), \
            f"Checklist item '{checklist_item.item}' required field is not boolean"


def test_system_prompt_mentions_grading():
    """Test that system prompt references grading criteria."""
    generator = AssignmentGenerator()
    prompt = generator.system_prompt

    # Verify grading-related terms are present
    assert "grading" in prompt.lower() or "criteria" in prompt.lower() or "rubric" in prompt.lower()


def test_build_user_prompt_includes_params():
    """Test that build_user_prompt includes learning_objective, total_points, estimated_hours."""
    generator = AssignmentGenerator()

    prompt = generator.build_user_prompt(
        learning_objective="Design normalized relational databases",
        topic="Database Design",
        total_points=100,
        estimated_hours=5,
        difficulty="intermediate"
    )

    # Verify key parameters are in prompt
    assert "Design normalized relational databases" in prompt or "normalized relational databases" in prompt.lower()
    assert "100" in prompt
    assert "5" in prompt or "five" in prompt.lower()


def test_extract_metadata_includes_total_points():
    """Test that extract_metadata includes total_points from schema."""
    generator = AssignmentGenerator()

    # Create a sample assignment
    assignment = AssignmentSchema(
        title="Test Assignment",
        overview="Test overview for assignment",
        deliverables=[
            AssignmentDeliverable(item="Deliverable 1", points=50),
            AssignmentDeliverable(item="Deliverable 2", points=50)
        ],
        grading_criteria=["Criterion 1", "Criterion 2", "Criterion 3"],
        submission_checklist=[
            ChecklistItem(item="Item 1", required=True),
            ChecklistItem(item="Item 2", required=True),
            ChecklistItem(item="Item 3", required=False)
        ],
        total_points=100,
        estimated_hours=5,
        learning_objective="Test objective"
    )

    metadata = generator.extract_metadata(assignment)

    # Verify metadata includes total_points
    assert metadata["total_points"] == 100
    assert metadata["estimated_duration_minutes"] == 300  # 5 hours * 60
    assert metadata["num_deliverables"] == 2
    assert metadata["content_type"] == "assignment"
    assert "word_count" in metadata
