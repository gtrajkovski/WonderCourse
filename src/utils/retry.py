"""Retry decorators for transient failures.

Provides tenacity-based retry decorators for AI API calls, file operations,
and network requests with exponential backoff and jitter.
"""

import logging
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_exception_type,
    before_sleep_log
)

logger = logging.getLogger(__name__)


def ai_retry(func):
    """Retry decorator for AI API calls with exponential backoff.

    Use this for Claude API calls that may fail due to:
    - Network timeouts
    - Temporary API unavailability
    - Rate limiting (5xx errors)

    Configuration:
    - 3 attempts max
    - Exponential backoff with jitter (4-10 seconds)
    - Retries TimeoutError, ConnectionError, and anthropic.APIError
    - Logs retries at WARNING level

    Example:
        @ai_retry
        def generate_content(self, prompt):
            return self.client.messages.create(...)
    """
    from anthropic import APIError

    return retry(
        stop=stop_after_attempt(3),
        wait=wait_random_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((TimeoutError, ConnectionError, APIError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )(func)


def file_retry(func):
    """Retry decorator for file operations with shorter backoff.

    Use this for file system operations that may fail due to:
    - File locks from antivirus scans
    - Temporary permission issues
    - Network file system glitches

    Configuration:
    - 5 attempts max
    - Shorter exponential backoff (1-5 seconds)
    - Retries IOError, OSError, PermissionError
    - Logs retries at WARNING level

    Example:
        @file_retry
        def save_to_disk(path, data):
            with open(path, 'w') as f:
                f.write(data)
    """
    return retry(
        stop=stop_after_attempt(5),
        wait=wait_random_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((IOError, OSError, PermissionError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )(func)


def network_retry(func):
    """Retry decorator for general HTTP/network requests.

    Use this for HTTP requests, webhooks, or external service calls that
    may fail due to:
    - Network connectivity issues
    - Temporary service unavailability
    - Request timeouts

    Configuration:
    - 3 attempts max
    - Exponential backoff with jitter (4-10 seconds)
    - Retries ConnectionError, TimeoutError
    - Logs retries at WARNING level

    Example:
        @network_retry
        def fetch_external_content(url):
            return requests.get(url, timeout=30)
    """
    return retry(
        stop=stop_after_attempt(3),
        wait=wait_random_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )(func)
