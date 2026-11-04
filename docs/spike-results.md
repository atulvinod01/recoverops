# Spike results (Phase A, 4 Nov 2026)

Status legend: PASS / FAIL / unverified. Nothing below is verified until a run fills it in.

## What the docs already told us (read 4 Nov, Switch 0.31 docs)

- **Deploying templates:** Console → Templates → **Import template** (paste YAML or load file), then **Use**. No public CLI/HTTP API documented for people; Console uses an internal `POST /gateway/rooms/from-template`. We deploy from Console.
- **`{agent}` placeholder** is documented as working only "in a document with a single `agent:`". With an `agents:` list it is left as written. So gotcha 1 is documented behaviour, **not a bug**. Drop the Track 03 bug idea.
- **Template keys we can use:** `auto_mode` (default true: Claude Code's own review decides what runs without asking, and posts a request in the room for the rest), `auto_approve` (bypass, unsafe), `room.instructions` (shared rules for every agent in the room), `room.users` (add `finance`/`sales` by Mattermost username; a missing user doesn't stop the run).
- **Sender identity:** Switch's `message` event carries `sender` and `sender_name`. Whether the Claude Code session shows them to the agent is spike 3.
- Switch Console writes `.switch/config/<agent>.json` into each agent's folder. Gitignored.

## Results

| # | Question | Result | Evidence / note |
|---|---|---|---|
| 1 | Agents run `../../tools/hello.py` from `{workspace}/agents/<name>` | unverified | |
| 2 | `finance` / `sales` users in the room get answered | unverified | |
| 3 | Agent can tell who sent a message | unverified | |
| 4 | Concurrent SQLite writes | **skipped by design** | Only case-lead writes, through `tools/case.py`. Others return results in the thread. |
| 5 | `.claude/settings.json` allow rule removes prompts (spike-a has Auto mode off) | unverified | |
| 5b | Auto mode on (spike-b): any prompts? | unverified | |
| extra | CLAUDE.md loaded (reply ends `[CLAUDE.md loaded: …]`) | unverified | |
| extra | Room instructions reach agents (reply starts `SPIKE`) | unverified | |
| extra | `owner-agents` ignores `finance` (spike-b) | unverified | |
| extra | Agent-to-agent delegation replies in the same thread | unverified | |
| 6 | Mattermost REST posting | deferred to Fri hardening | |

## Test script (post these in `spike-room`)

0. Kickoff posts itself. Expect two replies with JSON whose `cwd` ends in `agents/spike-a` / `agents/spike-b`. Note any permission request posted in the room. → spikes 1, 5, 5b, CLAUDE.md, room instructions.
1. As **finance**: `@spike-a who sent this message? Give the exact username and say where you got it.` → spikes 2, 3.
2. As **sales**: same message. → spike 3 (must name a different user).
3. As **finance**: `@spike-b hello` → expect no reply (owner-agents).
4. As **user** (Atul), in a thread under the kickoff: `@spike-a ask @spike-b to run python3 ../../tools/hello.py from-a and reply in this thread.` → delegation stays in thread.
5. As **user**: `@spike-a run cat ../../data/test.txt` → direct file read outside its folder: prompt or not?
