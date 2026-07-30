# FinalFlow Streamlit Prototype

This folder contains the existing Streamlit application for the project. Preserve `app.py` as the current entry point.

## Current behavior

`app.py` renders a mock operations dashboard with:

- growth trend line chart;
- revenue bar chart;
- channel mix donut chart;
- regional activity line chart;
- conversion-rate line chart;
- campaign-efficiency scatter chart;
- recent mock data table.

The dashboard currently uses hardcoded mock values from `build_mock_dashboard_data()`. It does not read Rice datasets, call OpenAI, call SerpAPI, or connect to a backend.

## Run locally

```bash
cd paddydash
python3 -m pip install -r requirements.txt
streamlit run app.py
```

Current dependency file:

```text
requirements.txt
```

At this stage it only requires Streamlit.

## Future data replacement

Future real data should replace `build_mock_dashboard_data()` through a small data-loading layer instead of spreading file reads throughout UI rendering code.

Recommended approach:

- keep raw datasets outside committed source control;
- load cleaned or summary tables from documented `data/` locations;
- validate required columns before rendering charts;
- keep `provided`, `derived`, `synthetic`, and `web` labels visible in downstream outputs where relevant.

## Folder roles

```text
paddydash/
├── app.py          # Current Streamlit entry point.
├── components/    # Reusable UI rendering helpers when app.py grows.
├── pages/         # Future Streamlit pages.
└── services/      # Data loading, AI/search service wrappers, and API adapters.
```

## Components

Put reusable chart, table, card, or layout helpers in `components/` when they are shared by more than one page or make `app.py` hard to scan. Do not move code only for style preference.

## Services

Put data-loading services in `services/` once real cleaned datasets exist.

Future AI and search wrappers should also live in `services/`, but do not add OpenAI or SerpAPI calls until the backend/API design is ready.

API keys must never appear in browser-visible code, committed files, notebooks, or static exports. Use local `.env` or deployment secret settings, and keep `.env` untracked.

## Collaboration

Hai Nam owns the store-visit analysis and Streamlit prototype direction. Tan Dat will support future weather, SerpAPI, OpenAI-plus-search, and source-display behavior. They should agree on response/source formats before UI integration.

Minh Tue will later receive deployment handoff documentation after the app, backend, environment variables, and run commands are finalized.
