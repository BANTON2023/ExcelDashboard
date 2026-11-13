"""Re-run the key integrity checks on the logistics CSVs.

Usage: python scripts/profile_data.py path/to/csv_folder
"""
import sys
import pandas as pd

d = sys.argv[1] if len(sys.argv) > 1 else "data/raw"
r = lambda n, **k: pd.read_csv(f"{d}/{n}.csv", low_memory=False, **k)

L, T = r("loads"), r("trips")
E = r("delivery_events", parse_dates=["scheduled_datetime", "actual_datetime"])
F, DM = r("fuel_purchases"), r("driver_monthly_metrics")

print("Loads:trips 1:1 ->", T.load_id.is_unique and set(T.load_id) == set(L.load_id))
print(f"Revenue  line-haul ${L.revenue.sum()/1e6:.1f}M | "
      f"incl. surcharge+accessorials ${(L.revenue+L.fuel_surcharge+L.accessorial_charges).sum()/1e6:.1f}M | "
      f"driver-monthly table ${DM.total_revenue.sum()/1e6:.1f}M")
E["late_min"] = (E.actual_datetime - E.scheduled_datetime).dt.total_seconds() / 60
for et, g in E.groupby("event_type"):
    print(f"{et}: on_time_flag {g.on_time_flag.mean():.1%} | within ±120 min "
          f"{g.late_min.between(-120, 120).mean():.1%} | not late {(g.late_min <= 0).mean():.1%}")
print(f"Fuel burned {T.fuel_gallons_used.sum()/1e6:.2f}M gal | purchased {F.gallons.sum()/1e6:.2f}M gal")
print("Trips missing driver or truck:", int((T.driver_id.isna() | T.truck_id.isna()).sum()))
