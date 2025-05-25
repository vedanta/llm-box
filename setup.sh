#!/bin/bash

# 🌟 llm-box Setup Script
# Usage: source setup.sh

export LLMBOX_HOME="$HOME/llm-box"
echo "🔧 Setting up llm-box aliases from $LLMBOX_HOME"
echo ""

# Set aliases
alias llm-box="python $LLMBOX_HOME/llm-box.py"
echo "✅ alias llm-box: runs the CLI with Typer"

alias llm-ls="llm-box --llm-ls"
echo "✅ alias llm-ls: lists files/folders with LLM-powered descriptions"

alias llm-cat="llm-box --llm-cat"
echo "✅ alias llm-cat: summarizes or explains a file’s contents"

alias llm-find="llm-box --llm-find"
echo "✅ alias llm-find: finds files via natural language (semantic search)"

alias llm-tldr="llm-box --llm-tldr"
echo "✅ alias llm-tldr: gives a TL;DR for large files (logs, docs)"

alias llm-help="llm-box --help"
echo "✅ alias llm-help: displays the help menu"

echo ""

# Check required Python packages
required_pkgs=("typer" "langchain" "langchain_ollama" "rich")

echo "🔍 Checking Python dependencies in current environment ($(which python))..."
missing=0
for pkg in "${required_pkgs[@]}"; do
    python -c "import $pkg" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "❌ Missing: $pkg"
        missing=1
    else
        echo "✅ Found: $pkg"
    fi
done

if [ $missing -eq 1 ]; then
    echo ""
    echo "⚠️  Some packages are missing. Run the following to install them:"
    echo "pip install typer langchain langchain-ollama rich"
else
    echo ""
    echo "🎉 All required Python packages are installed!"
fi

echo ""
echo "✨ llm-box CLI is ready. Try: llm-ls ."