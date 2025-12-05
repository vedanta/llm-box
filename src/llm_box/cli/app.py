"""Main CLI application for llm-box."""

from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from llm_box import __version__
from llm_box.cli.context import create_cache, create_context
from llm_box.cli.options import (
    FormatOption,
    ModelOption,
    NoCacheOption,
    ProviderOption,
    VerboseOption,
)

# Import commands to ensure they're registered
from llm_box.commands import CatCommand, CommandRegistry, LsCommand  # noqa: F401
from llm_box.config import get_config

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
) -> None:
    """LLM-powered terminal toolbox."""
    pass


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

    # Registered commands
    console.print("\n[bold]Registered Commands:[/bold]")
    for info in CommandRegistry.get_command_info():
        aliases = f" ({info['aliases']})" if info["aliases"] else ""
        console.print(f"  {info['name']}{aliases}: {info['description']}")


@app.command()
def ls(
    path: str = typer.Argument(".", help="Directory to list."),
    all_files: bool = typer.Option(False, "--all", "-a", help="Include hidden files."),
    pattern: str | None = typer.Option(None, "--pattern", "-g", help="Glob pattern."),
    format: FormatOption = None,
    provider: ProviderOption = None,
    model: ModelOption = None,
    no_cache: NoCacheOption = False,
    verbose: VerboseOption = False,
) -> None:
    """List files with LLM-generated descriptions."""
    try:
        ctx = create_context(
            provider=provider,
            model=model,
            format_choice=format,
            no_cache=no_cache,
            verbose=verbose,
            working_dir=Path(path).resolve().parent,
        )

        cmd = LsCommand()

        # Show spinner while generating descriptions
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task(
                description="Generating descriptions...", total=None
            )
            result = cmd.execute(
                ctx,
                path=path,
                all_files=all_files,
                pattern=pattern,
            )

        if result.success:
            # Format output
            data = result.data
            if isinstance(data, dict) and "files" in data:
                _print_ls_output(data, ctx.formatter, verbose)
            else:
                ctx.formatter.print_content(str(data), cached=result.cached)
        else:
            err_console.print(f"[red]Error:[/red] {result.error}")
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


def _print_ls_output(data: dict[str, Any], formatter: Any, verbose: bool) -> None:
    """Print ls command output in a formatted way."""
    files = data.get("files", [])
    count = data.get("count", 0)

    if count == 0:
        console.print("[dim]No files found[/dim]")
        return

    # Print as a table
    rows = []
    for f in files:
        file_type = f.get("type", "file")
        name = f.get("name", "")
        desc = f.get("description", "")

        # Add type indicator
        if file_type == "directory":
            type_icon = "📁"
        elif file_type in ("Python", "JavaScript", "TypeScript", "Go", "Rust"):
            type_icon = "📄"
        else:
            type_icon = "📃"

        cached_marker = " [dim](cached)[/dim]" if f.get("cached") and verbose else ""

        rows.append(
            {
                "": type_icon,
                "Name": name,
                "Description": desc + cached_marker,
            }
        )

    formatted = formatter.format_table(rows, columns=["", "Name", "Description"])
    console.print(formatted)
    console.print(f"\n[dim]{count} items[/dim]")


@app.command()
def cat(
    file: str = typer.Argument(..., help="File to explain."),
    brief: bool = typer.Option(False, "--brief", "-b", help="Brief summary only."),
    focus: str | None = typer.Option(None, "--focus", help="Focus on specific aspect."),
    format: FormatOption = None,
    provider: ProviderOption = None,
    model: ModelOption = None,
    no_cache: NoCacheOption = False,
    verbose: VerboseOption = False,
) -> None:
    """Explain file contents using LLM."""
    try:
        ctx = create_context(
            provider=provider,
            model=model,
            format_choice=format,
            no_cache=no_cache,
            verbose=verbose,
            working_dir=Path(file).resolve().parent,
        )

        cmd = CatCommand()
        file_name = Path(file).name

        # Show spinner while generating explanation
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task(
                description=f"Analyzing {file_name}...", total=None
            )
            result = cmd.execute(
                ctx,
                file=file,
                brief=brief,
                focus=focus,
            )

        if result.success:
            # Get file info from metadata
            result_file = Path(result.metadata.get("file", file)).name
            cached_note = " (cached)" if result.cached else ""

            # Print with title
            ctx.formatter.print_content(
                result.data,
                title=f"{result_file}{cached_note}",
                cached=result.cached,
            )
        else:
            err_console.print(f"[red]Error:[/red] {result.error}")
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        err_console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from None


@app.command()
def find(
    query: str = typer.Argument(..., help="Search query."),
    path: str = typer.Option(".", "--path", "-p", help="Directory to search."),
    mode: str = typer.Option("combined", "--mode", "-m", help="Search mode."),
    top: int = typer.Option(10, "--top", "-n", help="Number of results."),
) -> None:
    """Search files using semantic and fuzzy matching."""
    console.print(f"[dim]find command not yet implemented (query: {query})[/dim]")
    console.print("[dim]Coming in Milestone 7 (Search System)[/dim]")


# Cache subcommand group
cache_app = typer.Typer(help="Manage cache.")
app.add_typer(cache_app, name="cache")


@cache_app.command("stats")
def cache_stats() -> None:
    """Show cache statistics."""
    config = get_config()
    cache = create_cache(config)

    stats = cache.stats()

    console.print("[bold]Cache Statistics[/bold]\n")
    console.print(f"Enabled: {stats.get('enabled', config.cache.enabled)}")
    console.print(f"Total entries: {cache.count()}")
    console.print(f"Cache hits: {stats.get('hits', 0)}")
    console.print(f"Cache misses: {stats.get('misses', 0)}")

    hit_rate = stats.get("hit_rate")
    if hit_rate is not None:
        console.print(f"Hit rate: {hit_rate:.1%}")


@cache_app.command("clear")
def cache_clear(
    command_name: str | None = typer.Option(
        None, "--command", "-c", help="Clear specific command cache."
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation."),
) -> None:
    """Clear cache entries."""
    config = get_config()
    cache = create_cache(config)

    if not force:
        if command_name:
            msg = f"Clear cache for command '{command_name}'?"
        else:
            msg = "Clear all cache entries?"

        confirm = typer.confirm(msg)
        if not confirm:
            console.print("[dim]Cancelled[/dim]")
            return

    # Note: command-specific clearing would need DuckDBCache method
    # For now, clear all entries
    if command_name:
        console.print(
            f"[dim]Filtering by command '{command_name}' not yet implemented[/dim]"
        )
    cleared = cache.clear()
    console.print(f"Cleared {cleared} cache entries")


@app.command()
def commands() -> None:
    """List all available commands."""
    info_list = CommandRegistry.get_command_info()

    if not info_list:
        console.print("[dim]No commands registered[/dim]")
        return

    console.print("[bold]Available Commands[/bold]\n")
    for info in info_list:
        name = info["name"]
        desc = info["description"]
        aliases = info["aliases"]

        console.print(f"  [cyan]{name}[/cyan]")
        if aliases:
            console.print(f"    Aliases: {aliases}")
        console.print(f"    {desc}")
        console.print()


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
