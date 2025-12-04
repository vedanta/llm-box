# llm-box Project Plan

## Overview

This document outlines the implementation roadmap for llm-box, organized into milestones with clear deliverables and success criteria.

---

## Milestone 1: Foundation

**Goal**: Establish project structure, core abstractions, and development environment.

### Tasks

#### 1.1 Project Setup
- [ ] Create `pyproject.toml` with hatchling build system
- [ ] Set up src layout (`src/llm_box/`)
- [ ] Configure development dependencies (pytest, mypy, ruff)
- [ ] Create `py.typed` marker for PEP 561
- [ ] Set up pre-commit hooks

#### 1.2 Configuration System
- [ ] Create `config/schema.py` - Pydantic models for configuration
- [ ] Create `config/loader.py` - TOML + environment variable loading
- [ ] Create `config/defaults.py` - Default configuration values
- [ ] Support `~/.config/llm-box/config.toml`

#### 1.3 Exception Hierarchy
- [ ] Create `exceptions.py` with base `LLMBoxError`
- [ ] Define provider errors (`ProviderError`, `ProviderNotAvailableError`, `ProviderRateLimitError`)
- [ ] Define cache errors (`CacheError`)
- [ ] Define config errors (`ConfigError`)

#### 1.4 Utility Modules
- [ ] Create `utils/hashing.py` - Content and file hashing
- [ ] Create `utils/files.py` - File operations helpers
- [ ] Create `utils/logging.py` - Structured logging setup

### Deliverables
- Working `pip install -e .` development installation
- Configuration loading from TOML files
- Logging infrastructure
- Exception hierarchy

### Success Criteria
- [ ] `python -c "import llm_box"` works
- [ ] Configuration loads from `~/.config/llm-box/config.toml`
- [ ] All linting passes (`ruff check .`)
- [ ] Type checking passes (`mypy src/llm_box`)

---

## Milestone 2: Provider Abstraction

**Goal**: Implement LLM provider layer with LangChain integration.

### Tasks

#### 2.1 Base Provider
- [ ] Create `providers/base.py` - `LLMBoxProvider` class
- [ ] Define `LLMResponse` and `EmbeddingResponse` dataclasses
- [ ] Define `ProviderType` enum
- [ ] Implement `invoke()`, `ainvoke()`, `astream()`, `embed()` methods

#### 2.2 Provider Registry
- [ ] Create `providers/registry.py` - Factory pattern
- [ ] Implement provider caching (reuse instances)
- [ ] Implement `@ProviderRegistry.register()` decorator

#### 2.3 Ollama Provider
- [ ] Create `providers/ollama.py`
- [ ] Integrate `langchain-ollama` (ChatOllama, OllamaEmbeddings)
- [ ] Implement health check (connection test)
- [ ] Handle connection errors gracefully

#### 2.4 OpenAI Provider
- [ ] Create `providers/openai.py`
- [ ] Integrate `langchain-openai` (ChatOpenAI, OpenAIEmbeddings)
- [ ] Support API key from env var (`OPENAI_API_KEY`)
- [ ] Handle rate limits and auth errors

#### 2.5 Anthropic Provider
- [ ] Create `providers/anthropic.py`
- [ ] Integrate `langchain-anthropic` (ChatAnthropic)
- [ ] Use OpenAI embeddings as fallback (Anthropic has no embeddings API)
- [ ] Support API key from env var (`ANTHROPIC_API_KEY`)

#### 2.6 Mock Provider
- [ ] Create `providers/mock.py` for testing
- [ ] Deterministic responses based on input
- [ ] Fake embeddings from text hash

#### 2.7 Retry & Fallback
- [ ] Create `utils/retry.py` - tenacity decorators
- [ ] Create `providers/fallback.py` - Multi-provider fallback logic

### Deliverables
- Working provider abstraction
- All three providers (Ollama, OpenAI, Anthropic)
- Mock provider for testing
- Automatic retry on transient failures

### Success Criteria
- [ ] `ProviderRegistry.get(ProviderType.OLLAMA).invoke("Hello")` returns response
- [ ] Provider health checks work
- [ ] Fallback to secondary provider on failure
- [ ] Unit tests pass for all providers

