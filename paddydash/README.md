# FinalFlow Streamlit Application

> **Demo rule:** mobility metrics are derived from synthetic scenario inputs;
> historical commercial/weather context and current web sources keep their own
> provenance and must not be presented as observed match-day operations.

For a step-by-step explanation of how the site was created, how each layer
works, and how to modify it, see `paddydash/BUILD_GUIDE.md`.

This application implements a seven-page FinalFlow prototype. It uses compact
approved store-visit and historical-weather summaries, a bounded derived
spatial/urban-heat table, and an explicitly synthetic scenario dataset; it never
loads the restricted raw files or the 5.2 GB clean Parquet at runtime.

## Pages

1. **Executive Overview** (default): selected queue, utilization, wait, clearance,
   bottleneck, contextual evidence and deterministic recommended actions.
2. **Matchday Timeline**: canonical phase markers, a synchronized phase selector,
   calculated queues over time and selected-edge throughput.
3. **Mobility & Access**: corridor reference map, node queues and flow direction,
   edge throughput, baseline comparison and first/last-mile indicators.
4. **Commercial & POI Intelligence**: retained store-visit filters and charts,
   filtered exploratory POI/heat map, and separate synthetic placement examples
   and commercial scenario exploration.
5. **Weather & Heat**: historical risk and monthly weather charts, heat/location
   map, and rain-versus-baseline effects calculated from prepared mobility data.
6. **Scenario Lab**: five mobility alternatives, signed metric comparisons,
   evaluated interventions and a separate catalog of unevaluated suggestions.
7. **Ask FinalFlow**: grounded explanations of the same selected export-backed
   facts, historical context and separate web sources when explicitly requested.

## Shared match state

The global controls use canonical phase/scenario IDs from the
[mobility contract](../docs/project/mobility-contract.md). Existing business,
store-visit, spatial/heat and assistant features retain their historical data.
They are not silently filtered or reinterpreted as match-day measurements.

Session keys available to future integrations:

- `finalflow_phase_id`, `finalflow_scenario_id`: current canonical selection.
- `selected_phase_id`, `selected_scenario_id`: synchronized aliases.
- `finalflow_time_minutes`: elapsed replay minute shared across every page.
- `finalflow_mobility_snapshot`: derived exported node/edge snapshot, set by Mobility.

Phase changes reset the replay minute; scenario changes preserve valid times.
Shared facts are read from exports, never from a saved snapshot. The replay
slider moves within intervals; event markers use their exact
times. The pre-match preview starts during arrivals; the post-match preview is
30 minutes after final whistle. Markers at the same timestamp intentionally share
the same passenger state.

The existing engine in `services/mobility_simulator.py` produces the prepared
profile exports offline. The dashboard does not invoke the older default replay
as a fallback. Current node/edge values come from the selected scenario and
five-minute timestamp; whole-run metrics come from `scenario_summary.csv`.
All are **derived from synthetic scenario inputs**, never real-time observations.
Queue means residual waiting people, excluding stadium holding. Utilization is
service throughput/capacity, not unconstrained demand. Clearance is the whole-run
duration after final whistle, not time remaining. Mode totals count inbound and
outbound passenger movements, not unique spectators.

Rules in `recommendation_catalog.csv` produce scoped review prompts, not optimal
or safety-approved actions. Missing evidence never triggers a rule. Missing
exports disable dependent sections without synthesizing replacement numbers.
Zero baseline percentages are unavailable; ties and unchanged results are explicit.

Run locally from the repository root:

```bash
FINALFLOW_DISABLE_OPENAI=true FINALFLOW_DISABLE_SEARCH=true python3 -m streamlit run paddydash/app.py
python3 -m unittest discover -s tests -p 'test_mobility*.py' -v
```

## Data boundary

The app reads compact prepared tables, including these historical sources:

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
|-- store_visit_scenarios_dictionary.md
|-- corridor_reference.csv
`-- transit_service_capacity.csv

data/exports/
|-- executive_kpis.csv
|-- match_timeline_summary.csv
|-- mobility_node_timeseries.csv
|-- mobility_edge_timeseries.csv
|-- mobility_access_summary.csv
|-- scenario_summary.csv
|-- scenario_comparison.csv
|-- intervention_comparison.csv
|-- recommendation_catalog.csv
|-- commercial_context.csv
`-- weather_heat_context.csv

