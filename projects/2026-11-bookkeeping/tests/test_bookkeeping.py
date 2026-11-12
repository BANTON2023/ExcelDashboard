import datetime as dt
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bookkeeping import Ledger, BookkeepingError, status, reconcile, profit_report  # noqa: E402

TODAY = dt.date(2026, 11, 12)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.l = Ledger(Path(self.tmp.name), today=TODAY)
        self.l.opening_balance(date=TODAY, account="cash", amount=10000)
        self.l.record_purchase(date=TODAY, supplier="Ade", item="Rice", qty=10,
                               unit_cost=1000, paid_via="credit", evidence="INV1")

    def tearDown(self):
        self.tmp.cleanup()


class Rules(Base):
    def test_credit_sale_recorded_without_money(self):
        # [SRC] always record credit sales, even when no money is received
        self.l.record_sale(date=TODAY, customer="Chidi", item="Rice", qty=2,
                           unit_price=1500, paid_via="credit", evidence="S1")
        self.assertEqual(self.l.debt_balance("customer_debts"), {"Chidi": Decimal("3000.00")})
        self.assertEqual(self.l.balance("cash"), Decimal("10000.00"))

    def test_credit_sale_needs_customer(self):
        with self.assertRaises(BookkeepingError):
            self.l.record_sale(date=TODAY, customer="", item="Rice", qty=1,
                               unit_price=1500, paid_via="credit")

    def test_personal_expense_goes_to_drawings_not_expenses(self):
        # [SRC] keep personal expenses separate
        self.l.record_expense(date=TODAY, category="", description="school fees",
                              amount=2000, paid_via="cash", business=False, evidence="r")
        self.assertEqual(self.l.rows("expenses"), [])
        self.assertEqual(len(self.l.rows("drawings")), 1)
        rep = profit_report(self.l, TODAY, TODAY)
        self.assertEqual(rep["opex"], 0)
        self.assertEqual(rep["owner_drawings"], Decimal("2000.00"))

    def test_sales_is_not_profit(self):
        # [SRC] Sales - COGS - Operating expenses = Profit
        self.l.record_sale(date=TODAY, customer="", item="Rice", qty=4,
                           unit_price=1500, paid_via="cash", evidence="S")
        self.l.record_expense(date=TODAY, category="Transport", description="bike",
                              amount=500, paid_via="cash", business=True, evidence="r")
        rep = profit_report(self.l, TODAY, TODAY)
        self.assertEqual(rep["sales"], Decimal("6000.00"))
        self.assertEqual(rep["cogs"], Decimal("4000.00"))
        self.assertEqual(rep["profit"], Decimal("1500.00"))

    def test_cannot_sell_unrecorded_stock(self):
        with self.assertRaises(BookkeepingError):
            self.l.record_sale(date=TODAY, customer="", item="Beans", qty=1,
                               unit_price=100, paid_via="cash")

    def test_cash_book_cannot_go_negative(self):
        with self.assertRaises(BookkeepingError):
            self.l.record_expense(date=TODAY, category="Rent", description="rent",
                                  amount=999999, paid_via="cash", business=True)

    def test_weighted_average_cost(self):
        self.l.record_purchase(date=TODAY, supplier="Ade", item="Rice", qty=10,
                               unit_cost=2000, paid_via="credit")
        self.assertEqual(self.l.stock_on_hand("Rice"), (Decimal("20"), Decimal("1500.00")))

    def test_customer_payment_reduces_debt(self):
        self.l.record_sale(date=TODAY, customer="Chidi", item="Rice", qty=2,
                           unit_price=1500, paid_via="credit")
        self.l.receive_customer_payment(date=TODAY, customer="Chidi", amount=1000, account="bank")
        self.assertEqual(self.l.debt_balance("customer_debts")["Chidi"], Decimal("2000.00"))
        self.assertEqual(self.l.balance("bank"), Decimal("1000.00"))
        with self.assertRaises(BookkeepingError):
            self.l.receive_customer_payment(date=TODAY, customer="Chidi", amount=5000, account="bank")


class Stages(Base):
    def test_status_lists_reconciliation_and_debts(self):
        msgs = [(t.stage, t.message) for t in status(self.l).tasks]
        self.assertTrue(any(s == 4 and "Reconcile cash" in m for s, m in msgs))
        self.assertTrue(any(s == 4 and "Count Rice" in m for s, m in msgs))
        self.assertTrue(any(s == 3 and "You owe Ade" in m for s, m in msgs))

    def test_missing_evidence_flagged(self):
        self.l.record_expense(date=TODAY, category="Fuel", description="gen",
                              amount=100, paid_via="cash", business=True)
        self.assertTrue(any("no receipt" in t.message for t in status(self.l).tasks))

    def test_reconcile_difference_then_adjust(self):
        r = reconcile(self.l, date=TODAY, target="cash", actual=9500)
        self.assertEqual(Decimal(r["difference"]), Decimal("-500.00"))
        self.assertTrue(any("off by" in t.message for t in status(self.l).tasks))
        reconcile(self.l, date=TODAY, target="cash", actual=9500, note="unrecorded fuel", adjust=True)
        self.assertEqual(self.l.balance("cash"), Decimal("9500.00"))
        due = [t.message for t in status(self.l).tasks if t.stage == 4]
        self.assertFalse(any("Reconcile cash" in m for m in due))

    def test_stock_count_adjustment(self):
        reconcile(self.l, date=TODAY, target="stock:Rice", actual=9, note="damaged", adjust=True)
        self.assertEqual(self.l.stock_on_hand("Rice")[0], Decimal("9"))
        self.assertEqual(profit_report(self.l, TODAY, TODAY)["opex"], Decimal("1000.00"))

    def test_month_end_report_due_early_in_month(self):
        l = Ledger(Path(self.tmp.name) / "b", today=dt.date(2026, 11, 3))
        l.opening_balance(date="2026-10-20", account="cash", amount=100)
        l.record_expense(date="2026-10-21", category="Data", description="data",
                         amount=50, paid_via="cash", business=True, evidence="x")
        self.assertTrue(any(t.stage == 5 for t in status(l).tasks))


if __name__ == "__main__":
    unittest.main()
