# Build mode: dashboards, spreadsheets, data models

Order of questions (cheapest mistakes to catch first):

1. **Is it the right metric?** What decision does it support? Would a rate, average,
   median, percentile or distribution answer it better than a total? Example for
   logistics: "total deliveries" vs on-time-in-full % vs median lead time vs cost per
   drop.
2. **Is the total correct?** Grain of the data (one row = one shipment? one line
   item?), double counting after joins, blanks/zeros, duplicates, units and currencies,
   time zones, filters and slicers changing what is summed, grand totals of averages
   (an average of averages is usually wrong).
3. **Which way to build it?** Lay out the options side by side:

| Option | Good for | Watch out for |
| --- | --- | --- |
| `SUM` / `SUMIFS` / `COUNTIFS` | simple, transparent, fast to audit | criteria multiply; brittle ranges (use Tables) |
| `SUMPRODUCT` | multi-condition logic, weights | slow on big ranges; hard to read |
| `SUBTOTAL` / `AGGREGATE` | totals that respect filters / skip errors | doesn't respond to slicers on PivotTables |
| Dynamic arrays (`FILTER`, `UNIQUE`, `SORT`, `GROUPBY`, `PIVOTBY`) | spill-based summaries without pivots | version-dependent: check the user's Excel |
| `LET` / `LAMBDA` | readable, reusable logic | colleagues may not know them |
| PivotTable | fast exploration, drill-down | refresh needed; layout fragile for dashboards |
| Power Query | cleaning, merging CSVs, unpivoting before load | logic hidden in query steps; document them |
| Data Model + DAX measures (`SUM`, `SUMX`, `CALCULATE`, time intelligence) | many tables, relationships, filter-aware KPIs | learning curve; measure vs calculated column choice |
| Power BI / other BI tool | sharing, scheduled refresh, maps, row-level security | licensing; a second tool to maintain |

4. **Where should the logic live?** Upstream in the source / Power Query (clean once),
   in a measure (filter-aware), in a calculated column (row-level, static), or hard-coded
   (almost never; flag it).

Verify any function's availability for the user's Excel version against Microsoft's
documentation (learn.microsoft.com, support.microsoft.com) before recommending it.
Recompute a sample of any total by hand before trusting it.
