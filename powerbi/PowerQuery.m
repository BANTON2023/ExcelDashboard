// =====================================================================
// Logistics dashboard: Power Query (M) for every table
// How to use: Power BI Desktop > Home > Transform data > New Source >
// Blank Query > Advanced Editor. Paste ONE section per query and rename
// the query to the name in its header.
// Set the folder path in the DataFolder parameter first (keep the final \).
// =====================================================================

// ---------- Query: DataFolder  (Home > Manage Parameters > New, type Text) ----------
"C:\Users\YOU\Documents\logistics-data\" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]

// ---------- Query: fxLoadCsv  (helper function) ----------
(fileName as text) as table =>
let
    Source   = Csv.Document(File.Contents(DataFolder & fileName),
                 [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true])
in
    Promoted

// ---------- Query: stgLoads  (right-click > uncheck "Enable load") ----------
let
    Source = fxLoadCsv("loads.csv"),
    Typed  = Table.TransformColumnTypes(Source, {
        {"load_date", type date}, {"weight_lbs", Int64.Type}, {"pieces", Int64.Type},
        {"revenue", Currency.Type}, {"fuel_surcharge", Currency.Type},
        {"accessorial_charges", Currency.Type}}, "en-US")
in
    Typed

// ---------- Query: stgTrips  (uncheck "Enable load") ----------
let
    Source = fxLoadCsv("trips.csv"),
    Typed  = Table.TransformColumnTypes(Source, {
        {"dispatch_date", type date}, {"actual_distance_miles", Int64.Type},
        {"actual_duration_hours", type number}, {"fuel_gallons_used", type number},
        {"average_mpg", type number}, {"idle_time_hours", type number}}, "en-US"),
    // blank IDs -> null so they show as "(Blank)" rather than an empty driver/truck
    Nulls  = Table.ReplaceValue(Typed, "", null, Replacer.ReplaceValue,
                {"driver_id", "truck_id", "trailer_id"})
in
    Nulls

// ---------- Query: Shipments  (fact: 1 row = 1 load = 1 trip) ----------
let
    Merged   = Table.NestedJoin(stgLoads, {"load_id"}, stgTrips, {"load_id"}, "t", JoinKind.Inner),
    Expanded = Table.ExpandTableColumn(Merged, "t",
        {"trip_id", "driver_id", "truck_id", "trailer_id", "dispatch_date",
         "actual_distance_miles", "actual_duration_hours", "fuel_gallons_used",
         "average_mpg", "idle_time_hours"}),
    // Chosen revenue definition: line-haul + fuel surcharge + accessorials
    TotalRev = Table.AddColumn(Expanded, "total_revenue",
        each [revenue] + [fuel_surcharge] + [accessorial_charges], Currency.Type),
    Removed  = Table.RemoveColumns(TotalRev, {"load_status"})
in
    Removed

// ---------- Query: Events  (pickups and deliveries) ----------
let
    Source = fxLoadCsv("delivery_events.csv"),
    Typed  = Table.TransformColumnTypes(Source, {
        {"scheduled_datetime", type datetime}, {"actual_datetime", type datetime},
        {"detention_minutes", Int64.Type}, {"on_time_flag", type logical}}, "en-US"),
    Late   = Table.AddColumn(Typed, "late_minutes",
        each Duration.TotalMinutes([actual_datetime] - [scheduled_datetime]), type number),
    Band   = Table.AddColumn(Late, "lateness_band", each
        if [late_minutes] < -120 then "1 Early >2h"
        else if [late_minutes] <= 120 then "2 On time (±2h)"
        else if [late_minutes] <= 240 then "3 Late 2–4h"
        else "4 Late >4h", type text)
in
    Band

// ---------- Query: Fuel  (fuel-card purchases) ----------
let
    Source = fxLoadCsv("fuel_purchases.csv"),
    Typed  = Table.TransformColumnTypes(Source, {
        {"purchase_date", type datetime}, {"gallons", type number},
        {"price_per_gallon", type number}, {"total_cost", Currency.Type}}, "en-US"),
    Nulls  = Table.ReplaceValue(Typed, "", null, Replacer.ReplaceValue, {"truck_id", "driver_id"}),
    Day    = Table.AddColumn(Nulls, "purchase_day", each DateTime.Date([purchase_date]), type date),
    Drop   = Table.RemoveColumns(Day, {"fuel_card_number"}),
    // bring load_type across so fuel can be split Dry Van vs Refrigerated (page Fuel, U3)
    WithLT = Table.NestedJoin(Drop, {"trip_id"}, Shipments, {"trip_id"}, "s", JoinKind.LeftOuter),
    LT     = Table.ExpandTableColumn(WithLT, "s", {"load_type"})
