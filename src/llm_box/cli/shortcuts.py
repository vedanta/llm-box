"""Shortcut entry points for standalone commands.

These entry points allow commands to be invoked directly as
standalone executables (llm-ls, llm-cat, etc.) instead of
subcommands (llm-box ls, llm-box cat).

The shortcuts are defined in pyproject.toml under [project.scripts]:
    llm-ls = "llm_box.cli.shortcuts:ls_main"
    llm-cat = "llm_box.cli.shortcuts:cat_main"
    llm-find = "llm_box.cli.shortcuts:find_main"
"""

import sys


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
