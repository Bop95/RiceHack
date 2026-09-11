# FinalFlow Streamlit Application

For a step-by-step explanation of how the site was created, how each layer
works, and how to modify it, see `paddydash/BUILD_GUIDE.md`.

This application implements a seven-page FinalFlow prototype. It uses compact
approved store-visit and historical-weather summaries, a bounded derived
spatial/urban-heat table, and an explicitly synthetic scenario dataset; it never
loads the restricted raw files or the 5.2 GB clean Parquet at runtime.

## Pages

1. **Mobility readiness** (default) - shared match timeline and scenario controls,
   modeled queues, utilization, waits, corridor bottlenecks, and baseline comparison.
2. **Overview** - project scope, summary cards, monthly trend, leading categories,
   market intensity, and dataset limitations.
3. **Store-Visit Explorer** - brand/category rankings and filters, interactive
   brand/category monthly time series, category scatter, weekdays, markets,
   distribution percentiles, and the four report-ready static plots.
4. **Scenario Explorer** - filters and charts for six reproducible synthetic
   interface-testing scenarios with the required disclaimer.
5. **Spatial & Heat Map** - an interactive NY/NJ exploratory map with city,
   category, heat, recommendation, and parking filters; commercial tiers;
   nearest-UHI evidence; and a table fallback.
6. **Ask FinalFlow** - suggested questions, chat input, grounded answers,
   supporting evidence, related charts, data-type labels, limitations, loading,
   friendly fallback errors, and reviewed historical-weather retrieval.
7. **Commercial & weather context** - visit trends, POI spending tiers, parking
   flags, historical weather and heat, plus separately labeled vendor scenarios.

## Shared match state

The global controls use canonical phase/scenario IDs from the
[mobility contract](../docs/project/mobility-contract.md). Existing business,
store-visit, spatial/heat and assistant features retain their historical data.
They are not silently filtered or reinterpreted as match-day measurements.

Session keys available to future integrations:

- `finalflow_phase_id`, `finalflow_scenario_id`: current canonical selection.
- `finalflow_time_minutes`: selected elapsed replay minute, when mobility is rendered.
- `finalflow_mobility_snapshot`: JSON-compatible validated synthetic snapshot.

Changing the controls invalidates the old snapshot/time until the mobility page
renders the new selection. Consumers must handle their absence, not reuse stale
results. The replay slider moves within intervals; event markers use their exact
times. The pre-match preview starts during arrivals; the post-match preview is
30 minutes after final whistle. Markers at the same timestamp intentionally share
the same passenger state.

The small deterministic engine in `services/mobility_simulator.py` uses no raw
files or provider calls. It assumes one linear round-trip cohort and independent
directed capacities, and caches five immutable default runs. All readiness
metrics are **Scenario / modeled**, never observed real-time values. The
capacity-boost scenario may show no benefit when baseline demand is already
below capacity. Staggering may lengthen clearance while reducing release pressure.

Run locally from the repository root:

```bash
FINALFLOW_DISABLE_OPENAI=true FINALFLOW_DISABLE_SEARCH=true python3 -m streamlit run paddydash/app.py
python3 -m unittest discover -s tests -p 'test_mobility*.py' -v
```

## Data boundary

The app reads only these deployable files:

```text
data/summaries/
|-- summary_statistics.csv
|-- visit_percentiles.csv
|-- visits_by_brand.csv
|-- visits_by_category.csv
|-- visits_by_market.csv
|-- weekday_patterns.csv
|-- monthly_trends.csv
|-- brand_monthly_trends.csv
|-- category_monthly_trends.csv
|-- spatial_heat_locations.csv
|-- spatial_heat_locations.metadata.json
|-- weather_risk_summary.csv
`-- weather_risk_summary.metadata.json

data/synthetic/
|-- store_visit_scenarios.csv
`-- store_visit_scenarios_dictionary.md

notebooks/tan-dat/data/summaries/weather_monthly.csv
notebooks/duc-anh/data_clean/finalflow_business_integration.csv
```

Derived summary rows are labeled `derived`. Store-visit scenario rows set
`is_synthetic=true`; vendor examples use `data_type=synthetic` and
`data_confidence=scenario` with explicit assumptions.

## Install and run

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\run_finalflow_local.cmd
```

Before the first run, open `.env` in a text editor, paste the key after
`OPENAI_API_KEY=`, and save the file. The application loads this leader-provided
configuration format automatically with `python-dotenv`. The launcher never
accepts an API key through the terminal. Later runs reuse `.env` and open
`http://localhost:8501` without asking again.

To run without making OpenAI requests:

```powershell
.\run_finalflow_local.cmd -PreparedDataOnly
```