---

## Milestone 3: Caching Layer

**Goal**: Implement DuckDB-based caching for LLM responses and file metadata.

### Tasks

#### 3.1 DuckDB Cache
- [ ] Create `cache/duckdb_cache.py` - `DuckDBCache` class
- [ ] Implement schema initialization (`llm_cache` table)
- [ ] Implement `get()`, `set()`, `delete()` methods
- [ ] Implement TTL-based expiration
- [ ] Implement `stats()` for cache statistics

#### 3.2 Cache Keys
- [ ] Create `cache/keys.py`
- [ ] Implement `build_cache_key()` - deterministic key generation
- [ ] Implement `hash_prompt()` and `hash_file_content()`

#### 3.3 File Index
- [ ] Add `file_index` table schema
- [ ] Implement file metadata storage
- [ ] Implement content hash for cache invalidation

#### 3.4 Cache CLI Commands
- [ ] Implement `llm-box cache stats`
- [ ] Implement `llm-box cache clear`
- [ ] Implement `llm-box cache cleanup` (remove expired)

### Deliverables
- Working DuckDB cache at `~/.cache/llm-box/cache.duckdb`
- LLM response caching with TTL
- File metadata indexing
- Cache management CLI

### Success Criteria
- [ ] Cache hit returns instantly without LLM call
- [ ] Cache respects TTL expiration
- [ ] `llm-box cache stats` shows accurate statistics
- [ ] Cache survives process restarts (persistent)

---

## Milestone 4: Command Framework

**Goal**: Implement command pattern and output formatting.

### Tasks

#### 4.1 Base Command
- [ ] Create `commands/base.py`
- [ ] Define `CommandContext` dataclass
- [ ] Define `CommandResult` dataclass
- [ ] Define `BaseCommand` abstract class
- [ ] Implement cache key building helper
- [ ] Implement prompt template helper

#### 4.2 Command Registry
- [ ] Create `commands/registry.py`
- [ ] Implement `@CommandRegistry.register()` decorator
- [ ] Implement command discovery

#### 4.3 Output Formatters
- [ ] Create `output/base.py` - `OutputFormatter` protocol
- [ ] Create `output/rich_fmt.py` - Rich terminal formatting
- [ ] Create `output/plain.py` - Plain text output
- [ ] Create `output/json_fmt.py` - JSON output

#### 4.4 CLI Application
- [ ] Create `cli/app.py` - Main Typer application
- [ ] Create `cli/options.py` - Shared CLI options
- [ ] Create `cli/callbacks.py` - Global callbacks
- [ ] Implement `--format`, `--no-cache`, `--provider`, `--model`, `--verbose` options

#### 4.5 Entry Points
- [ ] Create `cli/shortcuts.py` - Entry points for `llm-ls`, `llm-cat`, etc.
- [ ] Create `__main__.py` for `python -m llm_box`

### Deliverables
- Working CLI framework with `llm-box` command
- Multiple output formats (rich, plain, JSON)
- Shared options across all commands
- Shortcut entry points

### Success Criteria
- [ ] `llm-box --help` shows available commands
- [ ] `llm-box --version` shows version
- [ ] `--format json` produces valid JSON output
- [ ] `--no-cache` bypasses cache

---

## Milestone 5: Core Commands

**Goal**: Implement the primary commands (ls, cat, find).

### Tasks

#### 5.1 ls Command
- [ ] Create `commands/ls.py` - `LsCommand` class
- [ ] List directory contents with LLM descriptions
- [ ] Support `--all` for hidden files
- [ ] Support `--recursive` with `--max-depth`
- [ ] Cache descriptions per file (content hash)

#### 5.2 cat Command
- [ ] Create `commands/cat.py` - `CatCommand` class
- [ ] Summarize file contents using LLM
- [ ] Handle large files (truncation)
- [ ] Support binary file detection (skip)

#### 5.3 Prompt Templates
- [ ] Create `utils/prompts.py`
- [ ] Define `ls_describe` prompt
- [ ] Define `cat_summarize` prompt
- [ ] Support template variable substitution

