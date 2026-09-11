"""FinalFlow match-synchronized mobility and commercial intelligence dashboard."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from paddydash.pages.ask_finalflow import render_ask_finalflow
from paddydash.components.finalflow_shell import render_header, render_methodology
from paddydash.pages.matchday_timeline import render_matchday_timeline
from paddydash.pages.mobility import render_mobility
from paddydash.pages.project_evidence import render_project_evidence
from paddydash.pages.overview import render_overview
from paddydash.pages.scenario_explorer import render_scenario_explorer
from paddydash.pages.weather_heat import render_weather_heat


st.set_page_config(
    page_title="FinalFlow Mobility Readiness",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="auto",
)


def main() -> None:
    render_header(REPOSITORY_ROOT)

    pages = {
        "FinalFlow": [
            st.Page(_safe_page(render_overview), title="Executive Overview", icon=":material/dashboard:", url_path="overview", default=True),
            st.Page(_safe_page(render_matchday_timeline), title="Matchday Timeline", icon=":material/timeline:", url_path="timeline"),
            st.Page(_safe_page(render_mobility), title="Mobility & Access", icon=":material/train:", url_path="mobility"),
            st.Page(_safe_page(render_project_evidence), title="Commercial & POI Intelligence", icon=":material/storefront:", url_path="commercial-poi"),
            st.Page(_safe_page(render_weather_heat), title="Weather & Heat", icon=":material/cloud:", url_path="weather-heat"),
            st.Page(_safe_page(render_scenario_explorer), title="Scenario Lab", icon=":material/biotech:", url_path="scenario-lab"),
            st.Page(_safe_page(render_ask_finalflow), title="Ask FinalFlow", icon=":material/chat:", url_path="ask-finalflow"),
        ]
    }
    navigation = st.navigation(pages)
    navigation.run()
    journey = ['Executive Overview', 'Matchday Timeline', 'Mobility & Access',
               'Scenario Lab', 'Weather & Heat', 'Commercial & POI Intelligence', 'Ask FinalFlow']
    next_title = journey[(journey.index(navigation.title) + 1) % len(journey)]
    next_page = next(page for page in pages['FinalFlow'] if page.title == next_title)
    st.divider()
    st.page_link(next_page, label=f'Next: {next_title}', icon=':material/arrow_forward:')
    render_methodology()


def _safe_page(renderer):
    """Keep the app navigable when an optional prepared table is absent."""
    def wrapped() -> None:
        try:
            renderer()
        except (OSError, KeyError, TypeError, ValueError, IndexError, ZeroDivisionError):
            st.warning("This section could not finish loading. Try reloading the page; other views remain available.")
    return wrapped


if __name__ == "__main__":
    main()
