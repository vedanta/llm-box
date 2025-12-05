"""Main CLI application for llm-box."""

import typer
from rich.console import Console

from llm_box import __version__
from llm_box.config import get_config
from llm_box.utils.logging import setup_logging

# Create Typer app
app = typer.Typer(
    name="llm-box",
    help="LLM-powered terminal toolbox",
    add_completion=True,
    no_args_is_help=True,
)

# Rich console for output
console = Console()
err_console = Console(stderr=True)


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"llm-box version {__version__}")
        raise typer.Exit()


@app.callback()
def main_callback(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output.",
    ),
) -> None:
    """LLM-powered terminal toolbox."""
    # Setup logging based on verbosity
    config = get_config()
    level = "DEBUG" if verbose else config.logging.level
    setup_logging(
        level=level,
        log_file=config.logging.file,
        json_format=config.logging.json_format,
    )


@app.command()
def config_cmd(
    show_path: bool = typer.Option(
        False,
        "--path",
        "-p",
        help="Show config file path.",
    ),
) -> None:
    """Show current configuration."""
    from llm_box.config.defaults import get_config_path

    if show_path:
        console.print(str(get_config_path()))
        return

    config = get_config()
    console.print("[bold]llm-box configuration[/bold]\n")
    console.print(f"Config file: {get_config_path()}")
    console.print(f"Default provider: {config.default_provider}")
    console.print(f"Cache enabled: {config.cache.enabled}")
    console.print(f"Output format: {config.output.default_format}")

    # Provider status
    console.print("\n[bold]Providers:[/bold]")
    console.print(
        f"  Ollama: {'enabled' if config.providers.ollama.enabled else 'disabled'}"
    )
    console.print(
        f"  OpenAI: {'enabled' if config.providers.openai.enabled else 'disabled'}"
    )
    console.print(
        f"  Anthropic: {'enabled' if config.providers.anthropic.enabled else 'disabled'}"
    )


# Placeholder commands - to be implemented in later milestones
@app.command()
def ls(
    path: str = typer.Argument(".", help="Directory to list."),
    all_files: bool = typer.Option(False, "--all", "-a", help="Include hidden files."),
    format: str | None = typer.Option(None, "--format", "-f", help="Output format."),
    no_cache: bool = typer.Option(False, "--no-cache", help="Bypass cache."),
) -> None:
    """List files with LLM-generated descriptions."""
    console.print(f"[dim]ls command not yet implemented (path: {path})[/dim]")
    console.print("[dim]Coming in Milestone 5[/dim]")


@app.command()
def cat(
    file: str = typer.Argument(..., help="File to summarize."),
    format: str | None = typer.Option(None, "--format", "-f", help="Output format."),
    no_cache: bool = typer.Option(False, "--no-cache", help="Bypass cache."),
) -> None:
    """Summarize file contents using LLM."""
    console.print(f"[dim]cat command not yet implemented (file: {file})[/dim]")
    console.print("[dim]Coming in Milestone 5[/dim]")


@app.command()
def find(
    query: str = typer.Argument(..., help="Search query."),
    path: str = typer.Option(".", "--path", "-p", help="Directory to search."),
    mode: str = typer.Option("combined", "--mode", "-m", help="Search mode."),
    top: int = typer.Option(10, "--top", "-n", help="Number of results."),
) -> None:
    """Search files using semantic and fuzzy matching."""
    console.print(f"[dim]find command not yet implemented (query: {query})[/dim]")
    console.print("[dim]Coming in Milestone 6[/dim]")


# Cache subcommand group
cache_app = typer.Typer(help="Manage cache.")
app.add_typer(cache_app, name="cache")


@cache_app.command("stats")
def cache_stats() -> None:
    """Show cache statistics."""
    console.print("[dim]cache stats not yet implemented[/dim]")
    console.print("[dim]Coming in Milestone 3[/dim]")


@cache_app.command("clear")
def cache_clear(
    command: str | None = typer.Option(
        None, "--command", "-c", help="Clear specific command cache."
    ),
) -> None:
    """Clear cache entries."""
    console.print("[dim]cache clear not yet implemented[/dim]")
    console.print("[dim]Coming in Milestone 3[/dim]")


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
