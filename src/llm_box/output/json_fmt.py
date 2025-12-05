"""JSON output formatter."""

import json
from typing import Any, TextIO

from llm_box.output.base import OutputData, OutputFormat, OutputFormatter


class JSONFormatter(OutputFormatter):
    """JSON output formatter.

    Produces structured JSON output suitable for programmatic
    consumption and integration with other tools.
    """

    def __init__(
        self,
        stream: TextIO | None = None,
        error_stream: TextIO | None = None,
        verbose: bool = False,
        indent: int | None = 2,
        ensure_ascii: bool = False,
    ) -> None:
        """Initialize JSON formatter.

        Args:
            stream: Output stream.
            error_stream: Error stream.
            verbose: Whether to show verbose output.
            indent: JSON indentation (None for compact).
            ensure_ascii: Whether to escape non-ASCII characters.
        """
        super().__init__(stream, error_stream, verbose)
        self._indent = indent
        self._ensure_ascii = ensure_ascii

    @property
    def format_type(self) -> OutputFormat:
        return OutputFormat.JSON

    def _to_json(self, data: Any) -> str:
        """Convert data to JSON string."""
        return json.dumps(
            data,
            indent=self._indent,
            ensure_ascii=self._ensure_ascii,
            default=str,  # Handle non-serializable types
        )

    def format(self, data: OutputData) -> str:
        """Format output data as JSON."""
        output: dict[str, Any] = {
            "success": data.success,
        }

        if data.title:
            output["title"] = data.title

        if data.success:
            output["content"] = data.content
            if data.cached:
                output["cached"] = True
        else:
            output["error"] = data.error

        # Include metadata if verbose or if there's metadata
        if self._verbose and data.metadata:
            output["metadata"] = data.metadata
        elif data.metadata:
            # Always include certain important metadata
            important_keys = ["tokens_used", "model", "provider", "duration_ms"]
            filtered = {k: v for k, v in data.metadata.items() if k in important_keys}
            if filtered:
                output["metadata"] = filtered

        return self._to_json(output)

    def format_list(self, items: list[str], title: str | None = None) -> str:
        """Format a list of items as JSON."""
        output: dict[str, Any] = {
            "success": True,
            "items": items,
            "count": len(items),
        }
        if title:
            output["title"] = title
        return self._to_json(output)

    def format_table(
        self,
        rows: list[dict[str, Any]],
        columns: list[str] | None = None,
        title: str | None = None,
    ) -> str:
        """Format data as JSON table."""
        output: dict[str, Any] = {
            "success": True,
            "rows": rows,
            "count": len(rows),
        }
        if title:
            output["title"] = title
        if columns:
            output["columns"] = columns
        return self._to_json(output)

    def format_code(
        self,
        code: str,
        language: str | None = None,
        title: str | None = None,
    ) -> str:
        """Format code as JSON."""
        output: dict[str, Any] = {
            "success": True,
            "code": code,
        }
        if language:
            output["language"] = language
        if title:
            output["title"] = title
        return self._to_json(output)


class JSONLinesFormatter(JSONFormatter):
    """JSON Lines (JSONL) output formatter.

    Produces newline-delimited JSON for streaming output,
    where each line is a valid JSON object.
    """

    def __init__(
        self,
        stream: TextIO | None = None,
        error_stream: TextIO | None = None,
        verbose: bool = False,
    ) -> None:
        """Initialize JSONL formatter.

        Args:
            stream: Output stream.
            error_stream: Error stream.
            verbose: Whether to show verbose output.
        """
        # JSONL uses compact JSON (no indentation)
        super().__init__(stream, error_stream, verbose, indent=None)

    def format_list(self, items: list[str], title: str | None = None) -> str:
        """Format each list item as a separate JSON line."""
        lines = []
        for item in items:
            line_data = {"item": item}
            if title:
                line_data["title"] = title
            lines.append(self._to_json(line_data))
        return "\n".join(lines)

    def format_table(
        self,
        rows: list[dict[str, Any]],
        columns: list[str] | None = None,
        title: str | None = None,
    ) -> str:
        """Format each table row as a separate JSON line."""
        lines = []
        for row in rows:
            line_data = dict(row)
            if title:
                line_data["_title"] = title
            lines.append(self._to_json(line_data))
        return "\n".join(lines)
