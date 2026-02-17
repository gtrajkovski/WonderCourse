"""Tests for standards profile import/export endpoints."""

import pytest
import json


class TestStandardsExport:
    """Tests for /api/standards/<id>/export endpoint."""

    def test_export_system_preset(self, authenticated_client):
        """Test exporting a system preset."""
        response = authenticated_client.get("/api/standards/std_coursera/export")
        assert response.status_code == 200

        data = response.get_json()
        assert "_export_version" in data
        assert "_exported_at" in data
        assert data["is_system_preset"] is False  # Exported as custom
        assert "id" not in data  # ID removed for import

    def test_export_nonexistent_profile(self, authenticated_client):
        """Test exporting a nonexistent profile."""
        response = authenticated_client.get("/api/standards/nonexistent/export")
        assert response.status_code == 404


class TestStandardsImport:
    """Tests for /api/standards/import endpoint."""

    def test_import_basic_profile(self, authenticated_client):
        """Test importing a basic profile."""
        profile_data = {
            "name": "Imported Test Profile",
            "description": "Test description",
            "video_max_duration_min": 15
        }

        response = authenticated_client.post(
            "/api/standards/import",
            data=json.dumps({"profile": profile_data}),
            content_type="application/json"
        )
        assert response.status_code == 201

        data = response.get_json()
        assert data["name"] == "Imported Test Profile"
        assert data["is_system_preset"] is False
        assert "id" in data  # New ID assigned

    def test_import_with_name_override(self, authenticated_client):
        """Test importing with name override."""
        profile_data = {
            "name": "Original Name",
            "description": "Test"
        }

        response = authenticated_client.post(
            "/api/standards/import",
            data=json.dumps({
                "name": "Overridden Name",
                "profile": profile_data
            }),
            content_type="application/json"
        )
        assert response.status_code == 201

        data = response.get_json()
        assert data["name"] == "Overridden Name"

    def test_import_missing_name(self, authenticated_client):
        """Test importing profile without name."""
        response = authenticated_client.post(
            "/api/standards/import",
            data=json.dumps({"profile": {"description": "No name"}}),
            content_type="application/json"
        )
        assert response.status_code == 400

    def test_import_missing_profile(self, authenticated_client):
        """Test importing without profile data."""
        response = authenticated_client.post(
            "/api/standards/import",
            data=json.dumps({"name": "Test"}),
            content_type="application/json"
        )
        assert response.status_code == 400

    def test_import_strips_export_metadata(self, authenticated_client):
        """Test that export metadata is stripped on import."""
        profile_data = {
            "name": "Test Profile",
            "_export_version": "1.0",
            "_exported_at": "2024-01-01T00:00:00",
            "id": "old_id_should_be_removed"
        }

        response = authenticated_client.post(
            "/api/standards/import",
            data=json.dumps({"profile": profile_data}),
            content_type="application/json"
        )
        assert response.status_code == 201

        data = response.get_json()
        assert "_export_version" not in data
        assert "_exported_at" not in data
        assert data["id"] != "old_id_should_be_removed"


class TestRoundTrip:
    """Test export-then-import workflow."""

    def test_export_import_round_trip(self, authenticated_client):
        """Test that exported profile can be imported."""
        # Export a system preset
        export_response = authenticated_client.get("/api/standards/std_flexible/export")
        assert export_response.status_code == 200
        exported = export_response.get_json()

        # Import it with a new name
        import_response = authenticated_client.post(
            "/api/standards/import",
            data=json.dumps({
                "name": "My Copy of Flexible",
                "profile": exported
            }),
            content_type="application/json"
        )
        assert import_response.status_code == 201

        imported = import_response.get_json()
        assert imported["name"] == "My Copy of Flexible"
        assert imported["is_system_preset"] is False

        # Verify values match (check a few fields)
        assert imported["video_max_duration_min"] == exported.get("video_max_duration_min", 10)
