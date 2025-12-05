# llm-box

**LLM-powered terminal toolbox** — AI-enhanced versions of `ls`, `cat`, `find`, and more.

llm-box brings the power of large language models to your command line. Instead of just listing files, it **describes what they do**. Instead of dumping file contents, it **explains them**. Instead of searching by filename, it **understands what you're looking for**.

## Features

| Command | Description |
|---------|-------------|
| `llm-box ls` | List files with AI-generated descriptions |
| `llm-box cat` | Explain file contents, not just display them |
| `llm-box find` | Semantic + fuzzy search across your codebase |
| `llm-box index` | Index files for fast semantic search |

**Shortcuts:** Use `llm-ls`, `llm-cat`, `llm-find` directly.

## Quick Start

### 1. Install llm-box

```bash
# From PyPI (recommended)
pip install llm-box

# With all LLM providers
pip install llm-box[all]

# Or install specific providers
pip install llm-box[ollama]    # Local models via Ollama
pip install llm-box[openai]    # OpenAI API
pip install llm-box[anthropic] # Anthropic API
```

### 2. Set up an LLM provider

**Option A: Ollama (Local, Free, Recommended)**

```bash
# Install Ollama (macOS)
brew install ollama

# Start the Ollama server
ollama serve

# Pull a model (in another terminal)
ollama pull llama3
```

**Option B: OpenAI**

```bash
export OPENAI_API_KEY="your-api-key"
```

**Option C: Anthropic**

```bash
export ANTHROPIC_API_KEY="your-api-key"
```

### 3. Start using llm-box

```bash
# List files with descriptions
llm-ls .

# Explain a file
llm-cat README.md

# Search your codebase
llm-find "authentication logic"
```

## Installation

### From PyPI

```bash
pip install llm-box
```

### From Source

```bash
git clone https://github.com/vedanta/llm-box.git
cd llm-box
pip install -e ".[dev]"
```

### Using Homebrew (macOS)

```bash
brew install vedanta/tap/llm-box
```

### Provider Dependencies

llm-box supports multiple LLM providers. Install the ones you need:

```bash
pip install llm-box[ollama]     # For Ollama (local)
pip install llm-box[openai]     # For OpenAI
pip install llm-box[anthropic]  # For Anthropic
pip install llm-box[all]        # All providers
```

## Commands

### llm-box ls

List files and directories with AI-generated descriptions.

```bash
# Basic usage
llm-ls .
llm-box ls /path/to/directory

# Include hidden files
llm-ls -a .

# Filter by pattern
llm-ls --pattern "*.py" src/

# Output as JSON
llm-ls --format json .
```

**Example output:**

```
 📁 src           Core source code for the llm-box package
 📁 tests         Unit and integration test suite
 📄 pyproject.toml Python package configuration and dependencies
 📄 README.md     Project documentation and usage guide

4 items
```

### llm-box cat

Explain file contents using AI.

```bash
# Basic explanation
llm-cat main.py

# Brief summary only
llm-cat --brief main.py

# Focus on specific aspect
llm-cat --focus "error handling" main.py

# Output as JSON
llm-cat --format json config.yaml
```

**Example output:**

```
main.py

This Python script serves as the entry point for the CLI application.
It imports the Typer app from the cli module and invokes it when run
directly. The script follows the standard Python idiom for executable
modules using the `if __name__ == "__main__"` guard.

Key components:
- Imports the `app` object from `llm_box.cli.app`
- Calls `app()` to start the CLI when executed
```

### llm-box find

Search files using semantic understanding and fuzzy matching.

```bash
# Semantic search (natural language)
llm-find "user authentication"

# Search in specific directory
llm-find "database queries" --path ./src

# Fuzzy search mode
llm-find --mode fuzzy "confg.yml"

# Combined mode (default) - uses both semantic and fuzzy
llm-find "auth config" --mode combined

# Limit results
llm-find "error handling" --top 5

# Filter by file type
llm-find "tests" --ext ".py,.js"

# Index before searching
llm-find "api endpoints" --index
```

**Example output:**

```
Search results (combined mode)

  0.89 auth/login.py
       Path: src/auth/login.py
       Type: semantic | Language: Python
       ...handles user authentication and session...

  0.76 config/auth.yaml
       Path: config/auth.yaml
       Type: fuzzy | Language: yaml
       ...authentication: enabled...

Found 2 results in 45.2ms
```

### llm-box index

Index files for semantic search (generates embeddings).

```bash
# Index current directory
llm-box index .

# Index specific file types
llm-box index . --ext ".py,.js,.ts"

# Force re-index all files
llm-box index . --force

# Skip embedding generation (metadata only)
llm-box index . --no-embeddings
```

**Example output:**

```
Indexing complete

  Path: /Users/you/project
  Files indexed: 47
  Files updated: 3
  Files unchanged: 44
  Files skipped: 12
```

### llm-box cache

Manage the response cache.

```bash
# View cache statistics
llm-box cache stats

# Clear all cache
llm-box cache clear

# Clear with confirmation skip
llm-box cache clear --force
```

### llm-box config

View current configuration.

```bash
# Show configuration
llm-box config

# Show config file path
llm-box config --path
```

## Configuration

llm-box uses a TOML configuration file located at `~/.config/llm-box/config.toml`.

### Default Configuration

