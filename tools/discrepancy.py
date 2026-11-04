"""Explain the gap between a payment and its invoice(s), line by line, with citations.

Usage: python3 ../../tools/discrepancy.py PAY-311 [--invoice INV-1042 ...]

Without --invoice it uses the invoices match.py found. Reports the invoice lines, the difference,
every deduction the customer claimed in a remittance note (amount + file:line), and
unexplained = difference - claimed total. It does not judge whether a claim is valid.
"""
import argparse
import re

from common import DATA, ROOT, fail, inr, out, rows
from match import match

AMOUNT = re.compile(r"(?:Rs\.?|₹|INR)\s*([\d,]+)", re.I)
# ponytail: a claimed deduction is any remittance line starting "Less:". Real remittances vary;
# extend this pattern (or add per-customer formats) when new layouts show up.
DEDUCTION = re.compile(r"^\s*less\s*:", re.I)


def remittance_claims(keys):
    """Deduction lines from remittance notes that mention any of `keys` (payment or invoice ids)."""
    claims, files = [], []
    for path in sorted((DATA / "remittance").glob("*.txt")):
        text = path.read_text()
        if not any(k in text for k in keys):
            continue
        rel = path.relative_to(ROOT).as_posix()
        files.append(rel)
        for n, line in enumerate(text.splitlines(), 1):
            m = AMOUNT.search(line)
            if DEDUCTION.match(line) and m:
                amt = int(m.group(1).replace(",", ""))
                claims.append({
                    "amount": amt,
                    "amount_inr": inr(amt),
                    "customer_text": line.strip(),
                    "citation": f"{rel}:{n}",
                })
    return claims, files


def discrepancy(payment_id, invoice_ids=None):
    m = match(payment_id)
    if not invoice_ids:
        if m["status"] in ("duplicate", "unmatched"):
            raise ValueError(f"{payment_id} is {m['status']}; pass --invoice explicitly")
        invoice_ids = [i["invoice_id"] for i in m["invoices"]]

    invoices = {i["invoice_id"]: i for i in rows("invoices")}
    missing = [i for i in invoice_ids if i not in invoices]
    if missing:
        raise ValueError(f"invoice(s) not found: {', '.join(missing)}")

    lines = [
        {
            "invoice_id": l["invoice_id"],
            "line_no": int(l["line_no"]),
            "description": l["description"],
            "qty": int(l["qty"]),
            "rate": int(l["rate"]),
            "amount": int(l["amount"]),
            "amount_inr": inr(int(l["amount"])),
        }
        for l in rows("invoice_lines")
        if l["invoice_id"] in invoice_ids
    ]
    total = sum(int(invoices[i]["total"]) for i in invoice_ids)
    diff = total - m["amount"]

    claims, files = remittance_claims([payment_id] + invoice_ids)
    for c in claims:
        same = [l for l in lines if l["amount"] == c["amount"]]
        c["equals_invoice_line"] = (
            f"{same[0]['invoice_id']} line {same[0]['line_no']} ({same[0]['description']})" if len(same) == 1 else None
        )
    claimed = sum(c["amount"] for c in claims)
    unexplained = diff - claimed

    flags = list(m["flags"])
    if not files:
        flags.append("no_remittance_note")
    if unexplained > 0:
        flags.append("unexplained_shortfall")
    elif unexplained < 0:
        flags.append("claims_exceed_shortfall")

    return {
        "payment_id": payment_id,
        "customer": m["customer"],
        "match_status": m["status"],
        "paid": m["amount"],
        "paid_inr": m["amount_inr"],
        "invoice_ids": invoice_ids,
        "invoice_total": total,
        "invoice_total_inr": inr(total),
        "invoice_lines": lines,
        "difference": diff,
        "difference_inr": inr(diff),
        "remittance_files": files,
        "claimed_deductions": claims,
        "claimed_total": claimed,
        "claimed_total_inr": inr(claimed),
        "unexplained": unexplained,
        "unexplained_inr": inr(unexplained),
        "flags": flags,
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("payment_id")
    ap.add_argument("--invoice", action="append")
    a = ap.parse_args()
    try:
        out(discrepancy(a.payment_id, a.invoice))
    except (KeyError, ValueError) as e:
        fail(str(e.args[0]))
