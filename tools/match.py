"""Match a payment to the invoice(s) it pays.

Usage: python3 ../../tools/match.py PAY-311

Status is one of:
  exact              paid amount equals the matched invoice total
  short_paid         paid less than the matched invoice total
  overpaid           paid more than the matched invoice total
  possible_combined  no single invoice fits, but a set of the customer's open invoices sums exactly
                     to the payment; NOT allocated, finance must approve the allocation
  duplicate          same customer, date, amount and reference as an earlier payment record;
                     not matched, so nothing is counted twice
  unmatched          nothing fits
"""
import sys
from itertools import combinations

from common import fail, inr, out, rows


def match(payment_id):
    pays = rows("payments")
    idx = next((i for i, p in enumerate(pays) if p["payment_id"] == payment_id), None)
    if idx is None:
        raise KeyError(f"payment {payment_id} not found in data/payments.csv")
    pay = pays[idx]
    amount = int(pay["amount"])
    result = {
        "payment_id": payment_id,
        "customer": pay["customer"],
        "date": pay["date"],
        "reference": pay["reference"],
        "amount": amount,
        "amount_inr": inr(amount),
        "status": "unmatched",
        "matched_by": None,
        "invoices": [],
        "invoice_total": None,
        "difference": None,
        "difference_inr": None,
        "duplicate_of": None,
        "flags": [],
    }

    same = ("customer", "date", "amount", "reference")
    earlier = [p for p in pays[:idx] if all(p[k] == pay[k] for k in same)]
    if earlier:
        result.update(status="duplicate", duplicate_of=earlier[0]["payment_id"])
        result["flags"].append("duplicate_record")
        return result

    open_inv = [
        i for i in rows("invoices") if i["customer"] == pay["customer"] and i["status"] == "open"
    ]
    by_ref = [i for i in open_inv if i["invoice_id"] in pay["reference"]]
    by_amount = [i for i in open_inv if int(i["total"]) == amount]

    if by_ref:
        invs, how = by_ref, "reference"
    elif len(by_amount) == 1:
        invs, how = by_amount, "amount"
    elif len(open_inv) == 1:
        invs, how = open_inv, "only_open_invoice"
    else:
        combos = [
            c
            for r in range(2, len(open_inv) + 1)
            for c in combinations(open_inv, r)
            if sum(int(i["total"]) for i in c) == amount
        ]
        if len(combos) == 1:
            invs = list(combos[0])
            result.update(
                status="possible_combined",
                matched_by="sum_of_open_invoices",
                invoices=[{"invoice_id": i["invoice_id"], "total": int(i["total"]), "total_inr": inr(int(i["total"]))} for i in invs],
                invoice_total=amount,
                difference=0,
                difference_inr=inr(0),
            )
            result["flags"] += ["no_single_invoice_match", "needs_finance_allocation"]
        elif open_inv:
            result["flags"].append("no_invoice_fits")
        else:
            result["flags"].append("no_open_invoices_for_customer")
        return result

    total = sum(int(i["total"]) for i in invs)
    diff = total - amount
    result.update(
        status="exact" if diff == 0 else "short_paid" if diff > 0 else "overpaid",
        matched_by=how,
        invoices=[{"invoice_id": i["invoice_id"], "total": int(i["total"]), "total_inr": inr(int(i["total"]))} for i in invs],
        invoice_total=total,
        difference=diff,
        difference_inr=inr(diff),
    )
    if how != "reference":
        result["flags"].append("no_invoice_reference_on_payment")
    return result


if __name__ == "__main__":
    if len(sys.argv) != 2:
        fail("usage: match.py PAYMENT_ID")
    try:
        out(match(sys.argv[1]))
    except KeyError as e:
        fail(str(e.args[0]))
