"""Case store for RecoverOps (SQLite). Only case-lead calls this. Every write is audited.

  case.py open PAY-311 --thread <root post id>             open (or return) the case for a payment
  case.py finding C-001 --key freight --agent investigator --amount 6000 --label likely
          --citation data/remittance/x.txt:11 --note "..."  add or update one deduction finding
  case.py draft C-001 --kind customer_message --text "..."  store a draft (nothing is sent)
  case.py decide C-001 --reviewer finance --decision approve|edit|reject [--comment ...]
          [--owner sales --due 2026-11-14]                   finance's decision; approve writes outbox/
  case.py show C-001 | board | audit C-001

Labels describe the customer's deduction: confirmed (valid, we accept it), likely, unknown.
recoverable_pending = difference - sum of confirmed deductions.
"""
import argparse
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from common import ROOT, fail, inr, out
from match import match

DB = Path(os.environ.get("RECOVEROPS_DB", ROOT / "cases.db"))
OUTBOX = Path(os.environ.get("RECOVEROPS_OUTBOX", ROOT / "outbox"))
# ponytail: the reviewer name is the Mattermost username case-lead copies from Switch's
# "[Switch] <user> addressed you" header. Fixed list; move to config if the team grows.
FINANCE_REVIEWERS = {"finance"}
LABELS = ("confirmed", "likely", "unknown")
CLOSED = ("approved", "rejected")

SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (
  id INTEGER PRIMARY KEY, case_id TEXT UNIQUE, payment_id TEXT UNIQUE, invoice_ids TEXT,
  customer TEXT, difference INTEGER, status TEXT, owner TEXT, due_date TEXT, thread_ref TEXT,
  created_at TEXT);
CREATE TABLE IF NOT EXISTS findings (
  case_id TEXT, key TEXT, agent TEXT, deduction_amount INTEGER, label TEXT, citation TEXT,
  note TEXT, updated_at TEXT, PRIMARY KEY (case_id, key));
CREATE TABLE IF NOT EXISTS drafts (
  case_id TEXT, kind TEXT, body TEXT, updated_at TEXT, PRIMARY KEY (case_id, kind));
CREATE TABLE IF NOT EXISTS approvals (
  approval_id INTEGER PRIMARY KEY, case_id TEXT, reviewer TEXT, decision TEXT, comment TEXT,
  timestamp TEXT);
CREATE TABLE IF NOT EXISTS audit_events (
  event_id INTEGER PRIMARY KEY, case_id TEXT, actor TEXT, action TEXT, summary TEXT,
  timestamp TEXT);
