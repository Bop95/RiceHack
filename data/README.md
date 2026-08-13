# FinalFlow Data Workspace

This folder is the planned local workspace for FinalFlow datasets, cleaned outputs, summaries, exports, samples, and generated scenarios.

## Data policy

Raw Rice datasets stay local. Do not commit raw, restricted, sensitive, large, or licensed files unless the team explicitly approves a small public sample.

Use these labels consistently:

- `provided`: original supplied files or approved reference data.
- `derived`: cleaned, joined, summarized, or feature-engineered data created from provided data.
- `synthetic`: generated scenarios or test records.
- `web`: information collected from search or other online sources.

## Folder purposes

```text
data/
├── raw/          # Local provided datasets. Usually not committed.
├── external/     # Local external reference files. Usually not committed.
├── processed/    # Cleaned and standardized derived tables.
├── synthetic/    # Generated scenario and test data.
├── summaries/    # Small summary tables and metrics.
├── exports/      # Power BI-ready or app-ready exports.
└── samples/      # Small approved sample files only.
```

## Expected local raw layout

Do not create fake raw files. When the Rice datasets are available locally, place them like this:

```text
data/raw/rice/
├── daily-spend-brand-and-state-rice/
├── store-visits-rice/
├── daily-weather-rice/
├── spend-patterns-rice/
├── urban-heat-index-rice/
├── core-poi-geometry-rice/
└── WorldCupHack_Dictionary.xlsx
```

## Preferred formats

- Use `.csv` for small readable exports.
- Use `.parquet` for larger analytical tables when supported.
- Use `.geojson` for small map-ready spatial outputs.
- Use `.xlsx` only when needed for Power BI or handoff.
- Avoid committing large generated `.html` files.

## Naming conventions

- Use lowercase folder names.
- Use snake_case filenames for generated data.
- Use descriptive names such as `store_visits_cleaned.csv` or `weather_risk_indicators.csv`.
- Use ISO dates when dates appear in filenames, such as `weather_summary_2026-07-19.csv`.
- Include `data_type` where practical with one of `provided`, `derived`, `synthetic`, or `web`.

## May be versioned

- Small approved sample files in `data/samples/`.
- Small summary tables that are safe to share.
- Power BI or app exports that are explicitly intended for team review.
- Schemas, dictionaries, and documentation.

## Current deployed integration artifacts

The Streamlit release includes these additional compact, derived artifacts:

| File | Grain and purpose |
| --- | --- |
| `summaries/spatial_heat_locations.csv` | One approved non-synthetic POI with aggregated commercial tiers and nearest-UHI evidence per row; 9,889 rows in the exploratory NY/NJ rectangle. |
| `summaries/spatial_heat_locations.metadata.json` | Source and runtime-artifact SHA-256 hashes, source revision, geofence, UHI match rule, aggregation rule, accepted/rejected counts, and missing-evidence count. |
| `summaries/weather_risk_summary.csv` | Eight historical multi-station metrics; every percentage uses station-date observations as its numerator/denominator unit. |
| `summaries/weather_risk_summary.metadata.json` | Source and runtime-artifact hashes, revision, validation counts, station/date coverage, rule version, and limitations. |

The spatial browser artifact intentionally excludes raw spend and raw customer
values. Synthetic and unknown-status POIs are excluded. A missing UHI match is
kept as `Insufficient evidence`, never converted to low heat.

The weather table is historical evidence, not a forecast. Its thresholds, risk
bands, and operational actions are FinalFlow project heuristics. The source has
no approved venue mapping, so the app preserves its reviewed multi-station
scope.

## Should remain local

- Raw Rice datasets.
- Restricted or licensed source data.
- Large processed files.
- Local scratch exports.
- Files containing secrets, API keys, credentials, or private paths.