notebooks/tan-dat/data/summaries/weather_monthly.csv
notebooks/duc-anh/data_clean/finalflow_business_integration.csv
```

Derived summary rows are labeled `derived`. Store-visit scenario rows set
`is_synthetic=true`; vendor examples use `data_type=synthetic` and
`data_confidence=scenario` with explicit assumptions.

Historical weather is pooled multi-station context, not a venue forecast.
Monthly precipitation is a sum across source observations. Mean visibility
distance and shuttle utilization remain unavailable; the reviewed low-visibility
observation share is available. Spatial tiers and nearby UHI require
site review; synthetic corridor coordinates are approximate references.
No new datasets or calibrated operational claims are introduced by these pages.

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
OPENAI_MODEL=gpt-5
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
seven Streamlit pages.

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

## Ask FinalFlow

The seventh view uses `services/project_context.py` to retrieve compact prepared
facts and `services/ai_service.py` for the optional official OpenAI SDK Responses
API (`responses.parse`, Pydantic narrative schema). No CSV is sent in full.
Selected phase/scenario/replay time scope each answer. Explicit final-whistle,
rain, disruption, or staggered-departure questions resolve their own scope without
changing the dashboard selection. Saved answers retain their original scope.

The application response includes `answer`, `key_findings`, `recommendations`,
`evidence` (`label`, `value`, `source`, `data_type`), `limitations`, and
`related_plot_id`. Evidence, findings, actions and plot IDs are attached locally,
not entrusted to model generation. The factual guard accepts only the prepared
narrative (whitespace changes allowed); other wording falls back to the local
answer. This intentionally limits free-form AI interpretation until semantic
validation is available. Missing or malformed provider responses silently
preserve the verified answer rather than surfacing provider failures to a user.

Sources are node/edge time series, scenario summaries, recommendation rules,
commercial/weather summaries, and the AI context/executive baseline references
for provenance questions. Historical context is not a venue forecast; mobility
results are derived from synthetic inputs. Current web requests remain separate.
Historical chart questions use the retained deterministic analytics handlers.

Requests allow 500 question characters, at most 18,000 combined project/web context/answer
characters, and 500 output tokens. Oversized context uses the local answer without
calling OpenAI. Only the current question/context is sent, not conversation history.
The browser retains the last 20 exchanges. Clear conversation preserves the global
replay selection and request allowance. Keys and model configuration remain server-only.

For a manual provider test, configure `OPENAI_API_KEY` in the ignored root `.env`,
optionally set `OPENAI_MODEL` to an account-supported structured-output model,
and set `FINALFLOW_DISABLE_OPENAI=false`. Leave search disabled unless testing it:

```bash
FINALFLOW_DISABLE_SEARCH=true .venv/bin/python -m streamlit run paddydash/app.py
```

Select Ask FinalFlow, ask about the final-whistle bottleneck, switch scenario,
and compare a new answer with the retained earlier scope. With no key or with
`FINALFLOW_DISABLE_OPENAI=true`, the same deterministic facts remain available.
Provider access/model availability have not been verified through live calls.

### Current public information

`services/search_service.py` is shared with Tan Dat's backend compatibility import;
there is no second search client. `should_search()` requires an explicit recency
term (current/latest/today/live/recent/new/now) and a transit, weather, or venue-access
topic. Project terms (scenario, queue, bottleneck, chart, modeled/prepared data,
staggered departure) and explicit no-search instructions take precedence. Split
mixed project/current-public questions into separate messages to request both.

Up to five SerpAPI organic results are normalized to `title`, `link`, `source`,
`snippet`, and nullable `date`. Missing source names use the URL hostname. Source
fields are bounded; malformed, oversized, or credential-bearing responses fail
closed. Search uses a five-second timeout and the existing ten-request session cap.
The legacy `summarize=True` option and summary helper are compatibility no-ops:
they never launch a separate unguarded OpenAI request.

Normalized results accompany the current question and project context in the
single guarded Responses request. They are marked as untrusted web evidence.
The structured application response retains `web_sources`, `search_used`, and
`web_status` (`available`, `no_results`, or `unavailable`), including on AI failure.
Project Evidence and Web Sources render separately; clickable source titles,
source/domain, excerpts, and supplied dates remain visible without OpenAI.
The factual guard does not permit free-form web synthesis to rewrite project facts.
Snippets are excerpts, not independently verified live alerts; dates may be missing,
sources may disagree, and no-results does not mean there are no disruptions.

For a manual live-provider test, configure both `OPENAI_API_KEY` and
`SERPAPI_API_KEY` in the ignored root `.env` (backend-only; never browser code),
then run:

```bash
FINALFLOW_DISABLE_OPENAI=false FINALFLOW_DISABLE_SEARCH=false \
  .venv/bin/python -m streamlit run paddydash/app.py
```

1. Ask about the rail-disruption bottleneck: no Web Sources section is added.
2. Ask "Are there current NJ Transit disruptions?": check the Web search used
   badge and separate source cards. Follow the issuing authority's notice to verify.
3. Ask for the latest weather alert or new venue access announcements.
4. Restart with search disabled: current questions show Live web search unavailable
   while project answers continue. Disable OpenAI alone to check source cards still work.

These commands enable live, potentially billable calls. Automated tests mock all providers.

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
