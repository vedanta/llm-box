"""Command registry for discovering and managing commands."""

from collections.abc import Callable
from typing import Any, TypeVar

from llm_box.commands.base import BaseCommand

# Type for command classes
CommandClass = TypeVar("CommandClass", bound=type[BaseCommand])


class CommandRegistry:
    """Registry for discovering and managing commands.

    This registry allows commands to be registered either by
    decorator or direct registration, and provides lookup
    by name or alias.

    Usage:
        # Register via decorator
        @CommandRegistry.register
        class CatCommand(BaseCommand):
            ...

        # Or register directly
        CommandRegistry.register_command(CatCommand)

        # Get a command
        cmd = CommandRegistry.get("cat")

        # List all commands
        for cmd in CommandRegistry.list_commands():
            print(cmd.name)
    """

    _commands: dict[str, type[BaseCommand]] = {}
    _aliases: dict[str, str] = {}  # alias -> command name

    @classmethod
    def register(cls, command_class: CommandClass) -> CommandClass:
        """Decorator to register a command class.

        Args:
            command_class: The command class to register.

        Returns:
            The command class (unchanged).

        Example:
            @CommandRegistry.register
            class MyCommand(BaseCommand):
                ...
        """
        cls.register_command(command_class)
        return command_class

    @classmethod
    def register_command(cls, command_class: type[BaseCommand]) -> None:
        """Register a command class.

        Args:
            command_class: The command class to register.

        Raises:
            ValueError: If a command with the same name is already registered.
        """
        # Create instance to get name and aliases
        instance = command_class()
        name = instance.name

        if name in cls._commands:
            raise ValueError(f"Command '{name}' is already registered")

        cls._commands[name] = command_class

        # Register aliases
        for alias in instance.aliases:
            if alias in cls._aliases or alias in cls._commands:
                raise ValueError(
                    f"Alias '{alias}' conflicts with existing command or alias"
                )
            cls._aliases[alias] = name

    @classmethod
    def get(cls, name: str) -> type[BaseCommand] | None:
        """Get a command class by name or alias.

        Args:
            name: The command name or alias.

        Returns:
            The command class, or None if not found.
        """
        # Check direct name first
        if name in cls._commands:
            return cls._commands[name]

        # Check aliases
        if name in cls._aliases:
            return cls._commands[cls._aliases[name]]

        return None

    @classmethod
    def get_instance(cls, name: str) -> BaseCommand | None:
        """Get a command instance by name or alias.

        Args:
            name: The command name or alias.

        Returns:
            A new command instance, or None if not found.
        """
        command_class = cls.get(name)
        if command_class is None:
            return None
        return command_class()

    @classmethod
    def list_commands(cls) -> list[type[BaseCommand]]:
        """List all registered command classes.

        Returns:
            List of command classes.
        """
        return list(cls._commands.values())

    @classmethod
    def list_names(cls) -> list[str]:
        """List all command names.

        Returns:
            List of command names (not aliases).
        """
        return list(cls._commands.keys())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if a command is registered.

        Args:
            name: The command name or alias.

        Returns:
            True if registered, False otherwise.
        """
        return name in cls._commands or name in cls._aliases

    @classmethod
    def unregister(cls, name: str) -> bool:
        """Unregister a command by name.

        Args:
            name: The command name (not alias).

        Returns:
            True if unregistered, False if not found.
        """
        if name not in cls._commands:
            return False

        # Get instance to find aliases
        instance = cls._commands[name]()

        # Remove aliases
        for alias in instance.aliases:
            cls._aliases.pop(alias, None)

        # Remove command
        del cls._commands[name]
        return True

    @classmethod
    def clear(cls) -> None:
        """Clear all registered commands (mainly for testing)."""
        cls._commands.clear()
        cls._aliases.clear()

    @classmethod
    def get_command_info(cls) -> list[dict[str, str]]:
        """Get info about all registered commands.

        Returns:
            List of dicts with name, description, and aliases.
        """
        info = []
        for command_class in cls._commands.values():
            instance = command_class()
            info.append(
                {
                    "name": instance.name,
                    "description": instance.description,
                    "aliases": ", ".join(instance.aliases) if instance.aliases else "",
                }
            )
        return info


def command(
    name: str | None = None,
    aliases: list[str] | None = None,
) -> Callable[[CommandClass], CommandClass]:
    """Decorator factory for registering commands with custom options.

    Args:
        name: Override the command name.
        aliases: Additional aliases for the command.

    Returns:
        Decorator function.

    Example:
        @command(name="explain", aliases=["e", "exp"])
        class ExplainCommand(BaseCommand):
            ...
    """

    def decorator(command_class: CommandClass) -> CommandClass:
        # Store custom name/aliases if provided
        if name is not None or aliases is not None:
            original_init = command_class.__init__

            def new_init(self: Any, *args: Any, **kwargs: Any) -> None:
                original_init(self, *args, **kwargs)
                if name is not None:
                    object.__setattr__(self, "_custom_name", name)
                if aliases is not None:
                    object.__setattr__(self, "_custom_aliases", aliases)

            command_class.__init__ = new_init  # type: ignore[method-assign]

            # Override name property if custom name provided
            if name is not None:
                # Store the original property's fget
                orig_name_prop: property = command_class.name  # type: ignore[assignment]
                orig_name_fget = orig_name_prop.fget

                @property  # type: ignore[misc]
                def name_prop(self: Any) -> str:
                    custom = getattr(self, "_custom_name", None)
                    if custom is not None:
                        return str(custom)
                    if orig_name_fget is not None:
                        return str(orig_name_fget(self))
                    return ""  # fallback

                command_class.name = name_prop  # type: ignore[method-assign]

            # Override aliases property if custom aliases provided
            if aliases is not None:
                # Store the original property's fget
                orig_aliases_prop: property = command_class.aliases  # type: ignore[assignment]
                orig_aliases_fget = orig_aliases_prop.fget

                @property  # type: ignore[misc]
                def aliases_prop(self: Any) -> list[str]:
                    custom = getattr(self, "_custom_aliases", None)
                    if custom is not None:
                        return list(custom)
                    if orig_aliases_fget is not None:
                        return list(orig_aliases_fget(self))
                    return []  # fallback

                command_class.aliases = aliases_prop  # type: ignore[method-assign]

        CommandRegistry.register(command_class)
        return command_class

    return decorator
