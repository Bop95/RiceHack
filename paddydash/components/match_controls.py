"""Global canonical match selection shared by all FinalFlow pages."""

import streamlit as st

from paddydash.services.mobility_config import default_mobility_config
from paddydash.services.finalflow_data import phase_window


def select_timeline_phase() -> None:
    """Apply a timeline choice before the global widgets are instantiated."""
    st.session_state['finalflow_phase_id'] = st.session_state['timeline_phase']
    st.session_state.pop('finalflow_time_selection', None)


def get_selected_match_state():
    """Resolve canonical state while retaining the original widget keys."""
    config = default_mobility_config()
    phases = {phase.phase_id.value: phase for phase in config.phases}
    scenarios = {scenario.scenario_id.value: scenario for scenario in config.scenarios}
    phase_id = st.session_state.get("finalflow_phase_id")
    scenario_id = st.session_state.get("finalflow_scenario_id")
    if phase_id not in phases:
        phase_id = st.session_state.get("selected_phase_id")
    if scenario_id not in scenarios:
        scenario_id = st.session_state.get("selected_scenario_id")
    phase_id = phase_id if phase_id in phases else "pre_match"
    scenario_id = scenario_id if scenario_id in scenarios else "baseline"
    if st.session_state.get("finalflow_phase_id") != phase_id:
        st.session_state["finalflow_phase_id"] = phase_id
    if st.session_state.get("finalflow_scenario_id") != scenario_id:
        st.session_state["finalflow_scenario_id"] = scenario_id
    st.session_state["selected_phase_id"] = phase_id
    st.session_state["selected_scenario_id"] = scenario_id
    return phase_id, scenario_id, phases[phase_id], scenarios[scenario_id]


def render_match_controls() -> None:
    config = default_mobility_config()
    phases = {p.phase_id.value: p for p in config.phases}
    scenarios = {s.scenario_id.value: s for s in config.scenarios}
    get_selected_match_state()
    with st.container():
        left, right = st.columns([3, 2])
        left.selectbox(
            'Match phase', options=list(phases), key='finalflow_phase_id',
            format_func=lambda value: phases[value].display_label,
            help='Match markers use the shared replay clock. Extra time is included in this scenario.',
        )
        right.selectbox(
            'Mobility scenario', options=list(scenarios), key='finalflow_scenario_id',
            format_func=lambda value: scenarios[value].display_label,
            help='Scenario / modeled. Changes transport assumptions, not historical business or weather data.',
        )
    st.session_state["selected_phase_id"] = st.session_state["finalflow_phase_id"]
    st.session_state["selected_scenario_id"] = st.session_state["finalflow_scenario_id"]
    selection = (st.session_state['finalflow_phase_id'], st.session_state['finalflow_scenario_id'])
    start, end, preview = phase_window(selection[0])
    previous = st.session_state.get('finalflow_time_selection')
    minute = st.session_state.get('finalflow_time_widget', preview)
    if not previous or previous[0] != selection[0] or not isinstance(minute, int) or not start <= minute <= end or minute % 5:
        minute = preview
    st.session_state['finalflow_time_widget'] = minute
    if end > start:
        minute = st.slider('Replay minute', start, end, step=5, key='finalflow_time_widget',
                           help='Elapsed minutes from kickoff including halftime; all displayed times are scenario assumptions.')
    else:
        st.caption(f'Kickoff {minute:+d} min · match marker')
    if st.session_state.get('finalflow_selection') != (*selection, minute):
        st.session_state.pop('finalflow_mobility_snapshot', None)
    st.session_state['finalflow_time_minutes'] = minute
    st.session_state['finalflow_time_selection'] = selection
    st.session_state['finalflow_selection'] = (*selection, minute)
    st.caption('Derived from synthetic scenario inputs · Not observed real-time passenger data.')
