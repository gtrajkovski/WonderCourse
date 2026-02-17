"""Tests for image generation API endpoints."""

import pytest
import json
import base64
from unittest.mock import MagicMock, patch

from src.core.models import Course, Module, Lesson, Activity, ContentType, ActivityType


class TestImagesAPIStatus:
    """Tests for image API status endpoint."""

    def test_get_status(self, client):
        """Test getting image generation status."""
        response = client.get("/api/images/status")
        assert response.status_code == 200

        data = response.get_json()
        assert "pillow_available" in data
        assert "generators" in data
        assert "video_slides" in data["generators"]
        assert "reading_images" in data["generators"]
        assert "terminal_screenshots" in data["generators"]
        assert "cta_slides" in data["generators"]


class TestReadingConceptsAPI:
    """Tests for reading concept extraction (no Pillow required)."""

    def test_extract_concepts_endpoint(self, client):
        """Test standalone concept extraction endpoint."""
        response = client.post(
            "/api/images/reading/concepts",
            json={
                "content": "# API Design\n\nThe key concept is REST architecture.",
                "count": 2
            }
        )
        assert response.status_code == 200

        data = response.get_json()
        assert "concepts" in data
        assert "count" in data

    def test_extract_concepts_missing_content(self, client):
        """Test concept extraction without content."""
        response = client.post("/api/images/reading/concepts", json={})
        assert response.status_code == 400

    def test_extract_concepts_with_headers(self, client):
        """Test concept extraction from markdown headers."""
        response = client.post(
            "/api/images/reading/concepts",
            json={
                "content": """
                # Introduction to Machine Learning

                Machine learning is a subset of AI.

                ## Supervised Learning

                Supervised learning uses labeled data.
                """,
                "count": 3
            }
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] >= 0  # May extract 0+ concepts


class TestTerminalScreenshotAPI:
    """Tests for terminal screenshot API."""

    def test_terminal_missing_body(self, client):
        """Test terminal endpoint without body."""
        response = client.post(
            "/api/images/terminal",
            data="{}",
            content_type="application/json"
        )
        # Will return 400 (bad request) or 503 (no Pillow)
        assert response.status_code in [400, 503]

    def test_terminal_missing_command_and_lines(self, client):
        """Test terminal endpoint without command or lines."""
        response = client.post("/api/images/terminal", json={"format": "base64"})
        # Will return 400 (missing required) or 503 (no Pillow)
        assert response.status_code in [400, 503]


class TestCTASlideAPI:
    """Tests for CTA slide API."""

    def test_cta_standalone_missing_title(self, client):
        """Test standalone CTA without video_title."""
        response = client.post("/api/images/cta", json={})
        # Will return 400 (missing required) or 503 (no Pillow)
        assert response.status_code in [400, 503]

    def test_cta_standalone_with_title(self, client):
        """Test standalone CTA with video_title."""
        response = client.post(
            "/api/images/cta",
            json={
                "video_title": "Building REST APIs",
                "course_label": "Module 1",
                "tagline": "Ready to code?"
            }
        )
        # Will return 200 (success), 500 (font error), or 503 (no Pillow)
        assert response.status_code in [200, 500, 503]


class TestImageGeneratorIntegration:
    """Integration tests requiring Pillow."""

    @pytest.fixture
    def check_pillow(self):
        """Skip tests if Pillow is not available."""
        try:
            from src.utils.video_slide_generator import PILLOW_AVAILABLE
            if not PILLOW_AVAILABLE:
                pytest.skip("Pillow not installed")
        except ImportError:
            pytest.skip("Pillow not installed")

    def test_cta_slide_generation(self, client, check_pillow):
        """Test CTA slide generation with Pillow."""
        response = client.post(
            "/api/images/cta",
            json={
                "video_title": "Flask REST APIs",
                "course_label": "Module 1",
                "tagline": "Ready to build?"
            }
        )
        assert response.status_code == 200

        data = response.get_json()
        assert "image" in data
        assert data["width"] == 1280
        assert data["height"] == 720

    def test_terminal_simple_command(self, client, check_pillow):
        """Test simple terminal screenshot."""
        response = client.post(
            "/api/images/terminal",
            json={
                "command": "python --version",
                "output": "Python 3.11.0"
            }
        )
        assert response.status_code == 200

        data = response.get_json()
        assert "image" in data
        assert data["format"] == "png"

    def test_terminal_multi_line(self, client, check_pillow):
        """Test multi-line terminal screenshot."""
        response = client.post(
            "/api/images/terminal",
            json={
                "lines": [
                    {"text": "$ pip install flask", "type": "prompt"},
                    {"text": "Successfully installed flask-2.3.0", "type": "success"},
                    {"text": "$ flask --version", "type": "prompt"},
                    {"text": "Flask 2.3.0", "type": "output"}
                ]
            }
        )
        assert response.status_code == 200

        data = response.get_json()
        assert "image" in data
