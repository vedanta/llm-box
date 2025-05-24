# Alias setup for llm-box CLI
# Usage: source alias.sh
export LLMBOX_HOME="$HOME/llm-box"
alias llm-box="python $LLMBOX_HOME/llm-box.py"
alias llm-ls="llm-box --llm-ls"
# Future commands
alias llm-cat="llm-box --llm-cat"
alias llm-find="llm-box --llm-find"
alias llm-tldr="llm-box --llm-tldr"
alias llm-help="llm-box --help"
echo "✅ llm-box aliases loaded. Root: $LLMBOX_HOME"
