"""Output formatting (rich, plain, JSON).

This module provides output formatters for displaying LLM responses
in different formats suitable for various use cases.

Usage:
    from llm_box.output import RichFormatter, OutputData

    # Create a formatter
    formatter = RichFormatter()

    # Format and print output
    data = OutputData.from_content("Hello, world!", title="Greeting")
    formatter.print(data)

    # Or format specific content types
    print(formatter.format_code("def foo(): pass", language="python"))
    print(formatter.format_table([{"name": "Alice", "age": 30}]))
"""

from typing import Any

from llm_box.output.base import OutputData, OutputFormat, OutputFormatter
from llm_box.output.json_fmt import JSONFormatter, JSONLinesFormatter
from llm_box.output.plain import PlainFormatter
from llm_box.output.rich_fmt import RichFormatter

__all__ = [
    # Base classes
    "OutputFormatter",
    "OutputData",
    "OutputFormat",
    # Formatters
    "PlainFormatter",
    "JSONFormatter",
    "JSONLinesFormatter",
    "RichFormatter",
]


def get_formatter(
    format_type: OutputFormat | str,
    verbose: bool = False,
    **kwargs: Any,
) -> OutputFormatter:
    """Get a formatter instance by format type.

    Args:
        format_type: The output format to use.
        verbose: Whether to enable verbose output.
        **kwargs: Additional formatter-specific options.

    Returns:
        An OutputFormatter instance.

    Raises:
        ValueError: If format_type is not recognized.
    """
    if isinstance(format_type, str):
        format_type = OutputFormat(format_type.lower())

    formatters: dict[OutputFormat, type[OutputFormatter]] = {
        OutputFormat.PLAIN: PlainFormatter,
        OutputFormat.JSON: JSONFormatter,
        OutputFormat.RICH: RichFormatter,
    }

    formatter_class = formatters.get(format_type)
    if formatter_class is None:
        raise ValueError(f"Unknown format type: {format_type}")

    return formatter_class(verbose=verbose, **kwargs)
