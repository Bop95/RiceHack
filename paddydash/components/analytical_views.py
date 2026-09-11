"""Shared charts and compact metrics for the prepared mobility exports."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from paddydash.components.ui import stretch_width

from paddydash.services.finalflow_data import change_text, load_table
from paddydash.services.mobility_config import default_mobility_config


COMPARISON_METRICS = (
    ('peak_queue_passengers', 'Peak total queue', 'people'),
    ('total_clearance_minutes', 'Clearance after whistle', 'min'),
    ('passenger_delay_proxy_person_minutes', 'Queue delay proxy', 'person-min'),
    ('overloaded_intervals', 'Overloaded intervals', '5-minute intervals'),
    ('peak_utilization', 'Peak utilization', 'ratio'),
)


def prepared_table(filename: str) -> list[dict]:
    rows, error = load_table(filename)
    if error:
        st.warning(error)
    return rows


def plot(figure: go.Figure, key: str) -> None:
    figure.update_layout(margin=dict(l=10, r=10, t=50, b=35), font=dict(size=12),
                         height=figure.layout.height or 340,
                         legend=dict(orientation='h', y=1.08, x=0), separators='.,')
    st.plotly_chart(figure, **stretch_width(st.plotly_chart), config={'displaylogo': False}, key=key)
    if isinstance(figure.layout.meta, dict) and figure.layout.meta.get('caption'):
        st.caption(figure.layout.meta['caption'])


def value_text(value: float | None, suffix: str = '', percent: bool = False) -> str:
    if value is None:
        return 'Unavailable'
    return f'{value:.0%}' if percent else f'{value:,.0f}{suffix}'


def current_metrics(context: dict) -> None:
    if context['error']:
        st.warning(context['error'])
    st.markdown(f"**{context['status']}** · Bottleneck: **{context['bottleneck']}**")
    st.caption('Heuristic readiness indicator, not a validated public-safety assessment. Derived from synthetic scenario inputs.')
    cards = st.columns(4)
    cards[0].metric('Largest node queue', value_text(context['queue']), help='People waiting at the busiest node at this replay minute; excludes stadium holding.')
    cards[1].metric('Current utilization', value_text(context['utilization'], percent=True), help='Maximum realized edge throughput divided by effective capacity. A low ratio does not imply low passenger demand everywhere.')
    cards[2].metric('Estimated longest wait', value_text(context['wait'], ' min'), help='Maximum modeled node wait at this replay minute, not an observed passenger journey.')
    summary = context['summary'] or {}
    cards[3].metric('Post-match clearance', value_text(summary.get('total_clearance_minutes'), ' min'),
                   help='Whole-run elapsed time after final whistle, not remaining time from the selected moment.')


def recommendations(context: dict) -> None:
    st.subheader('Recommended actions now')
    if not context['actions']:
        st.info('No applicable action is supported by the available current-state rules.')
    for action in context['actions'][:3]:
        st.markdown(action['recommendation'])
        st.caption(f"{action['evidence_type']} | {action['metric']} = {action['trigger_value']} | {action['scope']} | {action['source_file']}")
    st.caption('Curated review prompts; not optimal or safety-approved interventions.')


@st.cache_data(show_spinner=False, ttl=60, max_entries=64)
def pressure_figure(rows: list[dict], scenario_id: str, minute: int) -> go.Figure:
    """Sum residual node queues once per time boundary; no passenger double counting."""
    figure = go.Figure()
    frame = pd.DataFrame(rows)
    if frame.empty:
        return figure
    for scenario in dict.fromkeys(('baseline', scenario_id)):
        subset = frame[frame.scenario_id.eq(scenario)]
        if subset.empty:
            continue
        totals = subset.groupby('time_minutes', sort=True).queue_passengers.sum()
        phase_labels = {p.phase_id.value: p.display_label for p in default_mobility_config().phases}
        phase_at_time = subset.groupby('time_minutes', sort=True).phase_id.first().map(phase_labels)
        figure.add_scatter(x=totals.index, y=totals.values, name=scenario.replace('_', ' ').title(),
                           customdata=phase_at_time.values,
                           mode='lines', line=dict(width=3, color='#8b969e' if scenario == 'baseline' and scenario_id != 'baseline' else '#39B99A', dash='dash' if scenario == 'baseline' and scenario_id != 'baseline' else 'solid'),
                           hovertemplate='%{customdata}<br>Kickoff %{x:+} min<br>%{y:,} people queued<extra>%{fullData.name}</extra>')
    config = default_mobility_config()
    figure.add_vline(x=minute, line_color='#bd3950', annotation_text='Selected minute')
    figure.add_vline(x=next(p.start_minute for p in config.phases if p.phase_id.value == 'final_whistle'), line_dash='dot')
    figure.update_layout(height=330, xaxis_title='Minutes from kickoff',
                         yaxis_title='Queued people', hovermode='x unified')
    return figure


def edge_chart(context: dict, key: str) -> None:
    rows = prepared_table('mobility_edge_timeseries.csv')
    if not rows:
        return
    edges = default_mobility_config().edges
    edge_id = st.selectbox('Corridor edge', [e.edge_id for e in edges],
                           format_func=lambda v: v.replace('_to_', ' -> ').replace('_', ' ').title(), key=key + '_edge')
    frame = pd.DataFrame([r for r in rows if r['scenario_id'] == context['scenario_id'] and r['edge_id'] == edge_id])
    if frame.empty:
        st.info('No edge records match this selection.')
        return
    figure = px.line(frame.sort_values('time_minutes'), x='time_minutes', y=['throughput', 'capacity'],
                     labels={'time_minutes': 'Minutes from kickoff', 'value': 'People / 5-minute interval', 'variable': 'Measure'})
    figure.add_vline(x=context['time_minutes'], line_color='#bd3950')
    plot(figure, key)
    st.caption('Derived | mobility_edge_timeseries.csv | Edge crossings are not unique passenger totals.')


def comparison_rows(baseline: dict, selected: dict) -> list[dict]:
    return [{'Metric': f'{label} ({unit})', 'Baseline': baseline.get(field),
             'Selected scenario': selected.get(field)} for field, label, unit in COMPARISON_METRICS]


def comparison(context: dict, key: str) -> None:
    baseline, selected = context['baseline']['summary'], context['summary']
    if not baseline or not selected:
        st.info('Whole-run scenario comparison is unavailable.')
        return
    frame = pd.DataFrame(comparison_rows(baseline, selected))
    utilization = frame['Metric'].str.contains('utilization', case=False)
    frame.loc[utilization, 'Metric'] = frame.loc[utilization, 'Metric'].str.replace('(ratio)', '(%)', regex=False)
    styled = frame.style.format({'Baseline': '{:,.0f}', 'Selected scenario': '{:,.0f}'}, na_rep='Unavailable')
    styled = styled.format('{:.1%}', subset=(frame.index[utilization], ['Baseline', 'Selected scenario']), na_rep='Unavailable')
    st.dataframe(styled, hide_index=True, **stretch_width(st.dataframe))
    st.write(change_text('Peak queue', baseline['peak_queue_passengers'], selected['peak_queue_passengers']))
    rows = prepared_table('mobility_node_timeseries.csv')
    if rows:
        plot(pressure_figure(rows, context['scenario_id'], context['time_minutes']), key)


def spatial_explorer(key: str) -> None:
    """Reuse the reviewed, bounded spatial loader and map on both context pages."""
    from paddydash.components.charts import spatial_heat_map_figure
    from paddydash.services.data_service import load_spatial_heat_data
    try:
        rows = load_spatial_heat_data()
    except (OSError, ValueError, KeyError, TypeError):
        st.info('Reviewed spatial/heat evidence is unavailable.')
        return
    if not rows:
        st.info('No reviewed locations are available.')
        return
    left, right = st.columns(2)
    cities = left.multiselect('City', sorted({r['city'] for r in rows}), key=key + '_cities', placeholder='All cities')
    categories = right.multiselect('POI category', sorted({r['top_category'] for r in rows}), key=key + '_categories', placeholder='All categories')
    left, right = st.columns(2)
    heat = left.multiselect('Heat concern', sorted({r['heat_concern'] for r in rows}), default=sorted({r['heat_concern'] for r in rows}), key=key + '_heat')
    parking = right.selectbox('Parking evidence', ['All', 'Has parking', 'No parking', 'Unknown'], key=key + '_parking')
    filtered = [r for r in rows if (not cities or r['city'] in cities) and (not categories or r['top_category'] in categories)
                and r['heat_concern'] in heat and (parking == 'All' or r['includes_parking'] is {'Has parking': True, 'No parking': False, 'Unknown': None}[parking])]
    st.caption(f'Derived | spatial_heat_locations.csv | {len(filtered):,} of {len(rows):,} exploratory NY/NJ locations. Not verified event vendor sites.')
    if not filtered:
        st.info('No locations match these filters.')
        return
    figure = spatial_heat_map_figure(filtered)
    figure.update_layout(title_text='', height=530)
    plot(figure, key + '_map')
    st.caption('Heat is a nearby UHI match within 250 m, not an on-site temperature. Unknown heat remains insufficient evidence. Parking flags do not count available spaces.')
    frame = pd.DataFrame(filtered)
    opportunity = frame.groupby(['commercial_opportunity', 'heat_concern']).size().reset_index(name='Locations')
    plot(px.bar(opportunity, x='commercial_opportunity', y='Locations', color='heat_concern',
                labels={'commercial_opportunity': 'Relative commercial opportunity', 'heat_concern': 'Heat concern'}), key + '_opportunity')
    with st.expander('Location evidence and review classifications'):
        st.dataframe(frame[['location_name', 'city', 'top_category', 'spending_level', 'includes_parking', 'nearby_uhi', 'heat_concern', 'recommendation', 'reason', 'data_type']], hide_index=True, **stretch_width(st.dataframe))
