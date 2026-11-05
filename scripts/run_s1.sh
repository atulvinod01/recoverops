#!/usr/bin/env bash
# S1: ABC Distributors short-paid ₹18,000 (freight ₹6,000 waived by sales, damage ₹12,000 unproven).
# Also checks that sales cannot approve and that finance can edit, then approve. PAUSE=60 for a slow run.
source "$(dirname "$0")/lib.sh"
start
root=$(say finance "@case-lead payment PAY-311 from ABC Distributors, Rs 82,000"); echo "== S1 thread $root"
watch "@sales" >/dev/null
say sales "@investigator 1. Yes, Rahul approved the freight waiver because the truck was three days late. 2. Not aware of any damage. No damage report or return reached us." "$root" >/dev/null
watch "@finance" >/dev/null
echo "== sales tries to approve (must be refused)"
say sales "@case-lead approve" "$root" >/dev/null
watch "refus|only finance" >/dev/null
say finance "@case-lead edit: hold the credit note until sales confirms the waiver by email" "$root" >/dev/null
watch "@finance" >/dev/null
say finance "@case-lead approve. Owner sales, due 14 Nov" "$root" >/dev/null
watch "Case board" >/dev/null
summary C-001
