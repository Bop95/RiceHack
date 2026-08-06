# Suggested pull request

## Suggested title

`Harden FinalFlow OpenAI grounding with 100-case live verification`

## Description

### Summary

This PR validates FinalFlow's configured OpenAI integration with a real 100-case
matrix, fixes semantic grounding problems exposed by live model output, and adds
repeatable edge/regression tooling plus reviewer-ready evidence.

The primary run completed 100 live structured requests with zero API, timeout,
rate-limit, or parsing errors. Manual evidence review found 21 answers needing
correction, mainly incorrect per-store units, one reversed comparison, one
day-of-week ranking mismatch, and two synthetic-scenario labeling issues. All 21
discovered cases subsequently passed targeted live regression checks. The final
prompt also passed a nine-route live smoke matrix.

### Updates

- Added an opt-in 100-case live OpenAI harness covering brands, categories,
  markets, weekdays, distributions, overview questions, synthetic scenarios,
  security/injection attempts, and encoding/input boundaries.
- Added machine-readable, secret-safe results with questions, answers, routes,
  checks, and latency.
- Defined `mean` as visits per store-day and `stores` as unique-store count in the
  model contract.
- Defined day-of-week and synthetic high-risk-share semantics explicitly.
- Required comparison direction to match supplied numbers.
- Required every scenario narrative to retain `synthetic` or `illustrative`.
- Anchored narration to the deterministic local answer so the model cannot change
  the selected entity, rank, value, unit, label, or scope decision.
- Expanded request-shape tests to assert these guardrails.
- Added the complete live/offline test report and Streamlit screenshots.

### Live verification

```text
Primary matrix:             100 live requests, 0 provider errors
Initial semantic audit:      21 cases required correction
Targeted regression:         21/21 discovered cases passed after fixes
Final cross-category smoke:   9/9 passed
Total live requests:         132
```

Primary matrix composition:

| Area | Cases |
|---|---:|
| Brand | 12 |
| Category | 12 |
| Market | 12 |
| Weekday | 10 |
| Distribution | 10 |
| Overview | 10 |
| Synthetic scenario | 12 |
| Security / injection | 12 |
| Input / encoding edge | 10 |

Primary latency with five workers: 2.290s median, 6.112s p95, 8.788s max.

### Offline verification

```powershell
$env:FINALFLOW_DISABLE_OPENAI = "true"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
# 54 pre-CI tests passed

.\.venv\Scripts\python.exe scripts\validation\check_local_env.py .env
# passed without printing credential values

.\.venv\Scripts\python.exe scripts\validation\check_streamlit_deployment.py `
  --require-openai --require-tracked
# status: ready; errors: 0; warnings: 0
```

### Safety notes

- No API key or credential value is included in tests, requests, reports,
  screenshots, or result artifacts.
- OpenAI remains server-side and every request uses `store=False`.
- Evidence, plot selection, data type, core limitations, and factual baseline
  remain controlled by local prepared-data code.
- Prompt-injection, secret, password, environment-variable, and outside-knowledge
  cases were refused in the live run.
- The safe prepared-data fallback remains available when OpenAI is disabled or
  unavailable.
- No raw Rice data or large Parquet file is included.

### Remaining deployment checks

- Confirm the private hosted Streamlit deployment can read its server-side secret.
- Confirm the UI allowance switches to prepared-data mode when exhausted.
- Configure OpenAI project budgets and provider rate limits before public sharing.

### Screenshots

#### Overview

![FinalFlow overview](../screenshots/streamlit_overview.png)

#### OpenAI server configuration detected

![Ask FinalFlow configured](../screenshots/streamlit_ask_finalflow_configured.png)

#### Prepared-data fallback and evidence

![Prepared-data evidence response](../screenshots/streamlit_ask_finalflow_prepared_answer.png)

### Detailed evidence

See `reports/testing/api_key_edge_case_test_report.md` for the full matrix,
defects found, fixes, live regression results, local checks, artifacts, and
residual limitations.
