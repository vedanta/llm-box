# Command Pattern Design

## Overview

All llm-box commands share a common interface and execution pattern. This enables consistent behavior, shared options, caching, and error handling.

## Naming Convention

**Primary interface:** `llm-box <command>`

```bash
llm-box ls ./src
llm-box cat README.md
llm-box find "auth config"
llm-box ask "what does this do?"
```

**Optional aliases:** For convenience, standalone aliases can be configured:

```bash
# In ~/.bashrc or ~/.zshrc
alias lls='llm-box ls'
alias lcat='llm-box cat'
alias lfind='llm-box find'
alias lask='llm-box ask'
```

The `llm-box` CLI also installs entry points for direct invocation:
- `llm-ls` → `llm-box ls`
- `llm-cat` → `llm-box cat`
- `llm-find` → `llm-box find`

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     llm-box CLI (Typer)                          │
│                                                                  │
│   llm-box ls    llm-box cat    llm-box find    llm-box ask      │
└──────────┬────────────┬─────────────┬──────────────┬────────────┘
           │            │             │              │
           ▼            ▼             ▼              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      CommandContext                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │ Provider │  │  Cache   │  │Formatter │  │     Config       │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘ │
└──────────┬────────────┬─────────────┬──────────────┬────────────┘
           │            │             │              │
           ▼            ▼             ▼              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       BaseCommand                                │
│                                                                  │
│   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ...      │
│   │   ls    │  │   cat   │  │  find   │  │   ask   │           │
│   └─────────┘  └─────────┘  └─────────┘  └─────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

## Core Types

### CommandContext

```python
# commands/base.py

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class CommandContext:
    """Shared context passed to all commands."""
    provider: 'LLMBoxProvider'
    cache: 'Cache'
    formatter: 'OutputFormatter'
    config: 'LLMBoxConfig'
    use_cache: bool = True
    verbose: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)
```

### CommandResult

```python
@dataclass
class CommandResult:
    """Standardized result from command execution."""
    success: bool
    data: Any
    error: Optional[str] = None
    cached: bool = False
    duration_ms: Optional[int] = None
    tokens_used: Optional[int] = None
```

### BaseCommand

```python
from abc import ABC, abstractmethod


class BaseCommand(ABC):
    """Abstract base class for all commands."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Command name (e.g., 'ls', 'cat')."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Short description for help text."""
        pass

    @abstractmethod
    def execute(self, ctx: CommandContext, **kwargs) -> CommandResult:
        """Execute the command synchronously."""
        pass

    async def aexecute(self, ctx: CommandContext, **kwargs) -> CommandResult:
        """Execute the command asynchronously (default wraps sync)."""
        import asyncio
        return await asyncio.to_thread(self.execute, ctx, **kwargs)

    def _build_cache_key(self, **kwargs) -> str:
        """Build a cache key from command parameters."""
        from ..cache.keys import build_cache_key
        return build_cache_key(self.name, **kwargs)

    def _get_prompt(self, template_name: str, **kwargs) -> str:
        """Get a prompt from the template system."""
        from ..utils.prompts import get_prompt
        return get_prompt(template_name, **kwargs)
```

## Command List

### Tier 1: Core Commands

| Command | Description | Usage |
|---------|-------------|-------|
| `ls` | List files with LLM descriptions | `llm-box ls [PATH]` |
| `cat` | Summarize file contents | `llm-box cat FILE` |
| `find` | Semantic + fuzzy search | `llm-box find "query"` |
| `tldr` | Compress long files to summary | `llm-box tldr FILE` |
| `why` | Explain why a file exists | `llm-box why PATH` |

### Tier 2: Developer Tools

| Command | Description | Usage |
|---------|-------------|-------|
| `run` | Explain what a script does | `llm-box run script.py` |
| `fix` | Suggest fixes for broken code | `llm-box fix FILE` |
| `doc` | Generate documentation | `llm-box doc FILE` |
| `ask` | Q&A mode for files | `llm-box ask "question" FILE` |
| `plan` | Convert TODOs to action plan | `llm-box plan PATH` |

### Utility Commands

| Command | Description | Usage |
|---------|-------------|-------|
| `cache` | Manage cache | `llm-box cache stats|clear` |
| `config` | Show configuration | `llm-box config` |
| `index` | Index files for search | `llm-box index [PATH]` |
| `stats` | Show usage statistics | `llm-box stats` |
| `plugins` | Manage plugins | `llm-box plugins list|install` |

## Command Implementations

### ls Command

