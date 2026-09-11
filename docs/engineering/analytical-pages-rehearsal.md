# Analytical Pages Rehearsal

Reviewed on 2026-09-11 on `stephen-develop`. The application entrypoint remains
`paddydash/app.py`. No datasets were regenerated for this integration.

## Evidence Used

| View | Prepared evidence |
| --- | --- |
| Executive Overview | Executive KPIs, scenario summaries, node/edge snapshots, recommendation catalog, commercial and weather context |
| Matchday Timeline | Canonical timeline, node queues, edge throughput and capacity |
| Mobility & Access | Node/edge time series, scenario/access summaries, approximate synthetic corridor reference |
| Commercial & POI Intelligence | Existing store-visit summaries and filters, commercial context, spatial heat locations, synthetic business and placement examples |
| Weather & Heat | Weather context, reviewed risk summary, contributor monthly weather, spatial heat locations, exported rain/baseline metrics and synthetic capacity factors |
| Scenario Lab | Scenario summaries/comparison, node queues, evaluated and catalog-only intervention comparisons |

Header and assistant facts use the same prepared mobility rows. Historical chat
answers retain the scope recorded when they were created. The original simulator
remains available for offline generation and engine tests, not as a UI fallback.

## Validation

- Full unittest discovery: **163 tests passed**. The render matrix covers all
  six pages, five scenarios and thirteen canonical phases: **390 combinations**.
- Independent CSV comparisons verify selected queue, total pressure, utilization
  and wait. Tests cover duplicate/invalid rows, missing exports, empty filters,
  coincident phase markers, preserved replay time, zero baselines, recommendation
  scope and unevaluated interventions.
- Mocked OpenAI/search tests verify factual grounding, safe failures, project
  questions that do not search, separate web evidence and retained answer scope.
- Weather regression separates five June-July indicators from three all-month
  risk bands; their observation denominators are never combined in one chart.
- Ruff, compilation, dependency compatibility and strict tracked-bundle checks
  passed. The bundle is about **9.79 MB**, below its **20 MB** limit.
- Local validation uses the existing isolated environment with **Python 3.11.4**
  and **Streamlit 1.60.0**. GitHub CI declares **Python 3.12**; local results are
  not a claim that a remote Actions run has completed.
- No credentials, raw datasets or new data exports were staged. Provider calls
  were disabled for startup and browser checks. Provider behavior was mocked.

## Browser Observations

Headless Chrome via the installed Playwright package exercised navigation at
**1440 x 1000** and **390 x 844**. Phase/scenario/time remained synchronized
through all seven views. Final-whistle metrics for baseline, rain and rail
disruption matched independently loaded CSV rows. The automated judge matrix
also covers pre-match, kickoff and post-match.

All six analytical views rendered charts; the assistant remained available
offline. The corridor and exploratory POI/heat maps rendered public basemap
tiles. No browser JavaScript exceptions or page-level horizontal overflow were
observed. Narrow screenshots prompted shorter axes, separate weather windows,
and removal of an overlapping map title. Focused rendering tests and a final
map capture verified those fixes. Local screenshots are temporary review
artifacts under `/tmp/finalflow-browser-review`, not deployment assets.

The bounded Streamlit server returned `ok` from `/_stcore/health` and rehearsal
processes were stopped. An unrelated pre-existing user server was left alone.

## Remaining Limitations

- Historical multi-station weather, POI/spending tiers and nearby UHI need
  site-specific review. Maps do not identify verified stadium vendor locations.
- Synthetic reference points are approximate; nearby Meadowlands/Stadium
  markers can overlap at corridor scale. The node table identifies both.
- Monthly precipitation sums pooled source observations. Mean visibility
  distance is unavailable, although low-visibility observation share exists.
- Shuttle utilization lacks capacity inputs; mode totals are passenger
  movements, not unique spectators. Catalog-only interventions have no modeled
  effects. Simulated carbon totals are not introduced.
- Some metrics do not change between alternatives: the capacity boost keeps
  peak queue unchanged while reducing delay. No universal improvement is claimed.
- Calibration, live provider verification, deployment and official event
  schedule validation remain unfinished. Readiness and recommended actions are
  explicitly scenario-based review heuristics, not public-safety certification.
- On a freshly started server, a direct analytical-page URL can show Streamlit's
  page-not-found dialog and fall back to Overview before native navigation is
  initialized. Start at the root URL and use the sidebar. Sidebar navigation
  passed; cold-start bookmarks need a separate navigation compatibility fix.
