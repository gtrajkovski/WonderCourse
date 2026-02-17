"""Tests for cognitive taxonomy API endpoints."""

import pytest
import json


class TestListTaxonomies:
    """Tests for GET /api/taxonomies endpoint."""

    def test_list_returns_system_presets(self, authenticated_client):
        """Test that system presets are returned."""
        response = authenticated_client.get("/api/taxonomies")
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) >= 5  # 5 system presets

        # Check all 5 presets are present
        ids = {t["id"] for t in data}
        assert "tax_blooms" in ids
        assert "tax_solo" in ids
        assert "tax_webb" in ids
        assert "tax_marzano" in ids
        assert "tax_finks" in ids

    def test_system_presets_first(self, authenticated_client):
        """Test that system presets appear before custom taxonomies."""
        response = authenticated_client.get("/api/taxonomies")
        data = response.get_json()

        # All system presets should come first
        system_count = sum(1 for t in data if t["is_system_preset"])
        for i, taxonomy in enumerate(data):
            if i < system_count:
                assert taxonomy["is_system_preset"]
            else:
                assert not taxonomy["is_system_preset"]


class TestGetTaxonomy:
    """Tests for GET /api/taxonomies/<id> endpoint."""

    def test_get_blooms(self, authenticated_client):
        """Test getting Bloom's taxonomy."""
        response = authenticated_client.get("/api/taxonomies/tax_blooms")
        assert response.status_code == 200

        data = response.get_json()
        assert data["id"] == "tax_blooms"
        assert data["name"] == "Bloom's Revised Taxonomy"
        assert data["taxonomy_type"] == "linear"
        assert data["is_system_preset"]
        assert len(data["levels"]) == 6

    def test_get_finks_categorical(self, authenticated_client):
        """Test that Fink's taxonomy is categorical."""
        response = authenticated_client.get("/api/taxonomies/tax_finks")
        assert response.status_code == 200

        data = response.get_json()
        assert data["taxonomy_type"] == "categorical"
        assert not data["require_progression"]

    def test_get_nonexistent(self, authenticated_client):
        """Test getting non-existent taxonomy returns 404."""
        response = authenticated_client.get("/api/taxonomies/tax_invalid")
        assert response.status_code == 404

    def test_taxonomy_has_required_fields(self, authenticated_client):
        """Test that taxonomy has all required fields."""
        response = authenticated_client.get("/api/taxonomies/tax_blooms")
        data = response.get_json()

        assert "id" in data
        assert "name" in data
        assert "description" in data
        assert "taxonomy_type" in data
        assert "is_system_preset" in data
        assert "levels" in data
        assert "activity_mappings" in data
        assert "require_progression" in data
        assert "higher_order_threshold" in data

    def test_levels_have_required_fields(self, authenticated_client):
        """Test that each level has required fields."""
        response = authenticated_client.get("/api/taxonomies/tax_blooms")
        data = response.get_json()

        for level in data["levels"]:
            assert "id" in level
            assert "name" in level
            assert "value" in level
            assert "description" in level
            assert "order" in level
            assert "example_verbs" in level
            assert "color" in level


class TestGetDefaultTaxonomy:
    """Tests for GET /api/taxonomies/default endpoint."""

    def test_default_is_blooms(self, authenticated_client):
        """Test that default taxonomy is Bloom's."""
        response = authenticated_client.get("/api/taxonomies/default")
        assert response.status_code == 200

        data = response.get_json()
        assert data["id"] == "tax_blooms"
        assert data["name"] == "Bloom's Revised Taxonomy"


