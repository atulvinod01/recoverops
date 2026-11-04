"""Shared helpers for RecoverOps tools: repo paths, CSV loading, rupee formatting, JSON output."""
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


def inr(n):
    """Indian-grouped rupees: 100000 -> '₹1,00,000'. Agents quote this string verbatim."""
    s = str(abs(int(n)))
    head, tail = s[:-3], s[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ("-" if n < 0 else "") + "₹" + ",".join(groups + [tail])


def out(obj, code=0):
    print(json.dumps(obj, indent=2, ensure_ascii=False))
    sys.exit(code)


def fail(msg):
    out({"error": msg}, 1)


if __name__ == "__main__":
    assert inr(100000) == "₹1,00,000"
    assert inr(18000) == "₹18,000"
    assert inr(500) == "₹500"
    assert inr(12345678) == "₹1,23,45,678"
    assert inr(-3700) == "-₹3,700"
    print("ok")
