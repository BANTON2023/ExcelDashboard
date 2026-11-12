# Five-stage bookkeeping (small Nigerian business, ₦)

Turns the bookkeeping guidance from a ChatGPT conversation (excerpt pasted 12 Nov 2026)
into a prompt-driven tool. It asks you questions, posts each entry into the right books,
and tells you **which bookkeeping forms are due now**.

```bash
cd projects/2026-11-bookkeeping
python3 -m bookkeeping stages      # the 5 stages and the rule each one enforces
python3 -m bookkeeping record      # asks: what happened? then walks stages 1-3
python3 -m bookkeeping status      # what is due now, grouped by stage
python3 -m bookkeeping reconcile   # stage 4: cash count, bank statement, stock count
python3 -m bookkeeping report      # stage 5: Sales - COGS - Operating expenses = Profit
python3 -m bookkeeping export      # every book + "Due now" into one Excel workbook
python3 -m bookkeeping --data demo sample   # try it on sample entries first
python3 -m unittest discover -s tests       # 13 tests
```

Books are CSV files in `./books/` (open them in Excel). `books/` is git-ignored: real
financial records stay on your machine.

## The five stages

| Stage | What you do | Forms / books touched | Rule from the conversation |
| --- | --- | --- | --- |
| 1 Capture | Record the day it happens, with evidence ref | all | Record immediately, not from memory; keep receipts and payment evidence |
| 2 Separate | Business or personal? Cash, bank or credit? | Expenses vs owner drawings | Keep personal separate from business; always record credit sales |
| 3 Post | Entry written to every book it affects | Sales, Expenses, Customer debt, Supplier debt, Stock, Cash & bank | The six minimum books |
| 4 Reconcile | Count cash, match bank statement, count stock | Cash & bank, Stock, Reconciliation log | Reconcile cash and bank regularly |
| 5 Report | Profit for the period | Profit report | Sales − COGS − Operating expenses = Profit; never confuse sales with profit |

## What is enforced, and where it came from

**From the conversation (evidence):**
- A credit sale must name the customer and raises a customer debt, with no cash recorded.
- A personal spend goes to *owner drawings*. It never reaches the expenses book or profit.
- Each entry asks for a receipt or transfer reference. Missing ones stay on `status` until filed.
- Entries dated more than 2 days before they were typed are flagged as "from memory".
- The profit report shows Sales → COGS → Gross profit → each expense → Profit. Cash received,
  credit sales and drawings are listed separately so none of them is read as profit.

**Added by Claude to fill gaps (scaffolding, not from the conversation; check before relying on it):**
- The five-stage split itself. The pasted excerpt lists rules and six books, not five named stages.
  Sections 1–3 of the conversation were not pasted. If they define the stages differently, the
  mapping above should change.
- Owner drawings book and reconciliation log (a 7th and 8th file).
- Weighted-average cost for COGS. FIFO is the other common method. Pick one and keep it.
- Cadences: cash count every 7 days, bank and stock every 30, debts overdue after 30 days,
  month-end report due in the first 10 days of the month. All are constants at the top of `bookkeeping/stages.py`.
- Refusals: selling stock the stock book doesn't have, or taking cash or bank below zero.
  Both usually mean an earlier entry is missing.
- Write-offs (cash shortage, stock loss) only after a difference has been investigated, then booked as expenses.
- Keyword hints ("school fees", "family"...) that flag a business expense as possibly personal.
  These are heuristics, not rules.

**Not covered:** VAT, withholding tax, PAYE, CAC/FIRS filing, depreciation of equipment, loans,
multi-currency. These need guidance from FIRS or an accountant, not from this tool or a chat transcript.
