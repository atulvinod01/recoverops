#!/usr/bin/env bash
# Reset RecoverOps between demo runs: empty the case store and outbox, and clear each agent's memory.
# Fixtures in data/ never change, so they need no reset.
set -euo pipefail
cd "$(dirname "$0")/.."

rm -f cases.db
rm -rf outbox && mkdir outbox
echo "cases.db removed, outbox/ emptied."

# Clear agent context so they don't remember earlier cases (needs .env from the README setup).
if [ -f .env ]; then
  for a in case-lead reconciler investigator; do
    python3 scripts/mm.py say user "${ROOM:-recoverops}" "!reset @$a" >/dev/null && echo "sent !reset @$a"
  done
else
  echo "No .env: in the recoverops room, post  !reset @case-lead  !reset @reconciler  !reset @investigator"
fi
echo "If an agent is stuck: post  !interrupt @<agent>  in the room, then re-send the last message."
