# Shared helpers for the run_s*.sh scenario scripts. Source it; don't run it.
# PAUSE=<seconds>: after each awaited reply, wait this long (still printing posts) before the next
# human message, like a person reading and typing.
set -euo pipefail
cd "$(dirname "$0")/.."
R=${ROOM:-recoverops}
say() { python3 scripts/mm.py say "$1" "$R" "$2" ${3:+--thread "$3"}; }
watch() { python3 scripts/mm.py watch "$R" --quiet 120 --timeout 400 --linger "${PAUSE:-0}" ${1:+--until "$1"} | tee /dev/stderr; }
start() { scripts/reset_demo.sh; sleep 20; }   # 20 s: let the agents reconnect after !reset
summary() {
  echo "== outbox"; for f in outbox/*; do [ -e "$f" ] && { echo "-- $f"; cat "$f"; echo; }; done
  echo "== case $1"; python3 tools/case.py show "$1" | python3 -c "import json,sys;c=json.load(sys.stdin);print(c['status'],'difference',c['difference_inr'],'pending',c['recoverable_pending_inr'],'owner',c['owner'],'due',c['due_date']);[print(' ',f['key'],f['deduction_amount_inr'],f['label'],f.get('citation')) for f in c['findings']]"
  echo "== audit $1"; python3 tools/case.py audit "$1" | python3 -c "import json,sys;[print(' ',e['actor'],e['action'],e['summary'][:100]) for e in json.load(sys.stdin)['events']]"
}
