"""Spike tool: proves an agent can run a repo script and that the script finds repo data.

Usage: python3 ../../tools/hello.py <agent-name>
Prints JSON. Paths resolve from this file, not the caller's cwd, so it works from any agent folder.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

print(json.dumps({
    "hello": sys.argv[1] if len(sys.argv) > 1 else "anonymous",
    "cwd": os.getcwd(),
    "repo_root": str(ROOT),
    "test_txt": (ROOT / "data" / "test.txt").read_text().strip(),
}))
