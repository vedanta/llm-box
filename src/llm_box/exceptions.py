"""Exception hierarchy for llm-box."""


class LLMBoxError(Exception):
    """Base exception for all llm-box errors."""

    exit_code: int = 1
    user_message: str = "An error occurred"

    def __init__(
        self,
        message: str | None = None,
        *,
        user_message: str | None = None,
    ) -> None:
        super().__init__(message or self.user_message)
        if user_message:
            self.user_message = user_message


# Provider Errors
class ProviderError(LLMBoxError):
    """LLM provider-related errors."""

    exit_code = 2
    user_message = "LLM provider error"


class ProviderNotAvailableError(ProviderError):
    """Provider is not reachable or not configured."""

    exit_code = 2
    user_message = "LLM provider is not available"


class ProviderRateLimitError(ProviderError):
    """Rate limit exceeded."""

    exit_code = 3
    user_message = "Rate limit exceeded. Try again later."


class ProviderAuthError(ProviderError):
    """Authentication failed."""

    exit_code = 4
    user_message = "Authentication failed. Check your API key."


class ProviderTimeoutError(ProviderError):
    """Request timed out."""

    exit_code = 5
    user_message = "Request timed out. Try again."


# Cache Errors
class CacheError(LLMBoxError):
    """Cache-related errors."""

    exit_code = 10
    user_message = "Cache error"


class CacheConnectionError(CacheError):
    """Cannot connect to cache database."""

    exit_code = 11
    user_message = "Cannot connect to cache database"


class CacheCorruptedError(CacheError):
    """Cache database is corrupted."""

    exit_code = 12
    user_message = "Cache database is corrupted. Try 'llm-box cache clear'"


# Config Errors
class ConfigError(LLMBoxError):
    """Configuration errors."""

    exit_code = 20
    user_message = "Configuration error"


class ConfigNotFoundError(ConfigError):
    """Configuration file not found."""

    exit_code = 21
    user_message = "Configuration file not found"


class ConfigValidationError(ConfigError):
    """Configuration validation failed."""

    exit_code = 22
    user_message = "Invalid configuration"


# Search Errors
class SearchError(LLMBoxError):
    """Search-related errors."""

    exit_code = 30
    user_message = "Search error"


class IndexNotFoundError(SearchError):
    """Search index doesn't exist."""

    exit_code = 31
    user_message = "No search index found. Run 'llm-box index' first."


class IndexingError(SearchError):
    """Error during indexing."""

    exit_code = 32
    user_message = "Error indexing files"


# Command Errors
class CommandError(LLMBoxError):
    """Command execution errors."""

    exit_code = 40
    user_message = "Command error"


class FileNotFoundError(CommandError):
    """File or directory not found."""

    exit_code = 41
    user_message = "File or directory not found"


class InvalidArgumentError(CommandError):
    """Invalid argument provided."""

    exit_code = 42
    user_message = "Invalid argument"


# Plugin Errors
class PluginError(LLMBoxError):
    """Plugin-related errors."""

    exit_code = 50
    user_message = "Plugin error"


class PluginNotFoundError(PluginError):
    """Plugin not found."""

    exit_code = 51
    user_message = "Plugin not found"


class PluginLoadError(PluginError):
    """Failed to load plugin."""

    exit_code = 52
    user_message = "Failed to load plugin"
