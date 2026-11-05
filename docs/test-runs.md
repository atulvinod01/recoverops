# Scenario runs in the Switch room

Each run is driven by `scripts/run_s1.sh` (or by hand), playing finance and sales through `scripts/mm.py`.
Times are IST. Model: sonnet (template default).

## 4 Nov 2026: S1, two runs, both PASS

| Check | Run 1 (20:09) | Run 2 (20:15, from `reset_demo.sh`) |
|---|---|---|
| case-lead opens C-001, delegates to both agents in the thread | ✅ | ✅ |
| reconciler (owner-agents) wakes from case-lead's mention, returns ₹18,000 = ₹6,000 + ₹12,000 with `remittance…:11/:12` | ✅ | ✅ |
| investigator asks @sales, waits, then labels freight confirmed / damage unknown | ✅ | ✅ |
| case-lead waits for both results, then posts recommendation: recoverable pending ₹12,000 | ✅ 87 s after payment | ✅ 42 s |
| sales tries `@case-lead approve` → case.py refuses, nothing in outbox | ✅ | ✅ |
| finance `edit:` → credit note put ON HOLD, finance asked again | ✅ | ✅ |
| finance `approve. Owner sales, due 14 Nov` → 2 outbox files marked NOT SENT; board posted top-level | ✅ | ✅ |
| Every reply in the case thread (except the board) | ✅ | ✅ |
| Damage finding keeps its citation | ❌ saved with no citation → CLAUDE.md fixed | ✅ |

Notes
- Investigator cited the email at `:9` (waiver) in run 1 and `:8` (delay) in run 2. Both true; `evidence.py` (Phase D) will make citations deterministic.
- Switch posts its own "Starting a session…" / "Working…" status messages; one "Starting a session" landed top-level. Not ours to fix.

## 4 Nov 2026: S1 with Ponytail off, PASS

Atul turned off the Ponytail plugin on claude.ai. The change reached this Mac only when the agents restarted (sync manifest updated 21:48:29), so the 21:48 run still had Ponytail; it passed anyway.

| Check | Run 3 (21:48) | Run 4 (21:52, clean) |
|---|---|---|
| Every check from runs 1–2 above | ✅ | ✅ |
| Damage finding keeps its citation | ✅ | ✅ |
| `PONYTAIL` in the 3 agent session logs | 3 each (loaded at startup) | **0** |
| Payment posted → recommendation | 72 s | 48 s |

Notes
- Other synced plugins (engineering, product-management, founder-skill, linkedin-agent, frontend-design, playwright) still list their skills in each agent session. None of them run hooks or change behaviour, and no agent used them.
- To check a machine is clean: `grep -ci ponytail ~/.claude/projects/*recoverops-agents-*/<new session>.jsonl` → 0.

## 5 Nov 2026: S1 run 5 after bug fixes, PASS

Fixes under test:
- `tools/evidence.py`: the investigator gets fixed citations from a tool instead of grepping (it ran only `evidence.py PAY-311`, twice).
- case-lead's opening line used "paid <amount>", which `case.py open` never prints, so runs 1–3 copied ₹82,000 from finance's message (breaking rule 1). It now uses `difference <difference_inr>`.

| Check | Run 5 (19:18) |
|---|---|
| Every check from runs 1–4 | ✅ |
| Opening line: "difference ₹18,000" (from tool output) | ✅ |
| Evidence: freight `remittance…:11; emails…:9; sales in thread`, damage `remittance…:12`, same as evidence.py | ✅ |
| Payment posted → recommendation | 51 s |
| `PONYTAIL` in agent logs | 0 |
