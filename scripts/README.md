# FinalFlow Scripts

This folder contains small command-line utilities for data preparation, validation, visualization, and scenario support. Scripts should be beginner-friendly, configurable, and safe to run on local files.

## Folder purposes

```text
scripts/
├── data/           # Auditing, cleaning, summaries, and feature builders.
├── synthetic/      # Clearly labeled scenario generators.
├── validation/     # Export and data-contract checks.
└── visualization/  # Future plot and report helpers.
```

## Running scripts

Install the declared dependency and run scripts from the repository root:

```bash
python -m pip install -r requirements.txt
```

```bash
python scripts/data/audit_data.py --help
```

Example audit command:

```bash
python3 scripts/data/audit_data.py \
  --input /local/path/to/dataset.csv \
  --name store-visits-rice \
  --output reports/summaries/store_visits_audit.json
```

Use `--overwrite` only when you intentionally want to replace an existing output file.

The audit tool supports:

- `.csv` files with the Python standard library;
- `.jsonl` and `.ndjson` files with the Python standard library;
- `.parquet` files only when pandas and a Parquet engine are already installed.

Unsupported formats fail with a clear message.

## Script rules

- Use configurable input and output paths.
- Keep raw data unchanged.
- Do not silently overwrite files.
- Do not commit raw Rice datasets, secrets, or local-only paths.
- Avoid third-party imports unless the project already requires them.
- Keep generated outputs clearly labeled as `provided`, `derived`, `synthetic`, or `web`.

## Naming

- Use snake_case Python filenames.
- Use lowercase folder names.
- Use clear output names such as `store_visits_audit.json` or `weather_summary_2026-07-19.csv`.
- Use ISO dates in filenames when dates are needed.

## Current scripts

Implemented:

- `scripts/data/audit_data.py`: audits a local CSV, JSON Lines file, or supported Parquet file and optionally writes a JSON summary.
- `scripts/data/clean_store_visits.py`: streams the complete store-visit CSV/CSV.GZ dataset through DuckDB, writes a cleaned Parquet file, checks data quality, and produces summary tables.
- `scripts/data/build_streamlit_summaries.py`: creates compact monthly brand/category tables for the deployed explorer without making the app scan the full Parquet file.
- `scripts/data/build_spatial_heat_locations.py`: streams the spatial POI/UHI and spending ZIP exports, validates and geofences records, aggregates spend/customer rows by `PLACEKEY`, derives tiers, performs bounded nearest-UHI matching, and writes a privacy-reduced map table plus metadata.
- `scripts/data/build_weather_chat_summaries.py`: validates the cleaned station-date weather table, rejects impossible temperature ordering, computes eight historical risk metrics, and writes the chatbot table plus metadata.
- `scripts/visualization/create_store_visit_charts.py`: builds four static PNG charts, two self-contained interactive Plotly charts, and synchronized interpretation notes from the cleaned store-visit outputs.
- `scripts/synthetic/generate_store_visit_scenarios.py`: reproducibly creates 5,000-20,000 clearly labeled scenario records plus a data dictionary.

Example complete store-visit run:

```bash
python scripts/data/clean_store_visits.py \
  --input /local/path/to/store-visits-rice \
  --output-root data \
  --threads 4 \
  --memory-limit 8GB \
  --temp-limit 20GB
```

Use `--limit 10000` for a fast internally consistent test run. Use `--overwrite`
only to replace this pipeline's existing generated outputs. `--resume` is reserved
for a complete candidate or clean work Parquet left by an interrupted run; the script
verifies the saved source fingerprint, row limit, and high-visit threshold before
reusing it.

The generated outputs are:

- `data/processed/store_visits_clean.parquet`
- `data/summaries/data_quality_report.md`
- `data/summaries/summary_statistics.csv`
- `data/summaries/visit_percentiles.csv`
- five grouped summary CSV files
- `data/summaries/run_metadata.json`

The large clean Parquet, quality report, and run metadata remain local. The small
approved summary tables required by the Streamlit prototype are explicitly
versioned; restricted raw data remains ignored.

Example store-visit visualization run:

```bash
python scripts/visualization/create_store_visit_charts.py
```

The visualization script reads `data/summaries/` plus the clean Parquet file and
writes outputs under `reports/figures/`, `reports/interactive/`, and
`reports/summaries/`. Use `--overwrite` only when intentionally regenerating this
script's existing charts and notes.

Build the deployable monthly explorer summaries and synthetic scenarios with:

```bash
python scripts/data/build_streamlit_summaries.py --overwrite
python scripts/synthetic/generate_store_visit_scenarios.py --overwrite
```

The builder creates monthly explorer summaries and a prepared brand-category
relationship table, scanning the full clean Parquet during preparation only.
The scenario generator defaults to 12,000 rows, seed `2026`, six documented
scenarios, normalized zone effects, observed brand-category pairings,
non-negative values, and the required `synthetic` label.

Build the two collaboration artifacts with explicit local source paths and an
auditable UTC timestamp:

```powershell
.\.venv\Scripts\python.exe scripts\data\build_spatial_heat_locations.py `
  --poi-uhi-zip <path-to-poi_uhi_summary.zip> `
  --spending-zip <path-to-spending_summary.zip> `
  --output data\summaries\spatial_heat_locations.csv `
  --metadata data\summaries\spatial_heat_locations.metadata.json `
  --generated-at 2026-08-12T00:00:00Z

.\.venv\Scripts\python.exe scripts\data\build_weather_chat_summaries.py `
  --input <path-to-daily_weather_clean.csv> `
  --output data\summaries\weather_risk_summary.csv `
  --metadata data\summaries\weather_risk_summary.metadata.json `
  --generated-at 2026-08-12T00:00:00Z
```

The inputs remain local. Each command writes only its compact runtime CSV and
metadata JSON under `data/summaries/`. Review the recorded source hashes and
rejection counts whenever an upstream export changes.
If `--metadata` is omitted, it is derived beside the selected `--output`, so a
redirected test build remains isolated from repository manifests.

Placeholders:

- `scripts/data/clean_weather.py`
- `scripts/data/summarize_weather.py`
- `scripts/data/build_business_features.py`
- `scripts/data/build_weather_features.py` (a future observation-level feature
  pipeline; it is distinct from the implemented compact weather summary builder)
- `scripts/validation/validate_exports.py`

## Adding new scripts

New scripts should include:

- a descriptive module docstring;
- a small `main()` entry point;
- clear command-line arguments;
- validation before writing outputs;
- tests when logic is implemented.
