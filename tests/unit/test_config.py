"""Tests for configuration system."""

from pathlib import Path

import pytest

from llm_box.config.loader import load_config
from llm_box.config.schema import LLMBoxConfig, OutputFormat, ProviderType


class TestLLMBoxConfig:
    """Tests for LLMBoxConfig schema."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = LLMBoxConfig()

        assert config.default_provider == ProviderType.OLLAMA
        assert config.providers.ollama.enabled is True
        assert config.providers.ollama.default_model == "llama3"
        assert config.providers.openai.enabled is False
        assert config.providers.anthropic.enabled is False
        assert config.cache.enabled is True
        assert config.output.default_format == OutputFormat.RICH

    def test_config_from_dict(self) -> None:
        """Test creating config from dictionary."""
        data = {
            "default_provider": "openai",
            "providers": {
                "openai": {
                    "enabled": True,
                    "default_model": "gpt-4",
                }
            },
            "cache": {
                "enabled": False,
            },
        }
        config = LLMBoxConfig.model_validate(data)

        assert config.default_provider == ProviderType.OPENAI
        assert config.providers.openai.enabled is True
        assert config.providers.openai.default_model == "gpt-4"
        assert config.cache.enabled is False


class TestConfigLoader:
    """Tests for configuration loader."""

    def test_load_config_creates_default(self, temp_dir: Path) -> None:
        """Test that load_config creates default config file."""
        config_path = temp_dir / "config.toml"
        config = load_config(config_path, create_if_missing=True)

        assert config_path.exists()
        assert config.default_provider == ProviderType.OLLAMA

    def test_load_config_from_file(self, config_file: Path) -> None:
        """Test loading config from existing file."""
        config = load_config(config_file)

        assert config.default_provider == ProviderType.OLLAMA
        assert config.cache.default_ttl_seconds == 3600
        assert config.output.default_format == OutputFormat.PLAIN

    def test_load_config_without_file(self, temp_dir: Path) -> None:
        """Test loading config without creating file."""
        config_path = temp_dir / "nonexistent.toml"
        config = load_config(config_path, create_if_missing=False)

        assert not config_path.exists()
        assert config.default_provider == ProviderType.OLLAMA
