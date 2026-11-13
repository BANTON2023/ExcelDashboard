# Logistics dashboard: page-by-page plan (Power BI, Windows)

5 pages × **4 KPI cards** + **4 visuals**. Every visual combines at least two measures,
or data from at least two tables. Revenue = **line-haul + fuel surcharge + accessorials**
(your choice).

Files:
- `powerbi/PowerQuery.m`: loads and cleans every CSV
- `powerbi/Measures.dax`: every measure below, plus the Date table
- `KPI-TARGETS.md`: the value each card must show with no filters (computed separately
  in Python)

## Data model (set these up in Model view)

All relationships are many-to-one and single-direction (lookup table filters fact table).

| From (many) | To (one) | Column |
| --- | --- | --- |
| Shipments | Customers | customer_id |
| Shipments | Routes | route_id |
| Shipments | Drivers | driver_id |
| Shipments | Trucks | truck_id |
| Shipments | Date | dispatch_date → Date |
| Events | Shipments | load_id |
| Events | Facilities | facility_id |
| Incidents | Shipments | trip_id |
| Fuel | Trucks | truck_id |
| Fuel | Drivers | driver_id |
| Fuel | Date | purchase_day → Date |
| Maintenance | Trucks | truck_id |
| Maintenance | Date | maintenance_date → Date |

Deliberately **not** linked: Fuel → Shipments. Linking it would create two filter paths
from Trucks and Drivers to Shipments, and Power BI would refuse or pick one silently.
Fuel is compared with trips through Trucks, Drivers and Date instead.

The two monthly summary files (driver_monthly_metrics, truck_utilization_metrics) are
**left out**. They are copies of trip data, and they drop unassigned trips.
`utilization_rate` has no definition.

Slicers on every page (Format > Sync slicers): **Year**, **Month**, **booking_type**,
**load_type**.

---

## Page 1: Customer: who makes us money?

| KPI card | Measure | Whole-period value |
| --- | --- | ---: |
| Total Revenue | `Total Revenue` | $298.6M |
| Revenue per Mile | `Revenue per Mile` | $2.445 |
| Loads | `Loads` | 85,410 |
| Revenue after Fuel | `Revenue after Fuel` | $224.8M |

| # | Visual | Fields (what's being merged) |
| --- | --- | --- |
| C1 | **Scatter: customer value map** | Details: Customers[customer_label]; X: `Loads`; Y: `Revenue per Mile`; Size: `Total Revenue`; Legend: Customers[customer_type]. *Merges 3 measures + customer table* |
| C2 | **Combo: monthly revenue & yield** | X: Date[Month]; Columns: `Line-haul Revenue` + `Surcharge & Accessorial Revenue` (stacked); Line: `Revenue per Mile` |
| C3 | **Matrix: lane profitability** | Rows: Routes[lane]; Values: `Loads`, `Total Revenue`, `Revenue after Fuel per Mile`, `Delivery On-Time %`. *Merges customer revenue + fuel + service* |
| C4 | **Stacked bar: revenue mix** | Axis: Shipments[booking_type]; Legend: Shipments[load_type]; Value: `Total Revenue`; Tooltip: `Revenue per Load` |

Challenge: `Top-10 Customer Revenue Share` is only 5.7%, so no customer dominates. A
"top customers" chart will show near-identical bars. Use C1, which shows the spread
instead.

## Page 2: Service: are we on time?

| KPI card | Measure | Value |
| --- | --- | ---: |
| Delivery On-Time % (±2h) | `Delivery On-Time %` | 44.6% |
| Pickup On-Time % | `Pickup On-Time %` | 66.7% |
| Avg Detention per Stop | `Avg Detention (min)` | 91.5 min |
| Late Deliveries (>2h) | `Late Deliveries` | 37,926 |

| # | Visual | Fields |
| --- | --- | --- |
| S1 | **Line: on-time trend** | X: Date[Month]; Lines: `Delivery On-Time %`, `Pickup On-Time %`, `Delivery Not-Late %` (shows how the definition changes the answer) |
| S2 | **Column: lateness distribution** | X: Events[lateness_band]; Y: `Stops`; Legend: Events[event_type] |
| S3 | **Bar + line: worst facilities** | Axis: Facilities[facility_name] (Top N 10 by `Late Deliveries`); Bars: `Late Deliveries`; Line: `Avg Detention (min)` |
| S4 | **Matrix: customer service scorecard** | Rows: Customers[customer_label]; Values: `Delivery On-Time %`, `Avg Minutes Late (deliveries)`, `Detention Hours`, `Total Revenue`. Conditional formatting on on-time. *Merges service + revenue* |

Put a text box on the page: "On time = within ±2 hours of the scheduled time. More than
2 hours early counts as not on time."

