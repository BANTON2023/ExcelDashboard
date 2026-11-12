"""Storage and posting rules for a small-business bookkeeping system.

Every book is a CSV file in a data folder, so it opens directly in Excel.

Where each rule comes from is marked in comments:
  [SRC]  = stated in the user's ChatGPT conversation (pasted 12 Nov 2026)
  [STD]  = standard bookkeeping practice added to fill a gap (scaffolding,
           not from the conversation) -- check against your accountant / FIRS
           guidance before relying on it for tax.
"""

from __future__ import annotations

import csv
import datetime as dt
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

CURRENCY = "₦"
TWO = Decimal("0.01")

# [SRC] "Minimum records to maintain": the six books.
# [STD] drawings + reconciliations are added: drawings is where personal money
#       goes so it never lands in the expenses book; reconciliations keeps a
#       dated trail of every cash/bank/stock check.
BOOKS: dict[str, list[str]] = {
    "sales": ["id", "date", "customer", "item", "qty", "unit_price", "total",
              "paid_via", "cost_of_goods", "evidence", "recorded_at"],
    "expenses": ["id", "date", "category", "description", "amount", "paid_via",
                 "supplier", "evidence", "recorded_at"],
    "customer_debts": ["id", "date", "customer", "amount", "kind", "ref",
                       "evidence", "recorded_at"],
    "supplier_debts": ["id", "date", "supplier", "amount", "kind", "ref",
                       "evidence", "recorded_at"],
    "stock": ["id", "date", "item", "qty_in", "qty_out", "unit_cost", "kind",
              "ref", "recorded_at"],
    "cash_bank": ["id", "date", "account", "amount_in", "amount_out",
                  "description", "ref", "recorded_at"],
    "drawings": ["id", "date", "description", "amount", "paid_via", "evidence",
                 "recorded_at"],
    "reconciliations": ["id", "date", "target", "book_value", "actual_value",
                        "difference", "note", "recorded_at"],
}

BOOK_TITLES = {
    "sales": "Sales book",
    "expenses": "Expenses book",
    "customer_debts": "Customer debt book",
    "supplier_debts": "Supplier debt book",
    "stock": "Stock book",
    "cash_bank": "Cash and bank book",
    "drawings": "Owner drawings (personal, not business expense)",
    "reconciliations": "Reconciliation log",
}

# The shelf price list is master data (one row per item, edited in place),
# not a transaction book, so it is kept apart from BOOKS.
PRICE_LIST = "price_list"
PRICE_COLS = ["item", "selling_price", "reorder_level", "updated"]

PAY_METHODS = ("cash", "bank", "credit")
ACCOUNTS = ("cash", "bank")


class BookkeepingError(ValueError):
    """A rule was broken; the entry is refused."""


def money(value) -> Decimal:
    try:
        d = Decimal(str(value).replace(",", "").replace(CURRENCY, "").strip())
    except InvalidOperation as exc:
        raise BookkeepingError(f"Not an amount: {value!r}") from exc
    return d.quantize(TWO, rounding=ROUND_HALF_UP)


def fmt(amount: Decimal) -> str:
    sign = "-" if amount < 0 else ""
    return f"{sign}{CURRENCY}{abs(amount):,.2f}"


def parse_date(value) -> dt.date:
    if isinstance(value, dt.date):
        return value
    try:
        return dt.date.fromisoformat(str(value).strip())
    except ValueError as exc:
        raise BookkeepingError(f"Date must be YYYY-MM-DD, got {value!r}") from exc


