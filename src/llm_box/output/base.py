"""Output formatter protocol and base classes."""

import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TextIO


class OutputFormat(str, Enum):
    """Supported output formats."""

    PLAIN = "plain"
    JSON = "json"
    RICH = "rich"


@dataclass
class OutputData:
    """Container for output data to be formatted.

    Attributes:
        content: The main content to display.
        title: Optional title for the output.
        metadata: Additional metadata (tokens, timing, etc.).
        cached: Whether the result came from cache.
        error: Error message if operation failed.
        success: Whether the operation was successful.
    """

    content: str | list[str] | dict[str, Any]
    title: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    cached: bool = False
    error: str | None = None
    success: bool = True

    @classmethod
    def from_error(cls, error: str, title: str | None = None) -> "OutputData":
        """Create an OutputData instance for an error."""
        return cls(
            content="",
            title=title,
            error=error,
            success=False,
        )

    @classmethod
    def from_content(
        cls,
        content: str | list[str] | dict[str, Any],
        title: str | None = None,
        cached: bool = False,
        **metadata: Any,
    ) -> "OutputData":
        """Create an OutputData instance for successful output."""
        return cls(
            content=content,
            title=title,
            cached=cached,
            metadata=metadata,
            success=True,
        )


class OutputFormatter(ABC):
    """Abstract base class for output formatters.

    Formatters are responsible for rendering output data to the terminal
    in different formats (plain text, JSON, rich formatted).
    """

    def __init__(
        self,
        stream: TextIO | None = None,
        error_stream: TextIO | None = None,
        verbose: bool = False,
    ) -> None:
        """Initialize the formatter.

        Args:
            stream: Output stream (defaults to stdout).
            error_stream: Error stream (defaults to stderr).
            verbose: Whether to show verbose output.
        """
        self._stream = stream or sys.stdout
        self._error_stream = error_stream or sys.stderr
        self._verbose = verbose

    @property
    def stream(self) -> TextIO:
        """Get the output stream."""
        return self._stream

    @property
    def error_stream(self) -> TextIO:
        """Get the error stream."""
        return self._error_stream

    @property
    def verbose(self) -> bool:
        """Whether verbose output is enabled."""
        return self._verbose

    @property
    @abstractmethod
    def format_type(self) -> OutputFormat:
        """Get the format type of this formatter."""
        pass

    @abstractmethod
    def format(self, data: OutputData) -> str:
        """Format output data as a string.

        Args:
            data: The output data to format.

        Returns:
            Formatted string representation.
        """
        pass

    def print(self, data: OutputData) -> None:
        """Format and print output data.

        Args:
            data: The output data to print.
        """
        formatted = self.format(data)
        if data.success:
            print(formatted, file=self._stream)
        else:
            print(formatted, file=self._error_stream)

    def print_error(self, message: str, title: str | None = None) -> None:
        """Print an error message.

        Args:
            message: The error message.
            title: Optional title.
        """
        data = OutputData.from_error(message, title)
        self.print(data)

    def print_content(
        self,
        content: str | list[str] | dict[str, Any],
        title: str | None = None,
        cached: bool = False,
        **metadata: Any,
    ) -> None:
        """Print content directly.

        Args:
            content: The content to print.
            title: Optional title.
            cached: Whether result was cached.
            **metadata: Additional metadata.
        """
        data = OutputData.from_content(content, title, cached, **metadata)
        self.print(data)

    @abstractmethod
    def format_list(self, items: list[str], title: str | None = None) -> str:
        """Format a list of items.

        Args:
            items: List of strings to format.
            title: Optional title.

        Returns:
            Formatted string representation.
        """
        pass

    @abstractmethod
    def format_table(
        self,
        rows: list[dict[str, Any]],
        columns: list[str] | None = None,
        title: str | None = None,
    ) -> str:
        """Format data as a table.

        Args:
            rows: List of row dictionaries.
            columns: Column names (inferred from rows if None).
            title: Optional title.

        Returns:
            Formatted string representation.
        """
        pass

    @abstractmethod
    def format_code(
        self,
        code: str,
        language: str | None = None,
        title: str | None = None,
    ) -> str:
        """Format code with optional syntax highlighting.

        Args:
            code: The code to format.
            language: Programming language for highlighting.
            title: Optional title.

        Returns:
            Formatted string representation.
        """
        pass
