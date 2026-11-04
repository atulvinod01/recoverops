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
| 1 | Agents run `../../tools/hello.py` from `{workspace}/agents/<name>` | **PASS** (spike-b) | Session log: cwd `.../recoverops/agents/spike-b`, script read `data/test.txt`. Explicit `{workspace}/agents/<name>` directories work. |
| 2 | `finance` / `sales` users in the room get answered | **PASS** | Users created with `mmctl --local`, added to team `switch`, put in the room by `room.users`. `sales` (not linked to any Switch user) addressed spike-a (`anyone`) and got a correct answer in-thread. |
| 3 | Agent can tell who sent a message | **PASS** | Switch prepends `[Switch] <username> addressed you in room …` (seen: `user`, `finance`, `sales`, `Admin (workspace owner)`). spike-a answered sales: *It was sent by "sales" … from the header Switch put on the message … not from anything inside the message itself.* Approval gate can check the sender is `finance`; `case.py` will also refuse any other reviewer. |
| 4 | Concurrent SQLite writes | **skipped by design** | Only case-lead writes, through `tools/case.py`. Others return results in the thread. |
| 5 | `.claude/settings.json` allow rule removes prompts with Auto mode off (spike-a) | **FAIL** | spike-a called `python3 ../../tools/hello.py` at 17:57:12 and never got a result: blocked on a permission request that did not appear in the Mattermost room. |
| 5b | Auto mode on (spike-b): any prompts? | **PASS** | Same command ran with no prompt. **Decision: every RecoverOps agent keeps `auto_mode: true` (default); drop the settings files.** |
| extra | CLAUDE.md loaded | **PASS** | spike-b's reply and spike-a's DM reply both end `[CLAUDE.md loaded: …]`. |
| extra | Room instructions reach agents | **FAIL (not automatic)** | spike-b's reply didn't start with `SPIKE`; it never called `connect_to_room`/`read_context`. **Decision: all rules go in each agent's CLAUDE.md, not `room.instructions`.** |
| extra | Agent reply to the template kickoff shows in Mattermost | **FAIL** | spike-b called `post_message(thread_id=<kickoff message id>)`, Switch returned an event id, but the post never reached Mattermost (`mmctl post list` shows nothing). The bridge posts the kickoff as a *reply* inside a thread, so the agent threaded onto a non-root post. Hypothesis: replies to a normal top-level human message work. **Decision: kickoff must not ask agents to reply; test threading with a human post.** |
| extra | `owner-agents` refuses `finance` (spike-b) | **PASS** | Switch auto-replied in thread: "I only take instructions from my owner, and this chat account isn't linked to a Switch user yet". Right rule for `reconciler`. |
| extra | Agent reply in thread under a human top-level post | **PASS, but not reliable** | spike-b replied in finance's thread. spike-a answered sales in spike-room as a **new top-level post** (Switch's "Working…" status went in the thread). Agents only thread when they pass `thread_id`. **Decision: every CLAUDE.md says: always reply with `thread_id` = the case thread's root message id.** Re-test in Phase C. |
| extra | Permission requests with Auto mode off | **observed** | Console runs agents with `--permission-prompt-tool stdio`: the request waits in Switch Console, never in Mattermost. Stuck session blocked every later message to that agent ("Queued. Waiting for the agent to start…"). |
| extra | Stop current work | **observed** | Unblocks the agent, but the message queued behind it (finance → spike-a) was **dropped**: never answered on its own. (spike-a later mentioned it when answering sales, after reading room context.) Gotcha 7 confirmed: re-send after a stop. `reset_demo.sh` + README must say so. |
| extra | Agent-to-agent delegation replies in the same thread | unverified, deferred to Phase C | First real test is case-lead → reconciler in S1. |
| extra | User-level config leaks into agents | **observed** | Agents load `~/.claude/CLAUDE.md` and Atul's Claude Code plugins/hooks (Ponytail). Harmless; disable Ponytail before recording. Judges won't have it. |
| extra | macOS privacy prompt | **observed** | First run asks "Switch Console would like to access files in your Desktop folder". Must Allow. README: mention it, or suggest cloning outside Desktop/Documents. |
| 6 | Mattermost REST posting | deferred to Fri hardening | |

## Also seen

- Agents are members of every team channel (Town Square, Off-Topic) and answer there too. Demo stays in the RecoverOps room; not a problem.
- Session start takes ~10–30 s; a full answer ~30–50 s.

## Test script (post these in `spike-room`)

0. Kickoff posts itself. Expect two replies with JSON whose `cwd` ends in `agents/spike-a` / `agents/spike-b`. Note any permission request posted in the room. → spikes 1, 5, 5b, CLAUDE.md, room instructions.
1. As **finance**: `@spike-a who sent this message? Give the exact username and say where you got it.` → spikes 2, 3.
2. As **sales**: same message. → spike 3 (must name a different user).
3. As **finance**: `@spike-b hello` → expect no reply (owner-agents).
4. As **user** (Atul), in a thread under the kickoff: `@spike-a ask @spike-b to run python3 ../../tools/hello.py from-a and reply in this thread.` → delegation stays in thread.
5. As **user**: `@spike-a run cat ../../data/test.txt` → direct file read outside its folder: prompt or not?
