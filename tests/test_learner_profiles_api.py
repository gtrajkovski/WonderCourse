"""Tests for learner profiles API endpoints."""

import pytest
import json
from pathlib import Path


@pytest.fixture
def created_course(authenticated_client):
    """Create a course via API for testing."""
    response = authenticated_client.post(
        "/api/courses",
        data=json.dumps({
            "title": "Test Course",
            "description": "A test course",
            "audience_level": "beginner",
            "target_duration_minutes": 120,
            "modality": "online"
        }),
        content_type="application/json",
    )
    return response.get_json()


class TestListLearnerProfiles:
    """Tests for GET /api/learner-profiles endpoint."""

    def test_list_profiles_returns_defaults(self, authenticated_client):
        """Test that default profiles are created and returned."""
        response = authenticated_client.get("/api/learner-profiles")
        assert response.status_code == 200

        profiles = response.get_json()
        assert isinstance(profiles, list)
        assert len(profiles) >= 4  # Default profiles

        # Check default profile IDs exist
        profile_ids = [p["id"] for p in profiles]
        assert "lp_beginner_professional" in profile_ids
        assert "lp_intermediate_developer" in profile_ids
        assert "lp_career_changer" in profile_ids
        assert "lp_esl_learner" in profile_ids

    def test_list_profiles_sorted_by_name(self, authenticated_client):
        """Test profiles are sorted alphabetically by name."""
        response = authenticated_client.get("/api/learner-profiles")
        assert response.status_code == 200

        profiles = response.get_json()
        names = [p["name"] for p in profiles]
        assert names == sorted(names)


class TestGetLearnerProfile:
    """Tests for GET /api/learner-profiles/<id> endpoint."""

    def test_get_existing_profile(self, authenticated_client):
        """Test getting an existing profile."""
        response = authenticated_client.get(
            "/api/learner-profiles/lp_beginner_professional"
        )
        assert response.status_code == 200

        profile = response.get_json()
        assert profile["id"] == "lp_beginner_professional"
        assert profile["name"] == "Beginner Professional"
        assert profile["technical_level"] == "basic"

    def test_get_nonexistent_profile(self, authenticated_client):
        """Test getting a nonexistent profile returns 404."""
        response = authenticated_client.get("/api/learner-profiles/nonexistent")
        assert response.status_code == 404


