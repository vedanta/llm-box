"""Pytest fixtures for llm-box tests."""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from llm_box.config import reset_config
from llm_box.config.schema import LLMBoxConfig


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_files(temp_dir: Path) -> Path:
    """Create sample files for testing."""
    # Create some test files
    (temp_dir / "README.md").write_text("# Test Project\n\nThis is a test.")
    (temp_dir / "main.py").write_text("def main():\n    print('Hello')\n")
    (temp_dir / "config.toml").write_text("[settings]\nname = 'test'\n")

    # Create a subdirectory
    subdir = temp_dir / "src"
    subdir.mkdir()
    (subdir / "app.py").write_text("# Application code\n")
    (subdir / "__init__.py").write_text("")

    return temp_dir


@pytest.fixture
def default_config() -> LLMBoxConfig:
    """Get default configuration."""
    return LLMBoxConfig()


@pytest.fixture(autouse=True)
def reset_config_fixture() -> Generator[None, None, None]:
    """Reset config singleton between tests."""
    reset_config()
    yield
    reset_config()


@pytest.fixture
def config_file(temp_dir: Path) -> Path:
    """Create a test config file."""
    config_path = temp_dir / "config.toml"
    config_path.write_text("""
default_provider = "ollama"

[providers.ollama]
enabled = true
default_model = "llama3"

[cache]
enabled = true
default_ttl_seconds = 3600

[output]
default_format = "plain"
""")
    return config_path
