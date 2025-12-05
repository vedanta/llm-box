"""Configuration loading from TOML files and environment variables."""

import contextlib
import os
from pathlib import Path

from llm_box.config.defaults import (
    DEFAULT_CONFIG_TOML,
    ENV_ANTHROPIC_API_KEY,
    ENV_DEFAULT_MODEL,
    ENV_DEFAULT_PROVIDER,
    ENV_LOG_LEVEL,
    ENV_NO_CACHE,
    ENV_OLLAMA_HOST,
    ENV_OPENAI_API_KEY,
    ensure_directories,
    get_config_path,
)
from llm_box.config.schema import LLMBoxConfig, ProviderType
from llm_box.exceptions import ConfigError, ConfigValidationError

# Global config instance (singleton)
_config: LLMBoxConfig | None = None


def load_config(
    config_path: Path | None = None,
    *,
    create_if_missing: bool = True,
) -> LLMBoxConfig:
    """Load configuration from TOML file and environment variables.

    Args:
        config_path: Path to config file. If None, uses default.
        create_if_missing: Create default config if file doesn't exist.

    Returns:
        Loaded and validated configuration.

    Raises:
        ConfigError: If configuration cannot be loaded.
        ConfigValidationError: If configuration is invalid.
    """
    # Use Python 3.11+ tomllib or fallback
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError as err:
            raise ConfigError(
                "tomllib not available. Install 'tomli' for Python < 3.11"
            ) from err

    path = config_path or get_config_path()

    # Create default config if missing
    if not path.exists():
        if create_if_missing:
            ensure_directories()
            path.write_text(DEFAULT_CONFIG_TOML)
        else:
            # Return default config without file
            return _apply_env_overrides(LLMBoxConfig())

    # Load TOML file
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except Exception as e:
        raise ConfigError(f"Failed to load config from {path}: {e}") from e

    # Parse into Pydantic model
    try:
        config = LLMBoxConfig.model_validate(data)
    except Exception as e:
        raise ConfigValidationError(f"Invalid configuration: {e}") from e

    # Apply environment variable overrides
    config = _apply_env_overrides(config)

    return config


def _apply_env_overrides(config: LLMBoxConfig) -> LLMBoxConfig:
    """Apply environment variable overrides to configuration."""
    # Provider override
    provider_env = os.environ.get(ENV_DEFAULT_PROVIDER)
    if provider_env:
        with contextlib.suppress(ValueError):
            config.default_provider = ProviderType(provider_env.lower())

    # Model override (applied to default provider)
    model_env = os.environ.get(ENV_DEFAULT_MODEL)
    if model_env:
        if config.default_provider == ProviderType.OLLAMA:
            config.providers.ollama.default_model = model_env
        elif config.default_provider == ProviderType.OPENAI:
            config.providers.openai.default_model = model_env
        elif config.default_provider == ProviderType.ANTHROPIC:
            config.providers.anthropic.default_model = model_env

    # Log level override
    log_level = os.environ.get(ENV_LOG_LEVEL)
    if log_level:
        config.logging.level = log_level.upper()

    # Cache disable override
    no_cache = os.environ.get(ENV_NO_CACHE)
    if no_cache and no_cache.lower() in ("1", "true", "yes"):
        config.cache.enabled = False

    # API keys from environment
    openai_key = os.environ.get(ENV_OPENAI_API_KEY)
    if openai_key and not config.providers.openai.api_key:
        config.providers.openai.api_key = openai_key

    anthropic_key = os.environ.get(ENV_ANTHROPIC_API_KEY)
    if anthropic_key and not config.providers.anthropic.api_key:
        config.providers.anthropic.api_key = anthropic_key

    # Ollama host override
    ollama_host = os.environ.get(ENV_OLLAMA_HOST)
    if ollama_host:
        config.providers.ollama.base_url = ollama_host

    return config


def get_config() -> LLMBoxConfig:
    """Get the current configuration (singleton).

    Loads config on first access, caches for subsequent calls.

    Returns:
        Current configuration.
    """
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config(config_path: Path | None = None) -> LLMBoxConfig:
    """Reload configuration from disk.

    Args:
        config_path: Path to config file. If None, uses default.

    Returns:
        Reloaded configuration.
    """
    global _config
    _config = load_config(config_path)
    return _config


def reset_config() -> None:
    """Reset the configuration singleton (mainly for testing)."""
    global _config
    _config = None