## Page 3: Fleet: which trucks cost too much?

| KPI card | Measure | Value |
| --- | --- | ---: |
| Maintenance Cost per Mile | `Maintenance Cost per Mile` | $0.047 |
| Downtime Hours | `Downtime Hours` | 72,231 |
| Fleet Usage | `Fleet Usage %` | 76.7% (92 of 120) |
| Maintenance on Idle Trucks | `Maintenance on Idle Trucks` | $1.40M (24.5%) |

| # | Visual | Fields |
| --- | --- | --- |
| F1 | **Scatter: truck cost vs work** | Details: Trucks[truck_label]; X: `Total Miles`; Y: `Maintenance Cost per Mile`; Size: `Downtime Hours`; Legend: Trucks[make] |
| F2 | **Column: cost by age** | X: Trucks[model_year]; Columns: `Maintenance Cost per Mile`; Line: `Revenue per Truck`. *The "replace or keep" view* |
| F3 | **Stacked column: what we spend on** | X: Date[Year]; Legend: Maintenance[maintenance_type]; Y: `Maintenance Cost` |
| F4 | **Table: worst 15 trucks** | Trucks[truck_label], Trucks[status], `Maintenance Cost`, `Downtime Hours`, `Total Miles`, `Fuel Cost per Mile`, `Incidents`. *Merges maintenance + trips + fuel + safety* |

## Page 4: Driver: who drives best?

| KPI card | Measure | Value |
| --- | --- | ---: |
| Active Drivers | `Active Drivers` | 124 |
| Fleet MPG | `Fleet MPG` | 6.45 |
| Idle % of Trip Hours | `Idle % of Trip Hours` | 28.0% |
| Incidents per Million Miles | `Incidents per Million Miles` | 1.39 |

| # | Visual | Fields |
| --- | --- | --- |
| D1 | **Scatter: efficiency map** | Details: Drivers[driver_label]; X: `Idle % of Trip Hours`; Y: `Fleet MPG`; Size: `Total Miles` |
| D2 | **Matrix: driver scorecard** | Rows: Drivers[driver_label]; Values: `Total Miles`, `Fleet MPG`, `Idle % of Trip Hours`, `Delivery On-Time %`, `Incidents`, `Claim Cost` (conditional icons). *Merges trips + events + incidents* |
| D3 | **Stacked bar: incidents by type** | Axis: Incidents[incident_type]; Legend: Incidents[preventable_flag]; Value: `Incidents`; Tooltip: `Claim Cost` |
| D4 | **Column: experience vs performance** | X: Drivers[years_experience] (bins of 5); Columns: `Incidents per Million Miles`; Line: `Fleet MPG` |

## Page 5: Fuel: where does the fuel money go?

| KPI card | Measure | Value |
| --- | --- | ---: |
| Fuel Spend | `Fuel Spend` | $95.6M |
| Avg Price per Gallon | `Avg Price per Gallon` | $3.899 |
| Fuel Cost per Mile | `Fuel Cost per Mile` | $0.782 |
| Purchase Gap % | `Purchase Gap %` | +29.4% |

| # | Visual | Fields |
| --- | --- | --- |
| U1 | **Combo: spend vs price** | X: Date[Month]; Columns: `Fuel Spend`; Line: `Avg Price per Gallon` |
| U2 | **Clustered bar: bought vs burned by truck** | Axis: Trucks[truck_label] (sorted by `Purchase Gap %`); Values: `Gallons Purchased`, `Fuel Gallons Burned`. *Merges fuel cards + trips* |
| U3 | **Bar/map: price by state** | Fuel[location_state]; `Avg Price per Gallon`, `Gallons Purchased` |
| U4 | **Scatter: drivers' fuel discipline** | Details: Drivers[driver_label]; X: `Fleet MPG`; Y: `Purchase Gap %`; Size: `Fuel Spend` |

Challenge: the 29% gap may be the most important number here. It could mean fuel-card
misuse, fuel bought for reefer units on refrigerated loads, or just how the data was
generated. Check `Purchase Gap %` by load_type before calling it a problem.

---

## Build order (Power BI Desktop)
1. Download the 14 CSVs from Drive into one folder.
2. Transform data → create the `DataFolder` parameter → paste each query from
   `PowerQuery.m` → Close & Apply.
3. Modeling → New table → paste `Date`. Mark it as the date table and sort Month by
   MonthNo.
4. Model view → create the 13 relationships above.
5. Create the `_Measures` table → paste the measures.
6. Build Page 1 KPI cards first and compare with `KPI-TARGETS.md`. Only build the
   visuals once the cards match.
7. Then visuals, slicers, and the "On time = ±2h" note.
