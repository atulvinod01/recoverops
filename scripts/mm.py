"""Post to and read the local Mattermost as a test user, so scenario runs can be scripted.

  python3 scripts/mm.py say  <finance|sales|user> <channel> "<message>" [--thread ROOT_POST_ID]
  python3 scripts/mm.py read <channel> [--thread ROOT_POST_ID] [-n 20]

Tokens come from .env (gitignored): MM_URL, MM_TEAM, MM_TOKEN_FINANCE, MM_TOKEN_SALES, MM_TOKEN_USER.
`say` prints the new post id; use it as --thread to reply in or read that thread.
"""
import argparse
import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV = dict(
    line.split("=", 1) for line in (ROOT / ".env").read_text().splitlines() if "=" in line
)
URL = ENV["MM_URL"].rstrip("/") + "/api/v4"
READER = "user"  # any member token can read the channel


def api(who, method, path, body=None):
    req = urllib.request.Request(
        URL + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Authorization": "Bearer " + ENV["MM_TOKEN_" + who.upper()],
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def channel_id(who, name):
    return api(who, "GET", f"/teams/name/{ENV['MM_TEAM']}/channels/name/{name}")["id"]


def say(who, channel, message, thread=None):
    body = {"channel_id": channel_id(who, channel), "message": message}
    if thread:
        body["root_id"] = thread
    return api(who, "POST", "/posts", body)["id"]


def read(channel, thread=None, n=20):
    if thread:
        data = api(READER, "GET", f"/posts/{thread}/thread")
    else:
        data = api(READER, "GET", f"/channels/{channel_id(READER, channel)}/posts?per_page={n}")
    posts = sorted(data["posts"].values(), key=lambda p: p["create_at"])[-n:]
    names = {}
    for p in posts:
        uid = p["user_id"]
        if uid not in names:
            names[uid] = api(READER, "GET", f"/users/{uid}")["username"]
        when = datetime.fromtimestamp(p["create_at"] / 1000).strftime("%H:%M:%S")
        where = f"in-thread {p['root_id'][:8]}" if p["root_id"] else "top-level"
        print(f"{when} {p['id'][:8]} [{names[uid]}] ({where}) {p['message']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("say")
    s.add_argument("who", choices=["finance", "sales", "user"])
    s.add_argument("channel")
    s.add_argument("message")
    s.add_argument("--thread")
    r = sub.add_parser("read")
    r.add_argument("channel")
    r.add_argument("--thread")
    r.add_argument("-n", type=int, default=20)
    a = ap.parse_args()
    if a.cmd == "say":
        print(say(a.who, a.channel, a.message, a.thread))
    else:
        read(a.channel, a.thread, a.n)
    sys.exit(0)
