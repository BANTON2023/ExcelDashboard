"""Prompt-driven command line.

    python -m bookkeeping status          what needs doing now, by stage
    python -m bookkeeping record          record a transaction (asks questions)
    python -m bookkeeping reconcile       count cash, bank, stock (asks questions)
    python -m bookkeeping report          profit report (this month by default)
    python -m bookkeeping stages          the five stages and their rules
    python -m bookkeeping export          all books into one Excel workbook
    python -m bookkeeping sample          load sample naira entries to try it out
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

from .core import Ledger, BookkeepingError, BOOK_TITLES, BOOKS, fmt, money
from .stages import STAGES, status, reconcile, profit_report


# ---------- prompting ----------
def ask(label, default=None, choices=None, required=True):
    hint = f" [{'/'.join(choices)}]" if choices else ""
    hint += f" ({default})" if default not in (None, "") else ""
    while True:
        try:
            raw = input(f"  {label}{hint}: ").strip()
        except EOFError:
            raise SystemExit("\nInput ended; nothing more recorded.")
        value = raw or (str(default) if default is not None else "")
        if choices and value not in choices:
            print(f"    choose one of: {', '.join(choices)}")
            continue
        if required and not value:
            print("    required")
            continue
        return value


def yes(label, default="y") -> bool:
    return ask(label, default, ("y", "n")) == "y"


def evidence_prompt() -> str:
    # [SRC] keep receipts and payment evidence
    ev = ask("Receipt / transfer ref / evidence (blank = none yet)", required=False)
    if not ev:
        print("    ! No evidence. This will show on `status` until you add it.")
    return ev


# ---------- commands ----------
def cmd_stages(ledger, args):
    for n, (name, what, rule) in STAGES.items():
        print(f"Stage {n} - {name}\n    {what}\n    {rule}")
    print("\n[SRC] = from your ChatGPT conversation. [STD] = standard practice "
          "added to fill gaps.")


def cmd_status(ledger, args):
    today = dt.date.fromisoformat(args.today) if args.today else None
    st = status(ledger, today)
    print(f"Bookkeeping due on {st.today}\n")
    if not st.tasks:
        print("Nothing due. Books are up to date.")
        return
    for n, (name, _, _) in STAGES.items():
        tasks = [t for t in st.tasks if t.stage == n]
        if not tasks:
            continue
        print(f"Stage {n} - {name}")
        for t in tasks:
            mark = {"due": "[DUE] ", "warning": "[CHECK]", "info": "[info]"}[t.severity]
            print(f"  {mark} {t.form}: {t.message}")
        print()


RECORD_TYPES = {
    "sale": "Sale of goods (cash, bank transfer or on credit)",
    "purchase": "Buying stock to resell",
    "expense": "Paying a running cost (rent, fuel, data, wages...) or personal spend",
    "customer-payment": "A customer paying what they owe",
    "supplier-payment": "Paying a supplier what you owe",
    "transfer": "Moving money between cash and bank",
    "opening": "Opening cash or bank balance (first use only)",
}


def cmd_record(ledger, args):
    kind = args.kind
    if not kind:
        print("What happened?")
        for k, v in RECORD_TYPES.items():
            print(f"  {k:17} {v}")
        kind = ask("Type", choices=tuple(RECORD_TYPES))
    today = str(ledger._now())
    print(f"\nStage 1 - Capture: {RECORD_TYPES[kind]}")
    date = ask("Date (YYYY-MM-DD)", today)
    if kind == "sale":
        print("Stage 2 - Separate")
        paid = ask("Paid by", "cash", ("cash", "bank", "credit"))
        cust = ask("Customer name", required=(paid == "credit"))
        items = ledger.stock_items()
        if items:
            print(f"    in stock: {', '.join(items)}")
        item = ask("Item")
        qty = ask("Quantity", 1)
        price = ask("Unit price (₦)")
        ev = evidence_prompt()
        print("Stage 3 - Post")
        row = ledger.record_sale(date=date, customer=cust, item=item, qty=qty,
                                 unit_price=price, paid_via=paid, evidence=ev)
        print(f"  Sales book {row['id']}: {fmt(money(row['total']))}; stock book reduced"
              + ("; customer debt book raised (no money yet)." if paid == "credit"
                 else f"; {paid} book increased."))
        print(f"  Cost of these goods {fmt(money(row['cost_of_goods']))}, so this sale "
              f"adds {fmt(money(row['total']) - money(row['cost_of_goods']))} gross "
              "profit, not the full sale amount.")
    elif kind == "purchase":
        paid = ask("Paid by", "cash", ("cash", "bank", "credit"))
        sup = ask("Supplier name", required=(paid == "credit"))
        item = ask("Item")
        qty = ask("Quantity")
        cost = ask("Unit cost (₦)")
        ev = evidence_prompt()
        ledger.record_purchase(date=date, supplier=sup, item=item, qty=qty,
                               unit_cost=cost, paid_via=paid, evidence=ev)
        print("  Stock book increased"
              + ("; supplier debt book raised." if paid == "credit" else f"; {paid} book reduced."))
    elif kind == "expense":
        print("Stage 2 - Separate")
        business = yes("Is this a BUSINESS cost (not personal/family)?")
        desc = ask("Description")
        cat = ask("Category (rent, transport, data, wages, power...)") if business else "Drawings"
        amt = ask("Amount (₦)")
        paid = ask("Paid by", "cash", ("cash", "bank", "credit") if business else ("cash", "bank"))
        sup = ask("Supplier", required=(paid == "credit")) if business else ""
        ev = evidence_prompt()
        row = ledger.record_expense(date=date, category=cat, description=desc,
                                    amount=amt, paid_via=paid, business=business,
                                    supplier=sup, evidence=ev)
        print(f"  {'Expenses book' if business else 'Owner drawings'} {row['id']} recorded."
              + ("" if business else " Kept out of business expenses and profit."))
    elif kind == "customer-payment":
        owing = ledger.debt_balance("customer_debts")
        for c, b in owing.items():
            print(f"    {c}: {fmt(b)}")
        cust = ask("Customer", choices=tuple(owing) or None)
        amt = ask("Amount received (₦)", owing.get(cust))
        acct = ask("Received into", "bank", ("cash", "bank"))
        ledger.receive_customer_payment(date=date, customer=cust, amount=amt,
                                        account=acct, evidence=evidence_prompt())
        print(f"  {cust} now owes {fmt(ledger.debt_balance('customer_debts', cust)[cust])}.")
    elif kind == "supplier-payment":
        owed = ledger.debt_balance("supplier_debts")
        for s, b in owed.items():
            print(f"    {s}: {fmt(b)}")
        sup = ask("Supplier", choices=tuple(owed) or None)
        amt = ask("Amount paid (₦)", owed.get(sup))
        acct = ask("Paid from", "bank", ("cash", "bank"))
        ledger.pay_supplier(date=date, supplier=sup, amount=amt, account=acct,
                            evidence=evidence_prompt())
    elif kind == "transfer":
        frm = ask("From", "cash", ("cash", "bank"))
        to = "bank" if frm == "cash" else "cash"
        ledger.transfer(date=date, from_account=frm, to_account=to,
                        amount=ask("Amount (₦)"), ref=ask("Teller/ref", required=False))
    elif kind == "opening":
        acct = ask("Account", "cash", ("cash", "bank"))
        ledger.opening_balance(date=date, account=acct, amount=ask("Amount (₦)"))
    print(f"  Cash book {fmt(ledger.balance('cash'))} | Bank book {fmt(ledger.balance('bank'))}")


def cmd_reconcile(ledger, args):
    date = ask("Date of count (YYYY-MM-DD)", str(ledger._now()))
    print("Stage 4 - Reconcile. Leave blank to skip an item.")
    targets = ["cash", "bank"] + [f"stock:{i}" for i in ledger.stock_items()]
    for t in targets:
        if t == "cash":
            book, label = fmt(ledger.balance("cash")), "Cash counted in hand (₦)"
        elif t == "bank":
            book, label = fmt(ledger.balance("bank")), "Bank statement closing balance (₦)"
        else:
            book, label = str(ledger.stock_on_hand(t[6:])[0]), f"Physical count of {t[6:]}"
        print(f"\n  {t}: book says {book}")
        actual = ask(label, required=False)
        if not actual:
            continue
        r = reconcile(ledger, date=date, target=t, actual=actual)
        diff = money(r["difference"])
        if diff == 0:
            print("    Agrees.")
            continue
        print(f"    Difference {diff}. Look for: unrecorded sales/expenses, "
              "bank charges, unrecorded transfers, missing receipts.")
        if yes("    Investigated and want to write the difference off now?", "n"):
            note = ask("    Reason")
            reconcile(ledger, date=date, target=t, actual=actual, note=note, adjust=True)
            print("    Adjusted and logged.")


def cmd_report(ledger, args):
    today = ledger._now()
    start = args.date_from or str(today.replace(day=1))
    end = args.date_to or str(today)
    r = profit_report(ledger, start, end)
    w = 34
    print(f"Profit report {r['from']} to {r['to']}\n")
    print(f"{'Sales':{w}}{fmt(r['sales']):>18}")
    print(f"{'less Cost of goods sold':{w}}{fmt(-r['cogs']):>18}")
    print(f"{'= Gross profit':{w}}{fmt(r['gross_profit']):>18}")
    for cat, amt in sorted(r["opex_by_category"].items()):
        print(f"{'  less ' + cat:{w}}{fmt(-amt):>18}")
    print(f"{'= PROFIT':{w}}{fmt(r['profit']):>18}\n")
    print("Not profit, shown so they are not confused with it:")
    print(f"  Cash/bank actually received from customers  {fmt(r['cash_received_from_customers'])}")
    print(f"  Sales made on credit in this period         {fmt(r['credit_sales_in_period'])}")
    print(f"  Owner drawings (personal, outside profit)   {fmt(r['owner_drawings'])}")


def cmd_export(ledger, args):
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font
    except ImportError:
        raise SystemExit("Install openpyxl (pip install openpyxl), or open the CSVs in "
                         f"{ledger.folder} directly in Excel.")
    out = Path(args.out or ledger.folder / "bookkeeping.xlsx")
    wb = Workbook()
    ws = wb.active
    ws.title = "Due now"
    ws.append(["Stage", "Form / book", "Severity", "What to do"])
    for t in status(ledger).tasks:
        ws.append([f"{t.stage} {STAGES[t.stage][0]}", t.form, t.severity, t.message])
    numeric = {"qty", "unit_price", "total", "cost_of_goods", "amount", "qty_in",
               "qty_out", "unit_cost", "amount_in", "amount_out", "book_value",
               "actual_value", "difference"}
    for book, cols in BOOKS.items():
        s = wb.create_sheet(BOOK_TITLES[book][:31])
        s.append(cols)
        for row in ledger.rows(book):
            s.append([float(row[c]) if c in numeric and row[c] not in ("", None)
                      else row[c] for c in cols])
    for s in wb.worksheets:
        for c in s[1]:
            c.font = Font(bold=True)
        s.freeze_panes = "A2"
        for col in s.columns:
            s.column_dimensions[col[0].column_letter].width = min(
                60, max(10, max(len(str(c.value or "")) for c in col) + 2))
    wb.save(out)
    print(f"Wrote {out}")


def cmd_sample(ledger, args):
    if any(ledger.rows(b) for b in ("sales", "cash_bank")):
        raise SystemExit(f"{ledger.folder} already has entries; use an empty --data folder.")
    t = ledger._now()
    d = lambda n: str(t - dt.timedelta(days=n))
    ledger.opening_balance(date=d(20), account="cash", amount=50000)
    ledger.opening_balance(date=d(20), account="bank", amount=400000)
    ledger.record_purchase(date=d(19), supplier="Ade Wholesale", item="Rice 50kg",
                           qty=10, unit_cost=72000, paid_via="credit", evidence="INV-221")
    ledger.record_purchase(date=d(19), supplier="Balogun Market", item="Groundnut oil 25L",
                           qty=8, unit_cost=38000, paid_via="bank", evidence="TRF-0912")
    ledger.record_sale(date=d(15), customer="", item="Rice 50kg", qty=2,
                       unit_price=85000, paid_via="cash", evidence="RCPT-001")
    ledger.record_sale(date=d(12), customer="Mama Chidi Canteen", item="Rice 50kg",
                       qty=3, unit_price=84000, paid_via="credit", evidence="INV-S-002")
    ledger.record_sale(date=d(10), customer="Kunle Stores", item="Groundnut oil 25L",
                       qty=4, unit_price=45000, paid_via="bank", evidence="TRF-1177")
    ledger.record_expense(date=d(9), category="Transport", description="Delivery to Mama Chidi",
                          amount=6000, paid_via="cash", business=True, evidence="")
    ledger.record_expense(date=d(8), category="Rent", description="Shop rent (month)",
                          amount=60000, paid_via="bank", business=True, evidence="TRF-1180")
    ledger.record_expense(date=d(7), category="", description="Children school fees",
                          amount=45000, paid_via="bank", business=False, evidence="TRF-1185")
    ledger.receive_customer_payment(date=d(5), customer="Mama Chidi Canteen",
                                    amount=100000, account="bank", evidence="TRF-1201")
    ledger.pay_supplier(date=d(3), supplier="Ade Wholesale", amount=250000,
                        account="bank", evidence="TRF-1210")
    print(f"Sample entries loaded into {ledger.folder}. Try: status, report, export.")


def main(argv=None):
    p = argparse.ArgumentParser(prog="bookkeeping", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data", default="books", help="folder holding the books (default ./books)")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("stages")
    s = sub.add_parser("status")
    s.add_argument("--today", help="pretend today is YYYY-MM-DD")
    r = sub.add_parser("record")
    r.add_argument("kind", nargs="?", choices=tuple(RECORD_TYPES))
    sub.add_parser("reconcile")
    rep = sub.add_parser("report")
    rep.add_argument("--from", dest="date_from")
    rep.add_argument("--to", dest="date_to")
    e = sub.add_parser("export")
    e.add_argument("--out")
    sub.add_parser("sample")
    args = p.parse_args(argv)
    ledger = Ledger(Path(args.data))
    try:
        globals()[f"cmd_{args.cmd}"](ledger, args)
    except BookkeepingError as exc:
        print(f"Refused: {exc}", file=sys.stderr)
        return 1
    return 0
