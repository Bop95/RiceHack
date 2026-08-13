# FinalFlow application API

## Scope

FinalFlow currently exposes an **in-process Python API**, not an HTTP API.
`paddydash/app.py` imports the service functions directly inside the Streamlit
server process. There is no `/health`, `/chat`, OpenAPI document, FastAPI server,
authentication middleware, or CORS configuration in this release.

This distinction matters for deployment: run `paddydash/app.py` with Streamlit.
Do not configure a reverse proxy or client application to call routes that do
not exist.

## Service flow

```text
load_dashboard_data()
        |
        v
retrieve_for_question(question, data)
        |
        v
RetrievalResult (validated context + local answer + evidence)
        |
        v
answer_with_fallback(question, retrieval, safety_identifier)
        |
        +-- OpenAI configured and successful --> mode="openai"
        `-- disabled/missing/error -----------> mode="prepared-data"
```

Evidence, related plot, data type, and factual baseline always come from local
analytics. OpenAI only returns a structured narrative and limitations.

## Data service

Module: `paddydash.services.data_service`

### `load_dashboard_data(repository_root=None) -> DashboardData`

Loads, converts, labels, and caches the approved runtime CSV files. It validates
required columns, integer/float fields, optional values, non-empty tables,
`derived` labels for summary/weather rows, and `synthetic` plus
`is_synthetic=true` for scenario rows.

`DashboardData` fields:

```text
summary, percentiles, brands, categories, markets, weekdays,
monthly, brand_monthly, category_monthly, scenarios, weather
```

Raises `FileNotFoundError`, `KeyError`, `TypeError`, or `ValueError` for missing
or invalid prepared data. Deployment validation catches these before release.

### `load_spatial_heat_data(repository_root=None) -> list[dict]`

Separately loads and caches `spatial_heat_locations.csv`, so non-map pages do not
need the larger table. It validates the spatial schema, optional UHI fields,
`derived`/non-synthetic labels, the fixed 40.4-41.1 latitude and
-74.5--73.5 longitude bounds, and the rule that a missing UHI value must be
`Insufficient evidence`.

### `read_validated_csv(path) -> list[dict]`

Loads one supported prepared CSV according to the schema keyed by its filename.
This is a lower-level helper; callers should normally use
`load_dashboard_data()`.

### `validate_data_types(rows, expected, source) -> None`

Requires all records to use one exact data label. Raises `ValueError` on mixed or
unexpected labels.

## Deterministic analytics

Module: `paddydash.services.analytics`

| Function | Purpose |
| --- | --- |
| `get_top_brands(data, metric="total_visits", limit=10)` | Ranked brand rows; supported metrics are total visits, mean visits per store-day, and unique stores. |
| `get_top_categories(data, metric="total_visits", limit=10)` | Ranked category rows using the same supported metrics. |
| `get_visit_trend(data, category=None, start_date=None, end_date=None)` | Overall or category monthly rows filtered by inclusive `YYYY-MM` strings. |
| `get_weekday_pattern(data, category=None)` | Overall Monday-Sunday rows; category-specific weekday data is intentionally unsupported. |
| `get_market_summary(data, market=None)` | All markets or a case-insensitive exact market match. |
| `get_scenario_summary(data, scenario_id=None)` | Synthetic totals, uplift, record counts, and high-risk record share. |
| `get_weather_risk_summary(data, metric_ids=None)` | Approved historical weather metrics in stable source order. |
| `get_plot_metadata(plot_id)` | Validated title, source, and data type for a known plot ID. |
| `retrieve_for_question(question, data)` | Routes an untrusted question to an approved dataset and returns a grounded `RetrievalResult`. |

Unsupported metrics, unknown plot IDs, and unsupported category weekday queries
raise `ValueError`. Out-of-scope or prompt-injection-style questions are returned
as controlled refusals rather than exceptions. Future-weather questions return
a no-forecast result; ambiguous match/weather questions ask for clarification;
and unavailable humidity or snow fields do not return unrelated metrics.

Historical-weather results preserve the supplied `station_date_observation`
unit, numerator, denominator, percentage, threshold direction, multi-station
scope, `derived` label, and heuristic limitations. They must not be interpreted
as forecasts or venue-specific measurements.

## Response contracts

### `EvidenceItem`

```json
{
  "label": "Top brand",
  "value": "Example brand",
  "source": "visits_by_brand.csv"
}
```

### `ChatResponse`

`ChatResponse.to_dict()` produces browser-safe data:

```json
{
  "answer": "A concise grounded answer.",
  "evidence": [
    {
      "label": "Top brand",
      "value": "Example brand",
      "source": "visits_by_brand.csv"
    }
  ],
  "relatedPlotId": "brand_ranking",
  "dataType": "derived",
  "limitations": ["Store visits are a commercial-activity proxy."],
  "mode": "prepared-data"
}
```

`mode` is `prepared-data` or `openai`. `relatedPlotId` can be `null` for a
refusal. The current implementation does not return web sources.

## AI service

Module: `paddydash.services.ai_service`

### Configuration helpers

- `api_is_configured() -> bool`
- `get_model_name() -> str`
- `get_max_ai_requests_per_session() -> int`

`api_is_configured()` returns false when the key is absent or
`FINALFLOW_DISABLE_OPENAI` is `true`, `1`, `yes`, or `on`. The request allowance
defaults to 10 and is clamped to 1-100.

### `prepared_data_response(retrieval) -> ChatResponse`

Returns the deterministic local answer without an external request.

### `answer_with_openai(question, retrieval, safety_identifier=None)`

Uses the server-side OpenAI Responses API with:

- the configured model;
- structured Pydantic output;
- low reasoning effort and at most 500 output tokens;
- a 20-second client timeout and one retry;
- `store=False`; and
- an optional hashed safety identifier.

The prompt contains only the validated local answer and approved, question-
specific context. It explicitly forbids changing entities, values, rankings,
units, scope, or data labels. For weather, it also preserves the observation
unit, threshold direction, numerator, denominator, percentage, historical
scope, heuristic status, and `derived`/`synthetic` distinction. The key is read
by the server-side SDK and is never placed in a response.

For weather responses, the service also validates the optional narrative after
parsing. It falls back to the deterministic prepared-data answer if the model
introduces unapproved numbers, forecast/probability framing, venue narrowing,
incorrect observation entities, synthetic wording, or an unapproved threshold
comparison. Evidence, data labels, limitations, and plots remain local in all
cases.

Returns prepared-data mode when OpenAI is not configured. Raises the sanitized
`AIServiceError` when a configured request cannot complete safely.

### `answer_with_fallback(question, retrieval, safety_identifier=None)`

Returns `(ChatResponse, warning_or_none)`. It uses OpenAI when possible and
catches `AIServiceError`, returning the verified prepared-data response plus a
safe user message. Provider exception details and credentials are not returned.

## Environment contract

| Variable | Behavior |
| --- | --- |
| `OPENAI_API_KEY` | Optional server credential. Absence selects prepared-data mode. |
| `OPENAI_MODEL` | Optional model name; defaults to `gpt-5.6-luna`. |
| `FINALFLOW_MAX_AI_REQUESTS_PER_SESSION` | Optional integer, safely clamped to 1-100. |
| `FINALFLOW_DISABLE_OPENAI` | Optional boolean-like safety switch that disables external calls. |

See `.env.example` for a secret-free local template. Streamlit Community Cloud
values belong in its Secrets interface.

## Future HTTP boundary

If the team later adds FastAPI or another backend, treat this service layer as
domain logic rather than silently presenting it as an existing network API. A
future handoff must separately define routes, authentication, authorization,
rate limiting, request/response schemas, CORS, health checks, observability, and
deployment ownership. None of those network guarantees exist in this release.
