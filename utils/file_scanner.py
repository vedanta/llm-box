def sample_file_content(filepath: str, max_bytes: int = 1000) -> str:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read(max_bytes)
    except Exception:
        return ""