@dataclass
class Ledger:
    """All books for one business, stored as CSV files in `folder`."""

    folder: Path
    today: dt.date | None = None  # injectable for tests

    def __post_init__(self):
        self.folder = Path(self.folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        for name, cols in BOOKS.items():
            path = self._path(name)
            if not path.exists():
                with path.open("w", newline="", encoding="utf-8") as fh:
                    csv.writer(fh).writerow(cols)
        if not self._path(PRICE_LIST).exists():
            self._write_prices([])

    # ---------- storage ----------
    def _path(self, book: str) -> Path:
        return self.folder / f"{book}.csv"

    def rows(self, book: str) -> list[dict]:
        with self._path(book).open(newline="", encoding="utf-8") as fh:
            return list(csv.DictReader(fh))

    def _now(self) -> dt.date:
        return self.today or dt.date.today()

    def _append(self, book: str, row: dict) -> dict:
        existing = self.rows(book)
        prefix = book[:2].upper()
        row = {"id": f"{prefix}{len(existing) + 1:05d}", **row,
               "recorded_at": dt.datetime.now().isoformat(timespec="seconds")}
        with self._path(book).open("a", newline="", encoding="utf-8") as fh:
            csv.DictWriter(fh, fieldnames=BOOKS[book]).writerow(
                {k: row.get(k, "") for k in BOOKS[book]})
        return row

    def _check_date(self, date) -> dt.date:
        d = parse_date(date)
        if d > self._now():
            raise BookkeepingError("Date is in the future.")
        return d

    def _cash_move(self, date, account, amount_in, amount_out, description, ref):
        if account not in ACCOUNTS:
            raise BookkeepingError(f"Account must be cash or bank, got {account!r}")
        if amount_out and self.balance(account) - amount_out < 0:
            # [STD] a negative cash book means something was not recorded.
            raise BookkeepingError(
                f"This would take the {account} book below zero "
                f"({fmt(self.balance(account))} available). Record the money "
                f"that came in first.")
        self._append("cash_bank", {
            "date": date, "account": account,
            "amount_in": amount_in or "", "amount_out": amount_out or "",
            "description": description, "ref": ref})

    # ---------- balances ----------
    def balance(self, account: str) -> Decimal:
        total = Decimal("0")
        for r in self.rows("cash_bank"):
            if r["account"] == account:
                total += money(r["amount_in"] or 0) - money(r["amount_out"] or 0)
        return total

    def stock_on_hand(self, item: str) -> tuple[Decimal, Decimal]:
        """Return (quantity, weighted-average unit cost). [STD] AVCO method."""
        qty, value = Decimal("0"), Decimal("0")
        # Date order (stable within a day), so a back-dated entry is costed
        # where it belongs rather than where it was typed.
        rows = sorted(self.rows("stock"), key=lambda r: r["date"])
        for r in rows:
            if r["item"].lower() != item.lower():
                continue
            q_in, q_out = Decimal(r["qty_in"] or 0), Decimal(r["qty_out"] or 0)
            cost = money(r["unit_cost"] or 0)
            if q_in:
                qty += q_in
                value += q_in * cost
            if q_out:
                avg = value / qty if qty else Decimal("0")
                qty -= q_out
                value -= q_out * avg
        avg = (value / qty).quantize(TWO) if qty else Decimal("0")
        return qty, avg

    def stock_items(self) -> list[str]:
        seen: dict[str, str] = {}
        for r in self.rows("stock"):
            seen.setdefault(r["item"].lower(), r["item"])
        return sorted(seen.values())

    def debt_balance(self, book: str, party: str | None = None) -> dict[str, Decimal]:
        key = "customer" if book == "customer_debts" else "supplier"
        out: dict[str, Decimal] = {}
        for r in self.rows(book):
            name = r[key]
            out[name] = out.get(name, Decimal("0")) + money(r["amount"])
        out = {k: v for k, v in out.items() if v != 0}
        return {party: out.get(party, Decimal("0"))} if party else out

    # ---------- the shelf: stock already on hand + its price list ----------
    def _write_prices(self, rows: list[dict]) -> None:
        with self._path(PRICE_LIST).open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=PRICE_COLS)
            w.writeheader()
            for r in sorted(rows, key=lambda r: r["item"].lower()):
                w.writerow({k: r.get(k, "") for k in PRICE_COLS})

    def prices(self) -> dict[str, dict]:
        with self._path(PRICE_LIST).open(newline="", encoding="utf-8") as fh:
            return {r["item"].lower(): r for r in csv.DictReader(fh)}

    def canonical(self, item: str) -> str:
        """The item's name as first written on the shelf (case-insensitive match)."""
        key = item.strip().lower()
        for name in self.stock_items():
            if name.lower() == key:
                return name
        p = self.prices().get(key)
        return p["item"] if p else item.strip()

    def set_price(self, item: str, selling_price, reorder_level=None) -> None:
        item = self.canonical(item)
        rows = self.prices()
        old = rows.get(item.lower(), {})
        rows[item.lower()] = {
            "item": item, "selling_price": money(selling_price),
            "reorder_level": reorder_level if reorder_level not in (None, "")
            else old.get("reorder_level", ""),
            "updated": str(self._now())}
        self._write_prices(list(rows.values()))

    def price_of(self, item: str) -> Decimal | None:
        p = self.prices().get(item.strip().lower())
        return money(p["selling_price"]) if p and p["selling_price"] else None

    def stock_in(self, *, date, item, qty, unit_cost, selling_price=None,
                 reorder_level=None, ref="opening stock") -> dict:
        """Put stock already in the shop on the shelf (opening stock).

        [STD] Opening stock is the owner's capital already in the business: it
        moves no cash and creates no supplier debt. Stock bought from now on
        goes through record_purchase so the payment is recorded too.
        """
        date = self._check_date(date)
        qty, unit_cost = Decimal(str(qty)), money(unit_cost)
        if qty <= 0 or unit_cost < 0:
            raise BookkeepingError(f"{item}: quantity must be positive and cost not negative.")
        item = self.canonical(item)
        row = self._append("stock", {"date": date, "item": item, "qty_in": qty,
                                     "unit_cost": unit_cost, "kind": "opening",
                                     "ref": ref})
        if selling_price not in (None, ""):
            self.set_price(item, selling_price, reorder_level)
        return row

    def load_stock_list(self, path, date=None) -> int:
        """Load a CSV with columns item, qty, unit_cost, selling_price[, reorder_level]."""
        date = date or self._now()
        with open(path, newline="", encoding="utf-8-sig") as fh:
            rows = list(csv.DictReader(fh))
        need = {"item", "qty", "unit_cost", "selling_price"}
        if not rows or not need <= {c.strip().lower() for c in rows[0]}:
            raise BookkeepingError(f"Stock list needs columns: {', '.join(sorted(need))}"
                                   " (reorder_level optional).")
        clean = [{k.strip().lower(): (v or "").strip() for k, v in r.items()} for r in rows]
        for r in clean:  # validate every line before writing any
            if not r["item"]:
                raise BookkeepingError("A row in the stock list has no item name.")
            money(r["unit_cost"])
            money(r["selling_price"])
            try:
                if Decimal(r["qty"]) <= 0:
                    raise InvalidOperation
            except InvalidOperation:
                raise BookkeepingError(f"{r['item']}: quantity {r['qty']!r} is not a positive number.")
        for r in clean:
            self.stock_in(date=date, item=r["item"], qty=r["qty"],
                          unit_cost=r["unit_cost"], selling_price=r["selling_price"],
                          reorder_level=r.get("reorder_level"))
        return len(clean)

    def find_items(self, query: str) -> list[str]:
        """Search the shelf: every word of the query must appear in the item name."""
        words = query.lower().split()
        names = {n.lower(): n for n in self.stock_items()}
        for k, p in self.prices().items():
            names.setdefault(k, p["item"])
        return sorted(n for k, n in names.items() if all(w in k for w in words))

    def shelf(self, query: str = "") -> list[dict]:
        out = []
        for item in (self.find_items(query) if query else
                     sorted(set(self.stock_items()) |
                            {p["item"] for p in self.prices().values()}, key=str.lower)):
            qty, avg = self.stock_on_hand(item)
            p = self.prices().get(item.lower(), {})
            sell = money(p["selling_price"]) if p.get("selling_price") else None
            reorder = Decimal(p["reorder_level"]) if p.get("reorder_level") else None
            out.append({"item": item, "qty": qty, "unit_cost": avg,
                        "selling_price": sell, "stock_value": (qty * avg).quantize(TWO),
                        "margin_per_unit": (sell - avg) if sell is not None else None,
                        "reorder_level": reorder,
                        "low": reorder is not None and qty <= reorder})
        return out

    # ---------- stage 3: posting ----------
    def record_sale(self, *, date, customer, item, qty, paid_via,
                    unit_price=None, evidence="") -> dict:
        """Sell from the shelf. Without unit_price the listed selling price is used."""
        date = self._check_date(date)
        if paid_via not in PAY_METHODS:
            raise BookkeepingError(f"paid_via must be one of {PAY_METHODS}")
        item = self.canonical(item)
        if unit_price in (None, ""):
            unit_price = self.price_of(item)
            if unit_price is None:
                raise BookkeepingError(f"No selling price listed for {item}; give one.")
        qty, unit_price = Decimal(str(qty)), money(unit_price)
        if qty <= 0 or unit_price < 0:
            raise BookkeepingError("Quantity must be positive and price not negative.")
        # [SRC] "Always record credit sales, even when no money has been
        # received" -- a credit sale needs a named customer so the debt can be
        # chased.
        if paid_via == "credit" and not customer.strip():
            raise BookkeepingError("A credit sale needs the customer's name.")
        on_hand, avg_cost = self.stock_on_hand(item)
        if on_hand < qty:
            raise BookkeepingError(
                f"Stock book shows {on_hand} x {item}; cannot sell {qty}. "
                f"Record the purchase in the stock book first.")
        total = (qty * unit_price).quantize(TWO)
        cogs = (qty * avg_cost).quantize(TWO)
        sale = self._append("sales", {
            "date": date, "customer": customer or "walk-in", "item": item,
            "qty": qty, "unit_price": unit_price, "total": total,
            "paid_via": paid_via, "cost_of_goods": cogs, "evidence": evidence})
        self._append("stock", {"date": date, "item": item, "qty_out": qty,
                               "unit_cost": avg_cost, "kind": "sale",
                               "ref": sale["id"]})
        if paid_via == "credit":
            self._append("customer_debts", {
                "date": date, "customer": customer, "amount": total,
                "kind": "credit sale", "ref": sale["id"], "evidence": evidence})
        else:
            self._cash_move(date, paid_via, total, None,
                            f"Sale {item} to {customer or 'walk-in'}", sale["id"])
        return sale

    def receive_customer_payment(self, *, date, customer, amount, account,
                                 evidence="") -> dict:
        date, amount = self._check_date(date), money(amount)
        owed = self.debt_balance("customer_debts", customer)[customer]
        if amount <= 0 or amount > owed:
            raise BookkeepingError(f"{customer} owes {fmt(owed)}; cannot receive {fmt(amount)}.")
        row = self._append("customer_debts", {
            "date": date, "customer": customer, "amount": -amount,
            "kind": "payment", "ref": account, "evidence": evidence})
        self._cash_move(date, account, amount, None, f"Payment from {customer}", row["id"])
        return row

    def record_purchase(self, *, date, supplier, item, qty, unit_cost, paid_via,
                        evidence="", selling_price=None) -> dict:
        """Buying stock for resale goes to the stock book, not expenses."""
        date = self._check_date(date)
        item = self.canonical(item)
        qty, unit_cost = Decimal(str(qty)), money(unit_cost)
        if qty <= 0 or unit_cost < 0:
            raise BookkeepingError("Quantity must be positive and cost not negative.")
        if paid_via not in PAY_METHODS:
            raise BookkeepingError(f"paid_via must be one of {PAY_METHODS}")
        if paid_via == "credit" and not supplier.strip():
            raise BookkeepingError("A credit purchase needs the supplier's name.")
        total = (qty * unit_cost).quantize(TWO)
        if paid_via != "credit":
            self._cash_move(date, paid_via, None, total,
                            f"Stock {item} from {supplier}", f"purchase {item}")
        row = self._append("stock", {"date": date, "item": item, "qty_in": qty,
                                     "unit_cost": unit_cost, "kind": "purchase",
                                     "ref": supplier})
        if paid_via == "credit":
            self._append("supplier_debts", {
                "date": date, "supplier": supplier, "amount": total,
                "kind": "credit purchase", "ref": row["id"], "evidence": evidence})
        if selling_price not in (None, ""):
            self.set_price(item, selling_price)
        return row

    def pay_supplier(self, *, date, supplier, amount, account, evidence="") -> dict:
        date, amount = self._check_date(date), money(amount)
        owed = self.debt_balance("supplier_debts", supplier)[supplier]
        if amount <= 0 or amount > owed:
            raise BookkeepingError(f"You owe {supplier} {fmt(owed)}; cannot pay {fmt(amount)}.")
        self._cash_move(date, account, None, amount, f"Payment to {supplier}", "supplier")
        return self._append("supplier_debts", {
            "date": date, "supplier": supplier, "amount": -amount,
            "kind": "payment", "ref": account, "evidence": evidence})

    def record_expense(self, *, date, category, description, amount, paid_via,
                       business: bool, supplier="", evidence="") -> dict:
        date, amount = self._check_date(date), money(amount)
        if amount <= 0:
            raise BookkeepingError("Amount must be positive.")
        # [SRC] "Keep personal expenses separate from business expenses."
        if not business:
            if paid_via == "credit":
                raise BookkeepingError("Personal spending on business credit is not recorded here.")
            self._cash_move(date, paid_via, None, amount, f"Drawings: {description}", "drawings")
            return self._append("drawings", {
                "date": date, "description": description, "amount": amount,
                "paid_via": paid_via, "evidence": evidence})
        if paid_via not in PAY_METHODS:
            raise BookkeepingError(f"paid_via must be one of {PAY_METHODS}")
        if paid_via == "credit" and not supplier.strip():
            raise BookkeepingError("An expense on credit needs the supplier's name.")
        row = self._append("expenses", {
            "date": date, "category": category, "description": description,
            "amount": amount, "paid_via": paid_via, "supplier": supplier,
            "evidence": evidence})
        if paid_via == "credit":
            self._append("supplier_debts", {
                "date": date, "supplier": supplier, "amount": amount,
                "kind": "credit expense", "ref": row["id"], "evidence": evidence})
        else:
            self._cash_move(date, paid_via, None, amount, description, row["id"])
        return row

    def transfer(self, *, date, from_account, to_account, amount, ref="") -> None:
        """Cash banked or withdrawn: moves money, is neither income nor expense."""
        date, amount = self._check_date(date), money(amount)
        self._cash_move(date, from_account, None, amount, f"Transfer to {to_account}", ref)
        self._cash_move(date, to_account, amount, None, f"Transfer from {from_account}", ref)

    def opening_balance(self, *, date, account, amount) -> None:
        self._cash_move(self._check_date(date), account, money(amount), None,
                        "Opening balance", "opening")