class TestCreateLearnerProfile:
    """Tests for POST /api/learner-profiles endpoint."""

    def test_create_basic_profile(self, authenticated_client):
        """Test creating a basic learner profile."""
        profile_data = {
            "name": "Test Profile",
            "description": "A test learner profile",
            "technical_level": "intermediate",
        }

        response = authenticated_client.post(
            "/api/learner-profiles",
            data=json.dumps(profile_data),
            content_type="application/json",
        )
        assert response.status_code == 201

        profile = response.get_json()
        assert profile["name"] == "Test Profile"
        assert profile["description"] == "A test learner profile"
        assert profile["technical_level"] == "intermediate"
        assert "id" in profile

    def test_create_full_profile(self, authenticated_client):
        """Test creating a profile with all fields."""
        profile_data = {
            "name": "Full Profile",
            "description": "Complete profile",
            "technical_level": "advanced",
            "language_proficiency": "native",
            "learning_preference": "visual",
            "learning_context": "upskilling",
            "prior_knowledge": ["Python", "JavaScript"],
            "learning_goals": ["Master ML", "Build portfolio"],
            "attention_span_minutes": 25,
            "prefers_examples": True,
            "prefers_analogies": False,
            "available_hours_per_week": 15,
        }

        response = authenticated_client.post(
            "/api/learner-profiles",
            data=json.dumps(profile_data),
            content_type="application/json",
        )
        assert response.status_code == 201

        profile = response.get_json()
        assert profile["name"] == "Full Profile"
        assert profile["technical_level"] == "advanced"
        assert profile["language_proficiency"] == "native"
        assert profile["learning_preference"] == "visual"
        assert profile["prior_knowledge"] == ["Python", "JavaScript"]
        assert profile["attention_span_minutes"] == 25

    def test_create_profile_missing_name(self, authenticated_client):
        """Test creating profile without name returns 400."""
        response = authenticated_client.post(
            "/api/learner-profiles",
            data=json.dumps({"description": "No name"}),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_create_profile_empty_body(self, authenticated_client):
        """Test creating profile with no JSON returns 400."""
        response = authenticated_client.post(
            "/api/learner-profiles",
            data="",
            content_type="application/json",
        )
        assert response.status_code == 400


class TestUpdateLearnerProfile:
    """Tests for PUT /api/learner-profiles/<id> endpoint."""

    def test_update_profile(self, authenticated_client):
        """Test updating a profile."""
        # First create a profile
        create_response = authenticated_client.post(
            "/api/learner-profiles",
            data=json.dumps({"name": "Update Test"}),
            content_type="application/json",
        )
        profile_id = create_response.get_json()["id"]

        # Update it
        response = authenticated_client.put(
            f"/api/learner-profiles/{profile_id}",
            data=json.dumps({
                "description": "Updated description",
                "technical_level": "expert",
            }),
            content_type="application/json",
        )
        assert response.status_code == 200

        profile = response.get_json()
        assert profile["description"] == "Updated description"
        assert profile["technical_level"] == "expert"
        assert profile["name"] == "Update Test"  # Unchanged

    def test_update_preserves_id(self, authenticated_client):
        """Test that updating cannot change the profile ID."""
        # Create a profile
        create_response = authenticated_client.post(
            "/api/learner-profiles",
            data=json.dumps({"name": "ID Test"}),
            content_type="application/json",
        )
        profile_id = create_response.get_json()["id"]

        # Try to change the ID
        response = authenticated_client.put(
            f"/api/learner-profiles/{profile_id}",
            data=json.dumps({"id": "new_id"}),
            content_type="application/json",
        )
        assert response.status_code == 200

        profile = response.get_json()
        assert profile["id"] == profile_id  # ID unchanged

    def test_update_nonexistent_profile(self, authenticated_client):
        """Test updating nonexistent profile returns 404."""
        response = authenticated_client.put(
            "/api/learner-profiles/nonexistent",
            data=json.dumps({"name": "Test"}),
            content_type="application/json",
        )
        assert response.status_code == 404


class TestDeleteLearnerProfile:
    """Tests for DELETE /api/learner-profiles/<id> endpoint."""

    def test_delete_profile(self, authenticated_client):
        """Test deleting a profile."""
        # Create a profile
        create_response = authenticated_client.post(
            "/api/learner-profiles",
            data=json.dumps({"name": "Delete Test"}),
            content_type="application/json",
        )
        profile_id = create_response.get_json()["id"]

        # Delete it
        response = authenticated_client.delete(
            f"/api/learner-profiles/{profile_id}"
        )
        assert response.status_code == 200

        # Verify it's gone
        get_response = authenticated_client.get(
            f"/api/learner-profiles/{profile_id}"
        )
        assert get_response.status_code == 404

    def test_delete_nonexistent_profile(self, authenticated_client):
        """Test deleting nonexistent profile returns 404."""
        response = authenticated_client.delete(
            "/api/learner-profiles/nonexistent"
        )
        assert response.status_code == 404


class TestPromptContext:
    """Tests for GET /api/learner-profiles/<id>/prompt-context endpoint."""

    def test_get_prompt_context(self, authenticated_client):
        """Test getting prompt context for a profile."""
        response = authenticated_client.get(
            "/api/learner-profiles/lp_beginner_professional/prompt-context"
        )
        assert response.status_code == 200

        data = response.get_json()
        assert data["profile_id"] == "lp_beginner_professional"
        assert data["profile_name"] == "Beginner Professional"
        assert "prompt_context" in data
        assert isinstance(data["prompt_context"], str)
        assert len(data["prompt_context"]) > 0

    def test_prompt_context_contains_key_info(self, authenticated_client):
        """Test that prompt context includes relevant profile info."""
        # Create a profile with specific details
        profile_data = {
            "name": "Context Test Profile",
            "technical_level": "intermediate",
            "learning_preference": "hands_on",
            "prefers_examples": True,
        }

        create_response = authenticated_client.post(
            "/api/learner-profiles",
            data=json.dumps(profile_data),
            content_type="application/json",
        )
        profile_id = create_response.get_json()["id"]

        response = authenticated_client.get(
            f"/api/learner-profiles/{profile_id}/prompt-context"
        )
        assert response.status_code == 200

        context = response.get_json()["prompt_context"]
        # Should mention key characteristics
        assert "intermediate" in context.lower() or "technical" in context.lower()

    def test_prompt_context_nonexistent_profile(self, authenticated_client):
        """Test getting prompt context for nonexistent profile returns 404."""
        response = authenticated_client.get(
            "/api/learner-profiles/nonexistent/prompt-context"
        )
        assert response.status_code == 404


class TestEnumValues:
    """Tests for GET /api/learner-profiles/enum-values endpoint."""

    def test_get_enum_values(self, authenticated_client):
        """Test getting available enum values."""
        response = authenticated_client.get("/api/learner-profiles/enum-values")
        assert response.status_code == 200

        data = response.get_json()
        assert "technical_levels" in data
        assert "language_proficiencies" in data
        assert "learning_preferences" in data
        assert "learning_contexts" in data

        # Check specific values exist
        assert "basic" in data["technical_levels"]
        assert "intermediate" in data["technical_levels"]
        assert "advanced" in data["technical_levels"]
        assert "expert" in data["technical_levels"]

        assert "native" in data["language_proficiencies"]
        assert "hands_on" in data["learning_preferences"]
        assert "professional" in data["learning_contexts"]


class TestCourseProfileAssignment:
    """Tests for course learner profile assignment endpoints."""

    def test_get_course_profile_none(self, authenticated_client, created_course):
        """Test getting course profile when none is assigned."""
        response = authenticated_client.get(
            f"/api/courses/{created_course['id']}/learner-profile"
        )
        assert response.status_code == 200

        data = response.get_json()
        assert data["profile"] is None

    def test_set_course_profile(self, authenticated_client, created_course):
        """Test assigning a learner profile to a course."""
        response = authenticated_client.put(
            f"/api/courses/{created_course['id']}/learner-profile",
            data=json.dumps({"profile_id": "lp_beginner_professional"}),
            content_type="application/json",
        )
        assert response.status_code == 200

        data = response.get_json()
        assert data["profile_id"] == "lp_beginner_professional"

    def test_get_course_profile_after_set(self, authenticated_client, created_course):
        """Test getting course profile after assignment."""
        # Set the profile
        authenticated_client.put(
            f"/api/courses/{created_course['id']}/learner-profile",
            data=json.dumps({"profile_id": "lp_intermediate_developer"}),
            content_type="application/json",
        )

        # Get it back
        response = authenticated_client.get(
            f"/api/courses/{created_course['id']}/learner-profile"
        )
        assert response.status_code == 200

        data = response.get_json()
        assert data["profile"]["id"] == "lp_intermediate_developer"

    def test_unset_course_profile(self, authenticated_client, created_course):
        """Test unsetting a course's learner profile."""
        # Set a profile first
        authenticated_client.put(
            f"/api/courses/{created_course['id']}/learner-profile",
            data=json.dumps({"profile_id": "lp_beginner_professional"}),
            content_type="application/json",
        )

        # Unset it
        response = authenticated_client.put(
            f"/api/courses/{created_course['id']}/learner-profile",
            data=json.dumps({"profile_id": None}),
            content_type="application/json",
        )
        assert response.status_code == 200

        # Verify it's unset
        get_response = authenticated_client.get(
            f"/api/courses/{created_course['id']}/learner-profile"
        )
        assert get_response.get_json()["profile"] is None

    def test_set_nonexistent_profile(self, authenticated_client, created_course):
        """Test assigning nonexistent profile returns 404."""
        response = authenticated_client.put(
            f"/api/courses/{created_course['id']}/learner-profile",
            data=json.dumps({"profile_id": "nonexistent"}),
            content_type="application/json",
        )
        assert response.status_code == 404

    def test_set_profile_missing_field(self, authenticated_client, created_course):
        """Test assigning profile without profile_id returns 400."""
        response = authenticated_client.put(
            f"/api/courses/{created_course['id']}/learner-profile",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_set_profile_nonexistent_course(self, authenticated_client):
        """Test assigning profile to nonexistent course returns 404."""
        response = authenticated_client.put(
            "/api/courses/nonexistent/learner-profile",
            data=json.dumps({"profile_id": "lp_beginner_professional"}),
            content_type="application/json",
        )
        assert response.status_code == 404
