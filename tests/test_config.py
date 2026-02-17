import os
from pathlib import Path
import pytest
from src.config import Config


def test_config_has_required_attributes():
    """Test that Config class has all required attributes"""
    assert hasattr(Config, "ANTHROPIC_API_KEY")
    assert hasattr(Config, "MODEL")
    assert hasattr(Config, "MAX_TOKENS")
    assert hasattr(Config, "PROJECTS_DIR")
    assert hasattr(Config, "PORT")


def test_model_default_value():
    """Test MODEL defaults to claude-sonnet-4-20250514"""
    # Save original value
    original_model = os.environ.get("MODEL")

    # Remove MODEL from environment to test default
    if "MODEL" in os.environ:
        del os.environ["MODEL"]

    # Reimport to get fresh config
    from importlib import reload
    from src import config as config_module
    reload(config_module)

    assert config_module.Config.MODEL == "claude-sonnet-4-20250514"

    # Restore original value
    if original_model:
        os.environ["MODEL"] = original_model


def test_max_tokens_value():
    """Test MAX_TOKENS is 4096"""
    assert Config.MAX_TOKENS == 4096


def test_projects_dir_type():
    """Test PROJECTS_DIR is a Path object pointing to 'projects'"""
    assert isinstance(Config.PROJECTS_DIR, Path)
    assert str(Config.PROJECTS_DIR) == "projects"


def test_port_default_value():
    """Test PORT defaults to 5003"""
    # Save original value
    original_port = os.environ.get("PORT")

    # Remove PORT from environment to test default
    if "PORT" in os.environ:
        del os.environ["PORT"]

    # Reimport to get fresh config
    from importlib import reload
    from src import config as config_module
    reload(config_module)

    assert config_module.Config.PORT == 5003

    # Restore original value
    if original_port:
        os.environ["PORT"] = original_port


def test_ensure_dirs_creates_projects_directory(tmp_path, monkeypatch):
    """Test ensure_dirs creates projects directory"""
    # Create a temporary projects directory path
    test_projects_dir = tmp_path / "test_projects"

    # Monkeypatch Config.PROJECTS_DIR to use our test path
    monkeypatch.setattr(Config, "PROJECTS_DIR", test_projects_dir)

    # Verify directory doesn't exist yet
    assert not test_projects_dir.exists()

    # Call ensure_dirs
    result = Config.ensure_dirs()

    # Verify directory was created
    assert test_projects_dir.exists()
    assert test_projects_dir.is_dir()
    assert result == test_projects_dir


def test_course_duration_constants():
    """Test course duration min/max constants"""
    assert Config.COURSE_MIN_DURATION_MINUTES == 30
    assert Config.COURSE_MAX_DURATION_MINUTES == 180


def test_words_per_minute_constant():
    """Test WORDS_PER_MINUTE constant"""
    assert Config.WORDS_PER_MINUTE == 150


def test_max_reading_words_constant():
    """Test MAX_READING_WORDS constant"""
    assert Config.MAX_READING_WORDS == 1200


def test_max_textbook_words_per_outcome_constant():
    """Test MAX_TEXTBOOK_WORDS_PER_OUTCOME constant"""
    assert Config.MAX_TEXTBOOK_WORDS_PER_OUTCOME == 3000


def test_debug_default_value():
    """Test DEBUG defaults to True"""
    # Save original value
    original_debug = os.environ.get("FLASK_DEBUG")

    # Remove FLASK_DEBUG from environment to test default
    if "FLASK_DEBUG" in os.environ:
        del os.environ["FLASK_DEBUG"]

    # Reimport to get fresh config
    from importlib import reload
    from src import config as config_module
    reload(config_module)

    assert config_module.Config.DEBUG is True

    # Restore original value
    if original_debug:
        os.environ["FLASK_DEBUG"] = original_debug
