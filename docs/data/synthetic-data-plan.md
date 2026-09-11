# FinalFlow synthetic input plan

## Purpose and boundary

This plan fills missing *scenario inputs* for the FinalFlow World Cup mobility
case study. It does not claim that values are observed 2026 event conditions.
Synthetic inputs are consumed by deterministic calculations; queues, throughput,
utilization, waits, clearance, congestion, emissions and recommendations are
derived from those inputs and must never be independently randomized.

The plan reuses `finalflow_corridor_v1` from
[`mobility_config.py`](../../paddydash/services/mobility_config.py), its five
minute clock, canonical nodes/edges, and the scenario and phase identifiers in
[`mobility_contract.py`](../../paddydash/services/mobility_contract.py). It does
not change the strict runtime Pydantic models. A future generator may read these
files as inputs, but generation is explicitly out of scope for this document.

## Common contract

Every time-indexed file has one row for a five-minute interval. `time_minutes`
is kickoff-relative and `timestamp` is an illustrative ISO 8601 timestamp for
that interval; it is never a real match schedule. Use this initial bounded
window: `-180` through `315`, inclusive, at five-minute increments: 100 rows per
scenario. It covers pre-match arrivals, the assumed extra-time replay, and
three hours of initial post-match clearing. It is not a claim that clearing ends
at +315 minutes.

Use these IDs exactly:

| Contract | IDs |
| --- | --- |
| Scenarios | `baseline`, `rail_disruption`, `rail_capacity_boost`, `rain`, `staggered_departure` |
| Interval phases | `pre_match`, `ceremony`, `first_half`, `halftime`, `second_half`, `extra_time`, `post_match` |
| Event markers | `gates_open`, `kickoff`, `first_half_end`, `regulation_end`, `extra_time_end`, `final_whistle` |
| Nodes | `midtown`, `penn_station`, `secaucus`, `meadowlands`, `stadium` |
| Current edges | `midtown_to_penn_station`, `penn_station_to_midtown`, `penn_station_to_secaucus`, `secaucus_to_penn_station`, `secaucus_to_meadowlands`, `meadowlands_to_secaucus`, `meadowlands_to_stadium`, `stadium_to_meadowlands` |
| Corridor modes | `walk`, `rail`, `road`, `shuttle` |

At an event time, use the matching event `phase_id`; all other rows use the
active interval phase. `direction` is `inbound` or `outbound`. Use a non-real
fixed demonstration date in all `timestamp` values and store it in the manifest.
Do not use legacy commercial labels such as `during match` or `rainy_post_match`
as mobility `scenario_id` or `phase_id` values.

Each row must contain `data_type=synthetic`, `confidence_type=scenario`, and an
`assumption_note` that states why the value is illustrative. Counts are people
or vehicles per five-minute interval unless a field explicitly supplies another
unit. Percent fields are decimals, not 0-100 values. Rows must be deterministic
for a recorded seed; an omitted seed is invalid.

## Proposed input tables

| File | Grain | Fixed dimensions and estimated size |
| --- | --- | --- |
| `matchday_passenger_demand.csv` | scenario × interval × origin/destination/mode lane | 5 × 100 × 32 lanes = 16,000 rows |
| `transit_service_capacity.csv` | scenario × interval × current corridor edge | 5 × 100 × 8 edges = 4,000 rows |
| `first_last_mile_demand.csv` | scenario × interval × access zone × access mode | 5 × 100 × 5 zones × 4 modes = 10,000 rows |
| `road_access_demand.csv` | scenario × interval × road zone × vehicle mode | 5 × 100 × 5 zones × 3 vehicle modes = 7,500 rows |
| `parking_demand.csv` | scenario × interval × parking zone | 5 × 100 × 4 zones = 2,000 rows |
| `pedestrian_demand.csv` | scenario × interval × pedestrian segment | 5 × 100 × 6 segments = 3,000 rows |
| `interventions.csv` | one static intervention definition | 12-16 rows |
| `emissions_factors.csv` | one mode/factor definition | 5-8 rows |
| `corridor_reference.csv` | configured corridor node | 5 rows |
| `zone_reference.csv` | bounded first/last-mile analysis zone | 5 rows |

The generated target is 42,500 time-indexed rows, plus small reference tables. A
generator should not create rows for an unsupported route, zone, mode, or
scenario simply to reach a target count.

`corridor_reference.csv` and `zone_reference.csv` are compact synthetic map
references for the dashboard. Their coordinates are approximate demonstration
points and their zones are not official access boundaries or venue inventories.

### `matchday_passenger_demand.csv`

