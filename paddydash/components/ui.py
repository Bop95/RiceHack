"""Small shared interface elements for labels, evidence, and interpretations."""

from __future__ import annotations

from typing import Iterable

import streamlit as st

from paddydash.services.analytics import EvidenceItem


def data_type_label(data_type: str) -> None:
    descriptions = {
        "provided": "Original project source data",
        "derived": "Calculated from the cleaned store-visit dataset",
        "synthetic": "Generated for interface testing and scenario exploration",
        "web": "Retrieved from an external online source",
    }
    st.caption(
        f"**Data type: `{data_type}`** - {descriptions.get(data_type, 'Project data')}"
    )


def interpretation(observation: str, project_value: str, limitation: str) -> None:
    with st.container(border=True):
        st.markdown(f"**Observation:** {observation}")
        st.markdown(f"**Project value:** {project_value}")
        st.markdown(f"**Limitation:** {limitation}")


def evidence_panel(evidence: Iterable[EvidenceItem]) -> None:
    rows = [
        {"Evidence": item.label, "Value": str(item.value), "Source": item.source}
        for item in evidence
    ]
    if not rows:
        return
    st.markdown("#### Supporting evidence")
    st.dataframe(rows, width="stretch", hide_index=True)


def page_intro(title: str, explanation: str, data_type: str) -> None:
    st.title(title)
    st.write(explanation)
    data_type_label(data_type)
