"""Shared FinalFlow shell elements kept independent of individual pages."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from paddydash.components.match_controls import get_selected_match_state, render_match_controls
from paddydash.services.project_context import selected_context


PROVENANCE_TEXT = (
    "provided = source-backed context · derived = calculated · "
    "synthetic = scenario assumption · web = current external information"
)


def render_header(repository_root: Path) -> None:
    """Render the consistent shell header and the currently selected model state."""
    left, right = st.columns([5, 1])
    with left:
        st.title("FinalFlow")
        st.caption("Match-Synchronized Mobility Readiness Platform | 2026 World Cup Final - NY/NJ Corridor")
    with right:
        logo = repository_root / "asset" / "rice_hack.png"
        if logo.is_file():
            st.image(str(logo), width=112)
    render_match_controls()
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
    st.caption(PROVENANCE_TEXT)
    st.session_state["selected_phase_id"] = phase_id
    st.session_state["selected_scenario_id"] = scenario_id


def source_note(data_type: str, note: str) -> None:
    """Show concise provenance without turning source notes into an extra panel."""
    st.caption(f"{data_type.title()} | {note}")
