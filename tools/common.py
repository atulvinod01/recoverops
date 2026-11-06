"""Shared helpers for RecoverOps tools: repo paths, CSV loading, dollar formatting, JSON output."""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def rows(name):
    """All rows of data/<name>.csv as dicts, in file order."""
    with open(DATA / f"{name}.csv", newline="") as f:
        return list(csv.DictReader(f))


def usd(n):
    """US dollars with thousands separators: 100000 -> '$100,000'. Agents quote this string verbatim."""
    return ("-" if n < 0 else "") + f"${abs(int(n)):,}"


def out(obj, code=0):
    print(json.dumps(obj, indent=2, ensure_ascii=False))
    sys.exit(code)


def fail(msg):
    out({"error": msg}, 1)


if __name__ == "__main__":
    assert usd(100000) == "$100,000"
    assert usd(18000) == "$18,000"
    assert usd(500) == "$500"
    assert usd(12345678) == "$12,345,678"
    assert usd(-3700) == "-$3,700"
    print("ok")
