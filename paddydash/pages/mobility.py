"""Prepared corridor movement, queues and access indicators."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from paddydash.components.ui import stretch_width

from paddydash.components.analytical_views import comparison, current_metrics, edge_chart, plot, prepared_table, value_text
from paddydash.services.mobility_config import default_mobility_config
from paddydash.services.project_context import selected_context


def render_mobility() -> None:
    context = selected_context(st.session_state)
    st.title('Mobility & Access')
    st.caption(context['scope'] + ' | Derived from synthetic scenario inputs')
    st.subheader('Mobility readiness')
    current_metrics(context)
    config = default_mobility_config()
    names = {n.node_id: n.name for n in config.nodes}
    st.subheader('The corridor')
    reference = prepared_table('corridor_reference.csv')
    if context['available']:
        st.session_state['finalflow_mobility_snapshot'] = {
            'scenario_id': context['scenario_id'], 'phase_id': context['phase_id'],
            'time_minutes': context['time_minutes'], 'data_type': 'derived',
            'node_states': context['nodes'], 'edge_states': context['edges']}
        direction = 'Outbound' if context['time_minutes'] >= 135 else 'Inbound / late arrivals'
        st.caption('Stadium → Meadowlands → Secaucus → Penn Station → Midtown' if direction == 'Outbound'
                   else 'Midtown → Penn Station → Secaucus → Meadowlands → Stadium')
        rows = []
        for node in context['nodes']:
            outgoing = [e for e in context['edges'] if e['edge_id'].startswith(node['node_id'] + '_to_') and e['throughput'] > 0]
            active = ', '.join(names[e['edge_id'].split('_to_')[1]] for e in outgoing) or 'No outgoing flow'
            rows.append({'Location': names[node['node_id']], 'Queue': node['queue_passengers'],
                         'Utilization': value_text(node['utilization'], percent=True), 'Wait': value_text(node['estimated_wait_minutes'], ' min'),
                         'Flow toward': active, 'Status': 'Bottleneck' if node['node_id'] == context['bottleneck_id'] else 'Clear' if node['queue_passengers'] == 0 else 'Waiting'})
        frame = pd.DataFrame(rows)
        styled = frame.style.apply(lambda row: ['background-color: #fff0cc; color: #312b20' if row['Status'] == 'Bottleneck' else '' for _ in row], axis=1)
        st.dataframe(styled, hide_index=True, **stretch_width(st.dataframe))
        st.caption(f"Total residual corridor queue: {context['pressure']:,} people. Stadium holding is excluded. Utilization reflects service throughput, not unconstrained demand.")
        if reference:
            ordered = sorted(reference, key=lambda r: r['order'])
            counts = {r['node_id']: r for r in context['nodes']}
            fig = go.Figure(go.Scattermap(lat=[r['latitude'] for r in ordered], lon=[r['longitude'] for r in ordered],
                mode='lines+markers', marker=dict(size=14, color=['#bd3950' if r['node_id'] == context['bottleneck_id'] else '#087e8b' for r in ordered]),
                text=[r['display_name'] for r in ordered],
                customdata=[[counts[r['node_id']]['queue_passengers'], counts[r['node_id']]['estimated_wait_minutes']] for r in ordered],
                hovertemplate='%{text}<br>Queue %{customdata[0]:,}<br>Wait %{customdata[1]} min<extra></extra>'))
            fig.update_layout(map=dict(style='carto-positron', center=dict(lat=40.765, lon=-74.025), zoom=10), height=340)
            st.caption('Approximate corridor reference — synthetic for scenario visualization. Lines connect reference points, not surveyed routes.')
            plot(fig, 'corridor_map')
    nodes = prepared_table('mobility_node_timeseries.csv')
    if nodes:
        st.subheader('Queues by node')
        selected_nodes = st.multiselect('Nodes', list(names), default=list(names), format_func=names.get, key='mobility_nodes')
        frame = pd.DataFrame([r for r in nodes if r['scenario_id'] == context['scenario_id'] and r['node_id'] in selected_nodes])
        if frame.empty:
            st.info('No nodes selected.')
        else:
            frame['Location'] = frame.node_id.map(names)
            fig = px.area(frame.sort_values('time_minutes'), x='time_minutes', y='queue_passengers', color='Location',
                          labels={'time_minutes': 'Minutes from kickoff', 'queue_passengers': 'Queued people'})
            fig.add_vline(x=context['time_minutes'], line_color='#bd3950')
            plot(fig, 'node_queues')
    edge_chart(context, 'mobility_edge')
    st.subheader('Baseline comparison')
    if context['available'] and context['baseline']['available']:
        baseline = context['baseline']
        st.caption(f"Same minute: baseline total queue {baseline['pressure']:,}, selected total queue {context['pressure']:,}.")
    comparison(context, 'mobility_comparison')
    st.subheader('First and last mile')
    access = prepared_table('mobility_access_summary.csv')
    row = next((r for r in access if r['scenario_id'] == context['scenario_id']), None)
    if row:
        cards = st.columns(3)
        cards[0].metric('Peak pedestrian load ratio', f"{row['peak_pedestrian_load_ratio']:.3f}")
        cards[1].metric('Peak modeled parking use', f"{row['peak_parking_utilization']:.1%}")
        cards[2].metric('Peak rideshare demand / interval', f"{row['peak_rideshare_passengers']:,}")
        modes = {'Rail': row['rail_passenger_total'], 'Walk': row['walk_passenger_total'], 'Road': row['road_passenger_total'], 'Shuttle': row['shuttle_passenger_total']}
        plot(px.bar(x=list(modes), y=list(modes.values()), labels={'x': 'Mode', 'y': 'Passenger movements, full replay'}), 'access_modes')
        st.caption(f"Derived | mobility_access_summary.csv | Whole-run inbound and outbound movements, not unique spectators. Peak shuttle passengers / interval: {row['peak_shuttle_passengers']:,}. Shuttle utilization unavailable: no capacity input.")
