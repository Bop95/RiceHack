# Mobility simulation contract

Status: typed contract and illustrative configuration, now used by a small
[deterministic engine](../../paddydash/services/mobility_simulator.py) and the
[mobility page](../../paddydash/pages/mobility.py). This is not a calibrated transport model.

## Location and usage

- [mobility_contract.py](../../paddydash/services/mobility_contract.py) defines
  frozen Pydantic models, rejects unknown fields/nonfinite values, and checks
  references, bounds, ordering, and snapshot accounting.
- [mobility_config.py](../../paddydash/services/mobility_config.py) owns the
  default nodes, edges, phases, demand assumptions, and scenario modifiers.

These modules extend the existing shared service layer. They do not import
Streamlit, load datasets, contact providers, or create another backend.
Pydantic is already a root runtime dependency.

```python
from paddydash.services.mobility_config import default_mobility_config
from paddydash.services.mobility_contract import MobilityConfig

config = default_mobility_config()
payload = config.model_dump(mode="json")
restored = MobilityConfig.model_validate(payload)
json_text = config.model_dump_json(indent=2)
schema = MobilityConfig.model_json_schema()
```

Edit or load one validated configuration for each run; do not repeat constants
in pages or the future engine. Change `config_id` when assumptions change and
retain the complete configuration with exported snapshots. Revalidate edited
JSON with `model_validate`; do not use unchecked `model_copy(update=...)`.

## Scope and units

This is an explainable aggregate corridor model with **five-minute steps**,
not transportation microsimulation or a validated match-day forecast. It tracks
one illustrative 6,000-person cohort from Midtown to the stadium, holds
them during the match, and follows their return to Midtown.

Time is elapsed minutes relative to kickoff: negative before kickoff, zero at
kickoff. It is not the football clock or a wall-clock timestamp. Phase and demand
boundaries must align with the configured step. Counts are integer **people**;
edge capacities are people admitted per step, not seats per train or people per
hour. Changing the step requires rescaling those capacities explicitly.

No vehicle timetables, shared rolling stock, platform limits, route choice,
parking inventory, road traffic, pedestrian geometry, emissions, or accessibility
constraints are modeled yet. Daily commercial visits cannot establish event
passenger counts. This configuration has no claim of calibration or validation
against actual event ridership.

## Central corridor and demand assumptions

Node IDs in order: `midtown`, `penn_station`, `secaucus`, `meadowlands`, `stadium`.
Node types are `origin`, `station`, and `venue`; orders start at zero.

| Adjacent locations | Mode | Base people/5-minute step | Travel minutes |
| --- | --- | ---: | ---: |
| Midtown - Penn Station | walk | 600 | 15 |
| Penn Station - Secaucus Junction | rail | 900 | 15 |
| Secaucus Junction - Meadowlands Station | rail | 600 | 15 |
| Meadowlands Station - Stadium | walk | 600 | 10 |

Every row produces two explicit directed edges, named `<from_node>_to_<to_node>`.
The eight edges have independent symmetric capacities, a simplifying assumption
that does not represent actual train allocation. Base capacity must be positive;
effective runtime capacity may be zero during closure. Travel time may be zero.

The 6,000-person cohort enters at `midtown` over the half-open interval
`[-150, -30)`: 250 people per five-minute step under uniform release. These are
assumptions, not generated observations or stadium attendance estimates.
Default post-match release lasts 60 minutes starting at final whistle. It moves
the **same held people** into outbound queues; it must not inject another cohort.
For configurations that do not divide evenly, the future engine must allocate
integer remainders deterministically while preserving the cohort total.

## Match phases

| Phase ID | Display | Elapsed start | Kind |
| --- | --- | ---: | --- |
| `pre_match` | Pre-match | -180 | interval |
| `gates_open` | Gates open | -120 | event |
| `ceremony` | Closing ceremony | -30 | interval |
| `kickoff` | Kickoff | 0 | event |
| `first_half` | First half | 0 | interval |
| `first_half_end` | 45' | 45 | event |
| `halftime` | Halftime | 45 | interval |
| `second_half` | Second half | 60 | interval |
| `regulation_end` | 90' | 105 | event |
| `extra_time` | Extra time | 105 | interval |
| `extra_time_end` | 120' | 135 | event |
| `final_whistle` | Final whistle | 135 | event |
| `post_match` | Post-match | 135 | interval |

Each phase also has a `clock_reference` and `simulation_meaning`. Event markers
do not consume another step. Their explicit `order` resolves simultaneous
markers. An interval lasts until the next interval starts; events within it do
not end it. At a boundary, process markers in order before the following step.
An event snapshot is an optional view of that boundary, not additional movement.

This default assumes a 15-minute halftime, 30 minutes of extra time, no stoppage
time, no extra-time breaks, and no penalties. Hence 90' is elapsed minute 105
and 120' is elapsed minute 135. These are replay assumptions, not an official
schedule. For a regulation-only replay, omit the two extra-time definitions,
move final whistle/post-match to 105, and rebuild contiguous phase orders.

