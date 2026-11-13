# Logistics dashboard: data profile

Source: 14 CSV files from the shared Google Drive folder, downloaded 13 Nov 2026. The
raw data is **not** stored in this repo (see `.gitignore`). Every figure below was
computed with pandas on the full files.

## What's in the data

US truckload carrier, **1 Jan 2022 – 31 Dec 2024** (36 months).

| File | Rows | One row = | Key |
| --- | ---: | --- | --- |
| loads | 85,410 | a customer shipment (revenue, weight, type) | load_id |
| trips | 85,410 | the truck trip carrying it (miles, hours, fuel, MPG, idle) | trip_id; **exactly 1 trip per load** |
| delivery_events | 170,820 | a pickup or a delivery (scheduled vs actual, detention) | 2 per load |
| fuel_purchases | 196,442 | a fuel-card transaction | trip_id, truck_id, driver_id |
| maintenance_records | 2,920 | a service event | truck_id |
| safety_incidents | 170 | an incident with claim cost | trip_id |
| driver_monthly_metrics | 4,464 | driver × month (pre-aggregated) | driver_id + month |
| truck_utilization_metrics | 3,312 | truck × month (pre-aggregated) | truck_id + month |
| customers / drivers / trucks / trailers / routes / facilities | 200 / 150 / 120 / 180 / 58 / 50 | lookup tables | *_id |

Star schema: **loads ⇄ trips** form the fact core. Customers and routes hang off loads.
Drivers, trucks and trailers hang off trips. Events, fuel and incidents hang off trips
or loads. Maintenance hangs off trucks.

## What checks out ✅
- No duplicate rows; every ID column is unique where it should be.
- Loads ↔ trips are a clean 1:1, and load date = dispatch date.
- `trips.average_mpg` = miles ÷ gallons (within 0.004).
- `fuel_purchases.total_cost` = gallons × price; maintenance total = labour + parts;
  claim = vehicle + cargo damage.
- `fuel_surcharge` = route typical miles × route surcharge rate, exactly.
- The two monthly tables reconcile **exactly** to trips/loads for the trips they cover.
- No trips by drivers after their termination date; no trips on inactive trucks.

## What will break a dashboard if ignored ⚠️

1. **"Revenue" has three different totals.** You must pick one definition.
   - Line-haul `revenue` only: **$262.5M**
   - Line-haul + fuel surcharge + accessorials: **$298.6M**
   - Monthly driver/truck tables: **$257.3M**. These exclude the trips that have no
     driver (1,714) or no truck (1,672) assigned.
2. **On-time has a hidden rule.** `on_time_flag` = actual time within **±120 minutes**
   of scheduled. Delivering more than 2 h *early* counts as **not** on time. With that
   rule, delivery on-time is **44.6%** and pickup is **66.7%**. A strict "not late"
   rule gives about 33%. The dashboard must state which rule it uses.
3. **Fuel purchases don't match fuel burned.** Trips burned **18.9M gal**, but fuel
   cards bought **24.5M gal** (+29%). 8,471 trips have no purchase at all. Per trip,
   bought ÷ burned ranges from 0.3× to 9×. Cost per mile changes depending on which
   source you use. Recommendation: use trip consumption for efficiency, and purchases
   for spend.
4. **Event locations are unreliable.** The pickup facility's city matches the route's
   origin city only **3.4%** of the time. That is about the rate you'd get by chance.
   Don't build maps from facilities or events; use routes for geography.
5. **~2% of trips have no driver, truck or trailer** (3,349 trips, $10.3M revenue). They
   disappear from any per-driver or per-truck view. Show them as "Unassigned".
6. **Customer status is a snapshot, not history.** 13,809 loads belong to customers now
   marked Inactive. Customer names aren't unique (107 names for 200 IDs; "First Group"
   = 7 IDs). Always group by ID.
7. **Two "type" fields disagree.** `loads.booking_type` ≠ `customers.customer_type` on
   67% of loads. Pick one for "Spot vs Contract vs Dedicated".
8. **`utilization_rate` exceeds 100%** in 13% of truck-months, and its formula is
   undocumented. Don't use it until it's defined, or recompute it from hours.
9. **Detention is almost universal:** more than 0 minutes at 85–89% of stops, averaging
   about 92 minutes.

## The data looks synthetic
Sequential IDs, near-perfectly uniform lateness bands, flat volume in 2022–2024 (about
28.5k loads and $87–88M per year), and random event locations all suggest generated
practice data rather than a real carrier's records. *[Judgment]* That's fine for
learning. But don't present "findings" from it as real business insight, and expect
weak trends.

## Reproduce
`scripts/profile_data.py <folder-with-csvs>` reruns the key checks.