Grain: one scenario, interval, origin, destination and mode lane. Restrict modes
to `rail`, `walk`, `shuttle` and `road`. `road` represents road-carried people;
use `vehicle_mode` in road access data to distinguish rideshare and private
vehicle. This avoids adding `rideshare` and `private_vehicle` as conflicting
corridor modes before the runtime contract supports them.

Required fields:

```text
scenario_id,timestamp,time_minutes,phase_id,origin_node,destination_node,mode,
direction,passenger_demand,demand_multiplier,source_profile,data_type,
confidence_type,assumption_note
```

`passenger_demand` is a nonnegative integer people/interval. `demand_multiplier`
is the scenario adjustment relative to the same baseline lane. `source_profile`
identifies the synthetic profile such as `uniform_inbound_v1` or
`staggered_outbound_v1`; it is not a source citation.

### `transit_service_capacity.csv`

Grain: one scenario, interval and configured edge. It is the only initial
capacity input for the current mobility engine. A future shuttle or road edge
must first be added to the central configuration and contract.

```text
scenario_id,timestamp,time_minutes,phase_id,edge_id,from_node,to_node,mode,
scheduled_capacity,effective_capacity,service_frequency_minutes,
disruption_factor,weather_factor,data_type,confidence_type,assumption_note
```

Capacities are people/interval. Factors are nonnegative decimal multipliers and
must satisfy `effective_capacity = floor(scheduled_capacity * disruption_factor
* weather_factor)`. The baseline factors are 1.0. Rail disruption modifies rail
only; rain modifies walk/rail effective capacity and travel assumptions; boost
modifies rail only. `service_frequency_minutes` is illustrative and must not be
shown as an operator timetable.

### `first_last_mile_demand.csv`

Grain: one scenario, interval, named access zone and access mode. Start with the
five bounded zones `midtown_access`, `penn_station_access`,
`secaucus_transfer`, `meadowlands_access`, and `stadium_egress`; these are
synthetic analysis zones, not official boundaries.

```text
scenario_id,timestamp,time_minutes,phase_id,zone_id,access_mode,
arriving_passengers,departing_passengers,distance_band,walking_pressure,
data_type,confidence_type,assumption_note
```

`access_mode` is `walk`, `shuttle`, `road`, or `rail`; `distance_band` is one of
`under_400m`, `400m_to_800m`, `800m_to_1600m`, `over_1600m`; and
`walking_pressure` is an input label (`low`, `medium`, `high`), not a derived
queue result. Passenger counts must reconcile with their aggregate demand lanes;
do not double count transfer passengers.

### `road_access_demand.csv`

Grain: one scenario, interval, road zone and vehicle mode. Reuse the five access
zones above. `vehicle_mode` is `private_vehicle`, `rideshare`, or `shuttle`.

```text
scenario_id,timestamp,time_minutes,phase_id,zone_id,vehicle_mode,
vehicle_count,average_occupancy,passenger_count,pickup_dropoff_demand,
road_capacity_index,data_type,confidence_type,assumption_note
```

Vehicle counts are vehicles/interval, `passenger_count` is people/interval, and
`road_capacity_index` is a synthetic 0-1 input index. Require
`passenger_count = round(vehicle_count * average_occupancy)` using a documented
rounding rule. It is not a road traffic measurement.

### `parking_demand.csv`

Grain: one scenario, interval and synthetic parking zone. Start with
`stadium_parking`, `meadowlands_remote`, `secaucus_park_ride`, and
`midtown_park_ride`; names are scenario labels, not actual inventories.

```text
scenario_id,timestamp,time_minutes,phase_id,parking_zone_id,estimated_spaces,
occupied_spaces_input,arrival_vehicles,departure_vehicles,
average_vehicle_occupancy,data_type,confidence_type,assumption_note
```

All space/vehicle fields are nonnegative integers. `occupied_spaces_input` is a
synthetic state input and must stay between zero and `estimated_spaces`. It must
balance from the prior interval plus arrivals minus departures; do not generate
occupancy as an unrelated random series. This table cannot establish real stadium
parking availability.

### `pedestrian_demand.csv`

Grain: one scenario, interval and fixed pedestrian segment. Initial segments may
be `midtown_penn_walk`, `penn_concourse`, `secaucus_transfer`,
`meadowlands_platform`, `meadowlands_stadium_walk`, and `stadium_egress_walk`.
Segments are illustrative, pending official mapping.

```text
scenario_id,timestamp,time_minutes,phase_id,segment_id,from_zone,to_zone,
pedestrian_demand,effective_width_m,walking_speed_mps,
effective_capacity_per_interval,weather_factor,data_type,confidence_type,
assumption_note
```

