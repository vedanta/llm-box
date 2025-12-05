"""Cache key generation utilities.

This module provides functions for generating consistent cache keys
for different types of LLM operations.
"""

from pathlib import Path
from typing import Any

from llm_box.utils.hashing import hash_content, hash_file, hash_file_metadata


def generate_cache_key(
    command: str,
    provider: str,
    model: str,
    *,
    prompt: str | None = None,
    file_path: Path | None = None,
    use_file_content: bool = True,
    extra_params: dict[str, Any] | None = None,
) -> str:
    """Generate a cache key for an LLM operation.

    The key format is: {command}:{provider}:{model}:{content_hash}

    Args:
        command: The command name (e.g., "ls", "cat", "explain").
        provider: The LLM provider name (e.g., "ollama", "openai").
        model: The model name (e.g., "llama3", "gpt-4o-mini").
        prompt: The prompt text (optional, hashed if provided).
        file_path: Path to file being processed (optional).
        use_file_content: If True, hash file contents; if False, use metadata.
        extra_params: Additional parameters to include in the key.

    Returns:
        A unique cache key string.
    """
    import json

    # Build the key components
    components: dict[str, str] = {
        "cmd": command,
        "provider": provider,
        "model": model,
    }

    # Add prompt hash if provided
    if prompt:
        components["prompt"] = hash_content(prompt, 16)

    # Add file hash if provided
    if file_path:
        if use_file_content and file_path.exists():
            components["file"] = hash_file(file_path, 16)
        elif file_path.exists():
            components["file"] = hash_file_metadata(file_path, 16)
        else:
            # For non-existent files, hash the path
            components["file"] = hash_content(str(file_path), 16)

    # Add extra parameters
    if extra_params:
        # Hash extra params as a unit
        extra_str = json.dumps(extra_params, sort_keys=True)
        components["extra"] = hash_content(extra_str, 8)

    # Build the final key
    key_parts = [
        components["cmd"],
        components["provider"],
        components["model"],
    ]

    # Add content hash (combines prompt, file, and extra params)
    content_parts = []
    if "prompt" in components:
        content_parts.append(components["prompt"])
    if "file" in components:
        content_parts.append(components["file"])
    if "extra" in components:
        content_parts.append(components["extra"])

    if content_parts:
        content_hash = hash_content(":".join(content_parts), 24)
        key_parts.append(content_hash)

    return ":".join(key_parts)


def generate_prompt_key(
    command: str,
    provider: str,
    model: str,
    prompt: str,
) -> str:
    """Generate a cache key for a prompt-based operation.

    Shorthand for generate_cache_key with just a prompt.

    Args:
        command: The command name.
        provider: The LLM provider name.
        model: The model name.
        prompt: The prompt text.

    Returns:
        A unique cache key string.
    """
    return generate_cache_key(
        command=command,
        provider=provider,
        model=model,
        prompt=prompt,
    )


def generate_file_key(
    command: str,
    provider: str,
    model: str,
    file_path: Path,
    prompt: str | None = None,
    use_content: bool = True,
) -> str:
    """Generate a cache key for a file-based operation.

    Shorthand for generate_cache_key with a file path.

    Args:
        command: The command name.
        provider: The LLM provider name.
        model: The model name.
        file_path: Path to the file being processed.
        prompt: Optional additional prompt.
        use_content: If True, hash file contents; if False, use metadata.

    Returns:
        A unique cache key string.
    """
    return generate_cache_key(
        command=command,
        provider=provider,
        model=model,
        prompt=prompt,
        file_path=file_path,
        use_file_content=use_content,
    )


def parse_cache_key(key: str) -> dict[str, str]:
    """Parse a cache key into its components.

    Args:
        key: The cache key to parse.

    Returns:
        Dictionary with 'command', 'provider', 'model', and optionally 'hash'.
    """
    parts = key.split(":")

    result: dict[str, str] = {}

    if len(parts) >= 1:
        result["command"] = parts[0]
    if len(parts) >= 2:
        result["provider"] = parts[1]
    if len(parts) >= 3:
        result["model"] = parts[2]
    if len(parts) >= 4:
        result["hash"] = parts[3]

    return result
