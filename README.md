<p align="center">
  <img src="asset/rice_hack.png" alt="Rice Hack banner" width="100%">
</p>

# FinalFlow

FinalFlow is a tested Streamlit application for exploring commercial activity
and illustrative mobility-readiness scenarios around the 2026 World Cup Final.
The case study follows the Midtown Manhattan to New York New Jersey Stadium
corridor for a hypothetical Spain versus Argentina final.

The application combines compact approved store-visit summaries, clearly
labeled synthetic scenarios, a derived spatial/urban-heat explorer, reviewed
historical weather evidence, deterministic analytics, and optional server-side
OpenAI narration. It never loads the restricted raw Rice datasets or the
multi-gigabyte clean Parquet file at runtime.

## Release status

Implemented now:

- five Streamlit pages: Overview, Store-Visit Explorer, Scenario Explorer,
  Spatial & Heat Map, and Ask FinalFlow;
- compact `derived` summary tables and reproducible `synthetic` scenarios;
- a 9,889-location NY/NJ exploratory map with commercial tiers, nearest UHI
  evidence, an accessible table, and explicit missing-evidence handling;
- eight deterministic historical-weather metrics for grounded chatbot answers,
  with station-date units and forecast refusal;
- grounded answers with validated evidence, data labels, limitations, and plots;
- deterministic prepared-data operation when OpenAI is disabled or unavailable;
- optional server-side OpenAI Responses API narration;
- local launchers, deployment validation, unit/AppTest coverage, and GitHub CI;
- Streamlit Community Cloud deployment instructions for the `main` branch.

Not integrated into the deployed Streamlit application:

- a standalone REST/FastAPI service (a contributor prototype now exists under
  `notebooks/tan-dat/backend/`);
- a TypeScript/React frontend;
- AWS infrastructure or automated AWS deployment.

Do not design a deployment around those unimplemented components. The current
release is one Python 3.12 Streamlit service.

The `stephen-develop` working branch integrates the synthetic mobility replay,
prepared teammate evidence and optional server-side SerpAPI search. The future
release target remains `main`; this work does not deploy either branch.
Tan Dat's standalone backend prototype is not started by `paddydash/app.py`;
it reuses the app's shared search service. See the
[current evidence inventory](docs/project/teammate-evidence-integration.md) and
[earlier branch integration status](docs/project/branch-integration-status.md).

## Architecture

```text
Approved compact CSVs
        |
        v
data_service.py -- validates schema and data labels
        |
        v
analytics.py -- deterministic retrieval, evidence, and local answer
        |
        +-------------------------------+
        |                               |
        v                               v
prepared-data response          optional OpenAI narration
        |                        (server-side, grounded)
        +---------------+---------------+
                        |
                        v
               five Streamlit pages
```

OpenAI can improve wording, but the local analytics layer controls the selected
entity, values, units, ranking direction, evidence, data type, limitations, and
related plot.

## Requirements

- Python 3.12
- Git
- Windows PowerShell for the included one-command launcher, or any shell for the
  direct Streamlit command
- optional OpenAI project key for AI narration

The root `requirements.txt` is the single source of runtime dependencies.
`requirements-dev.txt` contains CI/development-only tools.

## Quick start

### Windows: prepared-data mode

From the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\run_finalflow_local.cmd -PreparedDataOnly
```

Open `http://localhost:8501` if the browser does not open automatically. This
mode is complete and makes no OpenAI request.

### Windows: optional OpenAI mode

```powershell
Copy-Item .env.example .env
```

Edit `.env`, add a project key after `OPENAI_API_KEY=`, then validate and run:

```powershell
.\.venv\Scripts\python.exe scripts\validation\check_local_env.py .env
.\run_finalflow_local.cmd
```

The launcher reads the ignored `.env` file and never accepts or prints the key.

