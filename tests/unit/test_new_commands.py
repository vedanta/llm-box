"""Tests for new commands (tldr, why, ask, doc)."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from llm_box.commands import (
    AskCommand,
    CommandContext,
    DocCommand,
    TldrCommand,
    WhyCommand,
)
from llm_box.config.schema import LLMBoxConfig
from llm_box.output.base import OutputFormatter
from llm_box.providers import MockProvider
from llm_box.providers.base import LLMBoxProvider


@pytest.fixture
def mock_provider() -> MockProvider:
    """Create a mock provider for testing."""
    return MockProvider(
        responses={"": "This is a mock LLM response for testing purposes."}
    )


@pytest.fixture
def mock_formatter() -> MagicMock:
    """Create a mock formatter."""
    formatter = MagicMock(spec=OutputFormatter)
    return formatter


@pytest.fixture
def mock_config() -> LLMBoxConfig:
    """Create a default config."""
    return LLMBoxConfig()


@pytest.fixture
def command_context(
    mock_provider: LLMBoxProvider,
    mock_formatter: MagicMock,
    mock_config: LLMBoxConfig,
) -> CommandContext:
    """Create a command context with mock provider."""
    from llm_box.cache import DuckDBCache

    cache = DuckDBCache(db_path=None)  # In-memory
    return CommandContext(
        provider=mock_provider,
        cache=cache,
        formatter=mock_formatter,
        config=mock_config,
        use_cache=False,
        verbose=False,
    )


@pytest.fixture
def temp_file() -> Path:
    """Create a temporary test file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("""
def hello_world():
    \"\"\"Print hello world.\"\"\"
    print("Hello, World!")

class Calculator:
    \"\"\"A simple calculator class.\"\"\"

    def add(self, a: int, b: int) -> int:
        \"\"\"Add two numbers.\"\"\"
        return a + b

    def subtract(self, a: int, b: int) -> int:
        \"\"\"Subtract b from a.\"\"\"
        return a - b
""")
        return Path(f.name)


