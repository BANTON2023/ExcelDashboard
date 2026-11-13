"""Compute every dashboard KPI independently of Power BI, for reconciliation.

Usage: python scripts/kpi_targets.py data/raw > projects/2026-11-logistics-dashboard/KPI-TARGETS.md
Definitions match powerbi/Measures.dax. Whole period: 2022-01-01 to 2024-12-31.
"""
import sys
import pandas as pd

d = sys.argv[1] if len(sys.argv) > 1 else "data/raw"
r = lambda n, **k: pd.read_csv(f"{d}/{n}.csv", low_memory=False, **k)

L, T = r("loads"), r("trips")
S = L.merge(T, on="load_id")                       # Shipments = loads + trips (1:1)
S["total_revenue"] = S.revenue + S.fuel_surcharge + S.accessorial_charges
E = r("delivery_events", parse_dates=["scheduled_datetime", "actual_datetime"])
E["late_minutes"] = (E.actual_datetime - E.scheduled_datetime).dt.total_seconds() / 60
F, M, I, TK = r("fuel_purchases"), r("maintenance_records"), r("safety_incidents"), r("trucks")

miles = S.actual_distance_miles.sum()
rev = S.total_revenue.sum()
burned = S.fuel_gallons_used.sum()
spend, bought = F.total_cost.sum(), F.gallons.sum()
price = spend / bought
est_fuel = burned * price
dlv, pck = E[E.event_type == "Delivery"], E[E.event_type == "Pickup"]
cust_rev = S.groupby("customer_id").total_revenue.sum().sort_values(ascending=False)
trucks_used = S.truck_id.nunique()
drivers_used = S.driver_id.nunique()

rows = [
    ("Customer", "Total Revenue (line-haul + fuel surcharge + accessorials)", f"${rev:,.0f}"),
    ("Customer", "Loads", f"{len(S):,}"),
    ("Customer", "Revenue per Mile", f"${rev/miles:,.3f}"),
    ("Customer", "Top-10 Customer Revenue Share", f"{cust_rev.head(10).sum()/rev:.1%}"),
    ("Customer", "Revenue after Fuel per Mile", f"${(rev-est_fuel)/miles:,.3f}"),
    ("Customer", "(support) Revenue after Est. Fuel", f"${rev-est_fuel:,.0f}"),
    ("Service", "Delivery On-Time % (±120 min, from flag)", f"{dlv.on_time_flag.mean():.1%}"),
    ("Service", "Pickup On-Time %", f"{pck.on_time_flag.mean():.1%}"),
    ("Service", "Avg Detention per Stop (min)", f"{E.detention_minutes.mean():.1f}"),
    ("Service", "Late Deliveries (>120 min late)", f"{(dlv.late_minutes > 120).sum():,}"),
    ("Service", "Late Delivery Rate", f"{(dlv.late_minutes > 120).mean():.1%}"),
    ("Service", "(alt) Delivery Not-Late %", f"{(dlv.late_minutes <= 0).mean():.1%}"),
    ("Fleet", "Maintenance Cost", f"${M.total_cost.sum():,.0f}"),
    ("Fleet", "Maintenance Cost per Mile", f"${M.total_cost.sum()/miles:,.4f}"),
    ("Fleet", "Downtime Hours", f"{M.downtime_hours.sum():,.1f}"),
    ("Fleet", "Maintenance on Idle Trucks", f"${M[~M.truck_id.isin(set(S.truck_id.dropna()))].total_cost.sum():,.0f}"),
    ("Fleet", "Trucks Used / Fleet", f"{trucks_used} / {len(TK)} = {trucks_used/len(TK):.1%}"),
    ("Driver", "Active Drivers", f"{drivers_used}"),
    ("Driver", "Fleet MPG (miles ÷ gallons, weighted)", f"{miles/burned:.3f}"),
    ("Driver", "(alt) Average of trip MPG (unweighted)", f"{S.average_mpg.mean():.3f}"),
    ("Driver", "Idle % of Trip Hours", f"{S.idle_time_hours.sum()/S.actual_duration_hours.sum():.1%}"),
    ("Driver", "Incidents per Million Miles", f"{len(I)/miles*1e6:.3f}"),
    ("Driver", "(support) Preventable Incidents", f"{int(I.preventable_flag.sum())}"),
    ("Fuel", "Fuel Spend (purchases)", f"${spend:,.0f}"),
    ("Fuel", "Avg Price per Gallon (weighted)", f"${price:.3f}"),
    ("Fuel", "Fuel Cost per Mile (purchases)", f"${spend/miles:.4f}"),
    ("Fuel", "Purchase Gap % (bought vs burned)", f"{(bought-burned)/burned:.1%}"),
    ("Fuel", "(alt) Fuel Cost per Mile (burned × price)", f"${est_fuel/miles:.4f}"),
]
print("# KPI targets: whole period, no slicers\n")
print("Computed with pandas from the raw CSVs (`scripts/kpi_targets.py`). With no filters")
print("applied, each Power BI card should show these values. If one doesn't, the measure or")
print("a relationship is wrong.\n")
print("| Page | KPI | Value |\n| --- | --- | ---: |")
for p, k, v in rows:
    print(f"| {p} | {k} | {v} |")
print("\nFuel totals include purchases on 1–2 Jan 2025 ($0.09M); the Date table runs to 31 Jan 2025 to keep them.")
print(f"\nSupporting totals: miles {miles:,.0f}; gallons burned {burned:,.0f}; "
      f"gallons bought {bought:,.0f}; incidents {len(I)}.")
