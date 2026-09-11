# FinalFlow Streamlit Build, Run, and Deployment Guide

This guide explains how to run the FinalFlow prototype and how its Streamlit
site was built. It is written as a learning guide, so it describes both what
each part does and why the project is organized this way.

The current seven-view navigation and export-backed analytical data flow are
documented in [the application README](README.md). The original explorer
walkthroughs below describe retained teammate components: store visits and
commercial scenarios now live inside Commercial & POI Intelligence. Scenario
Lab compares prepared mobility outputs. Shared page/header/assistant metrics
come from the exported profile replay, not the earlier default simulator run.

## 1. Run the app now

Open PowerShell and move to the repository root:

```powershell
cd C:\path\to\RiceHack
```

Install the dependencies if this is the first run or requirements changed:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Disable the first-run email/telemetry prompt for the current PowerShell window:

```powershell
$env:STREAMLIT_BROWSER_GATHER_USAGE_STATS = "false"
```

Start the application using the local `.env` configuration:

```powershell
.\run_finalflow_local.cmd
```

Before the first run, open `.env`, paste the key after `OPENAI_API_KEY=`, and
save the file. The app loads this leader-provided format automatically with
`python-dotenv`. The launcher reads only this Git-ignored file and never asks
for an API key in the terminal. The key remains plaintext on this computer, so
never share the file or remove its Git-ignore rule.

To inspect the complete site without calling OpenAI, use:

```powershell
.\run_finalflow_local.cmd -PreparedDataOnly
```

Streamlit should open the app automatically. If it does not, open:

```text
http://localhost:8501
```

Keep the PowerShell window open while using the app. Press `Ctrl+C` in that
window to stop the server.

### If the virtual environment does not exist

Create it, install the requirements, and then run the app:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\run_finalflow_local.cmd
```

The project currently works with Python 3.12 and Streamlit 1.60.

## 2. What the app contains

The prototype has five pages:

1. **Overview** presents the project scope, summary cards, historical monthly
   activity, leading categories, markets, and limitations.
2. **Store-Visit Explorer** provides rankings, filters, monthly time series,
   category comparisons, weekday patterns, market comparisons, distribution
   percentiles, and the report-ready static plots.
3. **Scenario Explorer** compares six clearly labeled synthetic scenarios using
   scenario, zone, and category filters.
4. **Spatial & Heat Map** displays the bounded derived NY/NJ location table with
   combined filters, heat-evidence states, commercial tiers, and a table
   fallback.
5. **Ask FinalFlow** answers questions from approved prepared data, including
   historical-weather evidence, attaches
   evidence and a related chart, and shows the relevant limitations.

## 3. Overall architecture

The application is split into preparation code and runtime code:

```text
Clean Parquet and Step-2 summaries
                |
                v
Offline preparation scripts
                |
                v
Compact derived and synthetic CSV files
                |
                v
Validated data service -> analytics and chart functions
                |
                v
