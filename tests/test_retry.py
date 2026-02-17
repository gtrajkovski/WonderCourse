"""Tests for retry decorators."""

import pytest
from unittest.mock import Mock, patch
from src.utils.retry import ai_retry, file_retry, network_retry


def test_ai_retry_succeeds_on_first_try():
    """Test that ai_retry doesn't retry when function succeeds."""
    mock_func = Mock(return_value="success")
    decorated = ai_retry(mock_func)

    result = decorated()

    assert result == "success"
    assert mock_func.call_count == 1


def test_ai_retry_succeeds_after_transient_failure():
    """Test that ai_retry retries after transient failure."""
    # Use TimeoutError instead of APIError since APIError requires request object
    mock_func = Mock(side_effect=[TimeoutError("Temporary error"), "success"])
    decorated = ai_retry(mock_func)

    result = decorated()

    assert result == "success"
    assert mock_func.call_count == 2


def test_ai_retry_raises_after_max_attempts():
    """Test that ai_retry raises after 3 attempts."""
    # Use ConnectionError which is simpler to instantiate
    mock_func = Mock(side_effect=ConnectionError("Persistent error"))
    decorated = ai_retry(mock_func)

    with pytest.raises(ConnectionError):
        decorated()

    assert mock_func.call_count == 3


def test_ai_retry_no_retry_on_permanent_error():
    """Test that ai_retry doesn't retry non-transient errors."""
    mock_func = Mock(side_effect=ValueError("Invalid input"))
    decorated = ai_retry(mock_func)

    with pytest.raises(ValueError):
        decorated()

    # Should not retry ValueError (only retries TimeoutError, ConnectionError, APIError)
    assert mock_func.call_count == 1


def test_file_retry_handles_permission_error():
    """Test that file_retry retries PermissionError."""
    mock_func = Mock(side_effect=[PermissionError("Access denied"), "success"])
    decorated = file_retry(mock_func)

    result = decorated()

    assert result == "success"
    assert mock_func.call_count == 2


def test_file_retry_handles_io_error():
    """Test that file_retry retries IOError."""
    mock_func = Mock(side_effect=[IOError("File locked"), "success"])
    decorated = file_retry(mock_func)

    result = decorated()

    assert result == "success"
    assert mock_func.call_count == 2


def test_file_retry_max_attempts():
    """Test that file_retry raises after 5 attempts."""
    mock_func = Mock(side_effect=OSError("Persistent file error"))
    decorated = file_retry(mock_func)

    with pytest.raises(OSError):
        decorated()

    assert mock_func.call_count == 5


def test_network_retry_with_connection_error():
    """Test that network_retry retries ConnectionError."""
    mock_func = Mock(side_effect=[ConnectionError("Network unavailable"), "success"])
    decorated = network_retry(mock_func)

    result = decorated()

    assert result == "success"
    assert mock_func.call_count == 2


def test_network_retry_with_timeout():
    """Test that network_retry retries TimeoutError."""
    mock_func = Mock(side_effect=[TimeoutError("Request timeout"), "success"])
    decorated = network_retry(mock_func)

    result = decorated()

    assert result == "success"
    assert mock_func.call_count == 2


def test_network_retry_max_attempts():
    """Test that network_retry raises after 3 attempts."""
    mock_func = Mock(side_effect=ConnectionError("Persistent network error"))
    decorated = network_retry(mock_func)

    with pytest.raises(ConnectionError):
        decorated()

    assert mock_func.call_count == 3
