"""Default configuration values and paths."""

from pathlib import Path
from typing import Final

# Default directories
DEFAULT_CONFIG_DIR: Final[Path] = Path.home() / ".config" / "llm-box"
DEFAULT_CACHE_DIR: Final[Path] = Path.home() / ".cache" / "llm-box"
DEFAULT_PLUGINS_DIR: Final[Path] = DEFAULT_CONFIG_DIR / "plugins"

# Default file paths
DEFAULT_CONFIG_FILE: Final[Path] = DEFAULT_CONFIG_DIR / "config.toml"
DEFAULT_CACHE_DB: Final[Path] = DEFAULT_CACHE_DIR / "cache.duckdb"
DEFAULT_LOG_FILE: Final[Path] = DEFAULT_CACHE_DIR / "llm-box.log"
DEFAULT_TELEMETRY_FILE: Final[Path] = DEFAULT_CACHE_DIR / "telemetry.jsonl"

# Environment variable names
ENV_CONFIG_PATH: Final[str] = "LLMBOX_CONFIG"
ENV_CACHE_PATH: Final[str] = "LLMBOX_CACHE_PATH"
ENV_LOG_LEVEL: Final[str] = "LLMBOX_LOG_LEVEL"
ENV_DEFAULT_PROVIDER: Final[str] = "LLMBOX_PROVIDER"
ENV_DEFAULT_MODEL: Final[str] = "LLMBOX_MODEL"
ENV_NO_CACHE: Final[str] = "LLMBOX_NO_CACHE"

# Provider environment variables
ENV_OPENAI_API_KEY: Final[str] = "OPENAI_API_KEY"
ENV_ANTHROPIC_API_KEY: Final[str] = "ANTHROPIC_API_KEY"
ENV_OLLAMA_HOST: Final[str] = "OLLAMA_HOST"

# Default config content (TOML)
DEFAULT_CONFIG_TOML: Final[str] = """\
# llm-box configuration
# https://github.com/vedanta/llm-box

default_provider = "ollama"

[providers.ollama]
enabled = true
default_model = "llama3"
base_url = "http://localhost:11434"
timeout = 120.0

[providers.openai]
enabled = false
default_model = "gpt-4o-mini"
# api_key = ""  # Use OPENAI_API_KEY env var

[providers.anthropic]
enabled = false
default_model = "claude-sonnet-4-20250514"
# api_key = ""  # Use ANTHROPIC_API_KEY env var

[cache]
enabled = true
default_ttl_seconds = 604800  # 7 days
max_size_mb = 500
cleanup_on_start = true

[cache_ttl]
ls = 86400      # 1 day
cat = 604800    # 7 days
find = 3600     # 1 hour

[search]
semantic_weight = 0.6
fuzzy_weight = 0.4
default_top_k = 10

[output]
default_format = "rich"
show_cached_indicator = true
color = true

[telemetry]
enabled = false
local_only = true

[plugins]
enabled = true
auto_discover = true

[logging]
level = "INFO"
json_format = false
"""


def ensure_directories() -> None:
    """Ensure all default directories exist."""
    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DEFAULT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    DEFAULT_PLUGINS_DIR.mkdir(parents=True, exist_ok=True)


def get_config_path() -> Path:
    """Get the configuration file path."""
    import os

    env_path = os.environ.get(ENV_CONFIG_PATH)
    if env_path:
        return Path(env_path)
    return DEFAULT_CONFIG_FILE


def get_cache_path() -> Path:
    """Get the cache database path."""
    import os

    env_path = os.environ.get(ENV_CACHE_PATH)
    if env_path:
        return Path(env_path)
    return DEFAULT_CACHE_DB
