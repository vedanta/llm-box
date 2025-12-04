"""Pydantic models for llm-box configuration."""

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class ProviderType(str, Enum):
    """Supported LLM providers."""

    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MOCK = "mock"


class OutputFormat(str, Enum):
    """Supported output formats."""

    RICH = "rich"
    PLAIN = "plain"
    JSON = "json"


class OllamaConfig(BaseModel):
    """Ollama provider configuration."""

    enabled: bool = True
    default_model: str = "llama3"
    base_url: str = "http://localhost:11434"
    timeout: float = 120.0


class OpenAIConfig(BaseModel):
    """OpenAI provider configuration."""

    enabled: bool = False
    default_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    api_key: str | None = None  # Use OPENAI_API_KEY env var
    timeout: float = 60.0


class AnthropicConfig(BaseModel):
    """Anthropic provider configuration."""

    enabled: bool = False
    default_model: str = "claude-sonnet-4-20250514"
    api_key: str | None = None  # Use ANTHROPIC_API_KEY env var
    max_tokens: int = 4096
    timeout: float = 60.0


class ProvidersConfig(BaseModel):
    """Configuration for all LLM providers."""

    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    anthropic: AnthropicConfig = Field(default_factory=AnthropicConfig)


class CacheConfig(BaseModel):
    """Cache configuration."""

    enabled: bool = True
    path: Path | None = None  # Default: ~/.cache/llm-box/cache.duckdb
    default_ttl_seconds: int = 604800  # 7 days
    max_size_mb: int = 500
    cleanup_on_start: bool = True


class CacheCommandTTL(BaseModel):
    """Per-command TTL overrides."""

    ls: int = 86400  # 1 day
    cat: int = 604800  # 7 days
    find: int = 3600  # 1 hour


class SearchConfig(BaseModel):
    """Search configuration."""

    semantic_weight: float = 0.6
    fuzzy_weight: float = 0.4
    default_top_k: int = 10
    min_score: float = 0.5
    chunk_size: int = 500
    chunk_overlap: int = 50


class OutputConfig(BaseModel):
    """Output configuration."""

    default_format: OutputFormat = OutputFormat.RICH
    show_cached_indicator: bool = True
    color: bool = True


class TelemetryConfig(BaseModel):
    """Telemetry configuration (opt-in)."""

    enabled: bool = False
    local_only: bool = True


class PluginsConfig(BaseModel):
    """Plugins configuration."""

    enabled: bool = True
    auto_discover: bool = True
    directory: Path | None = None  # Default: ~/.config/llm-box/plugins


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = "INFO"
    file: Path | None = None  # Default: no file logging
    json_format: bool = False


class LLMBoxConfig(BaseModel):
    """Root configuration for llm-box."""

    default_provider: ProviderType = ProviderType.OLLAMA
    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    cache_ttl: CacheCommandTTL = Field(default_factory=CacheCommandTTL)
    search: SearchConfig = Field(default_factory=SearchConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)
    plugins: PluginsConfig = Field(default_factory=PluginsConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    class Config:
        """Pydantic config."""

        use_enum_values = True