```python
# commands/ls.py

from dataclasses import dataclass
from typing import Optional, List
from pathlib import Path
from .base import BaseCommand, CommandContext, CommandResult
from .registry import CommandRegistry


@dataclass
class FileEntry:
    """Represents a file or directory entry."""
    name: str
    path: str
    is_dir: bool
    size: Optional[int]
    description: str
    cached: bool = False


@CommandRegistry.register("ls")
class LsCommand(BaseCommand):
    """LLM-enhanced ls command."""

    @property
    def name(self) -> str:
        return "ls"

    @property
    def description(self) -> str:
        return "List files with LLM-generated descriptions"

    def execute(
        self,
        ctx: CommandContext,
        path: str = ".",
        include_hidden: bool = False,
        recursive: bool = False,
        max_depth: int = 1
    ) -> CommandResult:
        target_path = Path(path).resolve()

        if not target_path.exists():
            return CommandResult(
                success=False,
                data=None,
                error=f"Path does not exist: {path}"
            )

        if not target_path.is_dir():
            return CommandResult(
                success=False,
                data=None,
                error=f"Not a directory: {path}"
            )

        entries = []
        for entry in sorted(target_path.iterdir(), key=lambda e: e.name):
            # Skip hidden files unless requested
            if entry.name.startswith(".") and not include_hidden:
                continue

            # Build cache key
            cache_key = self._build_cache_key(
                path=str(entry),
                content_hash=self._get_content_hash(entry)
            )

            # Check cache
            cached_desc = None
            if ctx.use_cache:
                cached_desc = ctx.cache.get(cache_key)

            if cached_desc:
                description = cached_desc
                was_cached = True
            else:
                # Generate description via LLM
                content_sample = self._sample_content(entry) if entry.is_file() else None
                prompt = self._get_prompt(
                    "ls_describe",
                    filename=entry.name,
                    is_dir=entry.is_dir(),
                    content_sample=content_sample
                )
                response = ctx.provider.invoke(prompt)
                description = response.content.strip()
                was_cached = False

                # Cache the result
                if ctx.use_cache:
                    ctx.cache.set(cache_key, description, command=self.name)

            entries.append(FileEntry(
                name=entry.name,
                path=str(entry),
                is_dir=entry.is_dir(),
                size=entry.stat().st_size if entry.is_file() else None,
                description=description,
                cached=was_cached
            ))

        return CommandResult(success=True, data=entries)

    def _sample_content(self, path: Path, max_bytes: int = 1000) -> Optional[str]:
        """Sample file content for LLM context."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read(max_bytes)
        except Exception:
            return None

    def _get_content_hash(self, path: Path) -> str:
        """Get hash of file for cache invalidation."""
        from ..utils.hashing import hash_file_metadata
        return hash_file_metadata(path)
```

### cat Command

```python
# commands/cat.py

from dataclasses import dataclass
from pathlib import Path
from .base import BaseCommand, CommandContext, CommandResult
from .registry import CommandRegistry


@dataclass
class CatOutput:
    """Output from cat command."""
    filename: str
    summary: str
    content_preview: str
    cached: bool = False


@CommandRegistry.register("cat")
class CatCommand(BaseCommand):
    """LLM-enhanced cat command - summarize file contents."""

    @property
    def name(self) -> str:
        return "cat"

    @property
    def description(self) -> str:
        return "Summarize file contents using LLM"

    def execute(
        self,
        ctx: CommandContext,
        file: str,
        max_content: int = 10000
    ) -> CommandResult:
        file_path = Path(file).resolve()

        if not file_path.exists():
            return CommandResult(
                success=False,
                data=None,
                error=f"File not found: {file}"
            )

        if file_path.is_dir():
            return CommandResult(
                success=False,
                data=None,
                error=f"'{file}' is a directory"
            )

        # Read content
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            return CommandResult(
                success=False,
                data=None,
                error=f"Could not read file: {e}"
            )

        # Build cache key
        from ..utils.hashing import hash_file_content
        content_hash = hash_file_content(content)
        cache_key = self._build_cache_key(
            file=str(file_path),
            content_hash=content_hash
        )

        # Check cache
        cached_summary = ctx.cache.get(cache_key) if ctx.use_cache else None

        if cached_summary:
            summary = cached_summary
            was_cached = True
        else:
            # Generate summary via LLM
            prompt = self._get_prompt(
                "cat_summarize",
                filename=file_path.name,
                content=content[:max_content]
            )
            response = ctx.provider.invoke(prompt)
            summary = response.content.strip()
            was_cached = False

            # Cache the result
            if ctx.use_cache:
                ctx.cache.set(cache_key, summary, command=self.name)

        return CommandResult(
            success=True,
            data=CatOutput(
                filename=file_path.name,
                summary=summary,
                content_preview=content[:500],
                cached=was_cached
            )
        )
```

## Shared CLI Options

All commands support these global options:

```bash
# Output format
--format, -f    rich|plain|json    # Default: rich

# Caching
--no-cache      Disable cache for this request

# Verbosity
--verbose, -v   Enable verbose output

# Provider override
--provider, -p  ollama|openai|anthropic
--model, -m     Model name override
```

## CLI App Structure

```python
# cli/app.py

import typer

app = typer.Typer(
    name="llm-box",
    help="LLM-powered terminal toolbox",
    add_completion=True
)

@app.command("ls")
def ls_command(...): ...

@app.command("cat")
def cat_command(...): ...

@app.command("find")
def find_command(...): ...

# Subcommand groups
cache_app = typer.Typer(help="Manage cache")
app.add_typer(cache_app, name="cache")

@cache_app.command("stats")
def cache_stats(): ...

@cache_app.command("clear")
def cache_clear(): ...


def main():
    app()
```

## Entry Points (pyproject.toml)

```toml
[project.scripts]
# Primary interface
llm-box = "llm_box.cli.app:main"

# Shortcut aliases
llm-ls = "llm_box.cli.shortcuts:ls_main"
llm-cat = "llm_box.cli.shortcuts:cat_main"
llm-find = "llm_box.cli.shortcuts:find_main"
llm-ask = "llm_box.cli.shortcuts:ask_main"
```

## Prompt Templates

```python
# utils/prompts.py

PROMPTS = {
    "ls_describe": """Describe the purpose of this {type} '{filename}' in one short line (under 10 words).
{content_section}
Respond with only the description, no explanations.""",

    "cat_summarize": """Summarize the content of '{filename}' in one concise paragraph.

Content:
{content}

Provide a clear, informative summary.""",

    "why_explain": """Explain why this file/folder exists: '{path}'
Based on its name and content, what is its purpose in the project?

Content preview:
{content}

Provide a clear, concise explanation.""",

    "ask_answer": """Answer this question about the file '{filename}':

Question: {question}

File content:
{content}

Provide a direct, helpful answer.""",
}
```

## See Also

- [architecture.md](./architecture.md) - Overall system architecture
- [providers.md](./providers.md) - LLM provider abstraction
- [caching.md](./caching.md) - How results are cached
