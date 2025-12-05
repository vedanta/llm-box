"""Shortcut entry points for standalone commands."""

import sys

import typer


def ls_main() -> None:
    """Entry point for llm-ls command."""
    from llm_box.cli.app import app

    # Rewrite sys.argv to inject 'ls' command
    sys.argv = ["llm-box", "ls"] + sys.argv[1:]
    app()


def cat_main() -> None:
    """Entry point for llm-cat command."""
    from llm_box.cli.app import app

    sys.argv = ["llm-box", "cat"] + sys.argv[1:]
    app()


def find_main() -> None:
    """Entry point for llm-find command."""
    from llm_box.cli.app import app

    sys.argv = ["llm-box", "find"] + sys.argv[1:]
    app()


def ask_main() -> None:
    """Entry point for llm-ask command."""
    # ask command not yet implemented
    typer.echo("llm-ask command not yet implemented (Coming in Milestone 7)")
    raise typer.Exit(1)
