"""Shortcut entry points for standalone commands.

These entry points allow commands to be invoked directly as
standalone executables (llm-ls, llm-cat, etc.) instead of
subcommands (llm-box ls, llm-box cat).

The shortcuts are defined in pyproject.toml under [project.scripts]:
    llm-ls = "llm_box.cli.shortcuts:ls_main"
    llm-cat = "llm_box.cli.shortcuts:cat_main"
    ...
"""

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
    typer.echo("llm-ask command not yet implemented (Coming in Milestone 8)")
    raise typer.Exit(1)


def tldr_main() -> None:
    """Entry point for llm-tldr command."""
    typer.echo("llm-tldr command not yet implemented (Coming in Milestone 8)")
    raise typer.Exit(1)


def why_main() -> None:
    """Entry point for llm-why command."""
    typer.echo("llm-why command not yet implemented (Coming in Milestone 8)")
    raise typer.Exit(1)


def run_main() -> None:
    """Entry point for llm-run command."""
    typer.echo("llm-run command not yet implemented (Coming in Milestone 8)")
    raise typer.Exit(1)


def fix_main() -> None:
    """Entry point for llm-fix command."""
    typer.echo("llm-fix command not yet implemented (Coming in Milestone 8)")
    raise typer.Exit(1)


def doc_main() -> None:
    """Entry point for llm-doc command."""
    typer.echo("llm-doc command not yet implemented (Coming in Milestone 8)")
    raise typer.Exit(1)


def plan_main() -> None:
    """Entry point for llm-plan command."""
    typer.echo("llm-plan command not yet implemented (Coming in Milestone 8)")
    raise typer.Exit(1)
