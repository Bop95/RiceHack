"""Overview page for the FinalFlow store-visit prototype."""

from __future__ import annotations

import streamlit as st

from paddydash.components.charts import overall_monthly_figure, ranking_figure
from paddydash.components.ui import interpretation, page_intro
from paddydash.services.analytics import LIMITATION
from paddydash.services.data_service import load_dashboard_data


def compact_number(value: int | float) -> str:
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    return f"{value:,.0f}"


def render_overview() -> None:
    data = load_dashboard_data()
    summary = data.summary
    page_intro(
        "FinalFlow Store-Visit Intelligence",
        "Explore historical commercial activity, compare markets and business "
        "groups, test modest synthetic scenarios, and ask questions grounded in "
        "approved prepared data.",
        "derived",
    )

    st.warning(
        "Store visits are a commercial-activity proxy. They do not measure "
        "stadium attendance, pedestrian counts, transit ridership, or future demand."
    )

    cards = st.columns(5)
    cards[0].metric("Store-day records", compact_number(summary["total_rows"]))
    cards[1].metric("Unique stores", f"{summary['unique_stores']:,}")
    cards[2].metric(
        "Total transformed visits", compact_number(summary["total_visits"])
    )
    cards[3].metric("Markets", f"{summary['unique_markets']:,}")
    cards[4].metric(
        "Date coverage",
        f"{summary['earliest_date'][:4]}-{summary['latest_date'][2:4]}",
        help=f"{summary['earliest_date']} through {summary['latest_date']}",
    )

    metric = st.segmented_control(
        "Monthly trend metric",
        options=["mean_daily_visits", "total_visits"],
        format_func=lambda value: {
            "mean_daily_visits": "Mean per store-day",
            "total_visits": "Total transformed visits",
        }[value],
        default="mean_daily_visits",
        key="overview_metric",
    )
    st.plotly_chart(
        overall_monthly_figure(data.monthly, metric or "mean_daily_visits"),
        width="stretch",
        theme="streamlit",
        config={"displaylogo": False},
    )

    highest = max(data.monthly, key=lambda row: row["mean_daily_visits"])
    lowest = min(data.monthly, key=lambda row: row["mean_daily_visits"])
    interpretation(
        (
            f"The monthly mean ranges from {lowest['mean_daily_visits']:,.2f} in "
            f"{lowest['month'][:7]} to {highest['mean_daily_visits']:,.2f} in "
            f"{highest['month'][:7]}."
        ),
        "This provides a transparent historical baseline for later scenario comparisons.",
        "The dataset does not identify what caused any increase or decline.",
    )

    left, right = st.columns(2)
    with left:
        st.plotly_chart(
            ranking_figure(
                data.categories,
                "category",
                "total_visits",
                7,
                "Leading commercial categories",
            ),
            width="stretch",
            theme="streamlit",
            config={"displaylogo": False},
        )
    with right:
        st.plotly_chart(
            ranking_figure(
                data.markets,
                "market",
                "mean_daily_visits",
                len(data.markets),
                "Market daily intensity",
            ),
            width="stretch",
            theme="streamlit",
            config={"displaylogo": False},
        )

    with st.expander("Dataset coverage and quality notes"):
        st.markdown(
            f"""
- **Brands:** {summary['unique_brands']:,}
- **Categories:** {summary['unique_categories']:,}
- **Dates:** {summary['unique_dates']:,}
- **Mean daily visits:** {summary['mean_daily_visits']:,.2f}
- **Median daily visits:** {summary['median_daily_visits']:,}
- **Zero-visit records retained:** {summary['zero_visit_rows']:,}
- **Primary limitation:** {LIMITATION}
"""
        )
