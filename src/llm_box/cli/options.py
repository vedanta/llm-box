"""Shared CLI options for llm-box commands.

This module provides reusable Typer options and option groups
that are shared across multiple commands.
"""

from enum import Enum
from typing import Annotated

import typer

from llm_box.output.base import OutputFormat
from llm_box.providers.base import ProviderType


class FormatChoice(str, Enum):
    """Output format choices for CLI."""

    PLAIN = "plain"
    JSON = "json"
    RICH = "rich"


# Type aliases for common CLI options
FormatOption = Annotated[
    FormatChoice | None,
    typer.Option(
        "--format",
        "-f",
        help="Output format (plain, json, rich). Defaults to config setting.",
        case_sensitive=False,
    ),
]

NoCacheOption = Annotated[
    bool,
    typer.Option(
        "--no-cache",
        help="Bypass cache for this request.",
    ),
]

ProviderOption = Annotated[
    str | None,
    typer.Option(
        "--provider",
        "-p",
        help="LLM provider to use (ollama, openai, anthropic).",
    ),
]

ModelOption = Annotated[
    str | None,
    typer.Option(
        "--model",
        "-m",
        help="Model to use. Defaults to provider's default model.",
    ),
]

VerboseOption = Annotated[
    bool,
    typer.Option(
        "--verbose",
        "-v",
        help="Show verbose output including metadata.",
    ),
]


def get_output_format(
    format_choice: FormatChoice | None, default: str = "rich"
) -> OutputFormat:
    """Convert CLI format choice to OutputFormat.

    Args:
        format_choice: CLI format choice or None.
        default: Default format if none specified.

    Returns:
        OutputFormat enum value.
    """
    if format_choice is None:
        return OutputFormat(default)
    return OutputFormat(format_choice.value)


def get_provider_type(provider: str | None, default: str = "ollama") -> ProviderType:
    """Convert CLI provider string to ProviderType.

    Args:
        provider: Provider name string or None.
        default: Default provider if none specified.

    Returns:
        ProviderType enum value.

    Raises:
        typer.BadParameter: If provider name is invalid.
    """
    provider_str = provider or default
    try:
        return ProviderType(provider_str.lower())
    except ValueError as e:
        valid = [p.value for p in ProviderType]
        raise typer.BadParameter(
            f"Invalid provider '{provider_str}'. Valid options: {', '.join(valid)}"
        ) from e
