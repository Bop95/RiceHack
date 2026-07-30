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

## Should remain local

- Raw Rice datasets.
- Restricted or licensed source data.
- Large processed files.
- Local scratch exports.
- Files containing secrets, API keys, credentials, or private paths.
