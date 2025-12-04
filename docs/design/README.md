# llm-box Design Documentation

This directory contains the technical design documentation for llm-box, an LLM-powered terminal toolbox.

## Documents

| Document | Description |
|----------|-------------|
| [architecture.md](./architecture.md) | High-level system architecture, project structure, and data flow |
| [providers.md](./providers.md) | LLM provider abstraction layer (Ollama, OpenAI, Anthropic) |
| [commands.md](./commands.md) | Command pattern design and implementation |
| [search.md](./search.md) | Search system (semantic + fuzzy matching) |
| [caching.md](./caching.md) | DuckDB caching strategy and schema |
| [distribution.md](./distribution.md) | Packaging for pip, Homebrew, and Conda |
| [project-plan.md](./project-plan.md) | **Project plan with milestones and deliverables** |

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI Layer (Typer)                        │
├─────────────────────────────────────────────────────────────────┤
│                        Command Layer                             │
│  ┌─────┐ ┌─────┐ ┌──────┐ ┌──────┐ ┌─────┐ ┌─────┐ ┌─────────┐ │
│  │ ls  │ │ cat │ │ find │ │ tldr │ │ why │ │ ask │ │ plugins │ │
│  └─────┘ └─────┘ └──────┘ └──────┘ └─────┘ └─────┘ └─────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                        Core Services                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │   Providers  │  │    Cache     │  │    Search    │           │
│  │  (LangChain) │  │   (DuckDB)   │  │ (Embeddings) │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
├─────────────────────────────────────────────────────────────────┤
│                     Infrastructure                               │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌─────────────────┐ │
│  │  Config  │  │  Logging  │  │ Telemetry│  │ Error Handling  │ │
│  └──────────┘  └───────────┘  └──────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

### 1. LangChain + LangGraph for LLM Abstraction
- Unified interface across Ollama, OpenAI, and Anthropic
- Built-in streaming, retry logic, and embedding support
- Future support for multi-step agent workflows

### 2. DuckDB for Persistence
- Single database for caching and vector embeddings
- Native array operations for cosine similarity
- Lightweight, embedded, no server required

### 3. Plugin System
- Extensible command and provider architecture
- Dynamic discovery from `~/.config/llm-box/plugins/`
- TOML-based plugin manifests

### 4. Search: Semantic + Fuzzy
- Semantic search via vector embeddings (LLM-powered)
- Fuzzy matching via rapidfuzz (string similarity)
- Combined ranking with configurable weights

## Milestones

See [project-plan.md](./project-plan.md) for detailed milestone breakdown.

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

## Related Files

- [Full architecture plan](/Users/vbarooah/.claude/plans/adaptive-twirling-fog.md)
- [Project README](/Users/vbarooah/llm-box/llm-box/README.md)
- [Command roadmap](/Users/vbarooah/llm-box/llm-box/commands_tiers.md)
