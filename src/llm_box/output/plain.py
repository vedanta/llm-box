"""Plain text output formatter."""

from typing import Any, TextIO

from llm_box.output.base import OutputData, OutputFormat, OutputFormatter


class PlainFormatter(OutputFormatter):
    """Plain text output formatter.

    Produces simple, unformatted text output suitable for
    piping to other commands or basic terminal display.
    """

    def __init__(
        self,
        stream: TextIO | None = None,
        error_stream: TextIO | None = None,
        verbose: bool = False,
        show_metadata: bool = False,
    ) -> None:
        """Initialize plain formatter.

        Args:
            stream: Output stream.
            error_stream: Error stream.
            verbose: Whether to show verbose output.
            show_metadata: Whether to show metadata in output.
        """
        super().__init__(stream, error_stream, verbose)
        self._show_metadata = show_metadata

    @property
    def format_type(self) -> OutputFormat:
        return OutputFormat.PLAIN

    def format(self, data: OutputData) -> str:
        """Format output data as plain text."""
        lines: list[str] = []

        # Add title if present
        if data.title:
            lines.append(data.title)
            lines.append("-" * len(data.title))
            lines.append("")

        # Handle error case
        if not data.success and data.error:
            lines.append(f"Error: {data.error}")
            return "\n".join(lines)

        # Format content based on type
        if isinstance(data.content, str):
            lines.append(data.content)
        elif isinstance(data.content, list):
            for item in data.content:
                lines.append(str(item))
        elif isinstance(data.content, dict):
            for key, value in data.content.items():
                lines.append(f"{key}: {value}")

        # Add metadata if verbose or show_metadata is enabled
        if (self._verbose or self._show_metadata) and data.metadata:
            lines.append("")
            lines.append("---")
            for key, value in data.metadata.items():
                lines.append(f"{key}: {value}")

        # Add cached indicator if verbose
        if self._verbose and data.cached:
            lines.append("(cached)")

        return "\n".join(lines)

    def format_list(self, items: list[str], title: str | None = None) -> str:
        """Format a list of items as plain text."""
        lines: list[str] = []

        if title:
            lines.append(title)
            lines.append("-" * len(title))
            lines.append("")

        for item in items:
            lines.append(f"  {item}")

        return "\n".join(lines)

    def format_table(
        self,
        rows: list[dict[str, Any]],
        columns: list[str] | None = None,
        title: str | None = None,
    ) -> str:
        """Format data as a plain text table."""
        if not rows:
            return ""

        # Determine columns
        if columns is None:
            columns = list(rows[0].keys())

        # Calculate column widths
        widths: dict[str, int] = {}
        for col in columns:
            widths[col] = len(col)
            for row in rows:
                value = str(row.get(col, ""))
                widths[col] = max(widths[col], len(value))

        lines: list[str] = []

        # Add title
        if title:
            lines.append(title)
            lines.append("")

        # Header row
        header = "  ".join(col.ljust(widths[col]) for col in columns)
        lines.append(header)
        lines.append("  ".join("-" * widths[col] for col in columns))

        # Data rows
        for row in rows:
            row_str = "  ".join(
                str(row.get(col, "")).ljust(widths[col]) for col in columns
            )
            lines.append(row_str)

        return "\n".join(lines)

    def format_code(
        self,
        code: str,
        language: str | None = None,
        title: str | None = None,
    ) -> str:
        """Format code as plain text (no highlighting)."""
        lines: list[str] = []

        if title:
            lines.append(title)
            lines.append("-" * len(title))
            lines.append("")

        # Add language hint if provided
        if language and self._verbose:
            lines.append(f"[{language}]")

        lines.append(code)

        return "\n".join(lines)
