# Homebrew formula for llm-box
# Install with: brew install --build-from-source ./Formula/llm-box.rb
# Or from tap: brew install vedanta/tap/llm-box

class LlmBox < Formula
  include Language::Python::Virtualenv

  desc "LLM-powered terminal toolbox"
  homepage "https://github.com/vedanta/llm-box"
  url "https://github.com/vedanta/llm-box/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "PLACEHOLDER_SHA256"
  license "MIT"
  head "https://github.com/vedanta/llm-box.git", branch: "main"

  depends_on "python@3.11"

  # Core dependencies
  resource "typer" do
    url "https://files.pythonhosted.org/packages/typer/typer-0.9.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "rich" do
    url "https://files.pythonhosted.org/packages/rich/rich-13.7.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "duckdb" do
    url "https://files.pythonhosted.org/packages/duckdb/duckdb-0.9.2.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "pydantic" do
    url "https://files.pythonhosted.org/packages/pydantic/pydantic-2.5.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "pydantic-settings" do
    url "https://files.pythonhosted.org/packages/pydantic-settings/pydantic_settings-2.1.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "langchain-core" do
    url "https://files.pythonhosted.org/packages/langchain-core/langchain_core-0.3.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "langgraph" do
    url "https://files.pythonhosted.org/packages/langgraph/langgraph-0.2.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "rapidfuzz" do
    url "https://files.pythonhosted.org/packages/rapidfuzz/rapidfuzz-3.5.0.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "tenacity" do
    url "https://files.pythonhosted.org/packages/tenacity/tenacity-8.2.3.tar.gz"
    sha256 "PLACEHOLDER"
  end

  def install
    virtualenv_install_with_resources

    # Install the package itself
    system libexec/"bin/pip", "install", "--no-deps", "."

    # Create wrapper scripts for all entry points
    %w[llm-box llm-ls llm-cat llm-find].each do |cmd|
      (bin/cmd).write_env_script(
        libexec/"bin"/cmd,
        PATH: "#{libexec}/bin:$PATH"
      )
    end
  end

  def caveats
    <<~EOS
      llm-box requires an LLM provider to function. You can use:

      1. Ollama (local, recommended):
         brew install ollama
         ollama serve
         ollama pull llama3

      2. OpenAI:
         export OPENAI_API_KEY="your-api-key"

      3. Anthropic:
         export ANTHROPIC_API_KEY="your-api-key"

      Configuration file: ~/.config/llm-box/config.toml
    EOS
  end

  test do
    # Test that the CLI runs
    assert_match "llm-box version", shell_output("#{bin}/llm-box --version")

    # Test help output
    assert_match "LLM-powered terminal toolbox", shell_output("#{bin}/llm-box --help")
  end
end
