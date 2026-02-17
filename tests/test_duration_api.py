"""Tests for course duration API endpoints."""

import pytest
import json
from src.core.models import Course, Module, Lesson, Activity, ContentType, ActivityType, DURATION_PRESETS


class TestDurationPresetsEndpoint:
    """Tests for /api/duration/presets endpoint."""

    def test_get_presets(self, client):
        """Test getting duration presets."""
        response = client.get("/api/duration/presets")
        assert response.status_code == 200

        data = response.get_json()
        assert "presets" in data
        assert len(data["presets"]) == len(DURATION_PRESETS)
        assert data["min_minutes"] == 30
        assert data["max_minutes"] == 180

    def test_presets_have_required_fields(self, client):
        """Test that each preset has required fields."""
        response = client.get("/api/duration/presets")
        data = response.get_json()

        for preset in data["presets"]:
            assert "id" in preset
            assert "minutes" in preset
            assert "label" in preset
            assert "description" in preset

    def test_presets_match_constants(self, client):
        """Test that API presets match model constants."""
        response = client.get("/api/duration/presets")
        data = response.get_json()

        preset_ids = {p["id"] for p in data["presets"]}
        expected_ids = set(DURATION_PRESETS.keys())
        assert preset_ids == expected_ids


class TestCourseDurationEndpoint:
    """Tests for /api/courses/<id>/duration endpoints."""

    def _create_course_with_activities(self, c, target_minutes=90):
        """Helper to create a course with activities via API."""
        # Create course
        response = c.post(
            "/api/courses",
            data=json.dumps({
                "title": "Duration Test Course",
                "target_duration_minutes": target_minutes
            }),
            content_type="application/json"
        )
        assert response.status_code == 201
        course_id = response.get_json()["id"]

        # Create module
        response = c.post(
            f"/api/courses/{course_id}/modules",
            data=json.dumps({"title": "Module 1", "order": 1}),
            content_type="application/json"
        )
        module_id = response.get_json()["id"]

        # Create lesson
        response = c.post(
            f"/api/courses/{course_id}/modules/{module_id}/lessons",
            data=json.dumps({
                "title": "Lesson 1"
            }),
            content_type="application/json"
        )
        lesson_id = response.get_json()["id"]

        # Create activities totaling 75 minutes
        for i, (title, ct, at, duration) in enumerate([
            ("Video 1", "video", "video_lecture", 15),
            ("Reading 1", "reading", "reading_material", 20),
            ("HOL 1", "hol", "hands_on_lab", 40),
        ]):
            c.post(
                f"/api/courses/{course_id}/lessons/{lesson_id}/activities",
                data=json.dumps({
                    "title": title,
                    "content_type": ct,
                    "activity_type": at,
                    "estimated_duration_minutes": duration,
                    "order": i + 1
                }),
                content_type="application/json"
            )

        return course_id

    def test_get_course_duration(self, authenticated_client):
        """Test getting course duration."""
        course_id = self._create_course_with_activities(authenticated_client, target_minutes=90)

        response = authenticated_client.get(f"/api/courses/{course_id}/duration")
        assert response.status_code == 200

        data = response.get_json()
        assert data["target_duration_minutes"] == 90
        assert "comparison" in data

    def test_duration_comparison_fields(self, authenticated_client):
        """Test that duration comparison has all fields."""
        course_id = self._create_course_with_activities(authenticated_client)

        response = authenticated_client.get(f"/api/courses/{course_id}/duration")
        data = response.get_json()

        comparison = data["comparison"]
        assert "target_minutes" in comparison
        assert "actual_minutes" in comparison
        assert "deviation_minutes" in comparison
        assert "deviation_percent" in comparison
        assert "status" in comparison
        assert "status_label" in comparison

    def test_duration_comparison_calculates_correctly(self, authenticated_client):
        """Test that duration comparison math is correct."""
        course_id = self._create_course_with_activities(authenticated_client, target_minutes=90)

        response = authenticated_client.get(f"/api/courses/{course_id}/duration")
        data = response.get_json()

        comparison = data["comparison"]
        # Course has 75 min actual (15+20+40), 90 min target
        assert comparison["target_minutes"] == 90
        assert comparison["actual_minutes"] == 75.0
        assert comparison["deviation_minutes"] == -15.0

    def test_set_duration_with_minutes(self, authenticated_client):
        """Test setting duration with direct minutes."""
        course_id = self._create_course_with_activities(authenticated_client)

        response = authenticated_client.put(
            f"/api/courses/{course_id}/duration",
            data=json.dumps({"target_duration_minutes": 120}),
            content_type="application/json"
        )
        assert response.status_code == 200

        data = response.get_json()
        assert data["target_duration_minutes"] == 120

    def test_set_duration_with_preset(self, authenticated_client):
        """Test setting duration with preset ID."""
        course_id = self._create_course_with_activities(authenticated_client)

        response = authenticated_client.put(
            f"/api/courses/{course_id}/duration",
            data=json.dumps({"preset_id": "comprehensive"}),
            content_type="application/json"
        )
        assert response.status_code == 200

        data = response.get_json()
        assert data["target_duration_minutes"] == 180
        assert data["preset_id"] == "comprehensive"

    def test_set_duration_invalid_preset(self, authenticated_client):
        """Test setting duration with invalid preset."""
        course_id = self._create_course_with_activities(authenticated_client)

        response = authenticated_client.put(
            f"/api/courses/{course_id}/duration",
            data=json.dumps({"preset_id": "nonexistent"}),
            content_type="application/json"
        )
        assert response.status_code == 400

    def test_set_duration_out_of_range(self, authenticated_client):
        """Test setting duration outside valid range."""
        course_id = self._create_course_with_activities(authenticated_client)

        # Too low
        response = authenticated_client.put(
            f"/api/courses/{course_id}/duration",
            data=json.dumps({"target_duration_minutes": 20}),
            content_type="application/json"
        )
        assert response.status_code == 400

        # Too high
        response = authenticated_client.put(
            f"/api/courses/{course_id}/duration",
            data=json.dumps({"target_duration_minutes": 200}),
            content_type="application/json"
        )
        assert response.status_code == 400

    def test_get_duration_comparison_detail(self, authenticated_client):
        """Test detailed duration comparison endpoint."""
        course_id = self._create_course_with_activities(authenticated_client)

        response = authenticated_client.get(f"/api/courses/{course_id}/duration/comparison")
        assert response.status_code == 200

        data = response.get_json()
        assert "module_breakdown" in data
        assert len(data["module_breakdown"]) == 1

        module = data["module_breakdown"][0]
        assert module["title"] == "Module 1"
        assert "duration_minutes" in module
        assert "lessons" in module


