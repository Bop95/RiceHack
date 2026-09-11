# FinalFlow deployment handoff for Minh Tue

## Handoff decision

FinalFlow is ready for a protected-branch Streamlit Community Cloud deployment.
The current release is a Python 3.12 Streamlit application with an optional
server-side OpenAI integration. It is not an AWS, FastAPI, React, or SerpAPI
release.

Deployment owner: **Minh Tue**

```text
Repository: Bop95/RiceHack
Release branch: main
Entrypoint: paddydash/app.py
Python: 3.12
Runtime dependencies: requirements.txt
Streamlit configuration: .streamlit/config.toml
```

## What is being handed over

- seven-page Streamlit application with a synthetic mobility replay;
- compact approved runtime CSVs and four static figures;
- a bounded spatial/heat map artifact and historical-weather evidence artifact,
  each with build provenance and rejection counts;
- deterministic analytics and prepared-data fallback;
- optional grounded OpenAI narration from the Streamlit server;
- secret-free environment template;
- local launchers and deployment validator;
- GitHub Actions quality gate;
- API/service contract, deployment guide, screenshots, and test evidence.

The deployment validator reports the current deployable bundle size and row
counts. The repository also contains notebooks and historical test evidence,
but the hosted app does not load them.

## Acceptance evidence

Before handoff, the release owner must record a passing result for:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m ruff check paddydash scripts tests
.\.venv\Scripts\python.exe -m compileall -q paddydash scripts tests
$env:FINALFLOW_DISABLE_OPENAI = "true"
.\.venv\Scripts\python.exe scripts\validation\check_streamlit_deployment.py --require-tracked
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The final recorded results are in
`reports/testing/final_handoff_validation_report.md`. Normal CI makes no live
OpenAI request. Historical live OpenAI evidence is retained under
`reports/testing/`.

## Local setup

### Windows

```powershell
git clone https://github.com/Bop95/RiceHack.git
cd RiceHack
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\run_finalflow_local.cmd -PreparedDataOnly
```

### macOS or Linux

```bash
git clone https://github.com/Bop95/RiceHack.git
cd RiceHack
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
FINALFLOW_DISABLE_OPENAI=true python -m streamlit run paddydash/app.py
```

Prepared-data mode is the safest first smoke test and is a supported operating
mode, not an error state.

## Environment and secrets

| Variable | Required | Hosted location | Notes |
| --- | --- | --- | --- |
| `OPENAI_API_KEY` | No | Streamlit Secrets | Enables optional narration. Never place it in GitHub or a committed file. |
| `OPENAI_MODEL` | No | Streamlit Secrets | Defaults to `gpt-5.6-luna`. |
| `FINALFLOW_MAX_AI_REQUESTS_PER_SESSION` | No | Streamlit Secrets | Defaults to 10; valid effective range is 1-100. |
| `FINALFLOW_DISABLE_OPENAI` | No | CI/process environment | Forces prepared-data mode for tests or emergency cost control. |
| `SERPAPI_API_KEY` | No | Server secrets | Enables explicit current public-information searches only. |
| `FINALFLOW_DISABLE_SEARCH` | No | CI/process environment | true/1/yes/on forces no-search mode. |

Local values may be stored in `.env`, which is ignored by Git. Copy
`.env.example`; never edit the example with real credentials. Search failures show
a fixed safe message while project answers remain available. Web source cards
are separate from project evidence and never modify simulator inputs.

Streamlit Secrets example:

```toml
OPENAI_API_KEY = "replace-in-streamlit-settings"
OPENAI_MODEL = "gpt-5.6-luna"
FINALFLOW_MAX_AI_REQUESTS_PER_SESSION = "10"
```

## Deployment procedure

1. Merge the release through a reviewed pull request into protected `main`.
2. Confirm **Python 3.12 quality gate** is green on the PR.
3. In Streamlit Community Cloud, create an app from `Bop95/RiceHack`.
4. Select branch `main` and entrypoint `paddydash/app.py`.
5. Select Python 3.12.
6. Deploy first without a key and complete the prepared-data smoke test.
7. If narration is approved, add the three OpenAI values in Streamlit Secrets.
8. Reboot the app and repeat the Ask FinalFlow checks.
9. Record the hosted URL, deployment owner, date, and smoke result below.

Use `paddydash/DEPLOYMENT_GUIDE.md` for the complete click-by-click security and
troubleshooting procedure.

## Hosted smoke checklist

