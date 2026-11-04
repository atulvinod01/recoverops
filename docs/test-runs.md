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
