"""Rich terminal output formatter."""

from typing import Any, TextIO

from llm_box.output.base import OutputData, OutputFormat, OutputFormatter


class RichFormatter(OutputFormatter):
    """Rich terminal output formatter.

    Produces beautifully formatted terminal output using the Rich library
    with syntax highlighting, tables, panels, and more.
    """

    def __init__(
        self,
        stream: TextIO | None = None,
        error_stream: TextIO | None = None,
        verbose: bool = False,
        theme: str = "monokai",
        width: int | None = None,
    ) -> None:
        """Initialize rich formatter.

        Args:
            stream: Output stream.
            error_stream: Error stream.
            verbose: Whether to show verbose output.
            theme: Syntax highlighting theme.
            width: Console width (None for auto-detect).
        """
        super().__init__(stream, error_stream, verbose)
        self._theme = theme
        self._width = width

        # Lazy initialization of Rich components
        self._console: Any = None
        self._error_console: Any = None

    def _get_console(self) -> Any:
        """Lazily initialize and return the Rich console."""
        if self._console is None:
            try:
                from rich.console import Console

                self._console = Console(
                    file=self._stream,
                    width=self._width,
                    force_terminal=True,
                )
            except ImportError:
                # Fallback: return None, will use plain text
                return None
        return self._console

    def _get_error_console(self) -> Any:
        """Lazily initialize and return the error console."""
        if self._error_console is None:
            try:
                from rich.console import Console

                self._error_console = Console(
                    file=self._error_stream,
                    width=self._width,
                    stderr=True,
                    force_terminal=True,
                )
            except ImportError:
                return None
        return self._error_console

    @property
    def format_type(self) -> OutputFormat:
        return OutputFormat.RICH

    def format(self, data: OutputData) -> str:
        """Format output data with Rich formatting."""
        console = self._get_console()

        # If Rich is not available, fall back to plain text
        if console is None:
            return self._format_plain(data)

        from io import StringIO

        from rich.console import Console
        from rich.markdown import Markdown
        from rich.panel import Panel
        from rich.text import Text

        # Capture output to string
        string_io = StringIO()
        temp_console = Console(file=string_io, width=self._width, force_terminal=False)

        # Handle error case
        if not data.success and data.error:
            error_text = Text(f"Error: {data.error}", style="bold red")
            if data.title:
                temp_console.print(
                    Panel(error_text, title=data.title, border_style="red")
                )
            else:
                temp_console.print(error_text)
            return string_io.getvalue().rstrip()

        # Format content based on type
        content_renderable: Any

        if isinstance(data.content, str):
            # Check if content looks like markdown
            if self._looks_like_markdown(data.content):
                content_renderable = Markdown(data.content)
            else:
                content_renderable = Text(data.content)
        elif isinstance(data.content, list):
            # Format as a list
            from rich.table import Table

            table = Table(show_header=False, box=None)
            table.add_column("Item")
            for item in data.content:
                table.add_row(str(item))
            content_renderable = table
        elif isinstance(data.content, dict):
            # Format as key-value pairs
            from rich.table import Table

            table = Table(show_header=False, box=None, padding=(0, 1))
            table.add_column("Key", style="bold cyan")
            table.add_column("Value")
            for key, value in data.content.items():
                table.add_row(str(key), str(value))
            content_renderable = table
        else:
            content_renderable = Text(str(data.content))

        # Wrap in panel if there's a title
        if data.title:
            subtitle = None
            if data.cached:
                subtitle = "[dim](cached)[/dim]"
            temp_console.print(
                Panel(content_renderable, title=data.title, subtitle=subtitle)
            )
        else:
            temp_console.print(content_renderable)
            if data.cached and self._verbose:
                temp_console.print("[dim](cached)[/dim]")

        # Add metadata if verbose
        if self._verbose and data.metadata:
            temp_console.print()
            from rich.table import Table

            meta_table = Table(title="Metadata", show_header=False, box=None)
            meta_table.add_column("Key", style="dim")
            meta_table.add_column("Value", style="dim")
            for key, value in data.metadata.items():
                meta_table.add_row(str(key), str(value))
            temp_console.print(meta_table)

        return string_io.getvalue().rstrip()

    def _format_plain(self, data: OutputData) -> str:
        """Fallback plain text formatting when Rich is unavailable."""
        lines: list[str] = []

        if data.title:
            lines.append(data.title)
            lines.append("-" * len(data.title))
            lines.append("")

        if not data.success and data.error:
            lines.append(f"Error: {data.error}")
            return "\n".join(lines)

        if isinstance(data.content, str):
            lines.append(data.content)
        elif isinstance(data.content, list):
            for item in data.content:
                lines.append(f"  {item}")
        elif isinstance(data.content, dict):
            for key, value in data.content.items():
                lines.append(f"{key}: {value}")

        return "\n".join(lines)

    def _looks_like_markdown(self, text: str) -> bool:
        """Check if text appears to be markdown."""
        markdown_indicators = [
            "# ",  # Headers
            "## ",
            "### ",
            "```",  # Code blocks
            "- ",  # Lists
            "* ",
            "1. ",  # Numbered lists
            "**",  # Bold
            "__",
            "[",  # Links
            "> ",  # Blockquotes
        ]
        return any(indicator in text for indicator in markdown_indicators)

    def format_list(self, items: list[str], title: str | None = None) -> str:
        """Format a list with Rich formatting."""
        console = self._get_console()

        if console is None:
            lines = []
            if title:
                lines.append(title)
                lines.append("-" * len(title))
                lines.append("")
            for item in items:
                lines.append(f"  • {item}")
            return "\n".join(lines)

        from io import StringIO

        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table

        string_io = StringIO()
        temp_console = Console(file=string_io, width=self._width, force_terminal=False)

        table = Table(show_header=False, box=None)
        table.add_column("Item")
        for item in items:
            table.add_row(f"• {item}")

        if title:
            temp_console.print(Panel(table, title=title))
        else:
            temp_console.print(table)

        return string_io.getvalue().rstrip()

    def format_table(
        self,
        rows: list[dict[str, Any]],
        columns: list[str] | None = None,
        title: str | None = None,
    ) -> str:
        """Format data as a Rich table."""
        if not rows:
            return ""

        console = self._get_console()

        # Determine columns
        if columns is None:
            columns = list(rows[0].keys())

        if console is None:
            # Fallback to plain text table
            lines: list[str] = []
            if title:
                lines.append(title)
                lines.append("")
            header = "  ".join(col.ljust(15) for col in columns)
            lines.append(header)
            lines.append("-" * len(header))
            for row in rows:
                row_str = "  ".join(str(row.get(col, "")).ljust(15) for col in columns)
                lines.append(row_str)
            return "\n".join(lines)

        from io import StringIO

        from rich.console import Console
        from rich.table import Table

        string_io = StringIO()
        temp_console = Console(file=string_io, width=self._width, force_terminal=False)

        table = Table(title=title)

        # Add columns
        for col in columns:
            table.add_column(col, style="cyan")

        # Add rows
        for row in rows:
            table.add_row(*[str(row.get(col, "")) for col in columns])

        temp_console.print(table)
        return string_io.getvalue().rstrip()

    def format_code(
        self,
        code: str,
        language: str | None = None,
        title: str | None = None,
    ) -> str:
        """Format code with Rich syntax highlighting."""
        console = self._get_console()

        if console is None:
            lines = []
            if title:
                lines.append(title)
                lines.append("-" * len(title))
                lines.append("")
            if language:
                lines.append(f"```{language}")
            lines.append(code)
            if language:
                lines.append("```")
            return "\n".join(lines)

        from io import StringIO

        from rich.console import Console
        from rich.panel import Panel
        from rich.syntax import Syntax

        string_io = StringIO()
        temp_console = Console(file=string_io, width=self._width, force_terminal=False)

        syntax = Syntax(
            code,
            language or "text",
            theme=self._theme,
            line_numbers=True,
            word_wrap=True,
        )

        if title:
            temp_console.print(Panel(syntax, title=title))
        else:
            temp_console.print(syntax)

        return string_io.getvalue().rstrip()

    def print(self, data: OutputData) -> None:
        """Print output using Rich console directly."""
        console = self._get_console() if data.success else self._get_error_console()

        if console is None:
            # Fallback to standard print
            super().print(data)
            return

        # For Rich, we format and then print directly
        formatted = self.format(data)
        console.print(formatted, highlight=False)