@pytest.fixture
def temp_dir() -> Path:
    """Create a temporary directory with files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create a README
        (tmpdir_path / "README.md").write_text("# Test Project\n\nA test project for unit tests.")

        # Create some Python files
        (tmpdir_path / "main.py").write_text("print('main')")
        (tmpdir_path / "utils.py").write_text("def util(): pass")

        yield tmpdir_path


class TestTldrCommand:
    """Tests for TldrCommand."""

    def test_command_properties(self) -> None:
        """Test command properties."""
        cmd = TldrCommand()
        assert cmd.name == "tldr"
        assert "summary" in cmd.aliases or "summarize" in cmd.aliases
        assert "summarize" in cmd.description.lower() or "tldr" in cmd.description.lower()

    def test_execute_no_file(self, command_context: CommandContext) -> None:
        """Test execution without file argument."""
        cmd = TldrCommand()
        result = cmd.execute(command_context)
        assert not result.success
        assert "file" in result.error.lower()

    def test_execute_nonexistent_file(self, command_context: CommandContext) -> None:
        """Test execution with nonexistent file."""
        cmd = TldrCommand()
        result = cmd.execute(command_context, file="/nonexistent/path.py")
        assert not result.success
        assert "not exist" in result.error.lower() or "does not exist" in result.error.lower()

    def test_execute_directory(
        self, command_context: CommandContext, temp_dir: Path
    ) -> None:
        """Test execution with directory instead of file."""
        cmd = TldrCommand()
        result = cmd.execute(command_context, file=str(temp_dir))
        assert not result.success
        assert "directory" in result.error.lower()

    def test_execute_success(
        self, command_context: CommandContext, temp_file: Path
    ) -> None:
        """Test successful execution."""
        cmd = TldrCommand()
        result = cmd.execute(command_context, file=str(temp_file))
        assert result.success
        assert result.data is not None
        temp_file.unlink()  # Clean up

    def test_execute_with_format_options(
        self, command_context: CommandContext, temp_file: Path
    ) -> None:
        """Test execution with different format options."""
        cmd = TldrCommand()

        for fmt in ["bullets", "paragraph", "oneline"]:
            result = cmd.execute(
                command_context, file=str(temp_file), format=fmt, lines=3
            )
            assert result.success

        temp_file.unlink()


class TestWhyCommand:
    """Tests for WhyCommand."""

    def test_command_properties(self) -> None:
        """Test command properties."""
        cmd = WhyCommand()
        assert cmd.name == "why"
        assert "purpose" in cmd.aliases or "reason" in cmd.aliases
        assert "why" in cmd.description.lower() or "purpose" in cmd.description.lower()

    def test_execute_no_path(self, command_context: CommandContext) -> None:
        """Test execution without path argument."""
        cmd = WhyCommand()
        result = cmd.execute(command_context)
        assert not result.success
        assert "path" in result.error.lower()

    def test_execute_nonexistent_path(self, command_context: CommandContext) -> None:
        """Test execution with nonexistent path."""
        cmd = WhyCommand()
        result = cmd.execute(command_context, path="/nonexistent/path")
        assert not result.success
        assert "not exist" in result.error.lower() or "does not exist" in result.error.lower()

    def test_execute_file_success(
        self, command_context: CommandContext, temp_file: Path
    ) -> None:
        """Test successful execution with a file."""
        cmd = WhyCommand()
        result = cmd.execute(command_context, path=str(temp_file))
        assert result.success
        assert result.data is not None
        temp_file.unlink()

    def test_execute_directory_success(
        self, command_context: CommandContext, temp_dir: Path
    ) -> None:
        """Test successful execution with a directory."""
        cmd = WhyCommand()
        result = cmd.execute(command_context, path=str(temp_dir))
        assert result.success
        assert result.data is not None

    def test_execute_with_deep_option(
        self, command_context: CommandContext, temp_file: Path
    ) -> None:
        """Test execution with deep analysis."""
        cmd = WhyCommand()
        result = cmd.execute(command_context, path=str(temp_file), deep=True)
        assert result.success
        temp_file.unlink()


class TestAskCommand:
    """Tests for AskCommand."""

    def test_command_properties(self) -> None:
        """Test command properties."""
        cmd = AskCommand()
        assert cmd.name == "ask"
        assert "question" in cmd.aliases or "q" in cmd.aliases
        assert "question" in cmd.description.lower() or "ask" in cmd.description.lower()

    def test_execute_no_question(self, command_context: CommandContext) -> None:
        """Test execution without question argument."""
        cmd = AskCommand()
        result = cmd.execute(command_context)
        assert not result.success
        assert "question" in result.error.lower()

    def test_execute_simple_question(self, command_context: CommandContext) -> None:
        """Test execution with a simple question."""
        cmd = AskCommand()
        result = cmd.execute(
            command_context,
            question="What is Python?",
        )
        assert result.success
        assert result.data is not None

    def test_execute_with_file_context(
        self, command_context: CommandContext, temp_file: Path
    ) -> None:
        """Test execution with file context."""
        cmd = AskCommand()
        result = cmd.execute(
            command_context,
            question="What does this code do?",
            file=str(temp_file),
        )
        assert result.success
        temp_file.unlink()

    def test_execute_with_multiple_files(
        self, command_context: CommandContext, temp_dir: Path
    ) -> None:
        """Test execution with multiple files."""
        cmd = AskCommand()
        files = [
            str(temp_dir / "main.py"),
            str(temp_dir / "utils.py"),
        ]
        result = cmd.execute(
            command_context,
            question="What do these files do?",
            files=files,
        )
        assert result.success

    def test_execute_with_extra_context(
        self, command_context: CommandContext
    ) -> None:
        """Test execution with additional context."""
        cmd = AskCommand()
        result = cmd.execute(
            command_context,
            question="How should I implement this?",
            context="This is a web application using Flask.",
        )
        assert result.success


class TestDocCommand:
    """Tests for DocCommand."""

    def test_command_properties(self) -> None:
        """Test command properties."""
        cmd = DocCommand()
        assert cmd.name == "doc"
        assert "document" in cmd.aliases or "docs" in cmd.aliases
        assert "documentation" in cmd.description.lower() or "document" in cmd.description.lower()

    def test_execute_no_file(self, command_context: CommandContext) -> None:
        """Test execution without file argument."""
        cmd = DocCommand()
        result = cmd.execute(command_context)
        assert not result.success
        assert "file" in result.error.lower()

    def test_execute_nonexistent_file(self, command_context: CommandContext) -> None:
        """Test execution with nonexistent file."""
        cmd = DocCommand()
        result = cmd.execute(command_context, file="/nonexistent/path.py")
        assert not result.success
        assert "not exist" in result.error.lower() or "does not exist" in result.error.lower()

    def test_execute_success(
        self, command_context: CommandContext, temp_file: Path
    ) -> None:
        """Test successful execution."""
        cmd = DocCommand()
        result = cmd.execute(command_context, file=str(temp_file))
        assert result.success
        assert result.data is not None
        temp_file.unlink()

    def test_execute_different_styles(
        self, command_context: CommandContext, temp_file: Path
    ) -> None:
        """Test execution with different documentation styles."""
        cmd = DocCommand()

        for style in ["docstring", "readme", "api"]:
            result = cmd.execute(command_context, file=str(temp_file), style=style)
            assert result.success

        temp_file.unlink()

    def test_execute_different_formats(
        self, command_context: CommandContext, temp_file: Path
    ) -> None:
        """Test execution with different output formats."""
        cmd = DocCommand()

        for fmt in ["markdown", "rst", "plain"]:
            result = cmd.execute(command_context, file=str(temp_file), format=fmt)
            assert result.success

        temp_file.unlink()

    def test_execute_without_examples(
        self, command_context: CommandContext, temp_file: Path
    ) -> None:
        """Test execution without examples."""
        cmd = DocCommand()
        result = cmd.execute(
            command_context, file=str(temp_file), include_examples=False
        )
        assert result.success
        temp_file.unlink()


class TestCommandRegistration:
    """Tests for command registration."""

    def _ensure_registered(self) -> None:
        """Ensure commands are registered (for test isolation)."""
        from llm_box.commands import CommandRegistry

        # Re-register if needed (in case test_commands.py cleared the registry)
        if not CommandRegistry.is_registered("tldr"):
            CommandRegistry.register_command(TldrCommand)
        if not CommandRegistry.is_registered("why"):
            CommandRegistry.register_command(WhyCommand)
        if not CommandRegistry.is_registered("ask"):
            CommandRegistry.register_command(AskCommand)
        if not CommandRegistry.is_registered("doc"):
            CommandRegistry.register_command(DocCommand)

    def test_tldr_registered(self) -> None:
        """Test TldrCommand is registered."""
        from llm_box.commands import CommandRegistry

        self._ensure_registered()
        assert CommandRegistry.is_registered("tldr")
        cmd = CommandRegistry.get_instance("tldr")
        assert isinstance(cmd, TldrCommand)

    def test_why_registered(self) -> None:
        """Test WhyCommand is registered."""
        from llm_box.commands import CommandRegistry

        self._ensure_registered()
        assert CommandRegistry.is_registered("why")
        cmd = CommandRegistry.get_instance("why")
        assert isinstance(cmd, WhyCommand)

    def test_ask_registered(self) -> None:
        """Test AskCommand is registered."""
        from llm_box.commands import CommandRegistry

        self._ensure_registered()
        assert CommandRegistry.is_registered("ask")
        cmd = CommandRegistry.get_instance("ask")
        assert isinstance(cmd, AskCommand)

    def test_doc_registered(self) -> None:
        """Test DocCommand is registered."""
        from llm_box.commands import CommandRegistry

        self._ensure_registered()
        assert CommandRegistry.is_registered("doc")
        cmd = CommandRegistry.get_instance("doc")
        assert isinstance(cmd, DocCommand)

    def test_aliases_registered(self) -> None:
        """Test command aliases are registered."""
        from llm_box.commands import CommandRegistry

        self._ensure_registered()

        # tldr aliases
        assert CommandRegistry.is_registered("summary") or CommandRegistry.is_registered("summarize")

        # why aliases
        assert CommandRegistry.is_registered("purpose") or CommandRegistry.is_registered("reason")

        # ask aliases
        assert CommandRegistry.is_registered("question") or CommandRegistry.is_registered("q")

        # doc aliases
        assert CommandRegistry.is_registered("document") or CommandRegistry.is_registered("docs")
