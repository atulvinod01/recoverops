#!/usr/bin/env bash
# S2: Kumar Agencies paid ₹41,300 for INV-1057 (₹45,000) with no note and no invoice reference.
# Pass = ₹3,700 stays unexplained/unknown with no guessed reason; the room owner (not finance) cannot
# approve; finance rejects, so nothing reaches outbox/.
source "$(dirname "$0")/lib.sh"
start
root=$(say finance "@case-lead payment PAY-322 from Kumar Agencies, Rs 41,300"); echo "== S2 thread $root"
out=$(watch "@sales|@finance" 2>&1 >/dev/null); echo "$out" >&2
if grep -q "@sales" <<<"$out"; then   # investigator may or may not ask sales
  say sales "@investigator Not aware of anything agreed with Kumar Agencies. No idea why they paid less." "$root" >/dev/null
  watch "@finance" >/dev/null
fi
echo "== room owner (user) tries to approve (must be refused)"
say user "@case-lead approve" "$root" >/dev/null
watch "refus|only finance" >/dev/null
say finance "@case-lead reject: I will call Kumar Agencies first, then decide" "$root" >/dev/null
watch "Case board" >/dev/null
summary C-001
