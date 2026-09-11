"""Global canonical match selection shared by all FinalFlow pages."""

import streamlit as st

from paddydash.services.mobility_config import default_mobility_config


def render_match_controls() -> None:
    config = default_mobility_config()
    phases = {p.phase_id.value: p for p in config.phases}
    scenarios = {s.scenario_id.value: s for s in config.scenarios}
    for key, options, default in (
        ('finalflow_phase_id', phases, 'pre_match'),
        ('finalflow_scenario_id', scenarios, 'baseline'),
    ):
        if not isinstance(st.session_state.get(key), str) or st.session_state[key] not in options:
            st.session_state[key] = default
    st.title('FinalFlow')
    left, right = st.columns([3, 2])
    left.selectbox(
        'Match phase', options=list(phases), key='finalflow_phase_id',
        format_func=lambda value: phases[value].display_label,
        help='Match markers use the shared replay clock. Extra time is included in this scenario.',
    )
    labels = {'baseline': 'Baseline', 'rail_disruption': 'Rail Disruption',
              'rail_capacity_boost': 'Rail Capacity Boost', 'rain': 'Rain',
              'staggered_departure': 'Staggered Departure'}
    right.selectbox(
        'Mobility scenario', options=list(scenarios), key='finalflow_scenario_id',
        format_func=lambda value: labels[value],
        help='Scenario / modeled. Changes transport assumptions, not historical business or weather data.',
    )
    selection = (st.session_state['finalflow_phase_id'], st.session_state['finalflow_scenario_id'])
    if st.session_state.get('finalflow_selection') != selection:
        for key in ('finalflow_mobility_snapshot', 'finalflow_time_minutes', 'finalflow_time_selection'):
            st.session_state.pop(key, None)
        st.session_state['finalflow_selection'] = selection
    st.caption('Scenario / modeled · Synthetic corridor replay, not observed real-time passenger data.')
