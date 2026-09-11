<p align="center">
  <img src="asset/rice_hack.png" alt="Rice Hack banner" width="100%">
</p>

<h1 align="center">FinalFlow</h1>

<p align="center">
  <strong>Match-Synchronized Mobility Readiness for the 2026 World Cup Final</strong><br>
  Midtown Manhattan → Penn Station → Secaucus Junction → Meadowlands Station → Stadium
</p>

<p align="center">
  <a href="#run-the-demo">Run the demo</a> ·
  <a href="#seven-page-journey">Explore the app</a> ·
  <a href="#data-and-provenance">Understand the data</a> ·
  <a href="#documentation">Read the guides</a>
</p>

![FinalFlow interface preview](asset/finalflow.jpeg)

> **Scenario-planning tool, not a real-time operations system.** FinalFlow makes
> synthetic event-day assumptions explicit, calculates their consequences, and
> keeps historical and web evidence visibly separate.

## The Decision Story

FinalFlow models a hypothetical Spain versus Argentina final at New York New
Jersey Stadium. A judge or planner can choose a match phase and scenario, trace
pressure along the five-node corridor, compare interventions, then inspect the
weather and commercial context behind a decision.

```text
Match phase + scenario
          │
          ▼
Synthetic demand and capacity assumptions
          │
          ▼
Derived queues, waits, utilization and clearance
          │
          ├──────────────► Weather / heat context
          ├──────────────► Commercial / POI context
          └──────────────► Grounded FinalFlow explanation
```

The mobility replay is intentionally explainable: five-minute intervals,
transparent capacities, canonical match phases, and deterministic derived
outputs. It is not calibrated to official event passenger counts.

## Seven-Page Journey

| View | Decision it supports | Primary evidence |
| --- | --- | --- |
| **Executive Overview** | What needs attention now? | Current derived queue, utilization, wait, clearance, and scoped actions |
| **Matchday Timeline** | When does pressure change? | Canonical phase markers and queue/throughput time series |
| **Mobility & Access** | Where is the corridor constrained? | Node queues, edge throughput, first/last-mile indicators, approximate corridor reference |
| **Commercial & POI Intelligence** | Where should activity be encouraged, controlled, or avoided? | Historical visit context, POIs, heat context, labeled synthetic placement examples |
| **Weather & Heat** | How do rain and heat change operating conditions? | Historical station context, heat locations, and derived rain comparisons |
| **Scenario Lab** | Which intervention changes the modeled outcome? | Baseline, disruption, capacity boost, rain, and staggered-departure comparisons |
| **Ask FinalFlow** | Why did this recommendation change? | Deterministic project evidence, optional OpenAI wording, and separate current web sources |

## Run the Demo

The dashboard is a single Streamlit application at `paddydash/app.py`. It runs
fully without API keys in deterministic prepared-data mode.

### macOS or Linux

```bash
cd /Users/macbook/Hack/RiceHack
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
FINALFLOW_DISABLE_OPENAI=true FINALFLOW_DISABLE_SEARCH=true \
  python3 -m streamlit run paddydash/app.py
```

Open <http://localhost:8501>.

### Windows PowerShell

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\run_finalflow_local.cmd -PreparedDataOnly
```

### Optional AI and current-public-information mode

Copy the secret-free template, add server-side keys locally, then restart the
application:

```bash
cp .env.example .env
```

| Variable | Role | Default |
| --- | --- | --- |
| `OPENAI_API_KEY` | Optional server-side narration | unset |
| `OPENAI_MODEL` | Responses API model | `gpt-5` |
| `SERPAPI_API_KEY` | Optional current-public-information search | unset |
| `FINALFLOW_DISABLE_OPENAI` | Disables model calls for CI/offline demos | `false` |
| `FINALFLOW_DISABLE_SEARCH` | Disables public search independently | `false` |

Keys never belong in browser code, Git, `.env.example`, or screenshots. Project
questions are answered from FinalFlow data; only explicit current-public
questions such as transit alerts, weather alerts, or venue notices may use
SerpAPI. Search results appear in **Web Sources**, separate from project evidence.

## Data and Provenance

| Label | Meaning in FinalFlow | Example |
| --- | --- | --- |
| `provided` | Source-backed context supplied to the project | Historical source data and reviewed inputs |
| `derived` | Calculated from prepared data or scenario inputs | Queues, utilization, waits, comparisons, summaries |
| `synthetic` | Transparent scenario assumption, never observed reality | Event demand, capacity, corridor coordinates, placement examples |
| `web` | Current external public information | A transit advisory returned by a requested search |

The application does **not** load restricted raw Rice datasets or large Parquet
files at runtime. It reads compact prepared exports and scenario inputs from
`data/`. Store visits are a historical commercial-activity proxy, not attendance
or ridership. Weather observations are historical multi-station context, not a
venue forecast. Approximate map points and vendor examples require site review.

## Architecture

```text
data/synthetic/ + data/exports/ + approved summaries
                         │
                         ▼
     paddydash/services/finalflow_data.py
       validates schema, IDs, units, provenance
                         │
                         ▼
 deterministic retrieval + mobility context + recommendation rules
                         │
          ┌──────────────┴──────────────┐
          ▼                             ▼
  seven Streamlit views       optional server-side AI/search
  (always usable offline)     (never authoritative for metrics)
```

OpenAI may improve presentation, but deterministic local analytics control
metrics, evidence, provenance, limitations, and recommendations. If the model
is disabled, unavailable, or its output cannot pass the factual guard, Ask
FinalFlow still returns the verified deterministic answer without exposing
provider details.

## Quality Checks

```bash
python3 -m pip check
python3 -m ruff check paddydash scripts tests
python3 -m compileall -q paddydash scripts tests
FINALFLOW_DISABLE_OPENAI=true FINALFLOW_DISABLE_SEARCH=true \
  python3 -m unittest discover -s tests -v
python3 scripts/validation/check_streamlit_deployment.py --require-tracked
```

Normal CI does not receive API keys or make paid live requests. See the
[demo rehearsal](docs/handoff/demo-rehearsal.md) for current visual checks and
known limitations.

## Repository Map

```text
asset/          project and README visuals
data/           compact exports, summaries, sample structure, synthetic inputs
docs/           project contracts, engineering notes, and deployment handoffs
paddydash/      the Streamlit application, components, pages, and services
scripts/        reproducible data, validation, and deployment helpers
tests/          deterministic, service, and Streamlit AppTest coverage
```

## Documentation

- [Streamlit application guide](paddydash/README.md)
- [Build and local-run guide](paddydash/BUILD_GUIDE.md)
- [Hosted deployment guide](paddydash/DEPLOYMENT_GUIDE.md)
- [Application API and response contracts](docs/api/application-api.md)
- [Mobility contract](docs/project/mobility-contract.md)
- [Teammate evidence inventory](docs/project/teammate-evidence-integration.md)
- [Data contracts](docs/project/data-contracts.md)
- [Minh Tue deployment handoff](docs/handoff/minh-tue-deployment-handoff.md)
- [CI/CD maintainer guide](docs/engineering/ci-cd-guide.md)

## Release Boundaries

Implemented: the seven-page Streamlit experience, scenario-based mobility replay,
prepared contextual evidence, conditional web-source display, optional
server-side AI wording, tests, and deployment documentation.

Still unfinished: official event-count calibration, venue/site validation,
live-provider monitoring, a standalone HTTP backend, React frontend, AWS
infrastructure, and production operational validation. The supported deployment
target remains Streamlit Community Cloud from protected `main`; work is prepared
and reviewed on `stephen-develop` before merging.
