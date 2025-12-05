"""Tests for command pattern infrastructure."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from llm_box.cache.base import Cache
from llm_box.commands.base import BaseCommand, CommandContext, CommandResult
from llm_box.commands.registry import CommandRegistry, command
from llm_box.config.schema import LLMBoxConfig
from llm_box.output.base import OutputData, OutputFormatter
from llm_box.providers.base import LLMBoxProvider

# --- Fixtures ---


@pytest.fixture
def mock_provider() -> MagicMock:
    """Create a mock LLM provider."""
    provider = MagicMock(spec=LLMBoxProvider)
    provider.invoke.return_value = "Mock response"
    return provider


@pytest.fixture
def mock_cache() -> MagicMock:
    """Create a mock cache."""
    return MagicMock(spec=Cache)


@pytest.fixture
def mock_formatter() -> MagicMock:
    """Create a mock output formatter."""
    return MagicMock(spec=OutputFormatter)


@pytest.fixture
def mock_config() -> LLMBoxConfig:
    """Create a mock config."""
    return LLMBoxConfig()


@pytest.fixture
def command_context(
    mock_provider: MagicMock,
    mock_cache: MagicMock,
    mock_formatter: MagicMock,
    mock_config: LLMBoxConfig,
    tmp_path: Path,
) -> CommandContext:
    """Create a command context with mocked dependencies."""
    return CommandContext(
        provider=mock_provider,
        cache=mock_cache,
        formatter=mock_formatter,
        config=mock_config,
        use_cache=True,
        verbose=False,
        working_dir=tmp_path,
    )


@pytest.fixture(autouse=True)
def clear_registry():
    """Clear the command registry before and after each test."""
    CommandRegistry.clear()
    yield
    CommandRegistry.clear()


# --- Sample Command Implementations ---


class SampleCommand(BaseCommand):
    """A sample command for testing."""

    @property
    def name(self) -> str:
        return "sample"

    @property
    def description(self) -> str:
        return "A sample command"

    @property
    def aliases(self) -> list[str]:
        return ["s", "samp"]

    def execute(self, ctx: CommandContext, **kwargs: Any) -> CommandResult:
        value = kwargs.get("value", "default")
        return CommandResult.ok(data=f"Result: {value}")


class FailingCommand(BaseCommand):
    """A command that always fails."""

    @property
    def name(self) -> str:
        return "failing"

    @property
    def description(self) -> str:
        return "A command that fails"

    def execute(self, ctx: CommandContext, **kwargs: Any) -> CommandResult:
        return CommandResult.fail(error="Something went wrong")


class AsyncCommand(BaseCommand):
    """A command with async support."""

    @property
    def name(self) -> str:
        return "async-cmd"

    @property
    def description(self) -> str:
        return "An async command"

    def execute(self, ctx: CommandContext, **kwargs: Any) -> CommandResult:
        return CommandResult.ok(data="sync result")

    async def aexecute(self, ctx: CommandContext, **kwargs: Any) -> CommandResult:
        return CommandResult.ok(data="async result")


# --- CommandResult Tests ---


class TestCommandResult:
    """Tests for CommandResult dataclass."""

    def test_ok_result(self):
        """Test creating a successful result."""
        result = CommandResult.ok(data="test data")

        assert result.success is True
        assert result.data == "test data"
        assert result.error is None
        assert result.cached is False
        assert result.metadata == {}

    def test_ok_result_with_cached(self):
        """Test creating a cached successful result."""
        result = CommandResult.ok(data="cached data", cached=True)

        assert result.success is True
        assert result.cached is True

    def test_ok_result_with_metadata(self):
        """Test creating a result with metadata."""
        result = CommandResult.ok(data="test", tokens_used=100, latency_ms=50)

        assert result.metadata == {"tokens_used": 100, "latency_ms": 50}

    def test_fail_result(self):
        """Test creating a failed result."""
        result = CommandResult.fail(error="Error message")

        assert result.success is False
        assert result.data is None
        assert result.error == "Error message"
        assert result.cached is False

    def test_fail_result_with_metadata(self):
        """Test creating a failed result with metadata."""
        result = CommandResult.fail(error="Error", error_code=500)

        assert result.success is False
        assert result.metadata == {"error_code": 500}

    def test_to_output_data_success(self):
        """Test converting successful result to OutputData."""
        result = CommandResult.ok(data="test data", cached=True)
        output = result.to_output_data(title="Test")

        assert output.content == "test data"
        assert output.title == "Test"
        assert output.cached is True
        assert output.success is True

    def test_to_output_data_failure(self):
        """Test converting failed result to OutputData."""
        result = CommandResult.fail(error="Error message")
        output = result.to_output_data(title="Test")

        assert output.error == "Error message"
        assert output.title == "Test"
        assert output.success is False


# --- CommandContext Tests ---


class TestCommandContext:
    """Tests for CommandContext dataclass."""

    def test_context_creation(self, command_context: CommandContext):
        """Test creating a command context."""
        assert command_context.use_cache is True
        assert command_context.verbose is False
        assert command_context.working_dir.exists()

    def test_with_provider(self, command_context: CommandContext):
        """Test creating context with different provider."""
        new_provider = MagicMock(spec=LLMBoxProvider)
        new_ctx = command_context.with_provider(new_provider)

        assert new_ctx.provider is new_provider
        assert new_ctx.cache is command_context.cache
        assert new_ctx.formatter is command_context.formatter

    def test_with_cache_disabled(self, command_context: CommandContext):
        """Test creating context with cache disabled."""
        new_ctx = command_context.with_cache_disabled()

        assert new_ctx.use_cache is False
        assert new_ctx.provider is command_context.provider

    def test_with_verbose(self, command_context: CommandContext):
        """Test creating context with verbose mode."""
        new_ctx = command_context.with_verbose(True)

        assert new_ctx.verbose is True
        assert new_ctx.provider is command_context.provider


# --- BaseCommand Tests ---


class TestBaseCommand:
    """Tests for BaseCommand abstract class."""

    def test_command_properties(self):
        """Test command name and description properties."""
        cmd = SampleCommand()

        assert cmd.name == "sample"
        assert cmd.description == "A sample command"
        assert cmd.aliases == ["s", "samp"]

    def test_execute(self, command_context: CommandContext):
        """Test synchronous execution."""
        cmd = SampleCommand()
        result = cmd.execute(command_context, value="hello")

        assert result.success is True
        assert result.data == "Result: hello"

    def test_execute_with_default(self, command_context: CommandContext):
        """Test execution with default kwargs."""
        cmd = SampleCommand()
        result = cmd.execute(command_context)

        assert result.data == "Result: default"

    @pytest.mark.asyncio
    async def test_aexecute_default(self, command_context: CommandContext):
        """Test default async execution falls back to sync."""
        cmd = SampleCommand()
        result = await cmd.aexecute(command_context, value="async")

        assert result.success is True
        assert result.data == "Result: async"

    @pytest.mark.asyncio
    async def test_aexecute_override(self, command_context: CommandContext):
        """Test overridden async execution."""
        cmd = AsyncCommand()
        result = await cmd.aexecute(command_context)

        assert result.data == "async result"

    def test_run_success(self, command_context: CommandContext):
        """Test run method prints output."""
        cmd = SampleCommand()
        cmd.run(command_context, value="test")

        command_context.formatter.print.assert_called_once()
        call_args = command_context.formatter.print.call_args[0][0]
        assert isinstance(call_args, OutputData)
        assert call_args.content == "Result: test"

    def test_run_failure(self, command_context: CommandContext):
        """Test run method with failed command."""
        cmd = FailingCommand()
        cmd.run(command_context)

        command_context.formatter.print.assert_called_once()
        call_args = command_context.formatter.print.call_args[0][0]
        assert call_args.success is False
        assert call_args.error == "Something went wrong"

    @pytest.mark.asyncio
    async def test_arun(self, command_context: CommandContext):
        """Test async run method."""
        cmd = AsyncCommand()
        await cmd.arun(command_context)

        command_context.formatter.print.assert_called_once()
        call_args = command_context.formatter.print.call_args[0][0]
        assert call_args.content == "async result"

    def test_repr(self):
        """Test command repr."""
        cmd = SampleCommand()
        assert repr(cmd) == "SampleCommand(name='sample')"


# --- CommandRegistry Tests ---


class TestCommandRegistry:
    """Tests for CommandRegistry."""

    def test_register_decorator(self):
        """Test registering a command via decorator."""

        @CommandRegistry.register
        class TestCmd(BaseCommand):
            @property
            def name(self) -> str:
                return "test"

            @property
            def description(self) -> str:
                return "Test command"

            def execute(self, ctx: CommandContext, **kwargs: Any) -> CommandResult:
                return CommandResult.ok(data="test")

        assert CommandRegistry.is_registered("test")
        assert CommandRegistry.get("test") is TestCmd

    def test_register_command_method(self):
        """Test registering a command directly."""
        CommandRegistry.register_command(SampleCommand)

        assert CommandRegistry.is_registered("sample")
        assert CommandRegistry.get("sample") is SampleCommand

    def test_register_duplicate_raises(self):
        """Test registering duplicate command raises error."""
        CommandRegistry.register_command(SampleCommand)

        with pytest.raises(ValueError, match="already registered"):
            CommandRegistry.register_command(SampleCommand)

    def test_register_alias_conflict_raises(self):
        """Test registering conflicting alias raises error."""
        CommandRegistry.register_command(SampleCommand)

        # Create a command with an alias that conflicts
        class ConflictCommand(BaseCommand):
            @property
            def name(self) -> str:
                return "conflict"

            @property
            def description(self) -> str:
                return "Conflict"

            @property
            def aliases(self) -> list[str]:
                return ["s"]  # Conflicts with SampleCommand

            def execute(self, ctx: CommandContext, **kwargs: Any) -> CommandResult:
                return CommandResult.ok(data="conflict")

        with pytest.raises(ValueError, match="conflicts"):
            CommandRegistry.register_command(ConflictCommand)

    def test_get_by_name(self):
        """Test getting command by name."""
        CommandRegistry.register_command(SampleCommand)

        result = CommandRegistry.get("sample")
        assert result is SampleCommand

    def test_get_by_alias(self):
        """Test getting command by alias."""
        CommandRegistry.register_command(SampleCommand)

        result = CommandRegistry.get("s")
        assert result is SampleCommand

        result = CommandRegistry.get("samp")
        assert result is SampleCommand

    def test_get_not_found(self):
        """Test getting nonexistent command."""
        result = CommandRegistry.get("nonexistent")
        assert result is None

    def test_get_instance(self, command_context: CommandContext):
        """Test getting command instance."""
        CommandRegistry.register_command(SampleCommand)

        instance = CommandRegistry.get_instance("sample")
        assert isinstance(instance, SampleCommand)

        result = instance.execute(command_context, value="instance")
        assert result.data == "Result: instance"

    def test_get_instance_by_alias(self):
        """Test getting command instance by alias."""
        CommandRegistry.register_command(SampleCommand)

        instance = CommandRegistry.get_instance("s")
        assert isinstance(instance, SampleCommand)

    def test_get_instance_not_found(self):
        """Test getting nonexistent command instance."""
        result = CommandRegistry.get_instance("nonexistent")
        assert result is None

    def test_list_commands(self):
        """Test listing all registered commands."""
        CommandRegistry.register_command(SampleCommand)
        CommandRegistry.register_command(FailingCommand)

        commands = CommandRegistry.list_commands()
        assert len(commands) == 2
        assert SampleCommand in commands
        assert FailingCommand in commands

    def test_list_names(self):
        """Test listing command names."""
        CommandRegistry.register_command(SampleCommand)
        CommandRegistry.register_command(FailingCommand)

        names = CommandRegistry.list_names()
        assert "sample" in names
        assert "failing" in names

    def test_is_registered(self):
        """Test checking if command is registered."""
        assert CommandRegistry.is_registered("sample") is False

        CommandRegistry.register_command(SampleCommand)

        assert CommandRegistry.is_registered("sample") is True
        assert CommandRegistry.is_registered("s") is True  # alias
        assert CommandRegistry.is_registered("nonexistent") is False

    def test_unregister(self):
        """Test unregistering a command."""
        CommandRegistry.register_command(SampleCommand)
        assert CommandRegistry.is_registered("sample")

        result = CommandRegistry.unregister("sample")
        assert result is True
        assert CommandRegistry.is_registered("sample") is False
        assert CommandRegistry.is_registered("s") is False  # alias also removed

    def test_unregister_not_found(self):
        """Test unregistering nonexistent command."""
        result = CommandRegistry.unregister("nonexistent")
        assert result is False

    def test_clear(self):
        """Test clearing all commands."""
        CommandRegistry.register_command(SampleCommand)
        CommandRegistry.register_command(FailingCommand)

        CommandRegistry.clear()

        assert len(CommandRegistry.list_commands()) == 0
        assert CommandRegistry.is_registered("sample") is False

    def test_get_command_info(self):
        """Test getting command info."""
        CommandRegistry.register_command(SampleCommand)
        CommandRegistry.register_command(FailingCommand)

        info = CommandRegistry.get_command_info()
        assert len(info) == 2

        sample_info = next(i for i in info if i["name"] == "sample")
        assert sample_info["description"] == "A sample command"
        assert sample_info["aliases"] == "s, samp"

        failing_info = next(i for i in info if i["name"] == "failing")
        assert failing_info["aliases"] == ""


# --- command decorator factory tests ---


class TestCommandDecorator:
    """Tests for @command decorator factory."""

    def test_command_decorator_basic(self):
        """Test basic command decorator usage."""

        @command()
        class BasicCmd(BaseCommand):
            @property
            def name(self) -> str:
                return "basic"

            @property
            def description(self) -> str:
                return "Basic command"

            def execute(self, ctx: CommandContext, **kwargs: Any) -> CommandResult:
                return CommandResult.ok(data="basic")

        assert CommandRegistry.is_registered("basic")

    def test_command_decorator_custom_name(self):
        """Test command decorator with custom name."""

        @command(name="custom-name")
        class CustomCmd(BaseCommand):
            @property
            def name(self) -> str:
                return "original"

            @property
            def description(self) -> str:
                return "Custom named command"

            def execute(self, ctx: CommandContext, **kwargs: Any) -> CommandResult:
                return CommandResult.ok(data="custom")

        assert CommandRegistry.is_registered("custom-name")
        assert CommandRegistry.is_registered("original") is False

        instance = CommandRegistry.get_instance("custom-name")
        assert instance.name == "custom-name"

    def test_command_decorator_custom_aliases(self):
        """Test command decorator with custom aliases."""

        @command(aliases=["a", "ali"])
        class AliasCmd(BaseCommand):
            @property
            def name(self) -> str:
                return "alias-cmd"

            @property
            def description(self) -> str:
                return "Command with aliases"

            @property
            def aliases(self) -> list[str]:
                return ["original-alias"]

            def execute(self, ctx: CommandContext, **kwargs: Any) -> CommandResult:
                return CommandResult.ok(data="alias")

        assert CommandRegistry.is_registered("alias-cmd")
        assert CommandRegistry.is_registered("a")
        assert CommandRegistry.is_registered("ali")
        # Original aliases should be overridden
        assert CommandRegistry.is_registered("original-alias") is False

    def test_command_decorator_name_and_aliases(self):
        """Test command decorator with both custom name and aliases."""

        @command(name="full-custom", aliases=["fc", "full"])
        class FullCmd(BaseCommand):
            @property
            def name(self) -> str:
                return "original"

            @property
            def description(self) -> str:
                return "Fully customized command"

            def execute(self, ctx: CommandContext, **kwargs: Any) -> CommandResult:
                return CommandResult.ok(data="full")

        assert CommandRegistry.is_registered("full-custom")
        assert CommandRegistry.is_registered("fc")
        assert CommandRegistry.is_registered("full")
        assert CommandRegistry.is_registered("original") is False

        instance = CommandRegistry.get_instance("full-custom")
        assert instance.name == "full-custom"
        assert instance.aliases == ["fc", "full"]