class TestCreateTaxonomy:
    """Tests for POST /api/taxonomies endpoint."""

    def test_create_custom_taxonomy(self, authenticated_client):
        """Test creating a custom taxonomy."""
        response = authenticated_client.post(
            "/api/taxonomies",
            data=json.dumps({
                "name": "My Custom Taxonomy",
                "description": "A test taxonomy",
                "taxonomy_type": "linear",
                "levels": [
                    {"name": "Basic", "value": "basic", "description": "Basic level", "order": 1},
                    {"name": "Intermediate", "value": "intermediate", "description": "Intermediate level", "order": 2},
                    {"name": "Advanced", "value": "advanced", "description": "Advanced level", "order": 3}
                ]
            }),
            content_type="application/json"
        )
        assert response.status_code == 201

        data = response.get_json()
        assert data["name"] == "My Custom Taxonomy"
        assert len(data["levels"]) == 3
        assert not data["is_system_preset"]

    def test_create_requires_name(self, authenticated_client):
        """Test that name is required."""
        response = authenticated_client.post(
            "/api/taxonomies",
            data=json.dumps({
                "levels": [{"name": "L1", "value": "l1"}]
            }),
            content_type="application/json"
        )
        assert response.status_code == 400

    def test_create_requires_levels(self, authenticated_client):
        """Test that levels are required."""
        response = authenticated_client.post(
            "/api/taxonomies",
            data=json.dumps({
                "name": "Empty Taxonomy"
            }),
            content_type="application/json"
        )
        assert response.status_code == 400


class TestUpdateTaxonomy:
    """Tests for PUT /api/taxonomies/<id> endpoint."""

    def test_update_custom_taxonomy(self, authenticated_client):
        """Test updating a custom taxonomy."""
        # First create a taxonomy
        create_response = authenticated_client.post(
            "/api/taxonomies",
            data=json.dumps({
                "name": "Original Name",
                "levels": [{"name": "L1", "value": "l1", "order": 1}]
            }),
            content_type="application/json"
        )
        taxonomy_id = create_response.get_json()["id"]

        # Update it
        response = authenticated_client.put(
            f"/api/taxonomies/{taxonomy_id}",
            data=json.dumps({"name": "Updated Name"}),
            content_type="application/json"
        )
        assert response.status_code == 200

        data = response.get_json()
        assert data["name"] == "Updated Name"

    def test_cannot_modify_system_preset(self, authenticated_client):
        """Test that system presets cannot be modified."""
        response = authenticated_client.put(
            "/api/taxonomies/tax_blooms",
            data=json.dumps({"name": "Hacked Bloom's"}),
            content_type="application/json"
        )
        assert response.status_code == 403


class TestDeleteTaxonomy:
    """Tests for DELETE /api/taxonomies/<id> endpoint."""

    def test_delete_custom_taxonomy(self, authenticated_client):
        """Test deleting a custom taxonomy."""
        # First create a taxonomy
        create_response = authenticated_client.post(
            "/api/taxonomies",
            data=json.dumps({
                "name": "To Delete",
                "levels": [{"name": "L1", "value": "l1", "order": 1}]
            }),
            content_type="application/json"
        )
        taxonomy_id = create_response.get_json()["id"]

        # Delete it
        response = authenticated_client.delete(f"/api/taxonomies/{taxonomy_id}")
        assert response.status_code == 200

        # Verify it's gone
        get_response = authenticated_client.get(f"/api/taxonomies/{taxonomy_id}")
        assert get_response.status_code == 404

    def test_cannot_delete_system_preset(self, authenticated_client):
        """Test that system presets cannot be deleted."""
        response = authenticated_client.delete("/api/taxonomies/tax_blooms")
        assert response.status_code == 403


class TestDuplicateTaxonomy:
    """Tests for POST /api/taxonomies/<id>/duplicate endpoint."""

    def test_duplicate_blooms(self, authenticated_client):
        """Test duplicating Bloom's taxonomy."""
        response = authenticated_client.post(
            "/api/taxonomies/tax_blooms/duplicate",
            data=json.dumps({"name": "My Bloom's Copy"}),
            content_type="application/json"
        )
        assert response.status_code == 201

        data = response.get_json()
        assert data["name"] == "My Bloom's Copy"
        assert data["id"] != "tax_blooms"
        assert not data["is_system_preset"]
        assert len(data["levels"]) == 6

    def test_duplicate_requires_name(self, authenticated_client):
        """Test that name is required for duplication."""
        response = authenticated_client.post(
            "/api/taxonomies/tax_blooms/duplicate",
            data=json.dumps({}),
            content_type="application/json"
        )
        assert response.status_code == 400


