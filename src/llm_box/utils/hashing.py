"""Content and file hashing utilities."""

import hashlib
from pathlib import Path


def hash_content(content: str, length: int = 16) -> str:
    """Hash string content using SHA256.

    Args:
        content: String content to hash.
        length: Length of hash to return (max 64).

    Returns:
        Hex digest truncated to specified length.
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:length]


def hash_bytes(data: bytes, length: int = 16) -> str:
    """Hash bytes using SHA256.

    Args:
        data: Bytes to hash.
        length: Length of hash to return (max 64).

    Returns:
        Hex digest truncated to specified length.
    """
    return hashlib.sha256(data).hexdigest()[:length]


def hash_file(path: Path, length: int = 16) -> str:
    """Hash file contents using SHA256.

    Args:
        path: Path to file.
        length: Length of hash to return (max 64).

    Returns:
        Hex digest truncated to specified length.

    Raises:
        FileNotFoundError: If file doesn't exist.
        IOError: If file cannot be read.
    """
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()[:length]


def hash_file_metadata(path: Path, length: int = 16) -> str:
    """Hash file metadata (path, size, mtime) for cache invalidation.

    This is faster than hashing file contents for large files.

    Args:
        path: Path to file.
        length: Length of hash to return.

    Returns:
        Hex digest based on file metadata.
    """
    stat = path.stat()
    metadata = f"{path.resolve()}:{stat.st_size}:{stat.st_mtime}"
    return hash_content(metadata, length)


def hash_prompt(prompt: str, length: int = 16) -> str:
    """Hash a prompt for cache key generation.

    Args:
        prompt: The prompt string.
        length: Length of hash to return.

    Returns:
        Hex digest of the prompt.
    """
    return hash_content(prompt, length)


def hash_for_cache(
    command: str,
    *,
    content_hash: str | None = None,
    prompt_hash: str | None = None,
    model: str | None = None,
    provider: str | None = None,
    **kwargs: str,
) -> str:
    """Generate a cache key from command parameters.

    Args:
        command: Command name (e.g., 'ls', 'cat').
        content_hash: Hash of file content (if applicable).
        prompt_hash: Hash of prompt (if applicable).
        model: Model name.
        provider: Provider name.
        **kwargs: Additional key-value pairs to include.

    Returns:
        Cache key in format "command:hash".
    """
    import json

    # Build deterministic key data
    key_data = {
        "command": command,
        "content_hash": content_hash,
        "prompt_hash": prompt_hash,
        "model": model,
        "provider": provider,
        **kwargs,
    }

    # Remove None values and sort for deterministic ordering
    key_data = {k: v for k, v in sorted(key_data.items()) if v is not None}

    key_string = json.dumps(key_data, sort_keys=True)
    key_hash = hash_content(key_string, 32)

    return f"{command}:{key_hash}"
