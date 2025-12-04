# Architecture Design

## Overview

llm-box is an LLM-powered terminal toolbox that enhances classic Unix shell commands with AI capabilities. It uses locally-run language models (via Ollama) or cloud providers (OpenAI, Anthropic) to provide semantic understanding of files and directories.

## Project Structure

```
llm-box/
├── pyproject.toml                 # Modern Python packaging (PEP 517/518)
├── docs/
│   ├── design/                    # Architecture documentation
│   └── user-guide/                # User documentation
├── src/
│   └── llm_box/                   # Main package (src layout)
│       ├── __init__.py            # Version, public API
│       ├── __main__.py            # python -m llm_box entry
│       ├── py.typed               # PEP 561 marker
│       │
│       ├── cli/                   # CLI Layer
│       │   ├── app.py             # Main Typer app, command registration
│       │   ├── options.py         # Shared CLI options
│       │   ├── shortcuts.py       # Entry points (llm-ls, llm-cat)
│       │   ├── callbacks.py       # Global callbacks
│       │   └── error_handler.py   # User-friendly error display
│       │
│       ├── commands/              # Command Implementations
│       │   ├── base.py            # BaseCommand, CommandContext, CommandResult
│       │   ├── ls.py              # llm-ls
│       │   ├── cat.py             # llm-cat
│       │   ├── find.py            # llm-find (semantic search)
│       │   ├── tldr.py            # llm-tldr
│       │   ├── why.py             # llm-why
│       │   ├── run.py             # llm-run
│       │   ├── fix.py             # llm-fix
│       │   ├── doc.py             # llm-doc
│       │   ├── ask.py             # llm-ask
│       │   └── plan.py            # llm-plan
│       │
│       ├── providers/             # LLM Provider Abstraction
│       │   ├── base.py            # LLMBoxProvider class
│       │   ├── registry.py        # Provider factory
│       │   ├── ollama.py          # Ollama implementation
│       │   ├── openai.py          # OpenAI implementation
│       │   ├── anthropic.py       # Anthropic implementation
│       │   └── mock.py            # Mock provider for testing
│       │
│       ├── cache/                 # Caching Layer
│       │   ├── base.py            # Cache protocol
│       │   ├── duckdb_cache.py    # DuckDB implementation
│       │   ├── vector_store.py    # Embeddings for semantic search
│       │   └── keys.py            # Cache key generation
│       │
│       ├── search/                # Search Engine
│       │   ├── engine.py          # Unified search interface
│       │   ├── semantic.py        # Vector similarity search
│       │   ├── fuzzy.py           # Fuzzy filename/content matching
│       │   ├── indexer.py         # File indexing
│       │   └── ranking.py         # Result ranking/scoring
│       │
│       ├── output/                # Output Formatting
│       │   ├── base.py            # OutputFormatter protocol
│       │   ├── plain.py           # Plain text output
│       │   ├── rich_fmt.py        # Rich terminal formatting
│       │   └── json_fmt.py        # JSON output
│       │
│       ├── config/                # Configuration
│       │   ├── loader.py          # TOML + ENV loading
│       │   ├── schema.py          # Pydantic models
│       │   └── defaults.py        # Default configuration
│       │
│       ├── utils/                 # Utilities
│       │   ├── files.py           # File operations
│       │   ├── hashing.py         # Content hashing
│       │   ├── prompts.py         # Prompt templates
│       │   ├── retry.py           # Retry decorators
│       │   ├── logging.py         # Structured logging
│       │   └── async_utils.py     # Async helpers
│       │
│       ├── telemetry/             # Usage Analytics
│       │   └── collector.py       # Local telemetry (opt-in)
│       │
│       ├── plugins/               # Plugin System
│       │   ├── base.py            # Plugin base classes
│       │   └── loader.py          # Plugin discovery
│       │
│       └── exceptions.py          # Exception hierarchy
│
├── tests/
│   ├── conftest.py                # Pytest fixtures
│   ├── unit/                      # Unit tests
│   ├── integration/               # Integration tests
│   └── e2e/                       # End-to-end tests
│
├── Formula/
│   └── llm-box.rb                 # Homebrew formula
└── conda/
    └── meta.yaml                  # Conda recipe
```

## Data Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                           User Input                              │
│                    llm-box find "auth config"                     │
└─────────────────────────────┬────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                         CLI Layer (Typer)                         │
│  • Parse arguments and options                                    │
│  • Load configuration                                             │
│  • Initialize CommandContext                                      │
└─────────────────────────────┬────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                      CommandContext                               │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  │
│  │  Provider  │  │   Cache    │  │ Formatter  │  │   Config   │  │
│  │ (LangChain)│  │  (DuckDB)  │  │   (Rich)   │  │   (TOML)   │  │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘  │
└─────────────────────────────┬────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                       Command.execute()                           │
│  1. Check cache for existing result                               │
│  2. If miss: invoke LLM provider                                  │
│  3. Store result in cache                                         │
│  4. Return CommandResult                                          │
└─────────────────────────────┬────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
┌─────────────────────────┐    ┌─────────────────────────┐
│      Cache Hit          │    │      Cache Miss         │
│  Return cached result   │    │  ┌─────────────────┐    │
└─────────────────────────┘    │  │  LLM Provider   │    │
                               │  │  (invoke/embed) │    │
                               │  └────────┬────────┘    │
                               │           │             │
                               │           ▼             │
                               │  ┌─────────────────┐    │
                               │  │  Store in Cache │    │
                               │  └─────────────────┘    │
                               └───────────┬─────────────┘
                                           │
                                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                      Output Formatter                             │
