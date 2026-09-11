"""Interactive canonical phase markers and exported corridor pressure."""

import plotly.graph_objects as go
import streamlit as st

from paddydash.components.analytical_views import edge_chart, plot, prepared_table, pressure_figure
from paddydash.components.match_controls import select_timeline_phase
from paddydash.services.mobility_config import default_mobility_config
from paddydash.services.project_context import selected_context


def render_matchday_timeline() -> None:
    context = selected_context(st.session_state)
    st.title('Matchday Timeline')
    st.caption(context['scope'] + ' | Derived from synthetic scenario inputs')
    phases = default_mobility_config().phases
    options = [p.phase_id.value for p in phases]
    labels = {p.phase_id.value: p.display_label for p in phases}
    st.session_state['timeline_phase'] = context['phase_id']
    st.selectbox('Jump to match phase', options, key='timeline_phase',
                 format_func=labels.get, on_change=select_timeline_phase)
    timeline = prepared_table('match_timeline_summary.csv')
    if timeline:
        rows = sorted(timeline, key=lambda r: options.index(r['phase_id']))
        figure = go.Figure(go.Scatter(
            x=[r['time_minutes'] for r in rows], y=list(range(len(rows))),
            mode='markers', marker=dict(size=14, color=['#39B99A' if r['phase_id'] == context['phase_id'] else '#8b969e' for r in rows]),
            customdata=[[r['display_name'], r['direction'], r['expected_pressure_level']] for r in rows],
            hovertemplate='%{customdata[0]}<br>Kickoff %{x:+} min<br>%{customdata[1]} / assumed %{customdata[2]} pressure<extra></extra>'))
        figure.update_layout(height=390, xaxis_title='Minutes from kickoff', yaxis=dict(
            tickmode='array', tickvals=list(range(len(rows))), ticktext=[r['display_name'] for r in rows], autorange='reversed'))
        plot(figure, 'phase_timeline')
        st.caption('Assumed event schedule. Coincident markers share a minute; assumed pressure labels are not calculated queues.')
    nodes = prepared_table('mobility_node_timeseries.csv')
    st.subheader('Calculated queue over time')
    if nodes:
        plot(pressure_figure(nodes, context['scenario_id'], context['time_minutes']), 'timeline_pressure')
    st.subheader('Service throughput')
    edge_chart(context, 'timeline_edge')
