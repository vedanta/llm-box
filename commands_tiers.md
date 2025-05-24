# 📦 llm-box Command Roadmap & Implementation Tracker

This document outlines all planned and in-progress CLI commands for `llm-box`, grouped by implementation tier. Each command is LLM-enhanced, semantic-aware, and locally runnable using Ollama + LangChain.

---

## ✅ Tier 1: Core CLI Enhancements

| Command        | Status | Description |
|----------------|--------|-------------|
| `--llm-ls`     | ✅ Done | LLM-enhanced `ls`. Lists files/folders with a one-line LLM description. |
| `--llm-cat`    | 🟡 In Progress | LLM-enhanced `cat`. Summarizes file contents, especially long text or code files. |
| `--llm-find`   | ⬜️ Planned | Semantic search. Query folder like: “Find files related to authentication config.” |
| `--llm-tldr`   | ⬜️ Planned | TLDR of long files. Compress logs, markdown docs, scripts into readable summaries. |
| `--llm-why`    | ⬜️ Planned | Answer: "Why is this file or folder here?" Based on content, name, and context. |

---

## 🧪 Tier 2: Output & UX Features

| Feature              | Status | Description |
|----------------------|--------|-------------|
| `--json`             | ⬜️ Planned | Output in JSON format for programmatic use. |
| `--ignore-hidden`    | ⬜️ Planned | Skip files/folders starting with `.` |
| Output formatting    | ⬜️ Planned | Use `rich` to color-code folders, files, errors. |
| Width auto-alignment | ⬜️ Planned | Align columns for better display. |
| Emoji/icons support  | ⬜️ Planned | Prefix items with 📄, 📁, ⚠️ etc. based on type. |

---

## 🧠 Tier 3: Intelligent Actions

| Command         | Status | Description |
|------------------|--------|-------------|
| `--llm-run`      | ⬜️ Planned | "What does this script do?" Summarize a `.py`, `.sh`, or `.sql` file without running it. |
| `--llm-fix`      | ⬜️ Planned | Suggest fixes for broken scripts or configs using LLM reasoning. |
| `--llm-doc`      | ⬜️ Planned | Generate or summarize documentation from code. |
| `--llm-ask`      | ⬜️ Planned | Ask a question about the content of a file or folder (Q&A mode). |
| `--llm-plan`     | ⬜️ Planned | Convert `TODO`, `roadmap.md`, or project folder into a plan of action. |

---

## 📈 Implementation Tracker

| ID | Feature/Command | Status       | Notes |
|----|------------------|--------------|-------|
| 1  | `--llm-ls`        | ✅ Done       | Fully working, single-line summaries from Llama3 |
| 2  | `--llm-cat`       | 🟡 In Progress| Needs content sampling and prompt tuning |
| 3  | `--llm-find`      | ⬜️ Planned    | Requires content indexing or summary-first search |
| 4  | `--llm-tldr`      | ⬜️ Planned    | Prompt chaining or chunking large inputs |
| 5  | JSON output       | ⬜️ Planned    | Format output as structured dictionary |
| 6  | Prompt tuning     | ✅ Done       | One-liner prompt refines verbosity and clarity |
| 7  | `alias.sh`        | ✅ Done       | Automatically loads commands via $LLMBOX_HOME |

---

✅ Legend:
- ✅ Done
- 🟡 In Progress
- ⬜️ Planned