Five Streamlit pages -> paddydash/app.py
```

This separation matters because the cleaned Parquet is approximately 5.2 GB.
The deployed app should not scan that file whenever a user opens a page.
Instead, expensive aggregation happens offline and Streamlit loads small CSVs.

The primary application structure is:

```text
paddydash/
|-- app.py
|-- pages/
|   |-- overview.py
|   |-- store_visit_explorer.py
|   |-- scenario_explorer.py
|   `-- ask_finalflow.py
|-- components/
|   |-- charts.py
|   `-- ui.py
|-- services/
|   |-- data_service.py
|   |-- analytics.py
|   `-- ai_service.py
|-- README.md
`-- BUILD_GUIDE.md
```

## 4. Preparing compact dashboard data

The standard Step-2 cleaning process produces the clean Parquet and summary
tables. The Streamlit preparation script then creates additional compact tables:

```powershell
.\.venv\Scripts\python.exe scripts\data\build_streamlit_summaries.py --overwrite
```

The script uses DuckDB to read the cleaned Parquet and creates:

- monthly results for the top 50 brands by total transformed visits;
- monthly results for all 132 prepared categories; and
- a brand-category relationship table used during synthetic generation.

The builder uses one DuckDB worker, a 2 GB memory limit, and a disk-backed
temporary directory. This makes the full-data build slower but less likely to
run out of memory. It is an offline preparation step and does not affect normal
Streamlit performance.

The runtime dashboard reads these derived files from `data/summaries/`:

- `summary_statistics.csv`
- `visit_percentiles.csv`
- `visits_by_brand.csv`
- `visits_by_category.csv`
- `visits_by_market.csv`
- `weekday_patterns.csv`
- `monthly_trends.csv`
- `brand_monthly_trends.csv`
- `category_monthly_trends.csv`

Every row is labeled `data_type=derived`. This prevents a prepared aggregation
from being confused with an original raw-data row.

## 5. Creating the synthetic scenarios

The scenario generator is run after the prepared summaries exist:

```powershell
.\.venv\Scripts\python.exe scripts\synthetic\generate_store_visit_scenarios.py --overwrite
```

It generates 12,000 reproducible rows using random seed `2026`. The six
documented scenario multipliers are:

- ordinary day: 1.00x;
- pre-match: 1.25x;
- during match: 0.85x;
- post-match: 1.45x;
- rainy post-match: 1.20x; and
- transit disruption: 1.10x.

The scenario records are constructed as follows:

1. A brand is sampled from the top 25 brands. Square-root total-visit weighting
   gives large brands more representation without letting them dominate every
   row.
2. A category is sampled from that brand's observed category relationships.
   This avoids impossible independent brand-category combinations.
3. A synthetic baseline is calculated from the brand and category mean
   intensities with bounded random variation.
4. The selected scenario multiplier is applied.
5. A zone factor is applied. Zone factors are divided by their mean of 1.175,
   so the expected overall change still matches the documented scenario
   multiplier.
6. Demand, pedestrian-pressure, and mobility-risk labels are calculated.
7. Every row is marked `is_synthetic=true` and `data_type=synthetic`.

The output is deliberately described as interface-testing data rather than a
forecast. Its timestamps are outside the real tournament period, and the app
always displays the synthetic-data disclaimer.

## 6. Loading and validating data

`paddydash/services/data_service.py` is the boundary between CSV files and the
rest of the application.

It defines:

- the required columns for every file;
- which columns must become integers, floats, or booleans;
- the `DashboardData` object used by every page; and
- checks that derived and synthetic labels are not mixed.

The `load_dashboard_data()` function uses `lru_cache`. Therefore, validated
CSVs are loaded once per application process instead of being reread after every
normal Streamlit interaction.

If a file is missing, empty, incorrectly typed, or incorrectly labeled, the app
stops with a useful preparation message rather than silently displaying bad data.

## 7. Building the Streamlit shell

`paddydash/app.py` is the entry point passed to `streamlit run`.

It performs four jobs:

1. Sets the page title, icon, wide layout, and expanded sidebar.
2. Validates that all prepared dashboard data can be loaded.
3. Registers the five page-rendering functions with `st.Page` and
   `st.navigation`.
4. Displays a permanent sidebar reminder that store visits are a proxy and that
   synthetic scenarios are illustrative.

Keeping `app.py` small means the page content can be developed and tested
independently.

## 8. Building the pages

Each file in `paddydash/pages/` contains one main render function.

### Overview

`render_overview()` loads the cached data and builds:

- five `st.metric` summary cards;
- a segmented control for switching the monthly metric;
- a Plotly monthly trend;
- category and market comparison charts; and
- an expandable dataset-quality section.

The wording uses **total transformed visits** because the source field is a
privacy-preserving transformed measure rather than a literal head count.

### Store-Visit Explorer

`render_store_visit_explorer()` uses Streamlit tabs to keep six analyses on one
page. Controls such as `selectbox`, `slider`, `radio`, and `multiselect` select
the dimension, metric, number of ranked rows, brands or categories, and years.

The controls change the Python arguments sent to reusable chart functions.
Streamlit reruns the page after a selection, while its widget state and cached
data make the interaction feel immediate.

### Scenario Explorer

`render_scenario_explorer()` filters the 12,000 synthetic rows by scenario,
zone, and category. It recalculates the displayed baseline, estimate, uplift,
and high-risk share from only the filtered records. A caption explicitly tells
the user how many records are represented by the current cards and charts.

### Ask FinalFlow

`render_ask_finalflow()` provides suggested-question buttons and a chat input
limited to 500 characters. Chat history is stored in `st.session_state`, so it
survives Streamlit reruns in the current browser session.

Each response contains:

- a concise answer;
- a `derived` or `synthetic` data label;
- validated evidence with source filenames;
- material limitations; and
- a related Plotly chart when applicable.

Questions outside the supported store-visit scope are declined instead of being
routed to a general-purpose chatbot.

## 9. Reusable interface and chart components

`paddydash/components/ui.py` contains repeated interface elements:

- data-type labels;
- observation, project-value, and limitation cards;
- evidence tables; and
- consistent page introductions.

`paddydash/components/charts.py` contains all interactive Plotly figures. A
shared layout function gives them consistent fonts, margins, colors, legends,
and hover behavior. Individual functions handle rankings, monthly trends,
category scatter, weekday activity, markets, percentiles, scenario comparisons,
and risk labels.

Two important encoding choices are:

- category bubble area and color represent total transformed visits; and
- the percentile chart uses a logarithmic y-axis because the visit distribution
  is strongly right-skewed.

Separating chart construction from page layout makes the same chart reusable in
the Explorer and in a chatbot response.

## 10. How the grounded chatbot works

The chatbot is intentionally split into deterministic analytics and optional AI
narration.

`paddydash/services/analytics.py` first classifies the question into a supported
route such as brand, category, weekday, market, time, or scenario. It then:

1. runs a controlled function against prepared data;
2. creates a small text context;
3. creates evidence items from known values;
4. selects a related plot ID; and
5. attaches the applicable limitations.

When two scenarios are named, only those named scenarios are placed into the
comparison context and evidence.

`paddydash/services/ai_service.py` optionally sends that restricted context to
the OpenAI Responses API from the server. The API key is never placed in browser
code. The model returns only a structured narrative; evidence, data labels, and
plot selection remain controlled by local Python code.

The hosted app applies a configurable best-effort allowance to OpenAI calls from
each browser session. Its default is 10 calls. This reduces accidental spending,
but it is not a replacement for OpenAI project budgets, rate limits, and access
control on a public application.

If no API key is present, or if the request fails, the same page shows the
deterministic prepared-data answer.

### Enable optional OpenAI narration locally

Set the variables in the same PowerShell window before launching Streamlit:

```powershell
$env:OPENAI_API_KEY = "your-key-here"
$env:OPENAI_MODEL = "gpt-5.6-luna"
$env:FINALFLOW_MAX_AI_REQUESTS_PER_SESSION = "10"
.\.venv\Scripts\python.exe -m streamlit run paddydash\app.py
```

Never commit a real key. Without these variables, the application remains fully
usable in prepared-data mode.

## 11. Testing

Run the complete test suite from the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The tests verify:

- cleaning and summary behavior;
- dashboard file schemas and data labels;
- deterministic scenario generation;
- scenario multiplier accuracy;
- valid brand-category pairs;
- named-scenario chatbot comparisons;
- spatial/weather builder validation, geofencing, and missing-evidence handling;
- historical-weather routing, exact station-date units, and forecast refusal;
- out-of-scope handling;
- the mocked OpenAI request and safe fallback;
- reviewed Plotly encodings; and
- successful rendering of all five Streamlit pages.

## 12. Common changes you may want to make

### Add a chart

1. Add a figure function to `paddydash/components/charts.py`.
2. Pass it validated rows from a page.
3. Render it with `st.plotly_chart`.
4. Add a small test for the important encoding or expected trace.

### Add a new prepared data file

1. Generate the compact file in an offline script.
2. Add its schema to `SCHEMAS` in `data_service.py`.
3. Add it to `DashboardData` and `load_dashboard_data()`.
4. Confirm its `data_type` label.
5. Add a loader test before using it on a page.

### Add or change a scenario

1. Update `SCENARIOS` in the scenario generator.
2. Regenerate the scenario CSV and dictionary.
3. Check that the realized aggregate uplift matches the documented multiplier.
4. Run the complete tests.

### Add a chatbot topic

1. Add a controlled analytics function.
2. Add a question route in `retrieve_for_question()`.
3. Attach evidence, limitations, and an approved related plot ID.
4. Add tests for the intended question and misleading variations.

## 13. Troubleshooting

### Streamlit asks for an email and then aborts

Set the telemetry option before starting it:

```powershell
$env:STREAMLIT_BROWSER_GATHER_USAGE_STATS = "false"
.\.venv\Scripts\python.exe -m streamlit run paddydash\app.py
```

### The app says a prepared file is missing

Confirm that you are on `main` or a feature branch created from it and are
running from the repository root. The compact CSV files are included with this
work. If you intentionally removed them, recreate the Step-2 outputs and then
run both preparation commands from Sections 4 and 5.

### PowerShell reports that a module is missing

Install the root requirements into the same interpreter used to run Streamlit:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Port 8501 is already in use

Run on another port:

```powershell
.\.venv\Scripts\python.exe -m streamlit run paddydash\app.py --server.port 8502
```

Then open `http://localhost:8502`.

## 14. Deploying the hosted application

For Streamlit Community Cloud:

1. Merge the approved pull request into the protected `main` branch.
2. Create a Streamlit Community Cloud app from the repository.
3. Select branch `main`.
4. Set the entry point to `paddydash/app.py`.
5. Add `OPENAI_API_KEY`, `OPENAI_MODEL`, and
   `FINALFLOW_MAX_AI_REQUESTS_PER_SESSION` in Advanced settings under Secrets.
6. Keep the first deployment private while testing if your Community Cloud
   workspace supports private-app access.
7. Deploy and test every page, every suggested question, and the evidence shown
   under each answer.

The root `requirements.txt` contains the Streamlit, Plotly, OpenAI, Pydantic,
DuckDB, and report-generation dependencies needed by this repository.

The full click-by-click deployment and security procedure is in
`paddydash/DEPLOYMENT_GUIDE.md`.
