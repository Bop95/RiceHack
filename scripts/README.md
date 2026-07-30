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

These derived outputs remain local and ignored by Git until the team explicitly
approves sharing them.

Placeholders:

- `scripts/data/clean_weather.py`
- `scripts/data/summarize_weather.py`
- `scripts/data/build_business_features.py`
- `scripts/data/build_weather_features.py`
- `scripts/synthetic/generate_store_visit_scenarios.py`
- `scripts/validation/validate_exports.py`

## Adding new scripts

New scripts should include:

- a descriptive module docstring;
- a small `main()` entry point;
- clear command-line arguments;
- validation before writing outputs;
- tests when logic is implemented.
