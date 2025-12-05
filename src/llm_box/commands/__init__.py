"""Command implementations for llm-box.

This module provides the command pattern infrastructure for building
extensible CLI commands with dependency injection.

Usage:
    from llm_box.commands import BaseCommand, CommandContext, CommandResult
    from llm_box.commands import CommandRegistry

    # Define a command
    @CommandRegistry.register
    class MyCommand(BaseCommand):
        @property
        def name(self) -> str:
            return "my-command"

        @property
        def description(self) -> str:
            return "Does something useful"

        def execute(self, ctx: CommandContext, **kwargs) -> CommandResult:
            # ... implementation ...
            return CommandResult.ok(data="result")

    # Execute a command
    cmd = CommandRegistry.get_instance("my-command")
    result = cmd.execute(context, arg1="value")
"""

from llm_box.commands.base import BaseCommand, CommandContext, CommandResult
from llm_box.commands.registry import CommandRegistry, command

# Import commands to trigger registration
from llm_box.commands.cat import CatCommand
from llm_box.commands.ls import LsCommand

__all__ = [
    # Base classes
    "BaseCommand",
    "CommandContext",
    "CommandResult",
    # Registry
    "CommandRegistry",
    "command",
    # Commands
    "CatCommand",
    "LsCommand",
]
