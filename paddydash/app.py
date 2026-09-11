"""FinalFlow match-synchronized mobility and commercial intelligence dashboard."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from paddydash.pages.ask_finalflow import render_ask_finalflow
from paddydash.components.match_controls import render_match_controls
from paddydash.pages.mobility import render_mobility
from paddydash.pages.project_evidence import render_project_evidence
from paddydash.pages.overview import render_overview
from paddydash.pages.scenario_explorer import render_scenario_explorer
from paddydash.pages.spatial_heat_map import render_spatial_heat_map
from paddydash.pages.store_visit_explorer import render_store_visit_explorer
from paddydash.services.data_service import load_dashboard_data


st.set_page_config(
    page_title="FinalFlow Mobility Readiness",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="auto",
)


def main() -> None:
    st.image(str(REPOSITORY_ROOT / 'asset/rice_hack.png'), use_container_width=True)
    render_match_controls()
    try:
        load_dashboard_data()
    except (FileNotFoundError, ValueError) as error:
        st.error("The prepared dashboard data could not be loaded.")
        st.code(str(error))
        st.info(
            "Run the cleaning, Streamlit-summary, and synthetic-scenario scripts "
            "described in paddydash/README.md, then restart the app."
        )
        st.stop()

    pages = {
        "Match readiness": [
            st.Page(render_mobility, title="Mobility readiness", icon=":material/train:", default=True),
            st.Page(render_project_evidence, title="Commercial & weather context", icon=":material/storefront:"),
        ],
        "Store-Visit Intelligence": [
            st.Page(render_overview, title="Overview", icon="📊"),
            st.Page(
                render_store_visit_explorer,
                title="Store-Visit Explorer",
                icon="🔎",
            ),
            st.Page(
                render_scenario_explorer,
                title="Scenario Explorer",
                icon="🧪",
            ),
            st.Page(
                render_spatial_heat_map,
                title="Spatial & Heat Map",
                icon="🗺️",
            ),
            st.Page(render_ask_finalflow, title="Ask FinalFlow", icon="💬"),
        ]
    }
    navigation = st.navigation(pages)
    st.sidebar.markdown("---")
    st.sidebar.caption(
        "Store visits are a commercial-activity proxy. Synthetic scenarios are "
        "illustrative and are always labeled."
    )
    navigation.run()


if __name__ == "__main__":
    main()
