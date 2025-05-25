# 🧠 llm-box

**llm-box** brings AI to your terminal — a local LLM-powered toolbox that explains files, folders, and scripts.

---

## 🚀 What It Does

`llm-box` enhances classic shell commands like `ls`, `cat`, and `find` using a local large language model (LLM). Instead of just listing files, it **describes their purpose**, **summarizes content**, and helps you understand your filesystem — semantically.

---

## ✨ Features

| Command       | Description |
|---------------|-------------|
| `llm-ls`      | Lists and explains files/folders using LLM summaries |
| `llm-cat`     | Summarizes or explains a file's content |
| `llm-find`    | Search for files via natural language (planned) |
| `llm-tldr`    | TLDR of large files like logs or markdown (planned) |

---

## ⚙️ Installation

### 1. Clone the Repo

```bash
git clone https://github.com/yourname/llm-box.git
cd llm-box
```

### 2. Create and Activate Environment (Recommended)

```bash
conda create -n llm-box python=3.10
conda activate llm-box
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 🛠️ Developer Setup

### ✅ Set Up Aliases

Run once per session (or add to your shell config):

```bash
source setup.sh
```

This sets:
- `llm-box`: main CLI
- `llm-ls`: enhanced `ls`
- `llm-cat`, `llm-find`, etc.

### 🔍 Project Structure

```
llm-box/
├── llm-box.py           # Main CLI runner
├── cli.py               # Typer app
├── commands/            # Each command as a module
├── llm/                 # LLM interface (Ollama wrapper)
├── utils/               # Helpers (file scanner, etc.)
├── setup.sh             # Sets aliases and checks dependencies
├── commands_tiers.md    # Command roadmap and status
└── requirements.txt     # pip dependencies
```

---

## 🧠 Powered By

- [Ollama](https://ollama.com) – local LLM engine
- [LangChain](https://www.langchain.com)
- [Typer](https://typer.tiangolo.com) – for CLI magic
- [Python 3.10+](https://www.python.org)

---

## 🤖 Example

```bash
llm-ls .
📄 README.md       – A README file provides essential information about a project or software package.
📁 commands        – Contains CLI command implementations like llm-ls.
```

---

## 📌 Roadmap

See [commands_tiers.md](./commands_tiers.md) for the full feature roadmap.