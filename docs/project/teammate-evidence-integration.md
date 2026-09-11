# Teammate evidence integration

The existing `paddydash/` app keeps mobility as its default view. Commercial &
weather context adds evidence without changing simulator demand or capacities.

| Contributor | Runtime evidence | Provenance |
| --- | --- | --- |
| Hai Nam | `data/summaries/monthly_trends.csv`, existing visit explorer and assistant summaries | derived transformed visits, not passenger counts |
| Que Anh | `data/summaries/spatial_heat_locations.csv` | derived spending tiers, parking flags, nearest heat match; exploratory NY/NJ bounds |
| Tan Dat | `data/summaries/weather_risk_summary.csv`, `notebooks/tan-dat/data/summaries/weather_monthly.csv` | derived historical multi-station context, not forecast |
| Duc Anh | `notebooks/duc-anh/data_clean/finalflow_business_integration.csv` | synthetic scenario examples, not verified placements |
| Phuong Anh | No standalone KPI/Power BI deliverable found | unavailable |

Unreviewed spending totals, large archives and raw data are not loaded by this
new page. Parking flags do not measure available spaces. Weather monthly averages
have a different preparation path from reviewed risk denominators. Heat matches
within 250 m and the UHI > 7 threshold are project heuristics, not site validation.

`services/project_context.py` resolves the selected phase/scenario/time afresh,
ignoring stale replay times. Exit-path, staging and shade recommendations are
heuristics with explicit evidence types. Comparisons use complete simulator runs;
capacity boost and disruption are alternative runs, not combined interventions.
Zero baseline queue cannot justify a percentage improvement claim.

The assistant's prepared narrative and evidence are deterministic. The existing
strict grounding check rejects model changes to approved facts. History retains
its original phase/scenario/time caption. External snippets are never simulator
inputs or authoritative project evidence.

Search runs only for explicit current public transit/weather/access questions.
Configure `SERPAPI_API_KEY` only in the server environment; set
`FINALFLOW_DISABLE_SEARCH=1` to force offline mode. No new dependency is required.
Search uses a five-second timeout and at most five sources, with ten attempts per
browser session. The app passes normalized snippets to its single guarded
Responses request as untrusted web context; it does not make a separate search
narration call. Snippets, clickable titles, domains and dates are displayed in
Web Sources, apart from Project Evidence. Structured answers retain web sources
even if OpenAI fails. The factual guard keeps the prepared project narrative
authoritative; snippets are not independently verified live alerts.
Missing keys/errors show Live web search unavailable and preserve project answers.
No provider exception text is surfaced. Tan Dat's backend re-exports the shared
search service and models to avoid a second implementation.

Validation: `python3 -m unittest discover -s tests -p 'test_project_context.py' -v`.
No live provider access is required. No AWS deployment or event-count calibration
is implied by this integration.
