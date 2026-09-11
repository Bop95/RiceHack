"""Synthetic scenario exploration page."""

from __future__ import annotations

import streamlit as st

from paddydash.components.charts import scenario_comparison_rows_figure, scenario_risk_figure
from paddydash.components.ui import interpretation, page_intro
from paddydash.services.analytics import SYNTHETIC_LIMITATION
from paddydash.services.data_service import load_dashboard_data
from scripts.synthetic.generate_store_visit_scenarios import DISCLAIMER


def render_scenario_explorer() -> None:
    data = load_dashboard_data()
    page_intro(
        "Scenario Explorer",
        "Compare a small set of reproducible interface-testing scenarios built "
        "from historical commercial-activity baselines.",
        "synthetic",
    )
    st.warning(DISCLAIMER)

    all_scenarios = sorted({row["scenario_id"] for row in data.scenarios})
    all_zones = sorted({row["zone_type"] for row in data.scenarios})
    all_categories = sorted({row["category"] for row in data.scenarios})
    first, second, third = st.columns(3)
    scenarios = first.multiselect(
        "Scenario filters",
        all_scenarios,
        default=all_scenarios,
        format_func=lambda value: value.replace("_", " ").title(),
    )
    zones = second.multiselect("Zone filters", all_zones, default=all_zones)
    categories = third.multiselect(
        "Category filters", all_categories, default=all_categories[:5]
    )

    filtered = [
        row
        for row in data.scenarios
        if row["scenario_id"] in scenarios
        and row["zone_type"] in zones
        and row["category"] in categories
    ]
    if not filtered:
        st.info("No synthetic records match the current filters.")
        return

    baseline = sum(row["baseline_visits"] for row in filtered)
    estimated = sum(row["estimated_visits"] for row in filtered)
    uplift = (estimated / max(baseline, 1) - 1) * 100
    high_risk = sum(
        row["mobility_conflict_risk"] == "high" for row in filtered
    ) / len(filtered) * 100
    metrics = st.columns(4)
    metrics[0].metric("Synthetic records", f"{len(filtered):,}")
    metrics[1].metric("Baseline visits", f"{baseline:,}")
    metrics[2].metric("Estimated visits", f"{estimated:,}", f"{uplift:+.1f}%")
    metrics[3].metric("High-risk labels", f"{high_risk:.1f}%")
    st.caption(
        f"Cards and charts reflect the current filter subset: {len(filtered):,} "
        f"of {len(data.scenarios):,} synthetic records."
    )

    st.plotly_chart(
        scenario_comparison_rows_figure(filtered),
        use_container_width=True,
        theme="streamlit",
        config={"displaylogo": False},
    )
    st.plotly_chart(
        scenario_risk_figure(filtered),
        use_container_width=True,
        theme="streamlit",
        config={"displaylogo": False},
    )
    interpretation(
        "The filters expose how documented scenario and zone multipliers change synthetic demand and risk labels.",
        "These records let the team test filters, evidence cards, charts, and backend responses before event data exists.",
        SYNTHETIC_LIMITATION,
    )

    with st.expander("Scenario assumptions"):
        st.markdown(
            """
- Ordinary day: **1.00x** baseline
- Pre-match: **1.25x** baseline
- During match: **0.85x** baseline
- Post-match: **1.45x** baseline
- Rainy post-match: **1.20x** baseline
- Transit disruption: **1.10x** baseline

The generator uses random seed `2026`, prevents negative values, labels every
record `synthetic`, and adds documented zone and bounded-noise factors. Zone
weights are normalized to a mean of **1.00x**, so each stated scenario
multiplier remains its expected overall effect. Categories are sampled from
each selected brand's observed prepared-data category mix.
"""
        )
