# Five-stage bookkeeping (small Nigerian business, ₦)

Turns the bookkeeping guidance from a ChatGPT conversation (excerpt pasted 12 Nov 2026)
into a prompt-driven tool. It asks you questions, posts each entry into the right books,
and tells you **which bookkeeping forms are due now**.

```bash
cd projects/2026-11-bookkeeping
python3 -m bookkeeping stock-in --file stock_list_template.csv   # put what's on the shelf in once
python3 -m bookkeeping shelf            # stock, cost, selling price, margin, value
python3 -m bookkeeping shelf milk       # search the shelf
python3 -m bookkeeping price "Rice 50kg" 87000 --reorder 3   # change a price / reorder level
python3 -m bookkeeping stages      # the 5 stages and the rule each one enforces
python3 -m bookkeeping record      # asks: what happened? then walks stages 1-3
python3 -m bookkeeping status      # what is due now, grouped by stage
python3 -m bookkeeping reconcile   # stage 4: cash count, bank statement, stock count
python3 -m bookkeeping report      # stage 5: Sales - COGS - Operating expenses = Profit
python3 -m bookkeeping export      # every book + "Due now" into one Excel workbook
python3 -m bookkeeping --data demo sample   # try it on sample entries first
python3 -m unittest discover -s tests       # 20 tests
```

Books are CSV files in `./books/` (open them in Excel). `books/` is git-ignored: real
financial records stay on your machine.

## Stock already on the shelf

Copy `stock_list_template.csv`, replace the sample rows with your own stock, and load it once:

| item | qty | unit_cost | selling_price | reorder_level |
| --- | --- | --- | --- | --- |
| Rice 50kg | 10 | 72000 | 85000 | 3 |

This is **opening stock**: goods already in the shop. It moves no cash and creates no supplier
debt. After that, every sale works from the shelf:

1. `record sale`, then search by part of the name (`ind`, `milk`). Add as many items as the
   customer buys. Leave the search blank to finish.
2. The listed selling price is filled in for you. Type a different price for a negotiated
   sale and the tool shows the difference against the list.
3. You can't sell more than is on the shelf.
4. On posting, each item is deducted from the stock book and gets its own sales book line,
   with its cost of goods. Payment goes to cash or bank, or for a credit sale, to the
   customer debt book. You get the gross profit on that sale, and any item that hits its
   reorder level is flagged.

New stock from a supplier goes through `record purchase`, which adds to the shelf,
records the payment or supplier debt, and can update the selling price.

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
- Opening stock is treated as owner's capital (no cash, no supplier debt).
- Shelf stock is costed in date order, so a back-dated purchase or sale lands where it
  happened. Limitation: a sale's cost of goods is fixed when it is posted. A purchase
  back-dated to *before* that sale doesn't re-cost it, so record purchases on the day
  (rule 1 of the conversation).
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