#### 5.4 Error Handling
- [ ] Create `cli/error_handler.py`
- [ ] User-friendly error messages
- [ ] Suggestions for common errors
- [ ] Verbose mode stack traces

### Deliverables
- Working `llm-box ls` command
- Working `llm-box cat` command
- Rich terminal output with descriptions
- Proper error handling

### Success Criteria
- [ ] `llm-box ls .` shows files with descriptions
- [ ] `llm-box cat README.md` shows summary
- [ ] Cached results return instantly
- [ ] Errors show helpful suggestions

---

## Milestone 6: Search System

**Goal**: Implement semantic and fuzzy search capabilities.

### Tasks

#### 6.1 File Indexer
- [ ] Create `search/indexer.py` - `FileIndexer` class
- [ ] Implement directory crawling
- [ ] Implement content chunking (500 chars, 50 overlap)
- [ ] Generate and store embeddings
- [ ] Detect programming languages

#### 6.2 Vector Store
- [ ] Create `cache/vector_store.py` - `VectorStore` class
- [ ] Add `embeddings` table to DuckDB schema
- [ ] Implement `store_embeddings()` method
- [ ] Implement `search()` with cosine similarity

#### 6.3 Semantic Search
- [ ] Create `search/semantic.py` - `SemanticSearch` class
- [ ] Generate query embeddings
- [ ] Search using vector similarity
- [ ] Return ranked results with scores

#### 6.4 Fuzzy Search
- [ ] Create `search/fuzzy.py` - `FuzzySearch` class
- [ ] Integrate rapidfuzz library
- [ ] Filename fuzzy matching
- [ ] Content fuzzy matching
- [ ] Extract match context snippets

#### 6.5 Search Engine
- [ ] Create `search/engine.py` - `SearchEngine` class
- [ ] Implement `SearchMode` enum (semantic, fuzzy, combined)
- [ ] Unified search interface

#### 6.6 Result Ranking
- [ ] Create `search/ranking.py` - `ResultRanker` class
- [ ] Implement score fusion (60% semantic, 40% fuzzy)
- [ ] Deduplicate results by file
- [ ] Sort by combined score

#### 6.7 find Command
- [ ] Create `commands/find.py` - `FindCommand` class
- [ ] Support `--mode` (semantic, fuzzy, combined)
- [ ] Support `--path` for directory scoping
- [ ] Support `--top` for result limit
- [ ] Support `--index` to re-index before search

#### 6.8 index Command
- [ ] Create `commands/index.py` - `IndexCommand` class
- [ ] Index directory for search
- [ ] Show indexing progress
- [ ] Support `--force` to re-index all

### Deliverables
- Working file indexer with embeddings
- Semantic search using vector similarity
- Fuzzy search using rapidfuzz
- Combined search with ranking
- `llm-box find` and `llm-box index` commands

### Success Criteria
- [ ] `llm-box index .` indexes current directory
- [ ] `llm-box find "auth config"` returns relevant files
- [ ] Semantic search finds conceptually related files
- [ ] Fuzzy search handles typos (`confg.yml` → `config.yml`)
- [ ] Combined mode ranks results appropriately

---

## Milestone 7: Additional Commands

**Goal**: Implement remaining developer tool commands.

### Tasks

#### 7.1 tldr Command
- [ ] Create `commands/tldr.py`
- [ ] Compress long files to summary
- [ ] Support `--lines` for output length

#### 7.2 why Command
- [ ] Create `commands/why.py`
- [ ] Explain why a file/folder exists
- [ ] Consider project context

#### 7.3 ask Command
- [ ] Create `commands/ask.py`
- [ ] Q&A mode for files
- [ ] Support multiple files as context

#### 7.4 run Command
- [ ] Create `commands/run.py`
- [ ] Explain what a script does (without executing)
- [ ] Identify potential issues

#### 7.5 fix Command
- [ ] Create `commands/fix.py`
- [ ] Suggest fixes for broken code
- [ ] Show diff of proposed changes

