# Data Contracts

This document defines shared labels and fields for FinalFlow data products and
the implemented assistant response contract. Runtime CSV schemas are enforced
in `paddydash/services/data_service.py`.

## Data type labels

Use these labels consistently:

- `provided`: original source data supplied to the project, including approved raw or reference data.
- `derived`: cleaned, transformed, summarized, joined, or feature-engineered data created from provided data.
- `synthetic`: generated data created for scenario testing, demos, stress tests, or gap filling.
- `web`: information retrieved from web search or external online sources.

Do not mix these labels with alternative names such as `raw`, `generated`, `external`, or `internet` in shared outputs. If more detail is needed, add a separate notes column.

## Suggested shared fields

Use these fields where they fit the table:

| Field | Purpose |
| --- | --- |
| `data_type` | One of `provided`, `derived`, `synthetic`, or `web`. |
| `source_file` | Original file path or source name used to create the record. |
| `generated_at` | Timestamp for generated outputs, preferably ISO 8601. |
| `scenario_id` | Identifier for synthetic or scenario-specific records. |
| `zone_id` | Stable zone, station, venue, POI, or analysis-area identifier. |
| `location_name` | Human-readable location name. |
| `latitude` | Decimal latitude when point geometry is available. |
| `longitude` | Decimal longitude when point geometry is available. |

## Naming guidance

- Use lowercase folder names.
- Use hyphens for contributor folders.
- Use snake_case for Python files and generated table names.
- Use ISO date format where dates appear in filenames or data fields.
- Keep `provided`, `derived`, `synthetic`, and `web` labels exact.

## Implemented assistant response contract

`ChatResponse.to_dict()` returns this shape:

```json
{
  "answer": "...",
  "evidence": [],
  "relatedPlotId": null,
  "dataType": "derived",
  "limitations": [],
  "mode": "prepared-data"
}
```

Field meanings:

- `answer`: concise user-facing answer.
- `evidence`: project data rows, snippets, metrics, or references used to support the answer.
- `relatedPlotId`: optional plot identifier for a related visualization.
- `dataType`: highest-risk or primary source type used in the answer.
- `limitations`: known caveats, missing data, assumptions, or uncertainty.
- `mode`: `prepared-data` or `openai`.

Each evidence item contains `label`, `value`, and `source`. The current
application does not retrieve web results and therefore has no `webSources`
field.

## Implemented spatial/heat runtime contract

`data/summaries/spatial_heat_locations.csv` contains one derived,
non-synthetic place per row. Public runtime fields include stable location
identity, name, market/city/region, coordinates, category, parking status,
commercial/customer tiers, optional nearest UHI and distance, evidence status,
heat concern, recommendation, reason, provenance, and generation time.

Contract rules:

- coordinates are within the exploratory rectangle 40.4-41.1 latitude and
  -74.5--73.5 longitude;
- spend and customer rows are summed by `PLACEKEY` before tiers are derived;
- raw spend and raw customer values are not shipped to the browser;
- source rows marked synthetic or with unknown synthetic status are excluded;
- nearest UHI uses WGS84 haversine distance with a 250 m maximum; and
- missing UHI must use `evidence_status=insufficient` and
  `heat_concern=Insufficient evidence`.

The companion metadata JSON records source revisions/hashes, aggregation and
matching rules, bounds, accepted/rejected counts, reasons, and missing-UHI count.

## Implemented weather runtime contract

`data/summaries/weather_risk_summary.csv` contains one derived historical
metric per row. Its contract fields include metric/scope identity, period,
month window, `observation_unit`, numerator, denominator, percentage, threshold,
recommended action, risk-rule version, provenance, generation time, and
limitation.

Contract rules:

- percentages are `100 * numerator / denominator`, rounded to two decimals;
- `station_date_observation` means a station-date observation, never a calendar
  day, person, event, location, or forecast probability;
- historical multi-station scope cannot be narrowed to a venue;
- temperature, precipitation, wind, and visibility units and threshold
  directions must not be altered;
- thresholds, risk bands, and actions are FinalFlow project heuristics; and
- answers preserve the `derived` versus `synthetic` distinction.

## Mobility simulation contract

The [mobility contract](mobility-contract.md) defines typed corridor nodes and
edges, canonical match phases/scenarios, demand assumptions, and simulation
snapshots in `paddydash/services/mobility_contract.py`. The central illustrative
configuration is `paddydash/services/mobility_config.py`; the bounded engine is
`paddydash/services/mobility_simulator.py`. Simulation outputs remain `synthetic` even when
reviewed inputs are `derived`; passenger counts are not observed event data.

## Source discipline

AI responses should distinguish project data from web results. Web results should not overwrite project data. Synthetic scenarios should always be labeled as `synthetic` and should not be presented as observed behavior.
