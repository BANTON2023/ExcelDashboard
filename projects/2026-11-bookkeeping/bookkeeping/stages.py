"""The five stages, the "what is due now" check, reconciliation and reporting.

The five-stage split is [STD] scaffolding: the pasted conversation gives the
rules and the six books but the excerpt does not name five stages, so each
stage below is mapped to the rule(s) it enforces from the conversation.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from decimal import Decimal

from .core import Ledger, BookkeepingError, money, fmt

STAGES = {
    1: ("Capture", "Record every transaction the day it happens, with its "
        "receipt or payment evidence.",
        "[SRC] record immediately, not from memory; keep receipts and payment evidence"),
    2: ("Separate", "Decide: business or personal? cash, bank or credit?",
        "[SRC] keep personal separate from business; always record credit sales"),
    3: ("Post", "Write the entry into the right book(s).",
        "[SRC] sales, expenses, customer debt, supplier debt, stock, cash and bank books"),
    4: ("Reconcile", "Count cash, check the bank statement, count stock, "
        "confirm who owes and who is owed.",
        "[SRC] reconcile cash and bank balances regularly"),
    5: ("Report", "Work out profit: Sales - Cost of Goods Sold - Operating Expenses.",
        "[SRC] never confuse sales revenue with profit"),
}

# [STD] reasonable small-business cadences; change to suit the business.
CASH_COUNT_EVERY_DAYS = 7
BANK_RECONCILE_EVERY_DAYS = 30
STOCK_COUNT_EVERY_DAYS = 30
LATE_ENTRY_DAYS = 2           # recorded this many days after it happened = "from memory"
DEBT_OVERDUE_DAYS = 30
# [STD] heuristic only: words that often mean a personal cost slipped into the
# business expenses book. A match is a prompt to check, not an error.
PERSONAL_HINTS = ("school fees", "family", "personal", "church", "wedding",
                  "house rent", "home", "children", "hospital")

TRANSACTION_BOOKS = ("sales", "expenses", "customer_debts", "supplier_debts",
                     "stock", "drawings")


@dataclass
class Task:
    stage: int
    form: str
    message: str
    severity: str = "due"   # "due", "warning", "info"


@dataclass
class Status:
    today: dt.date
    tasks: list[Task] = field(default_factory=list)

    def add(self, *args, **kw):
        self.tasks.append(Task(*args, **kw))


def _date(row) -> dt.date:
    return dt.date.fromisoformat(row["date"])


def _last_reconciled(ledger: Ledger, target: str) -> dt.date | None:
    dates = [_date(r) for r in ledger.rows("reconciliations") if r["target"] == target]
    return max(dates) if dates else None


def oldest_unpaid(ledger: Ledger, book: str, party: str) -> dt.date | None:
    """Apply payments to the oldest debts first; return date of oldest unpaid one."""
    key = "customer" if book == "customer_debts" else "supplier"
    rows = sorted((r for r in ledger.rows(book) if r[key] == party), key=_date)
    paid = sum((-money(r["amount"]) for r in rows if money(r["amount"]) < 0), Decimal("0"))
    for r in rows:
        amt = money(r["amount"])
        if amt <= 0:
            continue
        if paid >= amt:
            paid -= amt
            continue
        return _date(r)
    return None


def status(ledger: Ledger, today: dt.date | None = None) -> Status:
    today = today or ledger._now()
    st = Status(today)

    # ---- Stage 1: capture ----
    all_rows = [(b, r) for b in TRANSACTION_BOOKS for r in ledger.rows(b)]
    if not any(_date(r) == today for _, r in all_rows):
        st.add(1, "All books", f"Nothing recorded for {today}. Record today's "
               "sales, purchases and expenses before close of business.")
    # Only the books where a person makes the first entry; stock/debt/cash rows
    # created automatically from a sale or purchase would just repeat it.
    for book in ("sales", "expenses", "drawings", "stock"):
        late = [r["id"] for r in ledger.rows(book)
                if (book != "stock" or r["kind"] == "purchase")
                and (dt.datetime.fromisoformat(r["recorded_at"]).date()
                    - _date(r)).days > LATE_ENTRY_DAYS]
        if late:
            shown = ", ".join(late[:5]) + (" ..." if len(late) > 5 else "")
            st.add(1, book, f"{len(late)} entr{'y' if len(late) == 1 else 'ies'} "
                   f"recorded more than {LATE_ENTRY_DAYS} days after the event "
                   f"({shown}): written from memory. Check against evidence.",
                   "warning")
    for book in ("sales", "expenses", "drawings"):
        for r in ledger.rows(book):
            if not r["evidence"].strip():
                st.add(1, book, f"{r['id']} ({r['date']}) has no receipt or "
                       "payment evidence reference. Find and file it.", "warning")

    # ---- Stage 2: separate ----
    for r in ledger.rows("expenses"):
        text = f"{r['category']} {r['description']}".lower()
        if any(h in text for h in PERSONAL_HINTS):
            st.add(2, "Expenses book", f"{r['id']} '{r['description']}' looks "
                   "personal. If it is, it belongs in owner drawings, not "
                   "business expenses.", "warning")

    # ---- Stage 3: post / follow up the debt books ----
    for cust, bal in ledger.debt_balance("customer_debts").items():
        since = oldest_unpaid(ledger, "customer_debts", cust)
        age = (today - since).days if since else 0
        sev = "due" if age > DEBT_OVERDUE_DAYS else "info"
        st.add(3, "Customer debt book", f"{cust} owes {fmt(bal)} "
               f"(oldest unpaid {age} days). "
               + ("Chase payment." if sev == "due" else ""), sev)
    for sup, bal in ledger.debt_balance("supplier_debts").items():
        since = oldest_unpaid(ledger, "supplier_debts", sup)
        age = (today - since).days if since else 0
        st.add(3, "Supplier debt book", f"You owe {sup} {fmt(bal)} "
               f"(oldest unpaid {age} days).",
               "due" if age > DEBT_OVERDUE_DAYS else "info")
    credit_sales = sum((money(r["total"]) for r in ledger.rows("sales")
                        if r["paid_via"] == "credit"), Decimal("0"))
    credit_debts = sum((money(r["amount"]) for r in ledger.rows("customer_debts")
                        if r["kind"] == "credit sale"), Decimal("0"))
    if credit_sales != credit_debts:
        st.add(3, "Customer debt book", f"Credit sales {fmt(credit_sales)} do "
               f"not match debts raised {fmt(credit_debts)}. A credit sale is "
               "missing from one of the books.", "warning")

    # ---- Stage 4: reconcile ----
    for target, every, form in (
            ("cash", CASH_COUNT_EVERY_DAYS, "Cash and bank book (cash count)"),
            ("bank", BANK_RECONCILE_EVERY_DAYS, "Cash and bank book (bank statement)")):
        last = _last_reconciled(ledger, target)
        if last is None or (today - last).days >= every:
            when = "never" if last is None else f"last on {last}"
            st.add(4, form, f"Reconcile {target}: book says "
                   f"{fmt(ledger.balance(target))} ({when}).")
    for item in ledger.stock_items():
        last = _last_reconciled(ledger, f"stock:{item}")
        if last is None or (today - last).days >= STOCK_COUNT_EVERY_DAYS:
            qty, _ = ledger.stock_on_hand(item)
            st.add(4, "Stock book", f"Count {item}: stock book says {qty}.")
    for r in ledger.rows("reconciliations"):
        if money(r["difference"]) != 0 and "adjusted" not in r["note"]:
            st.add(4, "Reconciliation log", f"{r['target']} on {r['date']} was "
                   f"off by {r['difference']}. Investigate before adjusting.",
                   "warning")

    # ---- Stage 5: report ----
    first_this_month = today.replace(day=1)
    prev_end = first_this_month - dt.timedelta(days=1)
    prev_start = prev_end.replace(day=1)
    if today.day <= 10 and any(prev_start <= _date(r) <= prev_end
                               for _, r in all_rows):
        st.add(5, "Profit report", f"Month-end report for {prev_start:%B %Y} "
               f"is due: run  report --from {prev_start} --to {prev_end}")
    return st


def reconcile(ledger: Ledger, *, date, target: str, actual, note="",
              adjust=False) -> dict:
    """Compare the book with a physical count / statement and log the result.

    target is "cash", "bank" or "stock:<item>". With adjust=True a difference
    is written off ([STD]: only after you have investigated it).
    """
    date = ledger._check_date(date)
    if target in ("cash", "bank"):
        book_value = ledger.balance(target)
        actual_value = money(actual)
    elif target.startswith("stock:"):
        item = target.split(":", 1)[1]
        book_value, _ = ledger.stock_on_hand(item)
        actual_value = Decimal(str(actual))
    else:
        raise BookkeepingError("target must be cash, bank or stock:<item>")
    diff = actual_value - book_value
    if adjust and diff != 0:
        if target.startswith("stock:"):
            _, avg = ledger.stock_on_hand(item)
            ledger._append("stock", {
                "date": date, "item": item,
                "qty_in": diff if diff > 0 else "",
                "qty_out": -diff if diff < 0 else "",
                "unit_cost": avg, "kind": "count adjustment", "ref": note})
            if diff < 0:  # [STD] lost/damaged stock is an operating expense
                ledger._append("expenses", {
                    "date": date, "category": "Stock loss",
                    "description": f"{-diff} x {item} missing at count",
                    "amount": (-diff * avg).quantize(Decimal("0.01")),
                    "paid_via": "none", "evidence": f"stock count {date}"})
        else:
            if diff < 0:
                ledger._append("expenses", {
                    "date": date, "category": "Cash shortage",
                    "description": note or f"{target} shortage at reconciliation",
                    "amount": -diff, "paid_via": target,
                    "evidence": f"reconciliation {date}"})
            ledger._append("cash_bank", {
                "date": date, "account": target,
                "amount_in": diff if diff > 0 else "",
                "amount_out": -diff if diff < 0 else "",
                "description": f"Reconciliation adjustment: {note}",
                "ref": "reconciliation"})
        note = (note + " (adjusted)").strip()
    return ledger._append("reconciliations", {
        "date": date, "target": target, "book_value": book_value,
        "actual_value": actual_value, "difference": diff, "note": note})


def profit_report(ledger: Ledger, start, end) -> dict:
    """[SRC] Sales - Cost of Goods Sold - Operating Expenses = Profit."""
    start, end = dt.date.fromisoformat(str(start)), dt.date.fromisoformat(str(end))
    inside = lambda r: start <= _date(r) <= end
    sales = [r for r in ledger.rows("sales") if inside(r)]
    revenue = sum((money(r["total"]) for r in sales), Decimal("0"))
    cogs = sum((money(r["cost_of_goods"]) for r in sales), Decimal("0"))
    opex_by_cat: dict[str, Decimal] = {}
    for r in ledger.rows("expenses"):
        if inside(r):
            opex_by_cat[r["category"]] = opex_by_cat.get(r["category"], Decimal("0")) + money(r["amount"])
    opex = sum(opex_by_cat.values(), Decimal("0"))
    cash_from_sales = sum((money(r["total"]) for r in sales if r["paid_via"] != "credit"), Decimal("0"))
    collected = sum((-money(r["amount"]) for r in ledger.rows("customer_debts")
                     if inside(r) and r["kind"] == "payment"), Decimal("0"))
    drawings = sum((money(r["amount"]) for r in ledger.rows("drawings") if inside(r)), Decimal("0"))
    return {
        "from": start, "to": end, "sales": revenue, "cogs": cogs,
        "gross_profit": revenue - cogs, "opex_by_category": opex_by_cat,
        "opex": opex, "profit": revenue - cogs - opex,
        "credit_sales_in_period": revenue - cash_from_sales,
        "cash_received_from_customers": cash_from_sales + collected,
        "owner_drawings": drawings,
    }
