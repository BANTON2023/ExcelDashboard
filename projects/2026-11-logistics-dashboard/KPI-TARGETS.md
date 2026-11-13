# KPI targets: whole period, no slicers

Computed with pandas from the raw CSVs (`scripts/kpi_targets.py`). With no filters
applied, each Power BI card should show these values. If one doesn't, the measure or
a relationship is wrong.

| Page | KPI | Value |
| --- | --- | ---: |
| Customer | Total Revenue (line-haul + fuel surcharge + accessorials) | $298,621,429 |
| Customer | Loads | 85,410 |
| Customer | Revenue per Mile | $2.445 |
| Customer | Top-10 Customer Revenue Share | 5.7% |
| Customer | (support) Revenue after Est. Fuel | $224,755,088 |
| Service | Delivery On-Time % (±120 min, from flag) | 44.6% |
| Service | Pickup On-Time % | 66.7% |
| Service | Avg Detention per Stop (min) | 91.5 |
| Service | Late Deliveries (>120 min late) | 37,926 |
| Service | (alt) Delivery Not-Late % | 33.3% |
| Fleet | Maintenance Cost | $5,730,573 |
| Fleet | Maintenance Cost per Mile | $0.0469 |
| Fleet | Downtime Hours | 72,230.5 |
| Fleet | Trucks Used / Fleet | 92 / 120 = 76.7% |
| Driver | Active Drivers | 124 |
| Driver | Fleet MPG (miles ÷ gallons, weighted) | 6.448 |
| Driver | (alt) Average of trip MPG (unweighted) | 6.501 |
| Driver | Idle % of Trip Hours | 28.0% |
| Driver | Incidents per Million Miles | 1.392 |
| Driver | (support) Preventable Incidents | 64 |
| Fuel | Fuel Spend (purchases) | $95,592,992 |
| Fuel | Avg Price per Gallon (weighted) | $3.899 |
| Fuel | Fuel Cost per Mile (purchases) | $0.7825 |
| Fuel | Purchase Gap % (bought vs burned) | 29.4% |
| Fuel | (alt) Fuel Cost per Mile (burned × price) | $0.6047 |

Supporting totals: miles 122,159,201; gallons burned 18,946,280; gallons bought 24,519,038; incidents 170.
