"""Pytest configuration and shared fixtures for invoker integration tests."""

import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_project_dir():
    """Create a temporary directory for test projects.

    Yields the path to the temporary directory and cleans up after the test.
    """
    temp_dir = tempfile.mkdtemp(prefix="invoker_test_")
    yield Path(temp_dir)
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)
