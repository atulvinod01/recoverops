"""Exact-value tests for the RecoverOps tools, run the way agents run them: as CLI scripts printing JSON."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent.parent / "tools"


def run(tool, *args, env=None, ok=True):
    p = subprocess.run([sys.executable, str(TOOLS / tool), *args], capture_output=True, text=True, env=env)
    assert (p.returncode == 0) == ok, p.stdout + p.stderr
    return json.loads(p.stdout)


# --- match.py -------------------------------------------------------------

def test_s1_short_paid_by_reference():
    m = run("match.py", "PAY-311")
    assert m["status"] == "short_paid" and m["matched_by"] == "reference"
    assert [i["invoice_id"] for i in m["invoices"]] == ["INV-1042"]
    assert m["difference"] == 18000 and m["difference_usd"] == "$18,000"


def test_s2_only_open_invoice_flagged():
    m = run("match.py", "PAY-322")
    assert m["status"] == "short_paid" and m["matched_by"] == "only_open_invoice"
    assert m["difference_usd"] == "$3,700"
    assert "no_invoice_reference_on_payment" in m["flags"]


def test_s3_possible_combined_not_allocated():
    m = run("match.py", "PAY-318")
    assert m["status"] == "possible_combined"
    assert [i["invoice_id"] for i in m["invoices"]] == ["INV-1061", "INV-1063"]
    assert "needs_finance_allocation" in m["flags"]


def test_s4_duplicate_record():
    m = run("match.py", "PAY-312")
    assert m["status"] == "duplicate" and m["duplicate_of"] == "PAY-311"
    assert m["invoices"] == [] and m["difference"] is None


def test_unknown_payment_errors():
    assert "not found" in run("match.py", "PAY-999", ok=False)["error"]


# --- discrepancy.py -------------------------------------------------------

def test_s1_split_18000_into_6000_and_12000():
    d = run("discrepancy.py", "PAY-311")
    assert d["difference_usd"] == "$18,000"
    claims = [(c["amount"], c["citation"]) for c in d["claimed_deductions"]]
    assert claims == [
        (6000, "data/remittance/abc-distributors_2026-10-28.txt:11"),
        (12000, "data/remittance/abc-distributors_2026-10-28.txt:12"),
    ]
    assert d["claimed_deductions"][0]["equals_invoice_line"] == "INV-1042 line 3 (Freight)"
    assert d["claimed_deductions"][1]["equals_invoice_line"] is None
    assert d["unexplained"] == 0 and d["flags"] == []


def test_s2_nothing_claimed_all_unexplained():
    d = run("discrepancy.py", "PAY-322")
    assert d["claimed_deductions"] == [] and d["unexplained_usd"] == "$3,700"
    assert "no_remittance_note" in d["flags"] and "unexplained_shortfall" in d["flags"]


def test_s3_combined_difference_zero():
    d = run("discrepancy.py", "PAY-318")
    assert d["invoice_total"] == 60000 and d["difference"] == 0


def test_s5_injection_note_is_only_data():
    d = run("discrepancy.py", "PAY-330")
    assert [c["amount"] for c in d["claimed_deductions"]] == [2500] and d["unexplained"] == 0


# --- evidence.py ----------------------------------------------------------

def test_s1_evidence_fixed_citations():
    e = run("evidence.py", "PAY-311")
    fr, dmg = e["deductions"]
    assert (fr["key"], fr["amount_usd"], fr["label"]) == ("freight", "$6,000", "likely")
    assert fr["citation"] == "data/remittance/abc-distributors_2026-10-28.txt:11"
    assert fr["supporting"] == ["data/emails/abc-distributors_2026-10-03.txt:9"]
    assert (dmg["key"], dmg["amount_usd"], dmg["label"], dmg["supporting"]) == ("damage", "$12,000", "unknown", [])
    # CN-201 is ABC's but for INV-0998: it must not support this case
    assert e["credit_notes_for_other_invoices"] == ["data/credit_notes.csv:2"]
    assert e["untrusted_instructions"] == []


def test_s2_evidence_unexplained_only():
    e = run("evidence.py", "PAY-322")
    assert [(d["key"], d["amount_usd"], d["label"]) for d in e["deductions"]] == [("unexplained", "$3,700", "unknown")]


def test_s5_evidence_flags_injection():
    e = run("evidence.py", "PAY-330")
    [s] = e["deductions"]
    assert (s["key"], s["amount_usd"], s["label"], s["supporting"]) == ("scheme", "$2,500", "unknown", [])
    assert [u["citation"] for u in e["untrusted_instructions"]] == ["data/remittance/maple-retail_2026-11-01.txt:10"]


# --- case.py --------------------------------------------------------------

@pytest.fixture
def env(tmp_path):
    return dict(os.environ, RECOVEROPS_DB=str(tmp_path / "cases.db"), RECOVEROPS_OUTBOX=str(tmp_path / "outbox"))


def test_s1_case_flow_with_approval_gate(env, tmp_path):
    c = run("case.py", "open", "PAY-311", "--thread", "root1", env=env)
    assert c["case_id"] == "C-001" and c["recoverable_pending_usd"] == "$18,000"
    assert run("case.py", "open", "PAY-311", "--thread", "root1", env=env)["already_open"] is True

    cite = "data/remittance/abc-distributors_2026-10-28.txt"
    run("case.py", "finding", "C-001", "--key", "freight", "--agent", "investigator", "--amount", "6000",
        "--label", "likely", "--citation", cite + ":11", env=env)
    c = run("case.py", "finding", "C-001", "--key", "damage", "--agent", "investigator", "--amount", "12000",
            "--label", "unknown", env=env)
    assert c["recoverable_pending"] == 18000  # nothing confirmed yet

    # sales confirms the freight waiver
    c = run("case.py", "finding", "C-001", "--key", "freight", "--agent", "investigator", "--amount", "6000",
            "--label", "confirmed", "--citation", cite + ":11", "--note", "sales confirmed waiver", env=env)
    assert c["recoverable_pending_usd"] == "$12,000"

    # likely/confirmed without a citation is refused
    run("case.py", "finding", "C-001", "--key", "x", "--agent", "investigator", "--amount", "1",
        "--label", "likely", env=env, ok=False)

    run("case.py", "draft", "C-001", "--kind", "customer_message", "--text", "Dear ABC...", env=env)
    assert not (tmp_path / "outbox").exists()  # nothing written before approval

    err = run("case.py", "decide", "C-001", "--reviewer", "sales", "--decision", "approve", env=env, ok=False)
    assert "only finance" in err["error"]
    assert not (tmp_path / "outbox").exists()

    c = run("case.py", "decide", "C-001", "--reviewer", "finance", "--decision", "edit",
            "--comment", "hold the credit note", env=env)
    assert c["status"] == "changes_requested" and not (tmp_path / "outbox").exists()

    run("case.py", "draft", "C-001", "--kind", "customer_message", "--text", "Dear ABC, revised", env=env)
    c = run("case.py", "decide", "C-001", "--reviewer", "finance", "--decision", "approve",
            "--owner", "sales", "--due", "2026-11-14", env=env)
    assert c["status"] == "approved" and c["owner"] == "sales"
    assert "Dear ABC, revised" in (tmp_path / "outbox" / "C-001-customer_message.md").read_text()

    run("case.py", "decide", "C-001", "--reviewer", "finance", "--decision", "approve", env=env, ok=False)
    actions = [e["action"] for e in run("case.py", "audit", "C-001", env=env)["events"]]
    assert actions == ["open", "finding", "finding", "finding", "draft", "decision_refused", "edit", "draft", "approve"]

    board = run("case.py", "board", env=env)
    assert "| C-001 | ABC Distributors | PAY-311 | $18,000 | $12,000 | approved | sales | 2026-11-14 |" in board["markdown"]


def test_s4_duplicate_cannot_open_case(env):
    assert "duplicate" in run("case.py", "open", "PAY-312", "--thread", "r", env=env, ok=False)["error"]


def test_s3_allocation_needs_finance_approval(env, tmp_path):
    assert run("case.py", "open", "PAY-318", "--thread", "r", env=env)["status"] == "needs_allocation"
    run("case.py", "decide", "C-001", "--reviewer", "finance", "--decision", "approve", env=env, ok=False)
    run("case.py", "draft", "C-001", "--kind", "allocation", "--text", "PAY-318 -> INV-1061 + INV-1063", env=env)
    c = run("case.py", "decide", "C-001", "--reviewer", "finance", "--decision", "approve", env=env)
    assert c["status"] == "approved"
    assert "INV-1061 + INV-1063" in (tmp_path / "outbox" / "C-001-allocation.md").read_text()