#### 7.6 doc Command
- [ ] Create `commands/doc.py`
- [ ] Generate documentation for code
- [ ] Support multiple output formats

#### 7.7 plan Command
- [ ] Create `commands/plan.py`
- [ ] Convert TODOs to action plan
- [ ] Prioritize tasks

### Deliverables
- Full suite of developer tool commands
- Consistent interface across all commands

### Success Criteria
- [ ] All commands work with `--help`
- [ ] All commands support `--format` option
- [ ] All commands use caching appropriately

---

## Milestone 8: Plugin System

**Goal**: Enable extensibility through plugins.

### Tasks

#### 8.1 Plugin Base Classes
- [ ] Create `plugins/base.py`
- [ ] Define `PluginCommand` base class
- [ ] Define `PluginProvider` base class

#### 8.2 Plugin Loader
- [ ] Create `plugins/loader.py`
- [ ] Discover plugins in `~/.config/llm-box/plugins/`
- [ ] Load plugin manifests (`plugin.toml`)
- [ ] Dynamic command registration

#### 8.3 Plugin CLI
- [ ] Implement `llm-box plugins list`
- [ ] Implement `llm-box plugins info <name>`

#### 8.4 Example Plugin
- [ ] Create example `llm-git` plugin
- [ ] Document plugin development guide

### Deliverables
- Working plugin system
- Plugin discovery and loading
- Example plugin with documentation

### Success Criteria
- [ ] Plugins in `~/.config/llm-box/plugins/` are discovered
- [ ] Plugin commands appear in `llm-box --help`
- [ ] `llm-box plugins list` shows installed plugins

---

## Milestone 9: Telemetry & Stats

**Goal**: Implement usage tracking and statistics (opt-in).

### Tasks

#### 9.1 Telemetry Collector
- [ ] Create `telemetry/collector.py`
- [ ] Local-only telemetry storage
- [ ] Opt-in configuration

#### 9.2 Stats Command
- [ ] Implement `llm-box stats`
- [ ] Show command usage breakdown
- [ ] Show provider usage
- [ ] Show cache hit rate
- [ ] Show token usage estimates

### Deliverables
- Local telemetry collection
- Usage statistics command

### Success Criteria
- [ ] Telemetry disabled by default
- [ ] `llm-box stats` shows meaningful statistics
- [ ] No data sent externally

---

## Milestone 10: Testing

**Goal**: Comprehensive test coverage.

### Tasks

#### 10.1 Test Infrastructure
- [ ] Create `tests/conftest.py` with fixtures
- [ ] Mock provider fixture
- [ ] Temporary directory fixture
- [ ] Test cache fixture

#### 10.2 Unit Tests
- [ ] Provider tests (`tests/unit/test_providers.py`)
- [ ] Cache tests (`tests/unit/test_cache.py`)
- [ ] Command tests (`tests/unit/test_commands.py`)
- [ ] Config tests (`tests/unit/test_config.py`)
- [ ] Search tests (`tests/unit/test_search.py`)

#### 10.3 Integration Tests
- [ ] End-to-end command tests (`tests/integration/`)
- [ ] Provider integration tests (with real Ollama)
- [ ] Cache persistence tests

#### 10.4 E2E Tests
- [ ] CLI invocation tests (`tests/e2e/`)
- [ ] Full workflow tests

### Deliverables
- >80% code coverage
- Passing CI pipeline

### Success Criteria
- [ ] `pytest` passes all tests
- [ ] Coverage report shows >80%
- [ ] Tests run in CI

---

## Milestone 11: Documentation

**Goal**: User-facing documentation.

### Tasks

#### 11.1 README
- [ ] Update `README.md` with installation instructions
- [ ] Quick start guide
- [ ] Command reference
- [ ] Configuration guide

#### 11.2 User Guide
- [ ] Create `docs/user-guide/getting-started.md`
- [ ] Create `docs/user-guide/commands.md`
- [ ] Create `docs/user-guide/configuration.md`
- [ ] Create `docs/user-guide/providers.md`

#### 11.3 Developer Guide
- [ ] Create `docs/developer/contributing.md`
- [ ] Create `docs/developer/plugin-development.md`
- [ ] Create `docs/developer/architecture.md`

