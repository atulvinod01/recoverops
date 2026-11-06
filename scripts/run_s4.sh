#!/usr/bin/env bash
# S4: PAY-312 is a second copy of PAY-311 (same customer, date, amount, reference).
# Pass = case-lead posts case.py's duplicate error; no case is opened, nothing counted twice.
source "$(dirname "$0")/lib.sh"
start
root=$(say finance "@case-lead payment PAY-312 from ABC Distributors, \$82,000"); echo "== S4 thread $root"
watch "duplicate" >/dev/null
echo "== case store"; python3 tools/case.py board | python3 -c "import json,sys;print(json.load(sys.stdin)['markdown'])"
echo "== outbox"; ls outbox
