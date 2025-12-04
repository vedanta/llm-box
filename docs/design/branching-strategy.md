# Branching Strategy

## Overview

This document defines the Git branching strategy for llm-box development, designed to support milestone-based development with clear feature isolation.

---

## Branch Types

### Main Branches

| Branch | Purpose | Protected |
|--------|---------|-----------|
| `main` | Production-ready code, releases | Yes |
| `develop` | Integration branch for ongoing work | Yes |

### Milestone Branches

| Pattern | Purpose | Lifecycle |
|---------|---------|-----------|
| `milestone-{n}` | Milestone integration branch | Created at milestone start, merged to `develop` at completion |

Examples:
- `milestone-1` (Foundation)
- `milestone-2` (Provider Abstraction)
- `milestone-6` (Search System)

### Feature Branches

| Pattern | Purpose | Base Branch |
|---------|---------|-------------|
| `feature/{description}` | New features | `milestone-{n}` or `develop` |
| `feature/{milestone}-{description}` | Milestone-specific feature | `milestone-{n}` |

Examples:
- `feature/ollama-provider`
- `feature/1-config-loader`
- `feature/6-semantic-search`

### Other Branch Types

| Pattern | Purpose | Base Branch |
|---------|---------|-------------|
| `bugfix/{description}` | Bug fixes | `develop` or `milestone-{n}` |
| `hotfix/{description}` | Urgent production fixes | `main` |
| `docs/{description}` | Documentation only | `develop` |
| `refactor/{description}` | Code refactoring | `develop` or `milestone-{n}` |
| `test/{description}` | Test additions/fixes | `develop` or `milestone-{n}` |
| `chore/{description}` | Maintenance tasks | `develop` |

---

## Branch Hierarchy

```
main (releases)
 │
 └── develop (integration)
      │
      ├── milestone-1 (Foundation)
      │    ├── feature/1-project-setup
      │    ├── feature/1-config-loader
      │    ├── feature/1-exception-hierarchy
      │    └── feature/1-logging
      │
      ├── milestone-2 (Providers)
      │    ├── feature/2-base-provider
      │    ├── feature/2-ollama-provider
      │    ├── feature/2-openai-provider
      │    └── feature/2-anthropic-provider
      │
      ├── milestone-3 (Caching)
      │    ├── feature/3-duckdb-cache
      │    ├── feature/3-cache-keys
      │    └── feature/3-cache-cli
      │
      ├── milestone-4 (Command Framework)
      │    ├── feature/4-base-command
      │    ├── feature/4-output-formatters
      │    └── feature/4-cli-app
      │
      ├── milestone-5 (Core Commands)
      │    ├── feature/5-ls-command
      │    ├── feature/5-cat-command
      │    └── feature/5-error-handling
      │
      ├── milestone-6 (Search)
      │    ├── feature/6-file-indexer
      │    ├── feature/6-semantic-search
      │    ├── feature/6-fuzzy-search
      │    └── feature/6-find-command
      │
      └── ... (milestones 7-12)
```

---

## Workflow

### Starting a New Milestone

```bash
# Create milestone branch from develop
git checkout develop
git pull origin develop
git checkout -b milestone-1
git push -u origin milestone-1
```

### Working on a Feature

```bash
# Create feature branch from milestone
git checkout milestone-1
git pull origin milestone-1
git checkout -b feature/1-config-loader

# Work on feature...
git add .
git commit -m "Add TOML config loader"

# Push and create PR
git push -u origin feature/1-config-loader
# PR: feature/1-config-loader → milestone-1
```

### Completing a Feature

1. Create PR: `feature/1-config-loader` → `milestone-1`
2. Code review
3. Squash merge (recommended) or merge commit
4. Delete feature branch

### Completing a Milestone

```bash
# All features merged to milestone-1
# Create PR: milestone-1 → develop
git checkout develop
git pull origin develop
git merge milestone-1  # or PR with merge commit
git push origin develop

# Tag the milestone completion
git tag -a v0.1.0-m1 -m "Milestone 1: Foundation complete"
git push origin v0.1.0-m1
```

### Creating a Release

```bash
# From develop, create release
git checkout main
git pull origin main
git merge develop
git push origin main

# Tag release
git tag -a v0.1.0 -m "Release 0.1.0"
git push origin v0.1.0
```

### Hotfix Workflow

```bash
# Urgent fix needed on production
git checkout main
git checkout -b hotfix/critical-bug

# Fix the bug...
git commit -m "Fix critical bug in provider"

# PR: hotfix/critical-bug → main
# After merge, backport to develop
git checkout develop
git cherry-pick <hotfix-commit>
git push origin develop
```

---

## Naming Conventions

### Branch Names

- Use lowercase
- Use hyphens for word separation
- Keep names concise but descriptive
- Include milestone number for milestone-related work

**Good:**
```
feature/1-config-loader
feature/6-semantic-search
bugfix/cache-ttl-expiration
hotfix/provider-timeout
docs/user-guide
```

**Bad:**
```
feature/ConfigLoader          # No caps
feature/config_loader         # No underscores
my-feature                    # Not descriptive
feature/implement-the-config-loading-functionality  # Too long
```