## Scenario definitions

| Canonical scenario | Capacity modifier | Travel modifier | Departure duration |
| --- | --- | --- | --- |
| `baseline` | 1.0 | 1.0 | 60 minutes |
| `rail_disruption` | Rail edges x0.5 | 1.0 | 60 minutes |
| `rail_capacity_boost` | Rail edges x1.5 | 1.0 | 60 minutes |
| `rain` | Walk and rail edges x0.8 | Walk and rail edges x1.25 | 60 minutes |
| `staggered_departure` | 1.0 | 1.0 | 120 minutes |

Modifiers apply to both directions for the entire run; unaffected modes retain
their base values. Scenarios are independent comparisons, not automatically
combined. Commercial staggering delays release; it does not reduce the cohort
or prove a revenue increase. A future engine should floor effective capacity to
whole people and round travel/release durations upward to whole steps. Even
zero-time edges may only deliver at the next boundary, avoiding same-step
multi-edge movement. No modifiers are applied by the contract itself.

## State and snapshot semantics

`NodeState` contains `node_id`, `incoming_passengers`, `queue`,
`served_passengers`, `departing_passengers`, `holding_passengers`, `utilization`,
and `estimated_wait_minutes`.

- `incoming_passengers`: external entries plus edge arrivals during the last
  completed step, excluding transfers from local holding.
- `queue`: end-of-step people waiting for service, excluding holding.
- `served_passengers`: people removed from the queue for boarding, venue holding,
  or final system exit during the step. It may exceed new incoming people.
- `departing_passengers`: served people that leave the node for an edge or final
  exit; it cannot exceed served passengers. Moving into holding is not departure.
- `holding_passengers`: people at the venue deliberately awaiting release,
  counted in system inventory but not the service queue.
- `utilization`: served/service capacity, in [0, 1], or `null` when node service
  capacity is not independently modeled. Do not confuse it with queue pressure.
- `estimated_wait_minutes`: nonnegative queue-based estimate; `null` for blocked
  or unavailable service estimates. Never serialize infinity. A zero wait means
  a computed zero, not missing evidence.

`EdgeState` contains `edge_id`, `demand`, `capacity`, `throughput`, `utilization`,
and `in_transit_passengers`. Demand is the attempted admission count for that
step, capacity is the effective admission limit, and throughput is actual
admissions. Throughput cannot exceed either demand or capacity. Utilization is
throughput/capacity, or zero for a closed edge; closure is visible as capacity
zero and backlog at the node. In-transit passengers include earlier admissions
that have not arrived and can exceed one step's capacity.

`SimulationSnapshot` contains config/scenario/phase IDs, `time_minutes`, all node
and edge states, `total_entered`, `total_people_in_system`, `total_served`,
`data_type`, and `assumptions`. The implemented engine records inventory after
arrivals, cohort release, and service at each boundary. Flow counts describe that
boundary; newly admitted edge batches cannot arrive before a later boundary.
Initial flow counts are zero before demand begins. Always call
`snapshot.validate_against(config)` after constructing or loading a snapshot.

Accounting identities enforced by the schema:

```text
total_people_in_system = sum(node.queue + node.holding_passengers)
                        + sum(edge.in_transit_passengers)
total_entered = total_people_in_system + total_served
```

`total_served` means cumulative **final exits after the return trip**, not the
sum of station services or stadium admissions. It counts each person once.
Transfers do not change `total_entered`. The future engine must retain journey
direction and travel completion times internally, even though snapshots
aggregate each node's inventory. It must not send inbound Midtown arrivals
straight to final exit or send outbound travelers back toward the venue.

## Provenance and remaining engine work

Every simulation snapshot is `synthetic`, even when some inputs are derived
from measured data. Averages, queues, percentages, and scores computed from
simulated passengers remain synthetic. Approved historical transformations
remain `derived` in their own data tables and must not be relabeled as
observations of this replay.

Edge and demand assumptions may use `derived` only with a nonempty
`source_reference` documenting a reviewed input transformation. All defaults
here are synthetic. Mixed-source inputs do not make simulated outputs derived.
Keep original `provided`/`web` evidence separate under the shared data contract.

The engine implements integer demand allocation, directional routing, travel-time
batches, queue service, stadium holding/release, scenario modifiers, wait
estimates, and bounded termination. Tests check conservation and capacity
constraints across steps. Queue delay is the sum of post-service queues times
the step duration (person-minutes); overloaded steps have demand above capacity
on at least one edge. Clearance is elapsed time after final whistle until all
return trips finish; it is null when the horizon expires first.

Still to implement: calibration against approved passenger inputs, shared train
resources, richer disruptions, and linkage to commercial and weather evidence.
The UI shows comparative outputs but does not claim physical model validation.
