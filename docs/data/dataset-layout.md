# Dataset Layout

This document defines the intended data layout for FinalFlow contributors. The folders may be created later as data work begins.

## Raw data policy

Raw Rice datasets should be stored locally and should not be committed unless the team explicitly approves a small public sample. Do not commit restricted data, large files, local exports, or files containing secrets.

Suggested local raw layout:

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

## Planned data areas

```text
data/
├── raw/          # Local provided data, usually not committed.
├── external/     # Local external references, usually not committed.
├── processed/    # Cleaned and standardized derived tables.
├── synthetic/    # Generated scenarios and test records.
├── summaries/    # Small summary tables and metrics.
├── exports/      # Power BI and app-ready exports.
└── samples/      # Small approved sample files only.
```

## Dataset ownership

| Dataset | Primary contributor | Expected outputs |
| --- | --- | --- |
| `daily-spend-brand-and-state-rice` | Phuong Anh and Duc Anh | spend summaries, brand revenue tables, Power BI exports |
| `store-visits-rice` | Hai Nam | cleaned visits, summary tables, plots |
| `daily-weather-rice` | Tan Dat | cleaned weather, risk indicators, weather summary exports |
| `spend-patterns-rice` | Que Anh | spend-pattern summaries and recommendation exports |
| `urban-heat-index-rice` | Que Anh | heat-risk summaries and map-ready tables |
| `core-poi-geometry-rice` | Que Anh | POI and zone reference tables |
| `WorldCupHack_Dictionary.xlsx` | Shared | reference documentation and column definitions |

## Provided, derived, synthetic, and web data

- `provided`: original supplied files.
- `derived`: cleaned, transformed, joined, aggregated, or feature-engineered files.
- `synthetic`: generated scenario files.
- `web`: data gathered from web search or external online sources.

Use the `data_type` field when possible so downstream notebooks, dashboards, and AI responses can tell the difference.

## Preferred formats

- Use `.csv` for small, readable exports.
- Use `.parquet` for larger analytical tables when dependencies support it.
- Use `.geojson` for small spatial exports that need easy inspection.
- Use `.xlsx` only when required for Power BI or stakeholder handoff.
- Avoid committing large generated `.html` files unless they are intentionally reviewed artifacts.

## File naming

Use clear, lowercase, snake_case names:

```text
store_visits_cleaned.csv
weather_risk_indicators.csv
business_features_by_zone.csv
que_anh_spatial_recommendations.csv
power_bi_vendor_zone_export.csv
```

When dates are needed, use ISO format:

```text
weather_summary_2026-07-19.csv
```

## Commit guidance

Generally safe to commit:

- documentation;
- scripts and notebooks without secrets;
- small approved sample files;
- small summary tables intended for review;
- schema and data-contract examples.

Do not commit:

- raw restricted datasets;
- `.env` files;
- `.streamlit/secrets.toml`;
- OpenAI or AWS credentials;
- local virtual environments;
- notebook checkpoints;
- Python cache files;
- large generated exports.
