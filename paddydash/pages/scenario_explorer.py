"""Scenario comparisons and retained synthetic commercial exploration."""

import pandas as pd
import plotly.express as px
import streamlit as st

from paddydash.components.analytical_views import COMPARISON_METRICS, comparison, plot, prepared_table
from paddydash.components.charts import scenario_comparison_rows_figure, scenario_risk_figure
from paddydash.components.ui import interpretation, stretch_width
from paddydash.services.analytics import SYNTHETIC_LIMITATION
from paddydash.services.data_service import load_dashboard_data
from paddydash.services.finalflow_data import change_text
from paddydash.services.project_context import selected_context
from scripts.synthetic.generate_store_visit_scenarios import DISCLAIMER


def render_scenario_explorer() -> None:
    context = selected_context(st.session_state)
    st.title('Scenario Lab')
    st.caption(context['scope'] + ' | Derived from synthetic scenario inputs')
    comparison(context, 'scenario_pressure')
    summaries = prepared_table('scenario_summary.csv')
    catalog = prepared_table('scenario_comparison.csv')
    names = {r['scenario_id']: r['name'] for r in catalog}
    if summaries:
        st.subheader('Compare interventions across the full replay')
        selected_ids = st.multiselect('Scenarios to compare', [r['scenario_id'] for r in summaries],
            default=[r['scenario_id'] for r in summaries], format_func=lambda x: names.get(x, x.replace('_', ' ').title()), key='lab_scenarios')
        filtered = [r for r in summaries if r['scenario_id'] in selected_ids]
        if not filtered:
            st.info('No scenarios selected.')
        else:
            frame = pd.DataFrame(filtered)
            frame['Scenario'] = frame.scenario_id.map(lambda v: names.get(v, v))
            labels = {label: (metric, unit) for metric, label, unit in COMPARISON_METRICS}
            label = st.selectbox('Comparison metric', list(labels), key='lab_comparison_metric')
            metric, unit = labels[label]
            colors = {row['Scenario']: '#39B99A' if row['scenario_id'] == context['scenario_id']
                      else '#8b969e' if row['scenario_id'] == 'baseline' else '#547d99'
                      for row in frame.to_dict('records')}
            fig = px.bar(frame, y='Scenario', x=metric, color='Scenario', orientation='h',
                         labels={metric: unit}, color_discrete_map=colors)
            fig.update_layout(height=320, showlegend=False)
            fig.update_xaxes(tickformat='.0%' if metric == 'peak_utilization' else ',.0f')
            plot(fig, 'lab_selected_metric')
            st.caption('Green identifies the selected scenario when included. Queue relief, clearance and delay are different objectives; there is no single best intervention across all objectives.')
        st.subheader('What changes under this scenario?')
        base, selected = context['baseline']['summary'], context['summary']
        if base and selected:
            for field, label, _ in COMPARISON_METRICS:
                if field == 'peak_utilization':
                    st.write(f"Peak utilization: {base[field]:.1%} to {selected[field]:.1%}.")
                else:
                    st.write(change_text(label, base[field], selected[field]))
        st.caption('These are alternative scenario runs, not additive interventions. Unchanged metrics do not imply a failed intervention.')
    st.subheader('Intervention evidence')
    interventions = prepared_table('intervention_comparison.csv')
    if interventions:
        modeled = [r for r in interventions if r['evaluation_status'] == 'modeled']
        pending = [r for r in interventions if r['evaluation_status'] != 'modeled']
        if modeled:
            with st.expander('Evaluated scenario effects and provenance'):
                st.dataframe(modeled, hide_index=True, **stretch_width(st.dataframe))
        with st.expander('Catalog-only interventions: effects not evaluated'):
            st.dataframe([{k: r[k] for k in ('name', 'evaluation_status', 'assumption_note')} for r in pending], hide_index=True, **stretch_width(st.dataframe))
        st.caption('Derived comparison of synthetic scenarios. Missing effects remain unavailable; no estimated savings are assigned to catalog-only entries.')


def render_commercial_scenarios() -> None:
    """Preserve teammate commercial scenarios separately from mobility alternatives."""
    data = load_dashboard_data()
    st.subheader('Synthetic commercial scenarios')
    st.warning(DISCLAIMER)

    all_scenarios = sorted({row["scenario_id"] for row in data.scenarios})
    all_zones = sorted({row["zone_type"] for row in data.scenarios})
    all_categories = sorted({row["category"] for row in data.scenarios})
    first, second, third = st.columns(3)
    scenarios = first.multiselect(
        "Scenario filters",
        all_scenarios,
        default=all_scenarios,
        format_func=lambda value: value.replace("_", " ").title(),
    )
    zones = second.multiselect("Zone filters", all_zones, default=all_zones)
    categories = third.multiselect(
        "Category filters", all_categories, default=all_categories[:5]
    )

    filtered = [
        row
        for row in data.scenarios
        if row["scenario_id"] in scenarios
        and row["zone_type"] in zones
        and row["category"] in categories
    ]
    if not filtered:
        st.info("No synthetic records match the current filters.")
        return

    baseline = sum(row["baseline_visits"] for row in filtered)
    estimated = sum(row["estimated_visits"] for row in filtered)
    uplift = (estimated / max(baseline, 1) - 1) * 100
    high_risk = sum(
        row["mobility_conflict_risk"] == "high" for row in filtered
    ) / len(filtered) * 100
    metrics = st.columns(4)
    metrics[0].metric("Synthetic records", f"{len(filtered):,}")
    metrics[1].metric("Baseline visits", f"{baseline:,}")
    metrics[2].metric("Estimated visits", f"{estimated:,}", f"{uplift:+.1f}%")
    metrics[3].metric("High-risk labels", f"{high_risk:.1f}%")
    st.caption(
        f"Cards and charts reflect the current filter subset: {len(filtered):,} "
        f"of {len(data.scenarios):,} synthetic records."
    )

    plot(scenario_comparison_rows_figure(filtered), 'commercial_scenario_visits')
    plot(scenario_risk_figure(filtered), 'commercial_scenario_risk')
    interpretation(
        "The filters expose how documented scenario and zone multipliers change synthetic demand and risk labels.",
        "These records let the team test filters, evidence cards, charts, and backend responses before event data exists.",
        SYNTHETIC_LIMITATION,
    )

    with st.expander("Scenario assumptions"):
        st.markdown(
            """
- Ordinary day: **1.00x** baseline
- Pre-match: **1.25x** baseline
- During match: **0.85x** baseline
- Post-match: **1.45x** baseline
- Rainy post-match: **1.20x** baseline
- Transit disruption: **1.10x** baseline

The generator uses random seed `2026`, prevents negative values, labels every
record `synthetic`, and adds documented zone and bounded-noise factors. Zone
weights are normalized to a mean of **1.00x**, so each stated scenario
multiplier remains its expected overall effect. Categories are sampled from
each selected brand's observed prepared-data category mix.
"""
        )