"""


def now():
    return datetime.now().isoformat(timespec="seconds")


def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def audit(con, case_id, actor, action, summary):
    con.execute(
        "INSERT INTO audit_events (case_id, actor, action, summary, timestamp) VALUES (?,?,?,?,?)",
        (case_id, actor, action, summary, now()),
    )


def get_case(con, case_id):
    row = con.execute("SELECT * FROM cases WHERE case_id=?", (case_id,)).fetchone()
    if not row:
        fail(f"case {case_id} not found")
    return row


def summary(con, case_id):
    c = dict(get_case(con, case_id))
    del c["id"]
    findings = [dict(r) for r in con.execute("SELECT * FROM findings WHERE case_id=? ORDER BY key", (case_id,))]
    confirmed = sum(f["deduction_amount"] for f in findings if f["label"] == "confirmed")
    pending = None if c["difference"] is None else c["difference"] - confirmed
    c.update(
        invoice_ids=c["invoice_ids"].split(",") if c["invoice_ids"] else [],
        difference_inr=None if c["difference"] is None else inr(c["difference"]),
        confirmed_deductions=confirmed,
        confirmed_deductions_inr=inr(confirmed),
        recoverable_pending=pending,
        recoverable_pending_inr=None if pending is None else inr(pending),
        findings=[dict(f, deduction_amount_inr=inr(f["deduction_amount"])) for f in findings],
        drafts=[dict(r) for r in con.execute("SELECT kind, body, updated_at FROM drafts WHERE case_id=?", (case_id,))],
        approvals=[dict(r) for r in con.execute("SELECT reviewer, decision, comment, timestamp FROM approvals WHERE case_id=? ORDER BY approval_id", (case_id,))],
    )
    return c


def cmd_open(a):
    try:
        m = match(a.payment_id)
    except KeyError as e:
        fail(str(e.args[0]))
    if m["status"] == "duplicate":
        fail(f"{a.payment_id} is a duplicate record of {m['duplicate_of']}; no case opened, nothing counted twice")
    with db() as con:
        row = con.execute("SELECT case_id FROM cases WHERE payment_id=?", (a.payment_id,)).fetchone()
        if row:
            return dict(summary(con, row["case_id"]), already_open=True)
        status = "needs_allocation" if m["status"] == "possible_combined" else "investigating"
        cur = con.execute(
            "INSERT INTO cases (payment_id, invoice_ids, customer, difference, status, thread_ref, created_at)"
            " VALUES (?,?,?,?,?,?,?)",
            (a.payment_id, ",".join(i["invoice_id"] for i in m["invoices"]), m["customer"],
             m["difference"], status, a.thread, now()),
        )
        case_id = f"C-{cur.lastrowid:03d}"
        con.execute("UPDATE cases SET case_id=? WHERE id=?", (case_id, cur.lastrowid))
        audit(con, case_id, a.actor, "open", f"{a.payment_id} {m['status']} difference {m['difference_inr']}")
        return dict(summary(con, case_id), already_open=False, match_status=m["status"], match_flags=m["flags"])


def cmd_finding(a):
    if a.label not in LABELS:
        fail(f"label must be one of {LABELS}")
    if a.label != "unknown" and not a.citation:
        fail("a confirmed or likely finding needs --citation file:line")
    if a.amount < 0:
        fail("amount must be >= 0")
    with db() as con:
        c = get_case(con, a.case_id)
        if c["status"] in CLOSED:
            fail(f"{a.case_id} is {c['status']}; findings are frozen")
        con.execute(
            "INSERT OR REPLACE INTO findings VALUES (?,?,?,?,?,?,?,?)",
            (a.case_id, a.key, a.agent, a.amount, a.label, a.citation, a.note, now()),
        )
        audit(con, a.case_id, a.agent, "finding", f"{a.key}: {inr(a.amount)} {a.label} ({a.citation or 'no citation'})")
        return summary(con, a.case_id)


def cmd_draft(a):
    with db() as con:
        c = get_case(con, a.case_id)
        if c["status"] in CLOSED:
            fail(f"{a.case_id} is {c['status']}; no new drafts")
        con.execute("INSERT OR REPLACE INTO drafts VALUES (?,?,?,?)", (a.case_id, a.kind, a.text, now()))
        con.execute("UPDATE cases SET status='awaiting_approval' WHERE case_id=?", (a.case_id,))
        audit(con, a.case_id, a.actor, "draft", f"{a.kind} drafted; awaiting finance approval")
        return summary(con, a.case_id)


def cmd_decide(a):
    with db() as con:
        c = get_case(con, a.case_id)
        if a.reviewer not in FINANCE_REVIEWERS:
            audit(con, a.case_id, a.reviewer, "decision_refused", f"{a.decision} by non-finance user")
            con.commit()
            fail(f"only finance can decide on a case; '{a.reviewer}' cannot. Nothing changed.")
        if c["status"] in CLOSED:
            fail(f"{a.case_id} is already {c['status']}")
        if a.decision in ("edit", "reject") and not a.comment:
            fail(f"{a.decision} needs --comment")
        drafts = con.execute("SELECT kind, body FROM drafts WHERE case_id=?", (a.case_id,)).fetchall()
        if a.decision == "approve" and not drafts:
            fail("nothing to approve: no drafts on this case")

        written = []
        if a.decision == "approve":
            OUTBOX.mkdir(exist_ok=True)
            for d in drafts:
                path = OUTBOX / f"{a.case_id}-{d['kind']}.md"
                path.write_text(
                    f"<!-- {a.case_id} {d['kind']}: approved by {a.reviewer} at {now()}. NOT SENT. -->\n\n{d['body']}\n"
                )
                written.append(path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path))
        status = {"approve": "approved", "edit": "changes_requested", "reject": "rejected"}[a.decision]
        con.execute(
            "UPDATE cases SET status=?, owner=COALESCE(?, owner), due_date=COALESCE(?, due_date) WHERE case_id=?",
            (status, a.owner, a.due, a.case_id),
        )
        con.execute(
            "INSERT INTO approvals (case_id, reviewer, decision, comment, timestamp) VALUES (?,?,?,?,?)",
            (a.case_id, a.reviewer, a.decision, a.comment, now()),
        )
        audit(con, a.case_id, a.reviewer, a.decision, (a.comment or "") + (f" -> {', '.join(written)}" if written else ""))
        return dict(summary(con, a.case_id), outbox_files=written)


def cmd_board(a):
    with db() as con:
        cases = [summary(con, r["case_id"]) for r in con.execute("SELECT case_id FROM cases ORDER BY id")]
    lines = [
        "| Case | Customer | Payment | Difference | Recoverable pending | Status | Owner | Due |",
        "|---|---|---|---|---|---|---|---|",
    ] + [
        f"| {c['case_id']} | {c['customer']} | {c['payment_id']} | {c['difference_inr'] or '-'} | "
        f"{c['recoverable_pending_inr'] or '-'} | {c['status']} | {c['owner'] or '-'} | {c['due_date'] or '-'} |"
        for c in cases
    ]
    keep = ("case_id", "customer", "payment_id", "difference", "recoverable_pending", "status", "owner", "due_date")
    return {"cases": [{k: c[k] for k in keep} for c in cases], "markdown": "\n".join(lines)}


def cmd_show(a):
    with db() as con:
        return summary(con, a.case_id)


def cmd_audit(a):
    with db() as con:
        get_case(con, a.case_id)
        rows = con.execute("SELECT actor, action, summary, timestamp FROM audit_events WHERE case_id=? ORDER BY event_id", (a.case_id,))
        return {"case_id": a.case_id, "events": [dict(r) for r in rows]}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("open"); p.add_argument("payment_id"); p.add_argument("--thread", required=True)
    p.add_argument("--actor", default="case-lead"); p.set_defaults(fn=cmd_open)

    p = sub.add_parser("finding"); p.add_argument("case_id"); p.add_argument("--key", required=True)
    p.add_argument("--agent", required=True); p.add_argument("--amount", type=int, required=True)
    p.add_argument("--label", required=True); p.add_argument("--citation"); p.add_argument("--note", default="")
    p.set_defaults(fn=cmd_finding)

    p = sub.add_parser("draft"); p.add_argument("case_id")
    p.add_argument("--kind", required=True, choices=["customer_message", "credit_note_request"])
    p.add_argument("--text", required=True); p.add_argument("--actor", default="case-lead"); p.set_defaults(fn=cmd_draft)

    p = sub.add_parser("decide"); p.add_argument("case_id"); p.add_argument("--reviewer", required=True)
    p.add_argument("--decision", required=True, choices=["approve", "edit", "reject"])
    p.add_argument("--comment"); p.add_argument("--owner"); p.add_argument("--due"); p.set_defaults(fn=cmd_decide)

    p = sub.add_parser("show"); p.add_argument("case_id"); p.set_defaults(fn=cmd_show)
    p = sub.add_parser("board"); p.set_defaults(fn=cmd_board)
    p = sub.add_parser("audit"); p.add_argument("case_id"); p.set_defaults(fn=cmd_audit)

    args = ap.parse_args()
    out(args.fn(args))
