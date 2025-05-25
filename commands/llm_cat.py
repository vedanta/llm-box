# commands/llm_cat.py

from llm.ollama_client import summarize_file_content
from utils.file_scanner import sample_file_content
import os

def llm_cat(filepath: str):
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return

    if os.path.isdir(filepath):
        print(f"❌ '{filepath}' is a directory. Please provide a file.")
        return

    content = sample_file_content(filepath, max_bytes=3000)
    if not content:
        print(f"⚠️ Could not read content from: {filepath}")
        return

    summary = summarize_file_content(content)
    print(f"📄 {filepath}\n\n📝 Summary:\n{summary}")