### Deliverables
- Complete README
- User guide documentation
- Developer/contributor guide

### Success Criteria
- [ ] New users can install and use without help
- [ ] All commands documented
- [ ] Plugin developers have clear guide

---

## Milestone 12: Distribution

**Goal**: Package and distribute llm-box.

### Tasks

#### 12.1 PyPI
- [ ] Finalize `pyproject.toml`
- [ ] Create GitHub Actions workflow for PyPI release
- [ ] Test installation: `pip install llm-box`

#### 12.2 Homebrew
- [ ] Create `Formula/llm-box.rb`
- [ ] Set up Homebrew tap repository
- [ ] Create formula update workflow

#### 12.3 Conda
- [ ] Create `conda/meta.yaml`
- [ ] Submit to conda-forge (or personal channel)

#### 12.4 CI/CD
- [ ] Create `.github/workflows/ci.yml` (test on push)
- [ ] Create `.github/workflows/release.yml` (publish on tag)
- [ ] Multi-platform testing (Linux, macOS, Windows)
- [ ] Multi-Python testing (3.10, 3.11, 3.12)

### Deliverables
- Published PyPI package
- Homebrew formula
- Conda package
- Automated CI/CD

### Success Criteria
- [ ] `pip install llm-box` works
- [ ] `brew install llm-box` works (from tap)
- [ ] `conda install llm-box` works
- [ ] CI runs on every PR
- [ ] Releases auto-publish on tag

---

## Milestone Summary

| # | Milestone | Key Deliverable |
|---|-----------|-----------------|
| 1 | Foundation | Project structure, config, logging |
| 2 | Provider Abstraction | Multi-provider LLM support |
| 3 | Caching Layer | DuckDB cache with TTL |
| 4 | Command Framework | CLI with formatters |
| 5 | Core Commands | ls, cat commands |
| 6 | Search System | Semantic + fuzzy search |
| 7 | Additional Commands | tldr, why, ask, run, fix, doc, plan |
| 8 | Plugin System | Extensibility framework |
| 9 | Telemetry & Stats | Usage statistics |
| 10 | Testing | >80% coverage |
| 11 | Documentation | User & developer guides |
| 12 | Distribution | PyPI, Homebrew, Conda |

---

## Dependencies Between Milestones

```
M1 (Foundation)
 │
 ├──► M2 (Providers)
 │     │
 │     └──► M3 (Caching)
 │           │
 │           └──► M4 (Command Framework)
 │                 │
 │                 ├──► M5 (Core Commands)
 │                 │     │
 │                 │     └──► M6 (Search) ──► M7 (Additional Commands)
 │                 │
 │                 └──► M8 (Plugins)
 │
 └──► M9 (Telemetry) ─────────────────────────────────────────┐
                                                               │
M10 (Testing) ◄── Can start after M5, runs parallel ──────────┤
                                                               │
M11 (Documentation) ◄── Can start after M5, runs parallel ────┤
                                                               │
M12 (Distribution) ◄── Requires M10, M11 complete ────────────┘
```

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| DuckDB vector ops slow | Medium | Benchmark early; consider FAISS fallback |
| LangChain API changes | Medium | Pin versions; abstract behind our wrapper |
| Ollama not available | Low | Mock provider for development; clear error messages |
| Large file handling | Medium | Chunking strategy; memory limits |

### Schedule Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Scope creep | High | Strict milestone boundaries; defer features |
| Provider complexity | Medium | Start with Ollama only; add others incrementally |
| Testing overhead | Medium | Write tests alongside features, not after |

---

## Definition of Done

A milestone is complete when:

1. **Code**: All tasks checked off
2. **Tests**: Unit tests pass, coverage maintained
3. **Lint**: `ruff check .` passes
4. **Types**: `mypy src/llm_box` passes
5. **Docs**: README/docstrings updated
6. **Review**: Code reviewed (if team)

---

## See Also

- [architecture.md](./architecture.md) - Technical architecture
- [commands.md](./commands.md) - Command specifications
- [distribution.md](./distribution.md) - Packaging details
