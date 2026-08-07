# FinalFlow Streamlit Application

For a step-by-step explanation of how the site was created, how each layer
works, and how to modify it, see `paddydash/BUILD_GUIDE.md`.

This application implements the four-page store-visit prototype described in
Hai Nam's project guide. It uses compact approved summaries and a modest,
explicitly synthetic scenario dataset; it never loads the restricted raw files or
the 5.2 GB clean Parquet at runtime.

## Pages

1. **Overview** - project scope, summary cards, monthly trend, leading categories,
   market intensity, and dataset limitations.
2. **Store-Visit Explorer** - brand/category rankings and filters, interactive
   brand/category monthly time series, category scatter, weekdays, markets,
   distribution percentiles, and the four report-ready static plots.
3. **Scenario Explorer** - filters and charts for six reproducible synthetic
   interface-testing scenarios with the required disclaimer.
4. **Ask FinalFlow** - suggested questions, chat input, grounded answers,
   supporting evidence, related charts, data-type labels, limitations, loading,
   and friendly fallback errors.

## Data boundary

The app reads only these deployable files:

```text
data/summaries/
├── summary_statistics.csv
├── visit_percentiles.csv
├── visits_by_brand.csv
├── visits_by_category.csv
├── visits_by_market.csv
├── weekday_patterns.csv
├── monthly_trends.csv
├── brand_monthly_trends.csv
└── category_monthly_trends.csv

data/synthetic/
├── store_visit_scenarios.csv
└── store_visit_scenarios_dictionary.md
```

Derived summary rows are labeled `derived`. Scenario rows are labeled
`synthetic` and set `is_synthetic=true`.

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

The tests cover data contracts, controlled analytics, deterministic scenario
generation, evidence-based fallback responses, and all four Streamlit pages.

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
- A standalone `/api/chat` endpoint and TypeScript frontend are later project
  stages; this prototype's secure backend function runs inside Streamlit.
