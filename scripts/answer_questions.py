"""Answer each dashboard question from the raw CSVs (whole period 2022-2024).

Usage: python scripts/answer_questions.py data/raw
Definitions match powerbi/Measures.dax.
"""
import sys
import pandas as pd

d = sys.argv[1] if len(sys.argv) > 1 else "data/raw"
r = lambda n, **k: pd.read_csv(f"{d}/{n}.csv", low_memory=False, **k)
S = r("loads").merge(r("trips"), on="load_id")
S["rev"] = S.revenue + S.fuel_surcharge + S.accessorial_charges
S["year"] = pd.to_datetime(S.dispatch_date).dt.year
C, R, TK, D, FA = r("customers"), r("routes"), r("trucks"), r("drivers"), r("facilities")
E = r("delivery_events", parse_dates=["scheduled_datetime", "actual_datetime"])
E["late"] = (E.actual_datetime - E.scheduled_datetime).dt.total_seconds() / 60
F = r("fuel_purchases", parse_dates=["purchase_date"]); F["year"] = F.purchase_date.dt.year
M = r("maintenance_records", parse_dates=["maintenance_date"]); M["year"] = M.maintenance_date.dt.year
I = r("safety_incidents")
price = F.total_cost.sum() / F.gallons.sum()
dl = E[E.event_type == "Delivery"].merge(S[["load_id", "customer_id", "route_id", "driver_id"]], on="load_id")

def h(t): print(f"\n### {t}")

h("CUSTOMER")
c = S.groupby("customer_id").agg(loads=("load_id", "size"), rev=("rev", "sum"), mi=("actual_distance_miles", "sum"))
c["rpm"] = c.rev / c.mi
print("C1 rev/mile across customers: min %.3f median %.3f max %.3f; loads min %d max %d"
      % (c.rpm.min(), c.rpm.median(), c.rpm.max(), c.loads.min(), c.loads.max()))
print("   corr(loads, rev/mile) = %.2f" % c.loads.corr(c.rpm))
y = S.groupby("year").agg(rev=("rev", "sum"), mi=("actual_distance_miles", "sum")); y["rpm"] = y.rev / y.mi
print("C2 by year:", {k: (round(v.rev / 1e6, 2), round(v.rpm, 3)) for k, v in y.iterrows()})
l = S.merge(R, on="route_id").groupby(["origin_city", "destination_city"]).agg(
    loads=("load_id", "size"), rev=("rev", "sum"), mi=("actual_distance_miles", "sum"), gal=("fuel_gallons_used", "sum"))
l["after_fuel_pm"] = (l.rev - l.gal * price) / l.mi
ot = dl.merge(R, on="route_id").groupby(["origin_city", "destination_city"]).on_time_flag.mean()
l = l.join(ot.rename("ontime"))
print("C3 best lanes (after-fuel $/mile):"); print(l.sort_values("after_fuel_pm", ascending=False).head(3).round(3).to_string())
print("   worst lanes:"); print(l.sort_values("after_fuel_pm").head(3).round(3).to_string())
b = S.groupby(["booking_type", "load_type"]).agg(rev=("rev", "sum"), loads=("load_id", "size")); b["per_load"] = b.rev / b.loads
print("C4 revenue per load:"); print(b.round(0).to_string())

h("FUEL")
fy = F.groupby("year").agg(spend=("total_cost", "sum"), gal=("gallons", "sum")); fy["price"] = fy.spend / fy.gal
print("U1 by year:", {k: (round(v.spend / 1e6, 2), round(v.gal / 1e6, 2), round(v.price, 3)) for k, v in fy.iterrows()})
bt = F.groupby("truck_id").gallons.sum(); bu = S.groupby("truck_id").fuel_gallons_used.sum()
g = pd.DataFrame({"bought": bt, "burned": bu}).dropna(); g["gap"] = g.bought / g.burned - 1
print("U2 truck gap: min %.1f%% median %.1f%% max %.1f%%" % (g.gap.min() * 100, g.gap.median() * 100, g.gap.max() * 100))
print("   top 3:", g.sort_values("gap", ascending=False).head(3).gap.round(3).to_dict())
lt = S.groupby("load_type").fuel_gallons_used.sum()
st = F.groupby("location_state").agg(spend=("total_cost", "sum"), gal=("gallons", "sum")); st["price"] = st.spend / st.gal
print("U3 price by state: cheapest", st.price.idxmin(), round(st.price.min(), 3), "dearest", st.price.idxmax(), round(st.price.max(), 3))
dg = pd.DataFrame({"bought": F.groupby("driver_id").gallons.sum(), "burned": S.groupby("driver_id").fuel_gallons_used.sum(),
                   "mi": S.groupby("driver_id").actual_distance_miles.sum()}).dropna()
dg["gap"] = dg.bought / dg.burned - 1; dg["mpg"] = dg.mi / dg.burned
print("U4 driver gap: min %.1f%% max %.1f%%; mpg min %.2f max %.2f; corr %.2f" % (
    dg.gap.min() * 100, dg.gap.max() * 100, dg.mpg.min(), dg.mpg.max(), dg.gap.corr(dg.mpg)))

