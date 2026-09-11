# FinalFlow Demo Review

Working branch: `stephen-develop`. This review does not authorize publication or
claim calibrated operations, live-provider verification, or completed deployment.

## Judge Journey

Executive Overview -> Matchday Timeline -> Mobility & Access -> Scenario Lab ->
Weather & Heat -> Commercial & POI Intelligence -> Ask FinalFlow.
Each page has a native Next link; the sidebar preserves phase, scenario and replay
minute. Methodology & Assumptions is available on every page.

1. Start with the overview's bottleneck, recommended action and modeled-data label.
2. Replay pre-match, kickoff, final whistle and post-match. Event markers and
   intervals are distinct; queues need not peak at the exact whistle timestamp.
3. Compare baseline and disruption at the same post-match minute in Mobility.
4. In Scenario Lab, compare queue, clearance, delay, overload and utilization.
   Capacity boost and staggered departure do not improve every objective. Ties
   and unchanged results are meaningful, not errors.
5. Inspect rain effects and exploratory heat/commercial context. Historical
   values stay fixed when the synthetic mobility scenario changes.
6. Ask why a node is the bottleneck, which intervention performs best, and which
   values are synthetic. Request current transit alerts separately to demonstrate
   the web/offline boundary. Read sources before treating snippets as current facts.

## Judging Criteria

| Criterion | Demonstrable evidence | Boundary |
| --- | --- | --- |
| Impact | Baseline comparisons and intervention trade-offs | No measured real-world savings claim |
| Data Analytics | Prepared exports, units, provenance, source evidence | Historical context is exploratory |
| Innovation | Match-phase replay linked to a grounded decision assistant | Not a sophisticated microsimulation |
| Feasibility | Specific staging, throughput and covered-waiting review prompts | Not operationally approved instructions |
| Legacy | Reusable corridor/configuration approach for concerts, conventions and mega-events | Requires fresh inputs and local validation |
| Visualization | Timeline, corridor/heat maps, queue/throughput charts, objective selector | Approximate geography is labeled |
| Presentation | First-screen state/action, persistent controls, Next links | Desktop is the preferred judging format |

## Visual And Reliability Review

- Reviewed all seven pages at 1440x1000 and 390x844 with providers disabled.
  Native Next navigation completed on both viewports with no uncaught browser or
  Streamlit exceptions. Maps rendered; synthetic corridor geography is distinct
  from exploratory POI/heat context.
- Narrow layouts wrap headings, controls and recommendation text. Dense evidence
  tables retain native horizontal scrolling rather than hiding columns. Sidebar
  controls use Streamlit's native collapsed drawer on narrow displays.
- Retained the six commercial analysis tabs and their filters. Corrected the
  horizontal ranking axis, reduced bar-chart height and moved long explanatory
  subtitles into responsive captions. Scenario Lab shows one selectable objective
  chart instead of five stacked charts; all objectives remain accessible.
- Source cards and chat history remain separate from project evidence. Suggested
  questions collapse after an answer. Provider failures retain deterministic facts.
- Stable CSV reads were already cached. JSON cache expiry is now bounded to one
  minute, and repeated pressure figures use a bounded, one-minute cache keyed by
  data and replay selection. Existing contributor loaders remain cached.
- Automated coverage includes all canonical page/phase/scenario combinations,
  missing keys, empty filters/exports, malformed schemas, mocked provider failures,
  passenger conservation, chart controls, and sanitized page-level failures.
- Validation: 182 full-suite tests passed; 24 targeted service/chart tests passed
  after the final contrast, axis-tick and hover-label adjustments. Compilation,
  CI-scoped Ruff, dependency compatibility, whitespace and deployment-bundle
  checks passed. No credential-pattern matches or user-specific absolute paths
  were found in the inspected tracked source/documentation files; no environment
  secret file is tracked. No live provider calls or package installs were made.

Screenshots from this local review are temporary artifacts under
`/tmp/finalflow-polish/`, not deployment assets or new project data.

## Local Demo

### Local Runtime Compatibility Follow-up

The generic unavailable-data banners were reproduced on Streamlit 1.42:
`width="stretch"` raised a table-rendering TypeError, although prepared data was
present. Shared responsive sizing now selects the installed element's supported
API for tables, charts, images and buttons, retaining the modern API on 1.60.
Four sizing regressions passed on 1.42. A provider-disabled browser rehearsal
confirmed corridor, commercial, weather and scenario views render their tables
and charts without the page-error fallback. Desktop and narrow screenshots are
temporary artifacts in `/tmp/finalflow-sizing/`. The temporary server was stopped.
Genuinely missing exports still report their own unavailable-data state.

From the repository root, using the existing declared environment:

```bash
FINALFLOW_DISABLE_OPENAI=true FINALFLOW_DISABLE_SEARCH=true \
  .venv/bin/python -m streamlit run paddydash/app.py --server.port 8502
```

Open `http://localhost:8502`. No API key is required for the deterministic demo.
For live features, configure backend-only `OPENAI_API_KEY` and `SERPAPI_API_KEY`
in the ignored `.env`; set the corresponding disable flags to `false`. Optional
settings are `OPENAI_MODEL` and `FINALFLOW_MAX_AI_REQUESTS_PER_SESSION`.
Live calls can incur charges and were not made during this review.

## Remaining Submission Boundaries

- Simulator calibration, real event-count validation and deployment remain open.
- Historical weather/POI evidence requires site-specific review. Visibility and
  shuttle utilization remain unavailable where prepared inputs do not support them.
- The AI guard intentionally limits free-form wording; deterministic evidence wins.
- Web snippets can be stale or disagree. Map basemap tiles require internet access;
  the corridor table and other local evidence remain useful without a basemap.
- Rehearse the chosen laptop, browser zoom and network before presenting. Keep the
  offline provider flags available as the dependable fallback.
