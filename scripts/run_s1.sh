#!/usr/bin/env bash
# Run scenario S1 end to end in the recoverops room, playing finance and sales through scripts/mm.py.
# Needs .env (see README). Prints every post; ends with the outbox files and the audit log.
set -euo pipefail
cd "$(dirname "$0")/.."
R=${ROOM:-recoverops}
say() { python3 scripts/mm.py say "$1" "$R" "$2" ${3:+--thread "$3"}; }
watch() { python3 scripts/mm.py watch "$R" --quiet 120 --timeout 400 ${1:+--until "$1"}; }

scripts/reset_demo.sh
sleep 20   # let the agents reconnect after !reset

root=$(say finance "@case-lead payment PAY-311 from ABC Distributors, Rs 82,000")
echo "== S1 thread $root"
watch "@sales"

say sales "@investigator 1. Yes, Rahul approved the freight waiver because the truck was three days late. 2. Not aware of any damage. No damage report or return reached us." "$root" >/dev/null
watch "@finance"

echo "== sales tries to approve (must be refused)"
say sales "@case-lead approve" "$root" >/dev/null
watch "refus|only finance"

say finance "@case-lead edit: hold the credit note until sales confirms the waiver by email" "$root" >/dev/null
watch "@finance"

say finance "@case-lead approve. Owner sales, due 14 Nov" "$root" >/dev/null
watch "Case board"

echo "== outbox"; ls outbox
echo "== audit"; python3 tools/case.py audit C-001 | python3 -c "import json,sys;[print(e['actor'],e['action'],e['summary'][:100]) for e in json.load(sys.stdin)['events']]"
