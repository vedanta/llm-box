"""CLI layer for llm-box.

This module provides the command-line interface for llm-box,
built on Typer with Rich formatting support.

Usage:
    # Run the main CLI
    llm-box --help

    # Use shortcut commands
    llm-ls .
    llm-cat file.py
"""

from llm_box.cli.app import app, main
from llm_box.cli.context import create_context
from llm_box.cli.options import (
    FormatChoice,
    FormatOption,
    ModelOption,
    NoCacheOption,
    ProviderOption,
    VerboseOption,
)

__all__ = [
    # App
    "app",
    "main",
    # Context
    "create_context",
    # Options
    "FormatChoice",
    "FormatOption",
    "ModelOption",
    "NoCacheOption",
    "ProviderOption",
    "VerboseOption",
]
