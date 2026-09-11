# FinalFlow Dashboard Data Readiness

This inventory describes the compact data layer available before the next
Streamlit integration. It does not validate operational conditions, forecast
match-day demand, or replace site-specific review.

| Planned page | Available compact data | Provenance | Ready | Remaining issue |
| --- | --- | --- | --- | --- |
| Executive Overview | `executive_kpis.csv`, `scenario_summary.csv`, `summary_statistics.csv` | derived from synthetic mobility and historical commercial summaries | Yes | KPIs must retain their individual source labels; they are not one combined event measurement. |
| Matchday Timeline | `match_timeline_summary.csv`, `corridor_reference.csv` | derived timeline from synthetic configuration; synthetic map references | Yes | Phase times are illustrative, not an official match schedule. |
| Mobility & Access | mobility node/edge time series, access summary, corridor/zone references | derived from synthetic demand and capacity inputs | Yes | Road and shuttle are direct stadium-boundary access, not modeled network edges. |
| Commercial & POI Intelligence | `commercial_context.csv`, spatial heat locations, store-visit summaries, business scenarios | derived historical/exploratory context plus synthetic business examples | Yes | No verified stadium vendor-placement dataset or Phuong Anh Power BI deliverable is present. |
| Weather & Heat | `weather_heat_context.csv`, historical weather risk summary, spatial heat locations | derived historical and exploratory context | Yes | No venue-specific forecast, weather station mapping, or validated urban-heat survey exists. |
| Scenario Lab | `scenario_comparison.csv`, intervention comparison, recommendation catalog | derived replay outputs from synthetic assumptions | Yes | Only rail-capacity-50 and staggered-departure catalog actions currently have matching modeled scenarios. |
| Ask FinalFlow | `finalflow_ai_context.json`, recommendation catalog, scenario/timeline context | derived compact context with source labels | Yes | The assistant must use deterministic facts and must not treat synthetic values as observed operations. |

## Support Tables

- `data/synthetic/corridor_reference.csv`: five approximate synthetic corridor
  map points. These are not official coordinates or access geometry.
- `data/synthetic/zone_reference.csv`: five synthetic analysis zones anchored
  to the corridor. These are not official boundaries.
- `data/exports/recommendation_catalog.csv`: curated deterministic display rules.
  They are operational heuristics, not optimized or safety-approved guidance.
- `data/exports/finalflow_ai_context.json`: a compact machine-readable brief;
  it intentionally excludes raw POI, store-visit, weather, and mobility tables.

All exports carry `data_type` and, where sources differ, `source_data_type`.
Allowed labels are `provided`, `derived`, `synthetic`, and `web`.
