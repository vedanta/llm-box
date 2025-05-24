import os
from llm.ollama_client import ask_llm
from utils.file_scanner import sample_file_content

def llm_ls(path: str):
    print(f"📁 Scanning path: {path}\n")

    if not os.path.exists(path):
        print("❌ Path does not exist.")
        return

    entries = sorted(os.scandir(path), key=lambda e: e.name)

    for entry in entries:
        name = entry.name

        # Skip hidden files for now
        if name.startswith("."):
            continue

        if entry.is_file():
            content = sample_file_content(entry.path)
            desc = ask_llm(name, content)
            print(f"📄 {name:30} – {desc}")
        elif entry.is_dir():
            desc = ask_llm(name, None)
            print(f"📁 {name:30} – {desc}")
