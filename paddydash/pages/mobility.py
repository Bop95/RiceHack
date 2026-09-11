"""Match-synchronized readiness view of deterministic synthetic corridor runs."""

import pandas as pd
import streamlit as st

from paddydash.components.mobility_charts import queue_comparison_figure
from paddydash.services.mobility_config import default_mobility_config
from paddydash.services.mobility_contract import PhaseId
from paddydash.services.mobility_simulator import default_run


def render_mobility() -> None:
    config = default_mobility_config()
    phases = {p.phase_id.value: p for p in config.phases}
    scenarios = {s.scenario_id.value: s for s in config.scenarios}
    phase_id = st.session_state.get('finalflow_phase_id', 'pre_match')
    scenario_id = st.session_state.get('finalflow_scenario_id', 'baseline')
    # Standalone page tests and old sessions receive the same safe defaults.
    if phase_id not in phases:
        phase_id = 'pre_match'
    if scenario_id not in scenarios:
        scenario_id = 'baseline'
    phase, scenario = phases[phase_id], scenarios[scenario_id]
    selected, baseline = default_run(scenario_id), default_run('baseline')
    whistle = next(p.start_minute for p in config.phases if p.phase_id == PhaseId.FINAL_WHISTLE)
    start = phase.start_minute
    end = start
    if phase.kind == 'interval':
        following = [p.start_minute for p in config.phases
                     if p.kind == 'interval' and p.start_minute > start]
        end = min(following) - config.time_step_minutes if following else selected.snapshots[-1].time_minutes
    preview = start
    if phase_id == 'pre_match':
        preview = min(end, config.demand.arrival_start_minute + 15)
    elif phase_id == 'post_match':
        preview = min(end, start + 30)
    identity = (phase_id, scenario_id)
    if st.session_state.get('finalflow_time_selection') != identity:
        st.session_state['finalflow_time_widget'] = preview
        st.session_state['finalflow_time_selection'] = identity
    minute = start
    if end > start:
        current = st.session_state.get('finalflow_time_widget', preview)
        if ('finalflow_time_widget' not in st.session_state or not isinstance(current, int)
                or not start <= current <= end or current % config.time_step_minutes):
            st.session_state['finalflow_time_widget'] = preview
        minute = st.slider('Replay minute', min_value=start, max_value=end,
                           step=config.time_step_minutes, key='finalflow_time_widget',
                           help='Elapsed minutes from kickoff, including halftime. Negative values are pre-match.')
    snapshot = next(s for s in selected.snapshots if s.time_minutes == minute)
    st.session_state['finalflow_time_minutes'] = minute
    st.session_state['finalflow_mobility_snapshot'] = snapshot.model_dump(mode='json')
    st.subheader('Mobility readiness')
    st.caption(f'{phase.display_label} · {scenario.display_label} · Kickoff {minute:+d} min')
    if minute < 0:
        stage = 'Inbound arrival'
    elif minute < whistle:
        stage = 'Match in progress'
    else:
        stage = 'Outbound departure'
    holding = sum(n.holding_passengers for n in snapshot.node_states)
    in_transit = sum(e.in_transit_passengers for e in snapshot.edge_states)
    st.markdown(f'**{stage}** · {in_transit:,} traveling · {holding:,} at the stadium · '
                f'{snapshot.total_served:,} completed return trips')
    biggest = max(snapshot.node_states, key=lambda n: n.queue)
    names = {n.node_id: n.name for n in config.nodes}
    short = {'midtown': 'Midtown', 'penn_station': 'Penn Station', 'secaucus': 'Secaucus',
             'meadowlands': 'Meadowlands', 'stadium': 'Stadium'}
    current_utilization = max(e.utilization for e in snapshot.edge_states)
    waits = [n.estimated_wait_minutes for n in snapshot.node_states]
    wait = None if None in waits else max(waits)
    status = ('Blocked' if wait is None else 'Queueing' if biggest.queue else
              'Cleared' if snapshot.total_served == config.demand.cohort_size else
              'At capacity' if current_utilization >= 1 else 'Flowing' if current_utilization else
              'Holding' if holding else 'Not started')
    first = st.columns(3)
    first[0].metric('Largest node queue', f'{biggest.queue:,}', help='People waiting after this boundary\'s service; stadium holding is excluded.')
    first[1].metric('Current utilization', f'{current_utilization:.0%}',
                    help=f'Busiest edge this boundary. Whole-run peak: {selected.peak_utilization:.0%}.')
    first[1].caption(f'Whole-run peak: {selected.peak_utilization:.0%}')
    first[2].metric('Estimated longest wait', 'Blocked' if wait is None else f'{wait:.0f} min',
                    help='Queue divided by current service capacity, rounded to steps; not an observed travel time.')
    second = st.columns(3)
    second[0].metric('Bottleneck', short[biggest.node_id] if biggest.queue else 'None',
                     help='Node with the largest residual queue; ties follow corridor order.')
    second[1].metric('Post-match clearance', f'{selected.clearance_minutes} min' if selected.completed else 'Not cleared',
                     help='Whole-run elapsed time from final whistle until all modeled return trips finish.')
    second[2].metric('Modeled status', status,
                     help='Queue and capacity indicator only, not a validated public-safety readiness assessment.')

    st.subheader('The corridor')
    st.caption('Midtown → Penn Station → Secaucus → Meadowlands → Stadium' if minute < whistle else
               'Stadium → Meadowlands → Secaucus → Penn Station → Midtown')
    rows = [{
        'Location': names[n.node_id], 'Queue': n.queue,
        'Utilization': 'N/A' if n.utilization is None else f'{n.utilization:.0%}',
        'Wait': 'Blocked' if n.estimated_wait_minutes is None else f'{n.estimated_wait_minutes:.0f} min',
        'Status': 'Bottleneck' if n.queue and n.node_id == biggest.node_id else
                  'Waiting' if n.queue else 'Holding' if n.holding_passengers else 'Clear',
    } for n in snapshot.node_states]
    table = pd.DataFrame(rows)
    styled = table.style.apply(
        lambda row: ['background-color: #fff0cc; color: #312b20' if row['Status'] == 'Bottleneck' else '' for _ in row],
        axis=1,
    )
    st.dataframe(styled, hide_index=True, use_container_width=True)
    st.caption('Node utilization excludes unbounded terminal service (N/A); queues exclude spectators held for departure.')

    st.subheader('Baseline comparison')
    st.caption('Whole replay · Scenario / modeled · Holding time is excluded from queue delay.')
    comparison = pd.DataFrame({
        'Metric': ['Peak total queue (people)', 'Clearance after whistle (min)',
                   'Queue delay proxy (person-min)', 'Overloaded steps'],
        'Baseline': [baseline.peak_queue, baseline.clearance_minutes,
                     baseline.delay_person_minutes, baseline.overloaded_steps],
        'Selected scenario': [selected.peak_queue, selected.clearance_minutes,
                              selected.delay_person_minutes, selected.overloaded_steps],
    })
    st.dataframe(comparison, hide_index=True, use_container_width=True)
    if scenario_id != 'baseline':
        if baseline.peak_queue:
            change = (baseline.peak_queue - selected.peak_queue) / baseline.peak_queue * 100
            verb = 'reduces' if change >= 0 else 'increases'
            st.markdown(f'**{scenario.display_label} {verb} peak queue by {abs(change):.1f}%.**')
        elif selected.peak_queue:
            st.markdown(f'**{scenario.display_label} adds {selected.peak_queue:,} peak queued passengers versus baseline.**')
        else:
            st.markdown(f'**{scenario.display_label} leaves peak queue unchanged at zero under these demand assumptions.**')
    st.plotly_chart(queue_comparison_figure(baseline, selected, scenario.display_label, minute, whistle),
                    use_container_width=True, config={'displaylogo': False})
    st.caption('Red line: selected moment. Dotted gold line: final whistle. Overloaded steps count boundaries with demand above any edge capacity.')
    with st.expander('Model assumptions'):
        for assumption in snapshot.assumptions:
            st.markdown(f'- {assumption}')
        st.markdown('- Capacity and wait indicators are heuristic. Historical store visits, weather and POI data are not changed by these controls.')