### Commit Messages

Follow conventional commits format:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance

**Examples:**
```
feat(providers): add Ollama provider with embeddings support

fix(cache): handle TTL expiration correctly

docs(readme): update installation instructions

refactor(commands): extract base command logic

test(search): add semantic search unit tests

chore(deps): update langchain to 0.3.1
```

---

## Pull Request Guidelines

### PR Title Format

```
[M{n}] <type>: <description>
```

Examples:
- `[M1] feat: add TOML config loader`
- `[M6] feat: implement semantic search`
- `[M3] fix: cache key collision`

### PR Description Template

```markdown
## Summary
Brief description of changes.

## Related Milestone
Milestone-{n}: {Milestone Name}

## Changes
- Change 1
- Change 2

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests (if applicable)
- [ ] Manual testing performed

## Checklist
- [ ] Code follows project style
- [ ] Self-reviewed
- [ ] Documentation updated (if needed)
```

### Merge Strategy

| PR Type | Merge Strategy |
|---------|----------------|
| `feature/*` → `milestone-*` | Squash merge |
| `bugfix/*` → `milestone-*` | Squash merge |
| `milestone-*` → `develop` | Merge commit |
| `develop` → `main` | Merge commit |
| `hotfix/*` → `main` | Merge commit |

---

## Tag Strategy

### Version Tags

Follow semantic versioning: `v{major}.{minor}.{patch}`

| Tag | When |
|-----|------|
| `v0.1.0` | First release (after M12) |
| `v0.1.1` | Patch release |
| `v0.2.0` | Minor release |
| `v1.0.0` | Major/stable release |

### Milestone Tags

Track milestone completion: `v0.1.0-m{n}`

| Tag | Milestone |
|-----|-----------|
| `v0.1.0-m1` | Foundation complete |
| `v0.1.0-m2` | Providers complete |
| `v0.1.0-m3` | Caching complete |
| ... | ... |
| `v0.1.0-m12` | Distribution complete → `v0.1.0` |

---

## Branch Protection Rules

### `main` Branch

- Require PR reviews (1 minimum)
- Require status checks to pass
- Require branches to be up to date
- No direct pushes
- No force pushes

### `develop` Branch

- Require PR reviews (1 minimum)
- Require status checks to pass
- No force pushes

### `milestone-*` Branches

- Require status checks to pass
- Allow squash merging only for features

---

## Example: Complete Milestone 1 Workflow

```bash
# 1. Start milestone
git checkout develop
git checkout -b milestone-1
git push -u origin milestone-1

# 2. Work on project setup
git checkout -b feature/1-project-setup
# ... create pyproject.toml, src layout ...
git add .
git commit -m "feat(setup): create project structure with pyproject.toml"
git push -u origin feature/1-project-setup
# Create PR → milestone-1, squash merge

# 3. Work on config loader
git checkout milestone-1
git pull
git checkout -b feature/1-config-loader
# ... implement config ...
git commit -m "feat(config): add TOML config loader with Pydantic"
git push -u origin feature/1-config-loader
# Create PR → milestone-1, squash merge

# 4. Work on exceptions
git checkout milestone-1
git pull
git checkout -b feature/1-exceptions
# ... implement exceptions ...
git commit -m "feat(core): add exception hierarchy"
git push -u origin feature/1-exceptions
# Create PR → milestone-1, squash merge

# 5. Work on logging
git checkout milestone-1
git pull
git checkout -b feature/1-logging
# ... implement logging ...
git commit -m "feat(utils): add structured logging setup"
git push -u origin feature/1-logging
# Create PR → milestone-1, squash merge

# 6. Complete milestone
git checkout milestone-1
git pull
# Create PR → develop (merge commit)

# 7. Tag milestone
git checkout develop
git pull
git tag -a v0.1.0-m1 -m "Milestone 1: Foundation complete"
git push origin v0.1.0-m1

# 8. Start milestone 2
git checkout -b milestone-2
git push -u origin milestone-2
```

---

## CI/CD Integration

### Branch-based Triggers

```yaml
# .github/workflows/ci.yml
on:
  push:
    branches:
      - main
      - develop
      - 'milestone-*'
  pull_request:
    branches:
      - main
      - develop
      - 'milestone-*'
```

### Release Triggers

```yaml
# .github/workflows/release.yml
on:
  push:
    tags:
      - 'v*'
```

---

## Quick Reference

| Action | Command |
|--------|---------|
| Start milestone | `git checkout develop && git checkout -b milestone-{n}` |
| Start feature | `git checkout milestone-{n} && git checkout -b feature/{n}-{desc}` |
| Start bugfix | `git checkout milestone-{n} && git checkout -b bugfix/{desc}` |
| Start hotfix | `git checkout main && git checkout -b hotfix/{desc}` |
| Tag milestone | `git tag -a v0.1.0-m{n} -m "Milestone {n} complete"` |
| Tag release | `git tag -a v{x.y.z} -m "Release {x.y.z}"` |

---

## See Also

- [project-plan.md](./project-plan.md) - Milestone definitions
- [distribution.md](./distribution.md) - Release workflow