Demand and capacity are people/interval; width is metres and speed is metres per
second. `weather_factor` is a nonnegative input multiplier. Derive density,
walking delay and pedestrian queues only after generation.

### `interventions.csv`

This is static, not time-indexed. Use 12-16 records chosen from: increased rail
capacity, added shuttle service, staggered departures, mobility-aware vendor
placement, covered queue areas, rideshare geofencing, pedestrian routing,
platform management, staffed transfers, parking reservations, shade/water and
accessible wayfinding.

```text
intervention_id,name,category,target_id,capacity_change_pct,demand_shift_pct,
departure_spread_minutes,implementation_cost_band,description,data_type,
confidence_type,assumption_note
```

Percentage fields are decimal fractions. A catalog entry is not evidence that it
will work. Apply it only through documented input transformations; do not attach
fabricated improvement percentages.

### `emissions_factors.csv`

Keep this table below 50 rows. It is an input reference used only after vehicle
or passenger-kilometre calculations exist.

```text
mode,emissions_kg_co2e_per_passenger_km,average_occupancy,source_type,
data_type,confidence_type,assumption_note
```

Use `source_type=synthetic_assumption` until defensible public factors are
approved. The factors are not authoritative environmental estimates. Emissions
are derived as activity × distance × factor, with all assumptions shown.

## Manifest and generation order

Write one separate `data/synthetic/manifest.json` beside the
tables. This avoids adding extra fields to strict runtime Pydantic models. It
contains: `schema_version`, `generator_version`, `random_seed`, `generated_at`,
`config_id`, `timeline`, `source_references`, `assumptions`, `files`, row counts,
SHA-256 hashes and the fixed synthetic demonstration date. `source_references`
must distinguish the mobility configuration from contextual derived sources.

Generate in this order:

1. Read and validate the central config, phase map and scenario modifiers.
2. Construct baseline passenger demand and mode-share input lanes.
3. Apply scenario transformations deterministically to demand, capacity, weather
   and release assumptions.
4. Reconcile first/last-mile, road and parking inputs to demand/mode totals.
5. Generate pedestrian segment inputs from reconciled walk demand.
6. Validate unique keys, IDs, time alignment, nonnegative values, balances and
   cross-file conservation.
7. Write tables, manifest and a compact validation report.
8. Run the simulator and deterministic post-processors to derive outputs.

## Derived outputs and app mapping

Do not randomly generate: node/edge queues, edge throughput, utilization,
estimated wait, clearance, congestion, pedestrian density, parking occupancy
change, emissions totals, scenario improvements or recommendation scores. Those
are derived outputs with lineage back to synthetic inputs and deterministic rules.

| Streamlit area | Inputs | Derived display outputs |
| --- | --- | --- |
| Mobility readiness | passenger demand, edge capacity, intervention parameters | queue, bottleneck, utilization, wait, clearance and comparison |
| Commercial & weather context | first/last-mile, road, parking, pedestrian, weather factors | scenario context and carefully labeled operational recommendations |
| Spatial & Heat Map | curated provided/derived POI and heat layers only | context filters; never synthetic event facts |
| Ask FinalFlow | selected state, derived outputs and labeled contextual evidence | grounded explanation, never authoritative calculation by the model |

The deterministic post-processor is
[`derive_finalflow_mobility_outputs.py`](../../scripts/synthetic/derive_finalflow_mobility_outputs.py).
It writes `data/exports/mobility_node_timeseries.csv`,
`mobility_edge_timeseries.csv`, `scenario_summary.csv`,
`mobility_access_summary.csv`, `intervention_comparison.csv`, and a derived
manifest. Every exported row uses `data_type=derived` and retains an assumption
note stating that its inputs are synthetic. Road and shuttle inputs are modeled
as direct stadium-boundary access because the current shared corridor contract
does not define road or shuttle edges; their demand is accounted for but no
fictional network links are added.

The initial derived outputs intentionally omit emissions totals. Although the
input catalog has synthetic mode factors, the repository has no documented
mode-distance table. The derived manifest records this as
`not_derived_missing_mode_distance_inputs` rather than implying a measured or
EPA-validated carbon estimate.

## Limitations and approval gates

These are synthetic scenario inputs, not forecasts, service plans, event demand
or safety assessments. No input can validate the corridor without official route,
station, venue/access, parking, demand and operational data. Before generation,
the team must approve the profile shape, mode shares, assumed cohort scale,
synthetic zone/segment definitions, factor ranges and rounding rules. Public
transit schedules, event access maps, forecast/alert data and defensible emissions
factors should be obtained as `provided` or `web` sources rather than synthesized.
