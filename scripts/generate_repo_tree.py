#!/usr/bin/env python3
import os

# Move to project root (parent of scripts/)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

OUTPUT_FILE = "docs/repository_tree.md"
EXCLUDE = {".git", "node_modules", "__pycache__", ".venv", "dist", "build"}

def list_dirs(path):
    try:
        return sorted(
            d for d in os.listdir(path)
            if os.path.isdir(os.path.join(path, d)) and d not in EXCLUDE
        )
    except Exception:
        return []

def walk(path, prefix=""):
    dirs = list_dirs(path)
    for i, d in enumerate(dirs):
        connector = "└── " if i == len(dirs) - 1 else "├── "
        yield prefix + connector + d
        new_prefix = prefix + ("    " if i == len(dirs) - 1 else "│   ")
        yield from walk(os.path.join(path, d), new_prefix)

def ensure_parent_dir(path):
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)

def generate_tree():
    ensure_parent_dir(OUTPUT_FILE)

    lines = ["# Repository Directory Tree", "```"]
    lines.extend(walk("."))
    lines.append("```")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Tree written to {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_tree()