h("FLEET")
used = set(S.truck_id.dropna())
tm = pd.DataFrame({"cost": M.groupby("truck_id").total_cost.sum(), "down": M.groupby("truck_id").downtime_hours.sum(),
                   "mi": S.groupby("truck_id").actual_distance_miles.sum()}).join(TK.set_index("truck_id")[["make", "model_year", "status"]])
tr = tm.dropna(subset=["mi"]); tr = tr.assign(cpm=tr.cost / tr.mi)
print("F1 maint $/mile for running trucks: min %.4f median %.4f max %.4f" % (tr.cpm.min(), tr.cpm.median(), tr.cpm.max()))
my = tr.groupby("model_year").agg(cost=("cost", "sum"), mi=("mi", "sum"), n=("cost", "size")); my["cpm"] = my.cost / my.mi
print("F2 by model year:", {k: (int(v.n), round(v.cpm, 4)) for k, v in my.iterrows()})
mt = M.pivot_table(index="year", columns="maintenance_type", values="total_cost", aggfunc="sum")
print("F3 share by type (whole period):", (M.groupby("maintenance_type").total_cost.sum() / M.total_cost.sum()).round(3).to_dict())
idle = tm[~tm.index.isin(used)]
print("F4 idle trucks:", len(idle), "cost $%.0f" % idle.cost.sum(), "| worst running truck:", tr.cpm.idxmax(), round(tr.cpm.max(), 4))

h("DRIVER")
dd = S.groupby("driver_id").agg(mi=("actual_distance_miles", "sum"), gal=("fuel_gallons_used", "sum"),
                                 idle=("idle_time_hours", "sum"), dur=("actual_duration_hours", "sum"))
dd["mpg"] = dd.mi / dd.gal; dd["idle_pct"] = dd.idle / dd.dur
print("D1 idle%%: min %.1f%% max %.1f%%; mpg %.2f–%.2f; corr %.2f" % (dd.idle_pct.min() * 100, dd.idle_pct.max() * 100, dd.mpg.min(), dd.mpg.max(), dd.idle_pct.corr(dd.mpg)))
dd = dd.join(dl.groupby("driver_id").on_time_flag.mean().rename("ontime"))
inc = I.merge(S[["trip_id", "driver_id"]], on="trip_id", suffixes=("_i", "")).groupby("driver_id").size()
dd["inc"] = inc; dd.inc = dd.inc.fillna(0); dd["inc_pmm"] = dd.inc / dd.mi * 1e6
print("D2 on-time by driver: %.1f%%–%.1f%%; drivers with 0 incidents: %d of %d; max incidents %d"
      % (dd.ontime.min() * 100, dd.ontime.max() * 100, (dd.inc == 0).sum(), len(dd), dd.inc.max()))
print("D3 incidents by type:", I.groupby("incident_type").agg(n=("incident_id", "size"), prev=("preventable_flag", "mean"), claim=("claim_amount", "sum")).round(2).to_dict("index"))
dx = dd.join(D.set_index("driver_id").years_experience)
dx["band"] = pd.cut(dx.years_experience, [0, 5, 10, 15, 20, 25], labels=["≤5", "6–10", "11–15", "16–20", "21–25"])
eb = dx.groupby("band", observed=True).agg(mi=("mi", "sum"), inc=("inc", "sum"), gal=("gal", "sum"), n=("mi", "size"))
eb["inc_pmm"] = eb.inc / eb.mi * 1e6; eb["mpg"] = eb.mi / eb.gal
print("D4 by experience:", eb[["n", "inc_pmm", "mpg"]].round(2).to_dict("index"))

h("SERVICE")
e = E.merge(S[["load_id", "year"]], on="load_id")
print("S1 delivery on-time by year:", e[e.event_type == "Delivery"].groupby("year").on_time_flag.mean().round(3).to_dict())
band = pd.cut(e.late, [-1e9, -120, 120, 240, 1e9], labels=["Early >2h", "On time ±2h", "Late 2–4h", "Late >4h"])
print("S2 delivery bands:", e[e.event_type == "Delivery"].groupby(band[e.event_type == "Delivery"], observed=True).size().to_dict())
fd = dl.merge(FA, on="facility_id").groupby("facility_name").agg(late=("late", lambda x: (x > 120).sum()), det=("detention_minutes", "mean"), n=("late", "size"))
fd["late_rate"] = fd.late / fd.n
print("S3 facility late rate: min %.1f%% max %.1f%%; detention %.0f–%.0f min" % (fd.late_rate.min() * 100, fd.late_rate.max() * 100, fd.det.min(), fd.det.max()))
print("   most late (count):", fd.sort_values("late", ascending=False).head(3)[["late", "n", "late_rate"]].round(3).to_dict("index"))
cs = dl.groupby("customer_id").on_time_flag.mean().rename("ot").to_frame().join(c.rev)
print("S4 customer on-time: %.1f%%–%.1f%%; corr(on-time, revenue) %.2f" % (cs.ot.min() * 100, cs.ot.max() * 100, cs.ot.corr(cs.rev)))