## Rebuild the app data

After the Step-2 clean dataset and standard summary tables exist, create the two
compact explorer tables plus the brand-category relationship table used only
to generate realistic synthetic pairs:

```powershell
.\.venv\Scripts\python.exe scripts\data\build_streamlit_summaries.py --overwrite
```

Generate the reproducible 12,000-row scenario file and dictionary:

```powershell
.\.venv\Scripts\python.exe scripts\synthetic\generate_store_visit_scenarios.py --overwrite
```

The preparation build scans the clean Parquet for the two monthly dimensions
and the brand-category mix. The Streamlit app itself does not perform those scans.

Build the compact spatial table from Quế Anh's two ZIP exports without
extracting or committing the source archives:

```powershell
.\.venv\Scripts\python.exe scripts\data\build_spatial_heat_locations.py `
  --poi-uhi-zip <path-to-poi_uhi_summary.zip> `
  --spending-zip <path-to-spending_summary.zip> `
  --output data\summaries\spatial_heat_locations.csv `
  --metadata data\summaries\spatial_heat_locations.metadata.json `
  --generated-at 2026-08-12T00:00:00Z
```

Build the historical weather summary from Tấn Đạt's cleaned observation table:

```powershell
.\.venv\Scripts\python.exe scripts\data\build_weather_chat_summaries.py `
  --input <path-to-daily_weather_clean.csv> `
  --output data\summaries\weather_risk_summary.csv `
  --metadata data\summaries\weather_risk_summary.metadata.json `
  --generated-at 2026-08-12T00:00:00Z
```

Both commands write a compact CSV plus JSON metadata with source and artifact hashes,
revision, counts, rejected-row reasons, scope, and rule version. Use an explicit
UTC `--generated-at` value so regeneration is auditable. The spatial export
omits raw spend/customer values and excludes synthetic or unknown-status POIs.
When `--metadata` is omitted, each builder derives it beside `--output` as
`<output stem>.metadata.json`; redirected test builds cannot overwrite the
repository manifest accidentally.

## Server-side OpenAI mode

The browser never receives the API key and never calls OpenAI directly. The
server-side service in `paddydash/services/ai_service.py` retrieves a small,
question-relevant prepared-data context and uses the Responses API to produce a
structured narrative. Evidence, data labels, limitations, and related plot IDs
remain controlled by local analytics code.

Set these server-side environment variables:

```text
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-5.6-luna
FINALFLOW_MAX_AI_REQUESTS_PER_SESSION=10
```

`FINALFLOW_DISABLE_OPENAI=true` forces prepared-data mode for CI or an emergency
cost-control fallback. See the root README and `.env.example` for the complete
environment contract.

Do not commit `.env`. When no key is configured, the same chat interface returns
deterministic prepared-data answers and explains the mode to the user.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The tests cover data contracts, deterministic builders, controlled analytics,
weather routing and forecast refusal, evidence-based fallback responses, and all
five Streamlit pages.

## Hosted Streamlit Community Cloud deployment

Create an app from the GitHub repository, select branch `main`, and use:

```text
paddydash/app.py
```

Add `OPENAI_API_KEY`, `OPENAI_MODEL`, and
`FINALFLOW_MAX_AI_REQUESTS_PER_SESSION` in the deployment's Advanced settings
under Secrets. The prepared-data fallback works without an API key. See
`paddydash/DEPLOYMENT_GUIDE.md` for the complete account, security, deployment,
and verification sequence.

## Known limitations

- Store visits are a commercial-activity proxy, not attendance or pedestrian flow.
- The data covers historical 2020-2024 activity and does not prove causes.
- Brand monthly filters intentionally cover the top 50 brands by total transformed visits;
  category monthly filters cover all 132 prepared categories.
- Synthetic scenario multipliers are illustrative interface-testing assumptions;
  zone weights are normalized so each multiplier remains its expected effect.
- The spatial page uses an exploratory rectangle (40.4-41.1 latitude,
  -74.5--73.5 longitude), not an approved venue polygon.
- Missing UHI is labeled `Insufficient evidence`; heat thresholds and actions
  are FinalFlow heuristics.
- Weather percentages count historical station-date observations from a
  multi-station dataset. They are not live forecasts or venue-specific claims.
- A standalone `/api/chat` endpoint and TypeScript frontend are later project
  stages; this prototype's secure backend function runs inside Streamlit.

## Teammate evidence layer

The Commercial & weather context page combines prepared visit trends, reviewed
POI/spending tiers, historical weather and heat, with separately labeled synthetic
vendor examples. The assistant retains the selected replay scope and separates
web sources from project evidence. See the
[integration inventory and limitations](../docs/project/teammate-evidence-integration.md).
