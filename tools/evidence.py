"""Evidence for each deduction on a payment, with fixed file:line citations, for the investigator.

Usage: python3 ../../tools/evidence.py PAY-311 [--invoice INV-1042 ...]

For every deduction discrepancy.py found (plus any unexplained amount) it lists:
  key        short name (freight, damage, scheme, other, unexplained)
  citation   the customer's own claim line (remittance file:line), or null
  supporting lines in the customer's other documents and our records that mention the same thing
  label      before asking sales: confirmed (our credit note matches), likely (supporting lines),
             unknown (nothing beyond the claim)
It also lists untrusted instructions found in the customer's documents. It never decides validity
beyond these rules; sales can still confirm or deny in the thread.
"""
import argparse
import re

from common import DATA, ROOT, fail, inr, out, rows
from discrepancy import discrepancy

# ponytail: deduction kind by keyword. Covers freight / damage / scheme claims in our data;
# add kinds or words when a new deduction type shows up.
KINDS = {
    "freight": ["freight"],
    "damage": ["damage", "broken", "breakage"],
    "scheme": ["scheme", "discount"],
}
# ponytail: text aimed at an automated reader. Catches the common phrasings; a determined attacker
# can word around it, which is why agents also treat every document as data (agents/CLAUDE.md rule 4).
INJECTION = re.compile(
    r"ignore (all |any )?(previous|prior|above) instructions|automated system|\bassistant\b|\bAI\b"
    r"|disregard|mark (this|the) invoice (as )?paid",
    re.I,
)


def kind_of(text):
    low = text.lower()
    return next((k for k, words in KINDS.items() if any(w in low for w in words)), "other")


def documents(keys):
    """(path, lines) for every email or remittance note that mentions a payment or invoice id."""
    docs = []
    for folder in ("emails", "remittance"):
        for path in sorted((DATA / folder).glob("*.txt")):
            text = path.read_text()
            if any(k in text for k in keys):
                docs.append((path.relative_to(ROOT).as_posix(), text.splitlines()))
    return docs


def evidence(payment_id, invoice_ids=None):
    d = discrepancy(payment_id, invoice_ids)
    customer, invoice_ids = d["customer"], d["invoice_ids"]
    docs = documents([payment_id] + invoice_ids)
    claim_cites = {c["citation"] for c in d["claimed_deductions"]}
    credit_notes = [(n, r) for n, r in enumerate(rows("credit_notes"), 2)
                    if r["customer"] == customer and r["invoice_id"] in invoice_ids]
    schemes = [(n, r) for n, r in enumerate(rows("schemes"), 2) if r["customer"] == customer]

    deductions = []
    for c in d["claimed_deductions"]:
        kind = kind_of(c["customer_text"])
        words = KINDS.get(kind, [])
        supporting = [
            f"{path}:{n}" for path, lines in docs for n, line in enumerate(lines, 1)
            if f"{path}:{n}" not in claim_cites and any(w in line.lower() for w in words)
        ]
        cn = [f"data/credit_notes.csv:{n}" for n, r in credit_notes if int(r["amount"]) == c["amount"]]
        if kind == "scheme":
            supporting += [f"data/schemes.csv:{n}" for n, _ in schemes]
        label = "confirmed" if cn else "likely" if supporting else "unknown"
        deductions.append({
            "key": kind,
            "amount": c["amount"],
            "amount_inr": c["amount_inr"],
            "customer_text": c["customer_text"],
            "citation": c["citation"],
            "supporting": cn + supporting,
            "label": label,
        })
    if d["unexplained"] > 0:
        deductions.append({
            "key": "unexplained",
            "amount": d["unexplained"],
            "amount_inr": d["unexplained_inr"],
            "customer_text": None,
            "citation": None,
            "supporting": [],
            "label": "unknown",
        })

    untrusted = [
        {"citation": f"{path}:{n}", "text": line.strip()}
        for path, lines in docs for n, line in enumerate(lines, 1) if INJECTION.search(line)
    ]
    return {
        "payment_id": payment_id,
        "customer": customer,
        "invoice_ids": invoice_ids,
        "difference_inr": d["difference_inr"],
        "documents": [path for path, _ in docs],
        "deductions": deductions,
        "untrusted_instructions": untrusted,
        "credit_notes_for_other_invoices": [
            f"data/credit_notes.csv:{n}" for n, r in enumerate(rows("credit_notes"), 2)
            if r["customer"] == customer and r["invoice_id"] not in invoice_ids
        ],
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("payment_id")
    ap.add_argument("--invoice", action="append")
    a = ap.parse_args()
    try:
        out(evidence(a.payment_id, a.invoice))
    except (KeyError, ValueError) as e:
        fail(str(e.args[0]))
