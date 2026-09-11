"""Interactive explorer for brands, categories, time, markets, and distributions."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from paddydash.components.charts import (
    category_scatter_figure,
    dimension_time_series_figure,
    market_figure,
    percentile_figure,
    ranking_figure,
    weekday_figure,
)
from paddydash.components.ui import data_type_label, interpretation, page_intro
from paddydash.services.analytics import LIMITATION
from paddydash.services.data_service import REPOSITORY_ROOT, load_dashboard_data


METRIC_OPTIONS = {
    "Total transformed visits": "total_visits",
    "Mean per store-day": "mean_daily_visits",
    "Unique stores": "unique_stores",
}


def plot(figure: object) -> None:
    st.plotly_chart(
        figure,
        use_container_width=True,
        theme="streamlit",
        config={"displaylogo": False, "scrollZoom": False},
    )


def render_store_visit_explorer() -> None:
    data = load_dashboard_data()
    page_intro(
        "Store-Visit Explorer",
        "Filter prepared brand and category summaries, inspect temporal patterns, "
        "compare markets, and review the skewed visit distribution.",
        "derived",
    )

    ranking_tab, time_tab, scatter_tab, weekday_tab, market_tab, distribution_tab = st.tabs(
        ["Rankings", "Time series", "Category scatter", "Weekdays", "Markets", "Distribution"]
    )

    with ranking_tab:
        control_a, control_b, control_c = st.columns([1, 1, 1])
        dimension = control_a.selectbox(
            "Business dimension", ["Brand", "Category"], key="ranking_dimension"
        )
        metric_label = control_b.selectbox(
            "Ranking metric", list(METRIC_OPTIONS), key="ranking_metric"
        )
        limit = control_c.slider("Rows", 5, 20, 12, key="ranking_limit")
        rows = data.brands if dimension == "Brand" else data.categories
        label_column = "brand" if dimension == "Brand" else "category"
        metric = METRIC_OPTIONS[metric_label]
        plot(
            ranking_figure(
                rows, label_column, metric, limit, f"Top {dimension.lower()}s"
            )
        )
        selected = sorted(rows, key=lambda row: row[metric], reverse=True)[0]
        interpretation(
            (
                f"{selected[label_column]} ranks first by {metric_label.lower()} "
                f"at {selected[metric]:,.2f}."
            ),
            "Rankings help the business dashboard prioritize groups for deeper comparison.",
            "Totals combine footprint and intensity and should not be interpreted as causal.",
        )

    with time_tab:
        dimension = st.radio(
            "Time-series dimension",
            ["Brand", "Category"],
            horizontal=True,
            key="time_dimension",
        )
        if dimension == "Brand":
            rows = data.brand_monthly
            column = "brand"
            defaults = ["Walmart", "McDonald's"]
            st.caption(
                "Brand time-series options are limited to the top 50 brands by "
                "total transformed visits to keep the deployable data compact."
            )
        else:
            rows = data.category_monthly
            column = "category"
            defaults = [
                "Restaurants and Other Eating Places",
                "Gasoline Stations",
            ]
        options = sorted({row[column] for row in rows})
        defaults = [item for item in defaults if item in options]
        selected = st.multiselect(
            f"{dimension} filters (up to 5)",
            options,
            default=defaults or options[:2],
            max_selections=5,
            key=f"{column}_time_items",
        )
        left, right = st.columns(2)
        metric_label = left.selectbox(
            "Metric",
            ["Mean per store-day", "Total transformed visits", "Unique stores"],
            key="time_metric",
        )
        years = right.slider("Year range", 2020, 2024, (2020, 2024), key="time_years")
        if not selected:
            st.info(f"Select at least one {dimension.lower()} to display the time series.")
        else:
            plot(
                dimension_time_series_figure(
                    rows,
                    column,
                    selected,
                    METRIC_OPTIONS[metric_label],
                    years[0],
                    years[1],
                )
            )
            interpretation(
                "The selected lines show when commercial activity changes within each business group.",
                "This supports transparent historical baselines and reusable frontend filters.",
                "Temporal association does not identify the cause of a rise or decline.",
            )

    with scatter_tab:
        plot(category_scatter_figure(data.categories))
        interpretation(
            "Large-footprint categories and high-intensity categories are not always the same.",
            "The chart helps separate commercial scale from activity at a typical store-day.",
            LIMITATION,
        )

    with weekday_tab:
        plot(weekday_figure(data.weekdays))
        high = max(data.weekdays, key=lambda row: row["mean_daily_visits"])
        low = min(data.weekdays, key=lambda row: row["mean_daily_visits"])
        interpretation(
            f"{high['weekday']} is highest and {low['weekday']} is lowest by mean store-day visits.",
            "Weekday patterns can inform a simple day-of-week commercial baseline.",
            LIMITATION,
        )

    with market_tab:
        plot(market_figure(data.markets))
        top_total = max(data.markets, key=lambda row: row["total_visits"])
        top_mean = max(data.markets, key=lambda row: row["mean_daily_visits"])
        interpretation(
            (
                f"{top_total['market']} leads in total transformed visits, while "
                f"{top_mean['market']} leads in mean daily intensity."
            ),
            "The comparison distinguishes regional footprint from typical store-day activity.",
            "Combined market labels are regional groupings, not single cities.",
        )

    with distribution_tab:
        plot(percentile_figure(data.percentiles))
        median = data.summary["median_daily_visits"]
        mean = data.summary["mean_daily_visits"]
        zero_share = data.summary["zero_visit_rows"] / data.summary["total_rows"] * 100
        interpretation(
            (
                f"The median is {median:,}, below the mean of {mean:,.2f}; "
                f"{zero_share:.2f}% of records have zero visits."
            ),
            "Percentiles provide robust thresholds for summaries and anomaly review.",
            "Values above P99.9 are review candidates, not automatically invalid.",
        )

    with st.expander("Report-ready static plots"):
        figure_dir = Path(REPOSITORY_ROOT) / "reports" / "figures"
        for title, filename in (
            ("Top brands", "store_visits_top_brands.png"),
            ("Top categories", "store_visits_top_categories.png"),
            ("Weekday pattern", "store_visits_weekday_pattern.png"),
            ("Visit distribution", "store_visits_distribution.png"),
        ):
            st.markdown(f"#### {title}")
            st.image(str(figure_dir / filename), use_container_width=True)
        data_type_label("derived")
