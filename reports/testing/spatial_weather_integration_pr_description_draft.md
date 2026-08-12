# Pull request draft: Add spatial heat map and grounded historical weather answers

## Summary

This change connects Quế Anh's reviewed spatial exports and Tấn Đạt's reviewed
historical weather table to the existing FinalFlow Streamlit application.

- Adds a fifth **Spatial & Heat Map** page built from a compact validated CSV.
- Adds deterministic historical-weather retrieval and a related chart to **Ask
  FinalFlow**.
- Keeps optional OpenAI narration grounded in locally selected facts and keeps
  the full app usable with OpenAI disabled.
- Adds reproducible build scripts, source hashes, rejection reports, data/API
  documentation, deployment validation, tests, and handoff evidence.

## Spatial implementation

- Streams `poi_uhi_summary.zip` and `spending_summary.zip` without extracting or
  committing the upstream archives.
- Applies the documented exploratory NY/NJ rectangle: latitude 40.4-41.1 and
  longitude -74.5--73.5.
- Excludes provided POIs marked synthetic or with unknown synthetic status.
- Sums all supplied spending/customer rows per `PLACEKEY` before assigning
  deterministic tiers.
- Omits raw spend and raw customer values from the deployed browser artifact.
- Matches the nearest UHI point with WGS84 haversine distance and a 250 m limit.
- Preserves 222 unmatched rows as gray `Insufficient evidence`, never low heat.
- Escapes untrusted source labels before Plotly hover rendering.
- Provides city, category, heat, recommendation, and parking filters plus a
  non-map table fallback.

Build result:

```text
Input POIs: 511,934
Candidate POIs after geographic/synthetic checks: 124,384
Accepted deployed locations with spending evidence: 9,889
Missing UHI within 250 m: 222
Runtime CSV SHA-256: 49927DDF46616F7B6F81EB018660AEB1280760920F8B94C71EC5D95BA785BD56
```

## Historical weather implementation

- Validates the cleaned source schema, finite numeric fields, station identity,
  ISO dates, unique station-date grain, temperature ordering, and precipitation
  conversion.
- Rejects 110 impossible temperature-order rows and records the reason.
- Produces eight deterministic metrics with exact numerator, denominator,
  percentage, threshold, action, scope, rule version, and limitation fields.
- Uses `station_date_observation` consistently; observations are not renamed as
  calendar days, people, events, or locations.
- Treats the table as historical multi-station evidence, not a live forecast or
  venue-specific measurement.
- Treats thresholds, risk levels, and actions as FinalFlow project heuristics.
- Refuses future forecast requests, clarifies ambiguous match/weather questions,
  and declines unavailable humidity or snow fields instead of substituting an
  unrelated metric.
- Detects probability, likelihood, prediction, umbrella, stadium,
  next-weekday, conditions, and future-year forecast wording before scenario or
  historical routing.
- Validates optional weather narration after parsing and falls back to the exact
  deterministic answer if it changes approved facts, units, scope, or framing.

Build result:

```text
Input observations: 45,814
Accepted station-date observations: 45,704
Rejected invalid temperature order: 110
June-July station-date observations: 7,672
Unique stations: 401
Unique dates: 1,827
Runtime CSV SHA-256: D0BAE58E59E281798D42F97E06D9D06D63CEC6F820EFDD786E1CB06F302AB22F
```

## Validation

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m ruff check paddydash scripts tests
.\.venv\Scripts\python.exe -m compileall -q paddydash scripts tests
$env:FINALFLOW_DISABLE_OPENAI = "true"
.\.venv\Scripts\python.exe scripts\validation\check_streamlit_deployment.py --require-tracked
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Results:

- dependency compatibility: passed;
- Ruff: passed;
- compilation: passed;
- deployment validator: zero errors, 7.56 MB bundle, 9,889 spatial rows, eight
  weather metrics;
- ordinary pre-commit suite: **82/83 passed**; the sole expected failure requires
  the five new deployable files to be tracked;
- simulated post-commit suite: **83/83 passed** with a disposable Git index and
  no modification to the real staging area;
- deployment validation enforces artifact SHA-256/row counts, a 10 MB per-file
  limit, and a 20 MB bundle limit;
- both runtime CSVs rebuilt byte-for-byte identically;
- real Streamlit health and root page: HTTP 200;
- browser smoke: map rendered, parking filter returned 206/9,889, historical
  rain evidence reconciled to 2,911/7,672 (37.94%), and phone-width layout was
  usable after navigation collapse.

Normal CI disables OpenAI and makes no paid live request. Earlier live test
artifacts cover the established OpenAI connection and fallback, but they predate
the new weather prompt. A small paid weather regression can be run separately if
the team authorizes it.

## Screenshots

Attach these files to the pull request description:

- `reports/screenshots/streamlit_spatial_heat_map.png`
- `reports/screenshots/streamlit_weather_evidence.png`

## Known limitations and release gates

- The map boundary is an exploratory rectangle, not an approved venue polygon.
- Exact business names and coordinates are present; raw spend/customer values
  are not. Stephen Nguyen must confirm licensing/publication permission before a
  public deployment.
- The weather source is multi-station and has no approved venue mapping.
- UHI and weather thresholds/actions are FinalFlow heuristics, not scientific
  standards or forecasts.
- OpenStreetMap tiles require network access; the evidence table remains usable
  if tiles fail.
- SerpAPI, FastAPI, React, AWS, and live forecast retrieval remain out of scope.

## Requested review

- [ ] Quế Anh confirms the spatial source meaning, aggregation, scope, UHI match,
  missing-evidence behavior, and publishable fields.
- [ ] Tấn Đạt confirms the weather source meaning, station-date unit, rejected
  rows, thresholds, actions, and multi-station limitation.
- [ ] Stephen Nguyen confirms product scope, licensing/publication approval,
  release evidence, and deployment readiness.
- [ ] Hai Nam confirms the Streamlit behavior, chatbot routing, tests,
  documentation, and handoff package.
