"""Pytest fixtures for multi-agent code review tests."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock


# Mock Settings before any other imports
@pytest.fixture(autouse=True)
def mock_settings():
    """Mock Settings to avoid requiring LLM_API_KEY."""
    mock_settings_instance = MagicMock()
    mock_settings_instance.llm_provider = "openai"
    mock_settings_instance.llm_model = "gpt-4"
    mock_settings_instance.llm_api_key = "test-key"
    mock_settings_instance.max_tokens = 4096
    mock_settings_instance.temperature = 0.7
    mock_settings_instance.webui_port = 7860
    mock_settings_instance.webui_host = "0.0.0.0"
    mock_settings_instance.webui_share = False
    mock_settings_instance.project_root = "."
    mock_settings_instance.sandbox_enabled = True
    mock_settings_instance.max_file_size = 1024 * 1024

    with patch.dict('os.environ', {'LLM_API_KEY': 'test-key'}):
        yield mock_settings_instance


@pytest.fixture
def sample_code():
    """Sample Python code for testing."""
    return '''import os
import sys
import json

def hello():
    return "hello"

def unused_function():
    x = 1
    return x
'''


@pytest.fixture
def sample_code_with_issues():
    """Sample Python code with various issues."""
    return '''import os
import sys
import json

def bad_function(x):
    if x > 10:
        if x > 20:
            if x > 30:
                if x > 40:
                    return "very deep"
    return "ok"

class BadClass:
    def __init__(self):
        password = "hardcoded"
'''


@pytest.fixture
def temp_python_file(sample_code):
    """Create a temporary Python file with sample code."""
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".py",
        delete=False,
    ) as f:
        f.write(sample_code)
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
def temp_dir():
    """Create a temporary directory with Python files."""
    temp_dir = tempfile.mkdtemp()

    # Create some Python files
    files = []
    for i in range(3):
        file_path = Path(temp_dir) / f"module_{i}.py"
        file_path.write_text(f"""def function_{i}():
    return {i}
""")
        files.append(str(file_path))

    yield temp_dir, files

    # Cleanup
    import shutil

    shutil.rmtree(temp_dir, ignore_errors=True)