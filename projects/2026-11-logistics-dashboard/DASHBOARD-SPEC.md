# Logistics dashboard: questions, KPIs and visuals (Power BI, Windows)

5 pages: **Customer · Fuel · Fleet · Driver · Service**. Each page asks one headline
question, shows **3 KPI cards**, and has **4 visuals**, each answering one specific
question. Revenue = line-haul + fuel surcharge + accessorials.

Every "Answer" below was computed from the full CSVs (`scripts/answer_questions.py`),
so you know what each visual should show before you build it. **Signal** says how much
the data actually varies:
- **Strong:** a clear, actionable difference.
- **Moderate:** a real but small difference.
- **Flat:** almost no difference. That's still an answer ("it's not X"), but don't
  read patterns into noise.

Code: `powerbi/PowerQuery.m` and `powerbi/Measures.dax`. Card check-values:
`KPI-TARGETS.md`.

---

## Page 1: Customer: which lanes and customers are worth keeping, repricing or chasing?

| KPI card | Measure | Value |
| --- | --- | ---: |
| Total Revenue | `Total Revenue` | $298.6M |
| Revenue per Mile | `Revenue per Mile` | $2.445 |
| Revenue after Fuel per Mile | `Revenue after Fuel per Mile` | $1.840 |

| # | Question | Visual & fields | Answer from the data | Signal |
| --- | --- | --- | --- | --- |
| C1 | **Which lanes earn the least per mile after fuel, and should they be repriced?** | Bar chart, bottom 10 (Filters → Top N): Axis Routes[lane]; Value `Revenue after Fuel per Mile`; Tooltips `Loads`, `Total Revenue` | Worst: Charlotte → Denver **$1.10**, Las Vegas → New York **$1.11**, Miami → Seattle **$1.20**. Best: Philadelphia → New York **$3.01**. 3 lanes earn under $1.25 and carry 6.4% of revenue. | Strong |
| C2 | **Does lane length change what we earn per mile?** | Scatter: Details Routes[lane]; X Routes[typical_distance_miles] (Don't summarize); Y `Revenue after Fuel per Mile`; Size `Loads` | Only a little. Lanes under 500 miles earn $2.12; every other length band earns $1.78–1.87. The gap between lanes comes from each lane's **contracted rate**, not its length (correlation −0.13). | Moderate |
| C3 | **How much revenue comes from customers marked Inactive?** | Stacked column: X Date[Year]; Legend Customers[account_status]; Y `Total Revenue` | **16.2% every year**, about $16M a year, *including 2024*. Either the status field is wrong, or "inactive" customers are still shipping. Check with sales. | Strong |
| C4 | **Do any customers pay noticeably more or less per mile?** | Scatter: Details Customers[customer_label]; X `Loads`; Y `Revenue per Mile`; Size `Total Revenue`; Legend Customers[customer_type] | **No.** Every customer pays $2.39–2.51 per mile, whatever their volume (correlation 0.05). Pricing is uniform, so look for margin in the lanes (C1), not the customers. | Flat |

## Page 2: Fuel: where is the fuel money going, and is any of it leaking?

| KPI card | Measure | Value |
| --- | --- | ---: |
| Fuel Spend | `Fuel Spend` | $95.6M |
| Fuel Cost per Mile | `Fuel Cost per Mile` | $0.782 |
| Purchase Gap (bought vs burned) | `Purchase Gap %` | +29.4% |

| # | Question | Visual & fields | Answer from the data | Signal |
| --- | --- | --- | --- | --- |
| U1 | **Is fuel spend falling because of price or because of volume?** | Line and column combo: X Date[Month]; Columns `Fuel Spend`; Line `Avg Price per Gallon`; Tooltip `Gallons Purchased` | **Price.** Spend fell from $34.4M (2022) to $31.1M (2023) to $30.1M (2024). Gallons stayed flat at 8.1–8.2M a year, while price fell from $4.20 to $3.85 to $3.65 a gallon. | Strong |
| U2 | **Which trucks buy the most fuel beyond what they burn?** | Clustered bar, sorted by gap: Axis Trucks[truck_label]; Values `Gallons Purchased`, `Fuel Gallons Burned`; Tooltip `Purchase Gap %` | **Every truck** over-buys, by 19.5% to 41.1%. The worst are TRK00014 (+41%), TRK00036 (+39%) and TRK00038 (+38%). A gap on every truck points to a system-wide cause, not a few bad cards. | Moderate |
| U3 | **Is the gap explained by refrigerated loads, which need extra fuel for the cooling unit?** | Clustered column: X LoadType[load_type]; Values `Gallons Purchased`, `Fuel Gallons Burned`; Data label `Purchase Gap %` | **No.** Dry Van is +29.1% and Refrigerated is +29.7%, almost identical. Rule this explanation out. | Strong (as a "no") |
| U4 | **Which drivers' fuel cards buy the most beyond what they burn?** | Bar, top 15: Axis Drivers[driver_label]; Value `Purchase Gap %`; Tooltips `Fuel Spend`, `Fleet MPG` | The range is 20.1% to 38.4%, and it is **unrelated to how efficiently they drive** (correlation 0.06). This is the list to start a fuel-card audit with. | Moderate |

## Page 3: Fleet: which trucks should we fix, sell or replace?

| KPI card | Measure | Value |
| --- | --- | ---: |
| Maintenance Cost per Mile | `Maintenance Cost per Mile` | $0.047 |
| Downtime Hours | `Downtime Hours` | 72,231 |
| Maintenance on Idle Trucks | `Maintenance on Idle Trucks` | $1.40M (24.5%) |

| # | Question | Visual & fields | Answer from the data | Signal |
| --- | --- | --- | --- | --- |
| F1 | **How much do we spend maintaining trucks that never drive?** | Stacked bar: Axis Trucks[Ran Trips] (calculated column); Legend Trucks[status]; Value `Maintenance Cost`; Tooltip `Downtime Hours` | **28 trucks never ran a trip but cost $1.40M, 24.5% of all maintenance.** 15 are marked "Maintenance" and 13 "Inactive". Sell them or stop servicing them. | Strong |
| F2 | **Which running trucks cost the most to maintain per mile?** | Scatter: Details Trucks[truck_label]; X `Total Miles`; Y `Maintenance Cost per Mile`; Size `Downtime Hours`; Legend Trucks[make] | There is a **6× spread**, from $0.009 to $0.058 per mile (median $0.036). The worst is TRK00014, which is also the worst fuel over-buyer (U2). Investigate that truck first. | Strong |
| F3 | **Do older trucks cost more to maintain?** | Column and line combo: X Trucks[model_year]; Columns `Maintenance Cost per Mile`; Line `Trucks Used` | **No clear age effect.** 59 of the 92 running trucks are 2015 models, and later years have only 1–6 trucks each, too few to judge. The data doesn't support replacing trucks on age alone. | Flat |
| F4 | **Which 15 trucks should we act on first?** | Table, sorted by `Maintenance Cost` with conditional formatting: Trucks[truck_label], Trucks[status], `Maintenance Cost`, `Maintenance Cost per Mile`, `Downtime Hours`, `Purchase Gap %`, `Incidents` | An action list that combines maintenance, downtime, fuel and safety for each truck. TRK00014 should come out near the top on several of these at once. | Strong |

## Page 4: Driver: who are our safest drivers, and who needs coaching?

| KPI card | Measure | Value |
| --- | --- | ---: |
| Incidents per Million Miles | `Incidents per Million Miles` | 1.39 |
| Preventable Incidents | `Preventable Incidents` | 64 of 170 |
| Fleet MPG | `Fleet MPG` | 6.45 |

| # | Question | Visual & fields | Answer from the data | Signal |
| --- | --- | --- | --- | --- |
| D1 | **Which incident types cost the most, and how many could we have prevented?** | Stacked bar: Axis Incidents[incident_type]; Legend Incidents[preventable_flag]; Value `Incidents`; Tooltip `Claim Cost` | **Equipment damage** costs the most ($741k) but is the least preventable (26%). **DOT violations** (breaches of transport regulations) are the most frequent (39) and the most preventable (46%). Target coaching at DOT violations. | Strong |
| D2 | **Which drivers have the most incidents?** | Bar, top 15: Axis Drivers[driver_label]; Value `Incidents`; Tooltips `Incidents per Million Miles`, `Claim Cost`, `Total Miles` | 32 of 124 drivers had **no incidents**. The worst had **7**. Compare per million miles so that drivers who simply drive more aren't flagged unfairly. | Moderate |
| D3 | **Does experience make drivers safer?** | Column and line combo: X Drivers[experience_band]; Columns `Incidents per Million Miles`; Line `Fleet MPG` | **No.** Drivers with 0–5 years have the lowest rate (1.18), and 11–15 years the highest (1.63). There are only 170 incidents in total, so treat this as a hint, not proof. | Moderate |
| D4 | **Who should we coach first?** | Matrix with conditional icons: Rows Drivers[driver_label]; Values `Total Miles`, `Fleet MPG`, `Idle % of Trip Hours`, `Delivery On-Time %`, `Incidents`, `Claim Cost` | Fuel economy (6.38–6.54) and idle time (26–29%) **barely vary** between drivers. **Incidents and on-time (37–50%) are where drivers differ**, so rank by those. | Moderate |

## Page 5: Service: how late are we, and is it a site problem or a system problem?

| KPI card | Measure | Value |
| --- | --- | ---: |
| Delivery On-Time % (±2h) | `Delivery On-Time %` | 44.6% |
| Late Deliveries (>2h late) | `Late Deliveries` | 37,926 (44.4%) |
| Avg Detention per Stop | `Avg Detention (min)` | 91.5 min |

| # | Question | Visual & fields | Answer from the data | Signal |
| --- | --- | --- | --- | --- |
| S1 | **How much does the definition of "on time" change the answer, and is it improving?** | Line: X Date[Month]; Lines `Delivery On-Time %`, `Delivery Not-Late %`, `Pickup On-Time %` | Within ±2 hours: **44.6%**. Strictly not late: **33.3%**. It is **not improving**: 44.7%, 44.5% and 44.6% in 2022–2024. | Strong |
| S2 | **When we miss, how badly do we miss?** | Column: X Events[lateness_band]; Y `Stops`; Filter Events[event_type] = Delivery | Of 85,410 deliveries: 9,382 arrived more than 2 hours early, 38,102 on time, 18,817 were 2–4 hours late, and **19,109 were more than 4 hours late**. **22% of all deliveries are more than 4 hours late.** | Strong |
| S3 | **Is lateness concentrated at certain facilities?** | Bar and line combo, sorted: Axis Facilities[facility_name]; Columns `Late Delivery Rate`; Line `Avg Detention (min)` | **No.** Every facility is 42.6–47.8% late, with 103–110 minutes of detention. Lateness is also flat by weekday, hour and transit days. **It's a system problem** (scheduling windows, dispatch), not one bad site. | Strong (as a "no") |
| S4 | **Do our biggest customers get better service?** | Scatter: Details Customers[customer_label]; X `Total Revenue`; Y `Delivery On-Time %`; Size `Late Deliveries` | **No.** On-time ranges from 39.4% to 51.9% and is unrelated to how much a customer pays (correlation −0.07). Top-revenue accounts get no better treatment. | Moderate |

Put this note on the page: *"On time = within ±2 hours of the scheduled time. More
than 2 hours early counts as not on time."*

---

## Data model (Model view)

All relationships are many-to-one and single-direction.

| From (many) | To (one) | Column |
| --- | --- | --- |
| Shipments | Customers | customer_id |
| Shipments | Routes | route_id |
| Shipments | Drivers | driver_id |
| Shipments | Trucks | truck_id |
| Shipments | LoadType | load_type |
| Shipments | Date | dispatch_date → Date |
| Events | Shipments | load_id |
| Events | Facilities | facility_id |
| Incidents | Shipments | trip_id |
| Fuel | Trucks | truck_id |
| Fuel | Drivers | driver_id |
| Fuel | LoadType | load_type |
| Fuel | Date | purchase_day → Date |
| Maintenance | Trucks | truck_id |
| Maintenance | Date | maintenance_date → Date |

Fuel is **not** linked to Shipments directly; that would create a second filter path
from Trucks and Drivers. The monthly summary CSVs are left out: they duplicate trip data
and drop unassigned trips.

Slicers synced on every page: Date[Year], Date[Month], LoadType[load_type],
Shipments[booking_type].

## Build order
1. Put the 14 CSVs in one folder. Paste the queries from `PowerQuery.m` (set
   `DataFolder` first), then Close & Apply.
2. Create the `Date` table from `Measures.dax`, mark it as the date table, and sort Month
   by MonthNo.
3. Create the relationships above, then the Trucks[Ran Trips] calculated column, then
   the `_Measures` table.
4. **Build the 15 KPI cards first and check them against `KPI-TARGETS.md`.** Fix any
   mismatch before building visuals.
5. Build the visuals page by page. Use each question as the visual's title.

## Caveat
The data looks generated: flat volume, uniform lateness and near-identical customers.
Expect several "Flat" answers. In real data, these same questions would show more
variation. *[Judgment]*
