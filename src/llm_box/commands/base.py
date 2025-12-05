"""Base command pattern implementation.

This module provides the foundation for all llm-box commands,
including the CommandContext for dependency injection and
BaseCommand abstract class for command implementations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from llm_box.cache.base import Cache
from llm_box.config.schema import LLMBoxConfig
from llm_box.output.base import OutputData, OutputFormatter
from llm_box.providers.base import LLMBoxProvider


@dataclass
class CommandContext:
    """Context object passed to commands for dependency injection.

    This provides commands with access to all necessary services
    without tight coupling to specific implementations.

    Attributes:
        provider: The LLM provider to use for inference.
        cache: The cache for storing/retrieving responses.
        formatter: The output formatter for displaying results.
        config: The application configuration.
        use_cache: Whether to use caching for this invocation.
        verbose: Whether to show verbose output.
        working_dir: The working directory for file operations.
    """

    provider: LLMBoxProvider
    cache: Cache
    formatter: OutputFormatter
    config: LLMBoxConfig
    use_cache: bool = True
    verbose: bool = False
    working_dir: Path = field(default_factory=Path.cwd)

    def with_provider(self, provider: LLMBoxProvider) -> "CommandContext":
        """Create a new context with a different provider."""
        return CommandContext(
            provider=provider,
            cache=self.cache,
            formatter=self.formatter,
            config=self.config,
            use_cache=self.use_cache,
            verbose=self.verbose,
            working_dir=self.working_dir,
        )

    def with_cache_disabled(self) -> "CommandContext":
        """Create a new context with caching disabled."""
        return CommandContext(
            provider=self.provider,
            cache=self.cache,
            formatter=self.formatter,
            config=self.config,
            use_cache=False,
            verbose=self.verbose,
            working_dir=self.working_dir,
        )

    def with_verbose(self, verbose: bool = True) -> "CommandContext":
        """Create a new context with verbose mode set."""
        return CommandContext(
            provider=self.provider,
            cache=self.cache,
            formatter=self.formatter,
            config=self.config,
            use_cache=self.use_cache,
            verbose=verbose,
            working_dir=self.working_dir,
        )


@dataclass
class CommandResult:
    """Result of a command execution.

    Attributes:
        success: Whether the command succeeded.
        data: The result data (type depends on command).
        error: Error message if command failed.
        cached: Whether the result came from cache.
        metadata: Additional metadata about the execution.
    """

    success: bool
    data: Any = None
    error: str | None = None
    cached: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(
        cls,
        data: Any,
        cached: bool = False,
        **metadata: Any,
    ) -> "CommandResult":
        """Create a successful result."""
        return cls(
            success=True,
            data=data,
            cached=cached,
            metadata=metadata,
        )

    @classmethod
    def fail(cls, error: str, **metadata: Any) -> "CommandResult":
        """Create a failed result."""
        return cls(
            success=False,
            error=error,
            metadata=metadata,
        )

    def to_output_data(self, title: str | None = None) -> OutputData:
        """Convert to OutputData for formatting."""
        if self.success:
            return OutputData.from_content(
                content=self.data,
                title=title,
                cached=self.cached,
                **self.metadata,
            )
        else:
            return OutputData.from_error(
                error=self.error or "Unknown error",
                title=title,
            )


class BaseCommand(ABC):
    """Abstract base class for all llm-box commands.

    Commands encapsulate the logic for specific operations like
    listing files, explaining code, etc. They receive a CommandContext
    with all necessary dependencies and return a CommandResult.

    Example:
        class CatCommand(BaseCommand):
            @property
            def name(self) -> str:
                return "cat"

            @property
            def description(self) -> str:
                return "Explain a file's contents"

            def execute(self, ctx: CommandContext, **kwargs) -> CommandResult:
                file_path = kwargs.get("file_path")
                # ... implementation ...
                return CommandResult.ok(explanation)
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """The command name (used in CLI)."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """A short description of what the command does."""
        pass

    @property
    def aliases(self) -> list[str]:
        """Alternative names for the command."""
        return []

    @abstractmethod
    def execute(self, ctx: CommandContext, **kwargs: Any) -> CommandResult:
        """Execute the command.

        Args:
            ctx: The command context with dependencies.
            **kwargs: Command-specific arguments.

        Returns:
            CommandResult indicating success/failure and data.
        """
        pass

    async def aexecute(self, ctx: CommandContext, **kwargs: Any) -> CommandResult:
        """Async version of execute.

        Default implementation calls sync execute.
        Override for true async behavior.

        Args:
            ctx: The command context with dependencies.
            **kwargs: Command-specific arguments.

        Returns:
            CommandResult indicating success/failure and data.
        """
        return self.execute(ctx, **kwargs)

    def run(self, ctx: CommandContext, **kwargs: Any) -> None:
        """Execute and print the result.

        Convenience method that executes the command and
        prints the result using the context's formatter.

        Args:
            ctx: The command context with dependencies.
            **kwargs: Command-specific arguments.
        """
        result = self.execute(ctx, **kwargs)
        output_data = result.to_output_data(title=self.name)
        ctx.formatter.print(output_data)

    async def arun(self, ctx: CommandContext, **kwargs: Any) -> None:
        """Async version of run.

        Args:
            ctx: The command context with dependencies.
            **kwargs: Command-specific arguments.
        """
        result = await self.aexecute(ctx, **kwargs)
        output_data = result.to_output_data(title=self.name)
        ctx.formatter.print(output_data)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"
