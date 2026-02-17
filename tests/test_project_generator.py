"""Tests for ProjectMilestoneGenerator using TDD with mocked Anthropic API."""

import json
import pytest
from unittest.mock import Mock, MagicMock
from src.generators.project_generator import ProjectMilestoneGenerator
from src.generators.schemas.project import ProjectMilestoneSchema, MilestoneDeliverable


# Sample project data as dict
SAMPLE_PROJECT_DATA = {
    "title": "A1: Project Proposal and Planning",
    "milestone_type": "A1",
    "overview": "Define project scope, objectives, and create initial planning documents.",
    "prerequisites": [
        "Completed course modules 1-3",
        "Basic understanding of project management principles"
    ],
    "deliverables": [
        {
            "name": "Project Proposal Document",
            "description": "A 2-3 page document outlining project goals, scope, and approach",
            "format": "PDF report"
        },
        {
            "name": "Project Timeline",
            "description": "Gantt chart or similar timeline showing key milestones and deadlines",
            "format": "PDF or Excel spreadsheet"
        },
        {
            "name": "Resource Requirements List",
            "description": "Itemized list of tools, technologies, and resources needed",
            "format": "Markdown or PDF document"
        }
    ],
    "grading_criteria": [
        "Clear and achievable project objectives",
        "Realistic timeline with appropriate milestones",
        "Comprehensive resource identification",
        "Professional document formatting and clarity"
    ],
    "estimated_hours": 10,
    "learning_objective": "Students will be able to plan and scope a technical project with clear deliverables."
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
    """Test that generate() returns a valid ProjectMilestoneSchema instance."""
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_PROJECT_DATA)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    # Generate milestone
    generator = ProjectMilestoneGenerator()
    milestone, metadata = generator.generate(
        schema=ProjectMilestoneSchema,
        learning_objective="Plan and scope a technical project",
        topic="Web Application Development",
        milestone_type="A1",
        estimated_hours=10,
        difficulty="intermediate"
    )

    # Verify it's a valid ProjectMilestoneSchema
    assert isinstance(milestone, ProjectMilestoneSchema)
    assert milestone.title == "A1: Project Proposal and Planning"
    assert milestone.milestone_type == "A1"
    assert len(milestone.deliverables) >= 2
    assert len(milestone.grading_criteria) >= 3


def test_milestone_type_is_valid(mocker):
    """Test that milestone_type is one of A1, A2, A3."""
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_PROJECT_DATA)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    # Generate milestone
    generator = ProjectMilestoneGenerator()
    milestone, _ = generator.generate(
        schema=ProjectMilestoneSchema,
        learning_objective="Plan and scope a technical project",
        topic="Web Application Development",
        milestone_type="A1"
    )

    # Verify milestone_type is valid
    assert milestone.milestone_type in ["A1", "A2", "A3"]


def test_deliverables_have_format(mocker):
    """Test that each deliverable has name, description, format fields."""
    mock_client = MagicMock()
    _mock_tool_response(mock_client, SAMPLE_PROJECT_DATA)
    mocker.patch('src.generators.base_generator.Anthropic', return_value=mock_client)

    # Generate milestone
    generator = ProjectMilestoneGenerator()
    milestone, _ = generator.generate(
        schema=ProjectMilestoneSchema,
        learning_objective="Plan and scope a technical project",
        topic="Web Application Development",
        milestone_type="A1"
    )

    # Verify each deliverable has required fields
    for deliverable in milestone.deliverables:
        assert isinstance(deliverable, MilestoneDeliverable)
        assert hasattr(deliverable, 'name')
        assert hasattr(deliverable, 'description')
        assert hasattr(deliverable, 'format')
        assert len(deliverable.name) > 0
        assert len(deliverable.description) > 0
        assert len(deliverable.format) > 0


def test_system_prompt_mentions_scaffolding():
    """Test that system prompt references progressive/scaffolded/A1/A2/A3."""
    generator = ProjectMilestoneGenerator()
    prompt = generator.system_prompt

    # Verify scaffolding concepts are present
    scaffolding_keywords = ["progressive", "scaffolded", "scaffold", "A1", "A2", "A3"]
    assert any(keyword.lower() in prompt.lower() for keyword in scaffolding_keywords)


def test_build_user_prompt_includes_milestone_type():
    """Test that build_user_prompt includes milestone_type parameter."""
    generator = ProjectMilestoneGenerator()

    prompt = generator.build_user_prompt(
        learning_objective="Plan and scope a technical project",
        topic="Web Application Development",
        milestone_type="A1",
        estimated_hours=10,
        difficulty="intermediate"
    )

    # Verify milestone_type is in prompt
    assert "A1" in prompt


def test_extract_metadata_includes_milestone_type():
    """Test that extract_metadata includes milestone_type field."""
    generator = ProjectMilestoneGenerator()

    # Create a sample milestone
    milestone = ProjectMilestoneSchema(
        title="A1: Project Proposal",
        milestone_type="A1",
        overview="Plan the project",
        prerequisites=["Module 1"],
        deliverables=[
            MilestoneDeliverable(
                name="Proposal",
                description="Project proposal document",
                format="PDF"
            ),
            MilestoneDeliverable(
                name="Timeline",
                description="Project timeline",
                format="Gantt chart"
            )
        ],
        grading_criteria=["Clear objectives", "Realistic timeline", "Complete planning"],
        estimated_hours=10,
        learning_objective="Plan a technical project"
    )

    metadata = generator.extract_metadata(milestone)

    # Verify metadata includes milestone_type
    assert "milestone_type" in metadata
    assert metadata["milestone_type"] == "A1"
    assert "num_deliverables" in metadata
    assert metadata["num_deliverables"] == 2
    assert metadata["content_type"] == "project"
