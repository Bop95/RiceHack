"""Shared FinalFlow shell elements kept independent of individual pages."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from paddydash.components.match_controls import get_selected_match_state, render_match_controls
from paddydash.components.ui import stretch_width
from paddydash.services.project_context import selected_context


PROVENANCE_TEXT = (
    "provided = source-backed context · derived = calculated · "
    "synthetic = scenario assumption · web = current external information"
)


def render_header(repository_root: Path) -> None:
    """Render the consistent shell header and the currently selected model state."""
    left, right = st.columns([4, 2])
    with left:
        st.title("FinalFlow")
        st.caption("Match-Synchronized Mobility Readiness Platform | 2026 World Cup Final - NY/NJ Corridor")
    with right:
        logo = repository_root / "asset" / "rice_hack.png"
        if logo.is_file():
            st.image(str(logo), **stretch_width(st.image))
    with st.sidebar:
        st.subheader('Match state')
        render_match_controls(compact=True)
        with st.expander('About this data'):
            st.write('Provided: historical source-backed context. Synthetic: event demand and capacity assumptions. Derived: calculated simulation outputs. Web: current search excerpts, not verified operations.')
            st.caption('Scenario planning, not a real-time operational forecast.')
    phase_id, scenario_id, phase, scenario = get_selected_match_state()
    try:
        context = selected_context(st.session_state)
        recommendation = context['actions'][0]['recommendation'] if context['actions'] else 'No current action supported by available rules.'
        queue = 'Unavailable' if context['queue'] is None else f"{context['queue']:,}" if context["queue"] else "Clear"
        with st.container():
            st.markdown(f"**{phase.display_label} / {scenario.display_label}** · Bottleneck: **{context['bottleneck']}** · Queue: {queue}")
            st.caption(f"Current recommendation: {recommendation}")
    except (KeyError, StopIteration, ValueError):
        st.warning("Current modeled state is unavailable; other prepared views remain accessible.")
    st.caption('Midtown Manhattan → Penn Station → Secaucus Junction → Meadowlands Station → Stadium')
    st.caption('Scenario / modeled · Derived from synthetic inputs · Not observed real-time conditions')
    st.session_state["selected_phase_id"] = phase_id
    st.session_state["selected_scenario_id"] = scenario_id


def source_note(data_type: str, note: str) -> None:
    """Show concise provenance without turning source notes into an extra panel."""
    st.caption(f"{data_type.title()} | {note}")


def render_methodology() -> None:
    """Keep the demonstration's scope and limitations accessible on every view."""
    with st.expander('Methodology & Assumptions'):
        st.markdown('**Provided:** historical Rice source data and context. **Synthetic:** event-specific demand, mode shares and capacity assumptions. **Derived:** calculated queues, waits and comparisons. **Web:** current public search excerpts requiring source verification.')
        st.write('The five-minute scenario model represents the Midtown–stadium corridor, including inbound travel, match-time holding and outbound departure. Compare scenarios at the same replay minute; whole-run clearance is not remaining wait time.')
        st.write('Passenger counts are not observed attendance. Historical weather is multi-station context, not a venue forecast. Approximate corridor points and vendor examples are not verified infrastructure or approved placement plans.')
        st.caption('Calibration, operational validation and deployment remain unfinished. The approach could be adapted to concerts, conventions and other mega-events with new local inputs and validation.')