class TestPromptContext:
    """Tests for GET /api/taxonomies/<id>/prompt-context endpoint."""

    def test_get_prompt_context(self, authenticated_client):
        """Test getting AI prompt context."""
        response = authenticated_client.get("/api/taxonomies/tax_blooms/prompt-context")
        assert response.status_code == 200

        data = response.get_json()
        assert "prompt_context" in data
        assert "Bloom's Revised Taxonomy" in data["prompt_context"]
        assert "Remember" in data["prompt_context"]
        assert "Create" in data["prompt_context"]


class TestTaxonomyTypes:
    """Tests for GET /api/taxonomies/types endpoint."""

    def test_get_types(self, authenticated_client):
        """Test getting available taxonomy types."""
        response = authenticated_client.get("/api/taxonomies/types")
        assert response.status_code == 200

        data = response.get_json()
        assert "types" in data
        assert len(data["types"]) == 2

        values = {t["value"] for t in data["types"]}
        assert "linear" in values
        assert "categorical" in values


class TestCourseTaxonomy:
    """Tests for course taxonomy assignment."""

    def _create_course(self, client):
        """Helper to create a course."""
        response = client.post(
            "/api/courses",
            data=json.dumps({
                "title": "Test Course",
                "target_duration_minutes": 60
            }),
            content_type="application/json"
        )
        return response.get_json()["id"]

    def test_get_course_taxonomy_default(self, authenticated_client):
        """Test getting course taxonomy when none assigned."""
        course_id = self._create_course(authenticated_client)

        response = authenticated_client.get(f"/api/courses/{course_id}/taxonomy")
        assert response.status_code == 200

        data = response.get_json()
        assert data["is_default"]
        assert data["taxonomy"]["id"] == "tax_blooms"

    def test_set_course_taxonomy(self, authenticated_client):
        """Test setting course taxonomy."""
        course_id = self._create_course(authenticated_client)

        response = authenticated_client.put(
            f"/api/courses/{course_id}/taxonomy",
            data=json.dumps({"taxonomy_id": "tax_webb"}),
            content_type="application/json"
        )
        assert response.status_code == 200

        data = response.get_json()
        assert data["taxonomy_id"] == "tax_webb"
        assert data["taxonomy"]["name"] == "Webb's Depth of Knowledge"
        assert not data["is_default"]

    def test_set_course_taxonomy_to_null(self, authenticated_client):
        """Test resetting course taxonomy to default."""
        course_id = self._create_course(authenticated_client)

        # First set to Webb's
        authenticated_client.put(
            f"/api/courses/{course_id}/taxonomy",
            data=json.dumps({"taxonomy_id": "tax_webb"}),
            content_type="application/json"
        )

        # Then reset to default
        response = authenticated_client.put(
            f"/api/courses/{course_id}/taxonomy",
            data=json.dumps({"taxonomy_id": None}),
            content_type="application/json"
        )
        assert response.status_code == 200

        data = response.get_json()
        assert data["taxonomy_id"] is None
        assert data["is_default"]

    def test_set_course_taxonomy_invalid(self, authenticated_client):
        """Test setting invalid taxonomy returns 404."""
        course_id = self._create_course(authenticated_client)

        response = authenticated_client.put(
            f"/api/courses/{course_id}/taxonomy",
            data=json.dumps({"taxonomy_id": "tax_nonexistent"}),
            content_type="application/json"
        )
        assert response.status_code == 404