- [ ] Overview loads metrics, monthly trend, categories, and markets.
- [ ] Store-Visit Explorer filters and every tab render.
- [ ] Scenario Explorer labels every scenario as synthetic or illustrative.
- [ ] Spatial & Heat Map loads all approved records and combined filters work.
- [ ] Missing UHI rows are gray and labeled `Insufficient evidence`.
- [ ] The accessible spatial table remains usable if map tiles fail.
- [ ] Ask FinalFlow returns a prepared-data answer without a key.
- [ ] A historical rain question cites station-date observations and an approved
  threshold; a future match-weather question is declined as unavailable.
- [ ] Suggested questions show evidence, data type, limitation, and related plot.
- [ ] An unrelated or prompt-override question is refused.
- [ ] Optional OpenAI mode displays the model name but never the key.
- [ ] OpenAI failure or allowance exhaustion falls back safely.
- [ ] No raw data, traceback, provider error, or secret appears in the browser.
- [ ] The layout remains usable at phone width.

## CI and branch protection

The workflow reports status but does not enforce merging by itself. A repository
maintainer must configure a `main` ruleset that:

- requires a pull request;
- requires at least one approval when team size permits;
- requires **Python 3.12 quality gate**;
- requires the branch to be up to date;
- requires conversation resolution; and
- blocks force pushes and branch deletion.

The workflow has read-only contents permission, persists no checkout credential,
receives no OpenAI secret, and checks every PR plus pushes to `main`.

## Runtime data boundary

The app reads only compact versioned files in `data/summaries/` and
`data/synthetic/`, plus static figures in `reports/figures/`. The deployment must
not include restricted raw data, external source files, processed Parquet, local
interactive HTML, `.env`, or `.streamlit/secrets.toml`.

Run this before every release:

```powershell
.\.venv\Scripts\python.exe scripts\validation\check_streamlit_deployment.py --require-tracked
```

It validates required files, schemas, data labels, dependency declarations,
unsafe tracked data, Git tracking, artifact hashes and row counts, the 10 MB
per-file and 20 MB bundle limits, and OpenAI mode without calling OpenAI or
printing a credential.

## API boundary

There are no HTTP endpoints in this release. Streamlit directly imports the
Python services documented in `docs/api/application-api.md`. Do not configure a
frontend, API Gateway, load balancer health path, or `/chat` consumer until a
real network API is implemented and documented.

## Security and operating limits

- The browser never receives the OpenAI key.
- OpenAI requests use `store=False`, bounded output, timeout, and one retry.
- The per-session request allowance is best-effort and not global abuse control.
- Set an OpenAI project budget and provider rate limits before public sharing.
- Store visits are a historical commercial-activity proxy, not attendance.
- Synthetic scenarios are interface-testing assumptions, not forecasts.
- The spatial scope is an exploratory NY/NJ rectangle, not a verified venue
  polygon. Business commercial tiers are aggregated; raw spend/customer values
  are not deployed.
- Missing UHI means insufficient evidence. Map heat thresholds and actions are
  FinalFlow heuristics.
- Weather metrics count historical station-date observations across a reviewed
  multi-station dataset. They are not calendar-day probabilities, a live
  forecast, or venue-specific measurements; weather thresholds/actions are
  FinalFlow heuristics.
- Streamlit Community Cloud resource behavior and secret injection require a
  hosted smoke test; local CI cannot prove them.

For sustained public traffic, introduce an authenticated backend, shared rate
limiter, monitoring, and an explicit architecture review. That is a future
release, not part of this handoff.

## Rollback

If a merged release fails after deployment:

1. remove or rotate the OpenAI secret immediately if exposure is suspected;
2. switch to prepared-data mode by removing the key or setting
   `FINALFLOW_DISABLE_OPENAI=true` where supported;
3. identify the last green commit on `main`;
4. revert the failing pull request with a new reviewed pull request;
5. wait for the required quality gate and merge the revert;
6. reboot Streamlit and repeat the hosted smoke checklist.

Do not force-push or reset shared `main`.

## Deployment record

Minh Tue completes this after deployment:

```text
Hosted URL:
Deployed commit:
Deployment date/time:
Python version:
Prepared-data smoke result:
OpenAI smoke result (or not enabled):
Branch protection confirmed by:
Known follow-up owner:
```

## Handoff completion criteria

The handoff is complete when the release PR and CI are green, `main` protection
is active, Streamlit watches `main`, the hosted smoke checklist passes, secrets
exist only in Streamlit settings, and the deployment record above is filled in.
AWS remains an unimplemented future option and requires a separate decision.
