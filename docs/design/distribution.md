# Distribution Design

## Overview

llm-box will be distributed through three package managers:
1. **PyPI** - Primary Python package (`pip install llm-box`)
2. **Homebrew** - macOS users (`brew install llm-box`)
3. **Conda** - Data science/ML workflows (`conda install llm-box`)

## PyPI Distribution

### pyproject.toml

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "llm-box"
version = "0.1.0"
description = "LLM-powered terminal toolbox"
readme = "README.md"
license = "MIT"
requires-python = ">=3.10"
authors = [
    { name = "Your Name", email = "you@example.com" }
]
keywords = ["llm", "cli", "terminal", "ai", "ollama", "openai", "langchain"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Environment :: Console",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Topic :: Utilities",
]

dependencies = [
    "typer>=0.9.0",
    "rich>=13.0.0",
    "duckdb>=0.9.0",
    "pydantic>=2.0.0",
    "langchain-core>=0.3.0",
    "langgraph>=0.2.0",
    "rapidfuzz>=3.0.0",
    "tenacity>=8.0.0",
]

[project.optional-dependencies]
ollama = [
    "langchain-ollama>=0.3.0",
]
openai = [
    "langchain-openai>=0.2.0",
]
anthropic = [
    "langchain-anthropic>=0.2.0",
]
all = [
    "llm-box[ollama,openai,anthropic]",
]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.0.0",
    "mypy>=1.0.0",
    "ruff>=0.1.0",
    "pre-commit>=3.0.0",
]

[project.scripts]
# Primary CLI
llm-box = "llm_box.cli.app:main"

# Shortcut aliases
llm-ls = "llm_box.cli.shortcuts:ls_main"
llm-cat = "llm_box.cli.shortcuts:cat_main"
llm-find = "llm_box.cli.shortcuts:find_main"
llm-ask = "llm_box.cli.shortcuts:ask_main"

[project.urls]
Homepage = "https://github.com/yourname/llm-box"
Documentation = "https://github.com/yourname/llm-box#readme"
Repository = "https://github.com/yourname/llm-box"
Issues = "https://github.com/yourname/llm-box/issues"

[tool.hatch.build.targets.wheel]
packages = ["src/llm_box"]

