"""Prompt-driven command line.

    python -m bookkeeping status          what needs doing now, by stage
    python -m bookkeeping record          record a transaction (asks questions)
    python -m bookkeeping reconcile       count cash, bank, stock (asks questions)
    python -m bookkeeping report          profit report (this month by default)
    python -m bookkeeping stock-in --file stock_list.csv   load what is on the shelf
    python -m bookkeeping shelf [search]  stock, prices and value; search by name
    python -m bookkeeping price ITEM AMOUNT  change a selling price
    python -m bookkeeping stages          the five stages and their rules
    python -m bookkeeping export          all books into one Excel workbook
    python -m bookkeeping sample          load sample naira entries to try it out
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from decimal import Decimal
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


# ---------- the shelf ----------
def pick_item(ledger, allow_new=False):
    """Search the shelf and pick one item by number."""
    while True:
        q = ask("Search item (part of the name; blank = done)", required=False)
        if not q:
            return None
        hits = ledger.find_items(q)
        if len(hits) == 1:
            print(f"    -> {hits[0]}")
            return hits[0]
        if hits:
            for i, name in enumerate(hits, 1):
                qty, _ = ledger.stock_on_hand(name)
                price = ledger.price_of(name)
                print(f"    {i}. {name}  (shelf {qty}, {fmt(price) if price else 'no price'})")
            n = ask("Number", required=False)
            if n.isdigit() and 1 <= int(n) <= len(hits):
                return hits[int(n) - 1]
            continue
        if allow_new and yes(f"    '{q}' is not on the shelf. Add it as a new item?", "n"):
            return q.strip()
        print("    not found on the shelf; try another word.")


def sale_basket(ledger):
    """Build a sale line by line; quantities are checked against the shelf."""
    basket, held = [], {}
    print("Add items to the sale. Leave the search blank when done.")
    while True:
        item = pick_item(ledger)
        if item is None:
            break
        on_shelf = ledger.stock_on_hand(item)[0] - held.get(item, 0)
        if on_shelf <= 0:
            print(f"    {item}: none left on the shelf. Record a purchase first.")
            continue
        qty = Decimal(ask(f"Quantity (shelf has {on_shelf})", 1))
        if qty <= 0 or qty > on_shelf:
            print(f"    must be between 1 and {on_shelf}")
            continue
        listed = ledger.price_of(item)
        price = money(ask("Unit price (₦)", listed))
        if listed is not None and price != listed:
            print(f"    note: {fmt(price)} differs from the listed {fmt(listed)} "
                  f"({fmt(price - listed)} per unit).")
        basket.append((item, qty, price))
        held[item] = held.get(item, 0) + qty
        print(f"    added {qty} x {item} @ {fmt(price)} = {fmt(qty * price)}")
    if basket:
        print(f"  Basket total {fmt(sum(q * p for _, q, p in basket))}")
    return basket


def cmd_shelf(ledger, args):
    rows = ledger.shelf(" ".join(args.search))
    if not rows:
        print("Nothing on the shelf" + (f" matching '{' '.join(args.search)}'." if args.search
              else ". Load your stock list: stock-in --file stock_list.csv"))
        return
    print(f"{'Item':28}{'Qty':>8}{'Cost':>14}{'Sell':>14}{'Margin':>12}{'Value':>16}")
    for r in rows:
        sell = fmt(r["selling_price"]) if r["selling_price"] is not None else "-"
        margin = fmt(r["margin_per_unit"]) if r["margin_per_unit"] is not None else "-"
        flag = "  LOW" if r["low"] else ""
        print(f"{r['item'][:27]:28}{str(r['qty']):>8}{fmt(r['unit_cost']):>14}"
              f"{sell:>14}{margin:>12}{fmt(r['stock_value']):>16}{flag}")
    print(f"{'Stock value at cost':64}{fmt(sum(r['stock_value'] for r in rows)):>16}")


def cmd_stock_in(ledger, args):
    if args.file:
        n = ledger.load_stock_list(args.file, args.date)
        print(f"Loaded {n} items onto the shelf as opening stock.")
        return cmd_shelf(ledger, argparse.Namespace(search=[]))
    print("Opening stock: what is already on the shelf. Leave item blank to finish.")
    date = ask("Date (YYYY-MM-DD)", str(ledger._now()))
    while True:
        item = ask("Item", required=False)
        if not item:
            break
        ledger.stock_in(date=date, item=item, qty=ask("Quantity on shelf"),
                        unit_cost=ask("Cost price per unit (₦)"),
                        selling_price=ask("Selling price per unit (₦)"),
                        reorder_level=ask("Reorder when down to", required=False))
    cmd_shelf(ledger, argparse.Namespace(search=[]))


def cmd_price(ledger, args):
    item = ledger.canonical(args.item)
    old = ledger.price_of(item)
    ledger.set_price(item, args.amount, args.reorder)
    print(f"{item}: {fmt(old) if old else 'no price'} -> {fmt(money(args.amount))}")


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
        basket = sale_basket(ledger)
        if not basket:
            print("  Nothing sold; nothing recorded.")
            return
        print("Stage 2 - Separate")
        paid = ask("Paid by", "cash", ("cash", "bank", "credit"))
        cust = ask("Customer name" + (" (required for credit)" if paid == "credit" else ""),
                   required=(paid == "credit"))
        ev = evidence_prompt()
        print("Stage 3 - Post")
        total = cogs = 0
        for item, qty, price in basket:
            row = ledger.record_sale(date=date, customer=cust, item=item, qty=qty,
                                     unit_price=price, paid_via=paid, evidence=ev)
            total += money(row["total"])
            cogs += money(row["cost_of_goods"])
            left = ledger.stock_on_hand(item)[0]
            print(f"  Sales book {row['id']}: {qty} x {item} = {fmt(money(row['total']))}"
                  f"  | shelf now {left}")
        print(f"  Total {fmt(total)}"
              + (" -> customer debt book (no money yet)." if paid == "credit"
                 else f" -> {paid} book."))
        print(f"  Cost of goods {fmt(cogs)}, so gross profit on this sale is "
              f"{fmt(total - cogs)}, not {fmt(total)}.")
        for line in ledger.shelf():
            if line["low"] and line["item"] in {b[0] for b in basket}:
                print(f"  ! {line['item']} is down to {line['qty']} "
                      f"(reorder level {line['reorder_level']}). Restock.")
    elif kind == "purchase":
        paid = ask("Paid by", "cash", ("cash", "bank", "credit"))
        sup = ask("Supplier name", required=(paid == "credit"))
        item = None
        while not item:
            item = pick_item(ledger, allow_new=True)
        qty = ask("Quantity")
        cost = ask("Unit cost (₦)")
        listed = ledger.price_of(item)
        sell = ask("Selling price (₦) on the shelf", listed, required=False)
        ev = evidence_prompt()
        ledger.record_purchase(date=date, supplier=sup, item=item, qty=qty,
                               unit_cost=cost, paid_via=paid, evidence=ev,
                               selling_price=sell or None)
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
    sh = wb.create_sheet("Shelf (stock & prices)")
    sh.append(["Item", "Qty on shelf", "Avg cost", "Selling price", "Margin/unit",
               "Stock value at cost", "Reorder level", "Low?"])
    for r in ledger.shelf():
        sh.append([r["item"], float(r["qty"]), float(r["unit_cost"]),
                   float(r["selling_price"]) if r["selling_price"] is not None else None,
                   float(r["margin_per_unit"]) if r["margin_per_unit"] is not None else None,
                   float(r["stock_value"]),
                   float(r["reorder_level"]) if r["reorder_level"] is not None else None,
                   "LOW" if r["low"] else ""])
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
    template = Path(__file__).resolve().parents[1] / "stock_list_template.csv"
    ledger.load_stock_list(template, date=d(20))          # stock already on the shelf
    # sales: no price typed -> listed selling price is used, shelf is reduced
    ledger.record_sale(date=d(15), customer="", item="rice 50kg", qty=2,
                       paid_via="cash", evidence="RCPT-001")
    ledger.record_purchase(date=d(14), supplier="Ade Wholesale", item="Rice 50kg",
                           qty=5, unit_cost=74000, paid_via="credit", evidence="INV-221")
    ledger.record_sale(date=d(12), customer="Mama Chidi Canteen", item="Rice 50kg",
                       qty=3, unit_price=84000, paid_via="credit", evidence="INV-S-002")
    ledger.record_sale(date=d(10), customer="Kunle Stores", item="Groundnut oil 25L",
                       qty=4, paid_via="bank", evidence="TRF-1177")
    ledger.record_sale(date=d(10), customer="Kunle Stores", item="Indomie carton (40)",
                       qty=21, paid_via="bank", evidence="TRF-1177")
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
    print(f"Sample entries loaded into {ledger.folder}. Try: shelf, status, report, export.")


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
    sh = sub.add_parser("shelf", help="show / search the shelf")
    sh.add_argument("search", nargs="*")
    si = sub.add_parser("stock-in", help="load stock already on the shelf")
    si.add_argument("--file", help="CSV: item,qty,unit_cost,selling_price[,reorder_level]")
    si.add_argument("--date")
    pr = sub.add_parser("price", help="set an item's selling price")
    pr.add_argument("item")
    pr.add_argument("amount")
    pr.add_argument("--reorder")
    rep = sub.add_parser("report")
    rep.add_argument("--from", dest="date_from")
    rep.add_argument("--to", dest="date_to")
    e = sub.add_parser("export")
    e.add_argument("--out")
    sub.add_parser("sample")
    args = p.parse_args(argv)
    ledger = Ledger(Path(args.data))
    try:
        globals()[f"cmd_{args.cmd.replace('-', '_')}"](ledger, args)
    except BookkeepingError as exc:
        print(f"Refused: {exc}", file=sys.stderr)
        return 1
    return 0