```toml
default_provider = "ollama"

[providers.ollama]
enabled = true
default_model = "llama3"
base_url = "http://localhost:11434"

[providers.openai]
enabled = true
default_model = "gpt-4o-mini"
# API key from OPENAI_API_KEY environment variable

[providers.anthropic]
enabled = true
default_model = "claude-sonnet-4-20250514"
# API key from ANTHROPIC_API_KEY environment variable

[cache]
enabled = true
default_ttl_seconds = 604800  # 7 days

[output]
default_format = "rich"  # rich, plain, or json
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `LLM_BOX_PROVIDER` | Override default provider |
| `LLM_BOX_MODEL` | Override default model |

## Global Options

All commands support these options:

| Option | Short | Description |
|--------|-------|-------------|
| `--provider` | `-p` | LLM provider (ollama, openai, anthropic) |
| `--model` | `-m` | Model name |
| `--format` | `-f` | Output format (rich, plain, json) |
| `--no-cache` | | Bypass cache |
| `--verbose` | `-v` | Verbose output |
| `--version` | `-V` | Show version |
| `--help` | | Show help |

**Examples:**

```bash
# Use OpenAI instead of default
llm-ls . --provider openai

# Use a specific model
llm-cat file.py --model gpt-4

# Get JSON output
llm-ls . --format json

# Skip cache for fresh results
llm-cat README.md --no-cache
```

## Shortcuts

For convenience, llm-box provides standalone commands:

| Shortcut | Equivalent |
|----------|------------|
| `llm-ls` | `llm-box ls` |
| `llm-cat` | `llm-box cat` |
| `llm-find` | `llm-box find` |

These work exactly like their `llm-box` counterparts:

```bash
llm-ls -a .
llm-cat --brief main.py
llm-find "config files" --top 5
```

## Examples

### Exploring a New Codebase

```bash
# Get an overview of the project structure
llm-ls .

# Understand the main entry point
llm-cat main.py

# Find where authentication is handled
llm-find "authentication" --path ./src

# Get a brief summary of the config
llm-cat --brief config.yaml
```

### Code Review

```bash
# Understand what a file does
llm-cat pull_request.py

# Focus on error handling
llm-cat --focus "error handling" api/handler.py

# Find all test files
llm-find "test" --ext .py
```

### Documentation

```bash
# Summarize a long README
llm-cat --brief README.md

# Explain a configuration file
llm-cat docker-compose.yml

# Find documentation files
llm-find "documentation" --mode fuzzy
```

## Caching

llm-box caches LLM responses to improve performance and reduce API costs.

- Cache is stored in `~/.cache/llm-box/cache.duckdb`
- Default TTL is 7 days
- Cache keys include file content hashes, so changes invalidate cache
- Use `--no-cache` to bypass cache for any command

```bash
# View cache stats
llm-box cache stats

# Clear cache
llm-box cache clear
```

## Search Modes

The `find` command supports three search modes:

| Mode | Description | Best For |
|------|-------------|----------|
| `semantic` | Uses AI embeddings for meaning-based search | Natural language queries like "error handling" |
| `fuzzy` | Uses string matching for approximate matches | Typos, partial names like "confg.yml" |
| `combined` | Uses both and merges results (default) | General purpose searching |

```bash
# Semantic only
llm-find --mode semantic "user authentication flow"

# Fuzzy only (good for typos)
llm-find --mode fuzzy "requirments.txt"

# Combined (default)
llm-find "config files"
```

## Troubleshooting

### Ollama not running

```
Error: Cannot connect to Ollama at http://localhost:11434
```

**Solution:** Start Ollama with `ollama serve`

### Model not found

```
Error: Model 'llama3' not found
```

**Solution:** Pull the model with `ollama pull llama3`

### API key not set

```
Error: Authentication failed. Check your API key.
```

**Solution:** Set the appropriate environment variable:
```bash
export OPENAI_API_KEY="your-key"
# or
export ANTHROPIC_API_KEY="your-key"
```

### No search index

```
Error: No search index found
```

**Solution:** Index the directory first:
```bash
llm-box index .
# or search with auto-index
llm-find --index "query"
```

## Development

### Setup

```bash
git clone https://github.com/vedanta/llm-box.git
cd llm-box
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest tests/ -v
```

### Linting & Type Checking

```bash
ruff check src/ tests/
ruff format src/ tests/
mypy src/llm_box
```

### Project Structure

```
llm-box/
├── src/llm_box/
│   ├── cli/           # CLI commands and options
│   ├── commands/      # Command implementations
│   ├── providers/     # LLM provider abstractions
│   ├── cache/         # DuckDB caching layer
│   ├── search/        # Semantic + fuzzy search
│   ├── output/        # Output formatters
│   ├── config/        # Configuration loading
│   └── utils/         # Utilities
├── tests/             # Test suite
├── docs/              # Documentation
├── Formula/           # Homebrew formula
└── conda/             # Conda recipe
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Credits

Built with:
- [Ollama](https://ollama.com) - Local LLM inference
- [LangChain](https://langchain.com) - LLM framework
- [Typer](https://typer.tiangolo.com) - CLI framework
- [Rich](https://rich.readthedocs.io) - Terminal formatting
- [DuckDB](https://duckdb.org) - Embedded database for caching
- [RapidFuzz](https://github.com/rapidfuzz/RapidFuzz) - Fuzzy string matching