[tool.hatch.build.targets.sdist]
include = [
    "/src",
    "/tests",
    "/README.md",
    "/LICENSE",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "-v --cov=llm_box --cov-report=term-missing"

[tool.mypy]
python_version = "3.10"
strict = true
ignore_missing_imports = true

[tool.ruff]
target-version = "py310"
line-length = 88
select = ["E", "F", "I", "N", "W", "UP"]

[tool.ruff.isort]
known-first-party = ["llm_box"]
```

### Installation Commands

```bash
# Basic installation (no LLM providers)
pip install llm-box

# With Ollama support (local LLMs)
pip install llm-box[ollama]

# With OpenAI support
pip install llm-box[openai]

# With all providers
pip install llm-box[all]

# Development installation
pip install -e ".[dev,all]"
```

### Publishing Workflow

```yaml
# .github/workflows/release.yml

name: Release to PyPI

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install build tools
        run: pip install build twine

      - name: Build package
        run: python -m build

      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}
        run: twine upload dist/*
```

## Homebrew Distribution

### Formula

```ruby
# Formula/llm-box.rb

class LlmBox < Formula
  include Language::Python::Virtualenv

  desc "LLM-powered terminal toolbox"
  homepage "https://github.com/yourname/llm-box"
  url "https://files.pythonhosted.org/packages/source/l/llm-box/llm_box-0.1.0.tar.gz"
  sha256 "PLACEHOLDER_SHA256"
  license "MIT"
  head "https://github.com/yourname/llm-box.git", branch: "main"

  depends_on "python@3.11"

  resource "typer" do
    url "https://files.pythonhosted.org/packages/..."
    sha256 "..."
  end

  resource "rich" do
    url "https://files.pythonhosted.org/packages/..."
    sha256 "..."
  end

  resource "duckdb" do
    url "https://files.pythonhosted.org/packages/..."
    sha256 "..."
  end

  resource "pydantic" do
    url "https://files.pythonhosted.org/packages/..."
    sha256 "..."
  end

  resource "langchain-core" do
    url "https://files.pythonhosted.org/packages/..."
    sha256 "..."
  end

  resource "langchain-ollama" do
    url "https://files.pythonhosted.org/packages/..."
    sha256 "..."
  end

  # ... more resources

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "llm-box", shell_output("#{bin}/llm-box --version")
    assert_match "Usage:", shell_output("#{bin}/llm-box --help")
  end
end
```

### Installation Commands

```bash
# Install from tap
brew tap yourname/llm-box
brew install llm-box

# Or direct installation (once in homebrew-core)
brew install llm-box
```

### Formula Update Workflow

```yaml
# .github/workflows/homebrew.yml

name: Update Homebrew Formula

on:
  release:
    types: [published]

jobs:
  update-formula:
    runs-on: macos-latest
    steps:
      - name: Update Homebrew formula
        uses: dawidd6/action-homebrew-bump-formula@v3
        with:
          token: ${{ secrets.HOMEBREW_TAP_TOKEN }}
          tap: yourname/homebrew-llm-box
          formula: llm-box
```

## Conda Distribution

### meta.yaml

```yaml
# conda/meta.yaml

package:
  name: llm-box
  version: "0.1.0"

source:
  url: https://pypi.io/packages/source/l/llm-box/llm_box-0.1.0.tar.gz
  sha256: PLACEHOLDER_SHA256

build:
  number: 0
  noarch: python
  script: python -m pip install . -vv
  entry_points:
    - llm-box = llm_box.cli.app:main
    - llm-ls = llm_box.cli.shortcuts:ls_main
    - llm-cat = llm_box.cli.shortcuts:cat_main
    - llm-find = llm_box.cli.shortcuts:find_main

requirements:
  host:
    - python >=3.10
    - pip
    - hatchling
  run:
    - python >=3.10
    - typer >=0.9.0
    - rich >=13.0.0
    - duckdb >=0.9.0
    - pydantic >=2.0.0
    - langchain-core >=0.3.0
    - langgraph >=0.2.0
    - rapidfuzz >=3.0.0
    - tenacity >=8.0.0

test:
  imports:
    - llm_box
  commands:
    - llm-box --help
    - llm-box --version

about:
  home: https://github.com/yourname/llm-box
  license: MIT
  license_family: MIT
  license_file: LICENSE
  summary: LLM-powered terminal toolbox
  description: |
    llm-box brings AI to your terminal. A local LLM-powered toolbox
    that explains files, folders, and scripts using semantic search
    and natural language understanding.
  dev_url: https://github.com/yourname/llm-box

extra:
  recipe-maintainers:
    - yourname
```

### Installation Commands

```bash
# Install from conda-forge (once available)
conda install -c conda-forge llm-box

# Or from your channel
conda install -c yourname llm-box
```

## Version Management

### Version in Code

```python
# src/llm_box/__init__.py

__version__ = "0.1.0"
```

### Version Bumping

Use `hatch` for version management:

```bash
# Bump patch version (0.1.0 -> 0.1.1)
hatch version patch

# Bump minor version (0.1.0 -> 0.2.0)
hatch version minor

# Bump major version (0.1.0 -> 1.0.0)
hatch version major
```

## CI/CD Pipeline

### Full Workflow

```yaml
# .github/workflows/ci.yml

name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ['3.10', '3.11', '3.12']

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev,all]"

      - name: Lint with ruff
        run: ruff check .

      - name: Type check with mypy
        run: mypy src/llm_box

      - name: Test with pytest
        run: pytest --cov=llm_box --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml

  build:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Build package
        run: |
          pip install build
          python -m build

      - name: Check package
        run: |
          pip install twine
          twine check dist/*

      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: dist
          path: dist/
```

## Release Checklist

1. **Pre-release**
   - [ ] Update CHANGELOG.md
   - [ ] Run full test suite
   - [ ] Update version number
   - [ ] Update documentation

2. **Release**
   - [ ] Create git tag: `git tag v0.1.0`
   - [ ] Push tag: `git push origin v0.1.0`
   - [ ] GitHub Actions publishes to PyPI

3. **Post-release**
   - [ ] Update Homebrew formula
   - [ ] Update Conda recipe
   - [ ] Announce release

## Installation Verification

After installation, verify with:

```bash
# Check version
llm-box --version

# Check help
llm-box --help

# Test with Ollama (if running)
llm-box ls .

# Check configuration
llm-box config
```

## See Also

- [architecture.md](./architecture.md) - Overall system architecture
- [commands.md](./commands.md) - Command documentation
- [README.md](../../README.md) - User-facing documentation