in
    LT

// ---------- Query: LoadType  (2-row lookup that filters Shipments AND Fuel) ----------
let
    Source = #table(type table [load_type = text], {{"Dry Van"}, {"Refrigerated"}})
in
    Source

// ---------- Query: Maintenance ----------
let
    Source = fxLoadCsv("maintenance_records.csv"),
    Typed  = Table.TransformColumnTypes(Source, {
        {"maintenance_date", type date}, {"odometer_reading", Int64.Type},
        {"labor_hours", type number}, {"labor_cost", Currency.Type},
        {"parts_cost", Currency.Type}, {"total_cost", Currency.Type},
        {"downtime_hours", type number}}, "en-US")
in
    Typed

// ---------- Query: Incidents ----------
let
    Source = fxLoadCsv("safety_incidents.csv"),
    Typed  = Table.TransformColumnTypes(Source, {
        {"incident_date", type datetime}, {"at_fault_flag", type logical},
        {"injury_flag", type logical}, {"preventable_flag", type logical},
        {"vehicle_damage_cost", Currency.Type}, {"cargo_damage_cost", Currency.Type},
        {"claim_amount", Currency.Type}}, "en-US")
in
    Typed

// ---------- Query: Customers ----------
let
    Source = fxLoadCsv("customers.csv"),
    Typed  = Table.TransformColumnTypes(Source, {
        {"credit_terms_days", Int64.Type}, {"contract_start_date", type date},
        {"annual_revenue_potential", Currency.Type}}, "en-US"),
    // names repeat across IDs, so build a unique label
    Label  = Table.AddColumn(Typed, "customer_label",
        each [customer_name] & " (" & [customer_id] & ")", type text)
in
    Label

// ---------- Query: Routes ----------
let
    Source = fxLoadCsv("routes.csv"),
    Typed  = Table.TransformColumnTypes(Source, {
        {"typical_distance_miles", Int64.Type}, {"base_rate_per_mile", type number},
        {"fuel_surcharge_rate", type number}, {"typical_transit_days", Int64.Type}}, "en-US"),
    Lane   = Table.AddColumn(Typed, "lane",
        each [origin_city] & " → " & [destination_city], type text)
in
    Lane

// ---------- Query: Drivers ----------
let
    Source = fxLoadCsv("drivers.csv"),
    Typed  = Table.TransformColumnTypes(Source, {
        {"hire_date", type date}, {"termination_date", type date},
        {"date_of_birth", type date}, {"years_experience", Int64.Type}}, "en-US"),
    Label  = Table.AddColumn(Typed, "driver_label",
        each [first_name] & " " & [last_name] & " (" & [driver_id] & ")", type text),
    Band   = Table.AddColumn(Label, "experience_band", each
        if [years_experience] <= 5 then "1) 0–5 yrs"
        else if [years_experience] <= 10 then "2) 6–10 yrs"
        else if [years_experience] <= 15 then "3) 11–15 yrs"
        else if [years_experience] <= 20 then "4) 16–20 yrs"
        else "5) 21–25 yrs", type text),
    // keep personal data out of the model
    Drop   = Table.RemoveColumns(Band, {"license_number", "date_of_birth"})
in
    Drop

// ---------- Query: Trucks ----------
let
    Source = fxLoadCsv("trucks.csv"),
    Typed  = Table.TransformColumnTypes(Source, {
        {"model_year", Int64.Type}, {"acquisition_date", type date},
        {"acquisition_mileage", Int64.Type}, {"tank_capacity_gallons", Int64.Type}}, "en-US"),
    Label  = Table.AddColumn(Typed, "truck_label",
        each [make] & " #" & [unit_number] & " (" & [truck_id] & ")", type text)
in
    Label

// ---------- Query: Facilities ----------
let
    Source = fxLoadCsv("facilities.csv"),
    Typed  = Table.TransformColumnTypes(Source, {
        {"latitude", type number}, {"longitude", type number}, {"dock_doors", Int64.Type}}, "en-US")
in
    Typed