### macOS or Linux

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
FINALFLOW_DISABLE_OPENAI=true FINALFLOW_DISABLE_SEARCH=true python3 -m streamlit run paddydash/app.py
```

For optional OpenAI mode, copy `.env.example` to `.env`, add the server-side
key, and run the same Streamlit command without `FINALFLOW_DISABLE_OPENAI=true`.

## Environment variables

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `OPENAI_API_KEY` | No | unset | Enables server-side OpenAI narration. Without it, the app uses prepared-data mode. |
| `OPENAI_MODEL` | No | `gpt-5.6-luna` | Model used by the OpenAI Responses API. |
| `FINALFLOW_MAX_AI_REQUESTS_PER_SESSION` | No | `10` | Best-effort per-browser-session allowance, clamped to 1-100. |
| `FINALFLOW_DISABLE_OPENAI` | No | false | `true`, `1`, `yes`, or `on` forces prepared-data mode. CI sets this to `true`. |
| `SERPAPI_API_KEY` | No | unset | Server-only search credential for explicit current public-information requests. |
| `FINALFLOW_DISABLE_SEARCH` | No | false | `true`, `1`, `yes`, or `on` disables web search independently. |

Project questions never require search. Safe search failures preserve project
answers; web source cards remain separate from deterministic project evidence.
For local development, store values in the ignored `.env` file. For hosted
deployment, store them only in Streamlit Community Cloud Secrets.

## Validate the release

Run the same quality gates used by CI:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m ruff check paddydash scripts tests
.\.venv\Scripts\python.exe -m compileall -q paddydash scripts tests
$env:FINALFLOW_DISABLE_OPENAI = "true"
.\.venv\Scripts\python.exe scripts\validation\check_streamlit_deployment.py --require-tracked
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Normal CI deliberately does not receive an OpenAI key and does not make paid,
nondeterministic live requests. The committed live-test evidence is under
`reports/testing/`.

## Deploy

The supported release target is Streamlit Community Cloud:

```text
Repository: Bop95/RiceHack
Branch: main
Entrypoint: paddydash/app.py
Python: 3.12
Dependency file: requirements.txt (repository root)
Configuration: .streamlit/config.toml
```

Protect `main`, require the **Python 3.12 quality gate**, and deploy only merged
commits. Add optional OpenAI values in Streamlit Secrets, never GitHub Actions.
See the [hosted deployment guide](paddydash/DEPLOYMENT_GUIDE.md) for the complete
procedure and smoke checklist.

## Application API boundary

The current application has an in-process Python service API; it does not expose
HTTP routes. Streamlit imports `data_service.py`, `analytics.py`, and
`ai_service.py` directly. The callable signatures, response schema, errors, and
future backend boundary are documented in
[Application API](docs/api/application-api.md).

## Repository structure

```text
.
|-- .github/workflows/       GitHub Actions quality gate
|-- .streamlit/              tracked, non-secret Streamlit configuration
|-- asset/                   README and project images
|-- data/summaries/          compact approved derived runtime data
|-- data/synthetic/          reproducible, clearly labeled scenario data
|-- docs/api/                current service/API contract
|-- docs/engineering/        CI/CD setup and beginner guide
|-- docs/handoff/            deployment-owner handoff notes
|-- paddydash/               Streamlit pages, components, and services
|-- reports/                 figures, screenshots, and test evidence
|-- scripts/                 data preparation, validation, and launch utilities
|-- tests/                   unit, service, release, and Streamlit AppTest checks
|-- requirements.txt         runtime dependency source of truth
`-- requirements-dev.txt     local CI/development tools
```

## Data and security boundary

Never commit:

- `.env`, `.streamlit/secrets.toml`, or credentials;
- restricted raw/external/processed data;
- Parquet files or the large clean dataset;
- virtual environments, caches, bytecode, or generated interactive HTML.

Runtime data uses these labels:

- `derived`: approved transformed summary data;
- `synthetic`: reproducible scenario assumptions, never observed attendance;
- `provided` and `web`: reserved shared project labels, not runtime inputs to the
  current dashboard.

Store visits are a historical commercial-activity proxy. They are not World Cup
attendance, pedestrian flow, transit ridership, or a causal forecast.
Weather percentages count station-date observations in the reviewed
multi-station table; they are not calendar-day probabilities or live forecasts.
Map heat labels and recommended actions are FinalFlow heuristics. The current
rectangular NY/NJ extent is exploratory and must not be described as a verified
venue boundary.

## Documentation

- [Beginner build and run guide](paddydash/BUILD_GUIDE.md)
- [Hosted deployment guide](paddydash/DEPLOYMENT_GUIDE.md)
- [Application API](docs/api/application-api.md)
- [Minh Tue deployment handoff](docs/handoff/minh-tue-deployment-handoff.md)
- [CI/CD beginner guide](docs/engineering/ci-cd-beginner-guide.md)
- [CI/CD maintainer guide](docs/engineering/ci-cd-guide.md)
- [Data contracts](docs/project/data-contracts.md)
- [Spatial and weather integration design](docs/engineering/spatial-weather-streamlit-integration-design.md)
- [Final validation report](reports/testing/final_handoff_validation_report.md)

## Ownership and handoff

Minh Tue receives the tested repository, setup/environment/API documentation,
deployment checklist, and known limitations. No AWS resources should be created
from this release without a separate architecture decision. The immediate
handoff target is the protected `main` branch and Streamlit Community Cloud.