│  • Format result (rich/plain/json)                                │
│  • Display to stdout                                              │
└──────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. CLI Layer (`cli/`)

Built on **Typer** for type-safe argument parsing:

```python
# cli/app.py
app = typer.Typer(name="llm-box", help="LLM-powered terminal toolbox")

@app.command("ls")
def ls_command(
    path: str = typer.Argument("."),
    format: str = typer.Option("rich", "--format", "-f"),
    no_cache: bool = typer.Option(False, "--no-cache"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p"),
): ...

@app.command("find")
def find_command(
    query: str = typer.Argument(...),
    path: str = typer.Option(".", "--path", "-p"),
    mode: str = typer.Option("combined", "--mode", "-m"),
): ...
```

### 2. Command Layer (`commands/`)

All commands share a common interface:

```python
# commands/base.py
@dataclass
class CommandContext:
    provider: LLMBoxProvider
    cache: Cache
    formatter: OutputFormatter
    config: LLMBoxConfig
    use_cache: bool = True
    verbose: bool = False

@dataclass
class CommandResult:
    success: bool
    data: Any
    error: Optional[str] = None
    cached: bool = False

class BaseCommand(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def execute(self, ctx: CommandContext, **kwargs) -> CommandResult: ...
```

### 3. Provider Layer (`providers/`)

Wraps LangChain for unified LLM access:

```python
# providers/base.py
class LLMBoxProvider:
    def __init__(self, chat_model: BaseChatModel, embeddings: Embeddings = None):
        self.chat = chat_model
        self.embeddings = embeddings

    def invoke(self, prompt: str) -> str:
        return self.chat.invoke(prompt).content

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self.embeddings.embed_documents(texts)
```

### 4. Cache Layer (`cache/`)

DuckDB-based caching with vector support:

```python
# cache/duckdb_cache.py
class DuckDBCache:
    def get(self, key: str) -> Optional[str]: ...
    def set(self, key: str, value: str, ttl: int = None): ...
    def delete(self, key: str) -> bool: ...
    def stats(self) -> dict: ...
```

### 5. Search Layer (`search/`)

Unified semantic + fuzzy search:

```python
# search/engine.py
class SearchEngine:
    def search(
        self,
        query: str,
        path: str = ".",
        mode: SearchMode = SearchMode.COMBINED,
        top_k: int = 10
    ) -> list[SearchResult]: ...
```

## Configuration

### File Locations (in priority order)

1. `.llm-box.toml` (project local)
2. `~/.config/llm-box/config.toml` (XDG config)
3. `~/.llm-box.toml` (home directory)

### Example Configuration

```toml
default_provider = "ollama"

[providers.ollama]
enabled = true
default_model = "llama3"
base_url = "http://localhost:11434"

[providers.openai]
enabled = true
default_model = "gpt-4o-mini"
# api_key from OPENAI_API_KEY env var

[cache]
enabled = true
default_ttl_seconds = 604800  # 7 days

[output]
default_format = "rich"

[telemetry]
enabled = false
local_only = true
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `LLMBOX_PROVIDER` | Override default provider |
| `LLMBOX_MODEL` | Override default model |
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `OLLAMA_HOST` | Ollama server URL |

## Error Handling

### Exception Hierarchy

```
LLMBoxError (base)
├── ProviderError
│   ├── ProviderNotAvailableError
│   ├── ProviderRateLimitError
│   └── ProviderAuthError
├── CacheError
├── ConfigError
└── SearchError
    └── IndexNotFoundError
```

### Graceful Degradation

- If cache fails, continue without caching
- If primary provider fails, try fallback providers
- If search index missing, offer to create it

## Dependencies

### Core

- typer >= 0.9.0
- rich >= 13.0.0
- duckdb >= 0.9.0
- pydantic >= 2.0.0
- langchain-core >= 0.3.0
- langgraph >= 0.2.0
- rapidfuzz >= 3.0.0
- tenacity >= 8.0.0

### Provider-specific (optional extras)

- langchain-ollama >= 0.3.0
- langchain-openai >= 0.2.0
- langchain-anthropic >= 0.2.0

## See Also

- [providers.md](./providers.md) - LLM provider abstraction
- [commands.md](./commands.md) - Command pattern design
- [search.md](./search.md) - Search system design
- [caching.md](./caching.md) - DuckDB caching strategy