class TestDurationStatus:
    """Tests for duration status calculations."""

    def _create_course_with_duration(self, c, target_minutes, actual_minutes):
        """Create a course with specific target and actual duration."""
        # Create course
        response = c.post(
            "/api/courses",
            data=json.dumps({
                "title": "Status Test Course",
                "target_duration_minutes": target_minutes
            }),
            content_type="application/json"
        )
        course_id = response.get_json()["id"]

        # Create module
        response = c.post(
            f"/api/courses/{course_id}/modules",
            data=json.dumps({"title": "Module 1", "order": 1}),
            content_type="application/json"
        )
        module_id = response.get_json()["id"]

        # Create lesson
        response = c.post(
            f"/api/courses/{course_id}/modules/{module_id}/lessons",
            data=json.dumps({
                "title": "Lesson 1"
            }),
            content_type="application/json"
        )
        lesson_id = response.get_json()["id"]

        # Create one activity with the full actual duration
        c.post(
            f"/api/courses/{course_id}/lessons/{lesson_id}/activities",
            data=json.dumps({
                "title": "Activity",
                "content_type": "video",
                "activity_type": "video_lecture",
                "estimated_duration_minutes": actual_minutes,
                "order": 1
            }),
            content_type="application/json"
        )

        return course_id

    def test_on_target_status(self, authenticated_client):
        """Test status when within 10% of target."""
        course_id = self._create_course_with_duration(authenticated_client, 100, 95)

        response = authenticated_client.get(f"/api/courses/{course_id}/duration")
        data = response.get_json()
        assert data["comparison"]["status"] == "on_target"

    def test_acceptable_status(self, authenticated_client):
        """Test status when 10-20% deviation."""
        course_id = self._create_course_with_duration(authenticated_client, 100, 85)

        response = authenticated_client.get(f"/api/courses/{course_id}/duration")
        data = response.get_json()
        assert data["comparison"]["status"] == "acceptable"

    def test_needs_adjustment_status(self, authenticated_client):
        """Test status when >20% deviation."""
        course_id = self._create_course_with_duration(authenticated_client, 100, 70)

        response = authenticated_client.get(f"/api/courses/{course_id}/duration")
        data = response.get_json()
        assert data["comparison"]["status"] == "needs_adjustment"
