"""Reusable Plotly charts for the FinalFlow Streamlit prototype."""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime
from typing import Any

import plotly.graph_objects as go

from paddydash.services.data_service import DashboardData


RICE_BLUE = "#00205B"
MID_BLUE = "#4C78A8"
LIGHT_BLUE = "#8FB9D9"
RICE_GOLD = "#C69214"
WEEKEND_ORANGE = "#E07A5F"
TEAL = "#2A9D8F"
SERIES = [RICE_BLUE, RICE_GOLD, TEAL, WEEKEND_ORANGE, MID_BLUE, "#7A5195"]

METRICS = {
    "total_visits": ("Total transformed visits", "Transformed visits"),
    "mean_daily_visits": (
        "Mean visits per store-day",
        "Mean transformed visits per store-day record",
    ),
    "unique_stores": ("Unique stores", "Unique stores"),
}


def parse_month(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d")


def common_layout(
    figure: go.Figure,
    title: str,
    subtitle: str,
    y_title: str | None = None,
    height: int = 470,
) -> go.Figure:
    figure.update_layout(
        title={"text": f"{title}<br><sup>{subtitle}</sup>", "x": 0.01},
        margin={"l": 30, "r": 25, "t": 90, "b": 45},
        height=height,
        hovermode="closest",
        legend={"orientation": "h", "y": 1.02, "x": 0},
        font={"family": "Arial, sans-serif", "size": 13},
        colorway=SERIES,
    )
    figure.update_xaxes(showgrid=False, automargin=True)
    figure.update_yaxes(
        gridcolor="rgba(128,128,128,0.18)",
        zeroline=False,
        automargin=True,
        title=y_title,
    )
    return figure


def ranking_figure(
    rows: list[dict[str, Any]],
    label_column: str,
    metric: str,
    limit: int,
    title: str,
) -> go.Figure:
    selected = sorted(rows, key=lambda row: row[metric], reverse=True)[:limit]
    selected.reverse()
    values = [row[metric] for row in selected]
    custom = [
        [row["total_visits"], row["mean_daily_visits"], row["unique_stores"]]
        for row in selected
    ]
    figure = go.Figure(
        go.Bar(
            x=values,
            y=[row[label_column] for row in selected],
            orientation="h",
            marker_color=MID_BLUE,
            customdata=custom,
            hovertemplate=(
                "<b>%{y}</b><br>Total visits: %{customdata[0]:,.0f}"
                "<br>Mean per store-day: %{customdata[1]:,.2f}"
                "<br>Unique stores: %{customdata[2]:,.0f}<extra></extra>"
            ),
        )
    )
    metric_title, axis_title = METRICS[metric]
    return common_layout(
        figure,
        title,
        f"Ranked by {metric_title.lower()}; hover for scale and intensity evidence.",
        axis_title,
        height=max(430, 54 * limit),
    )


def overall_monthly_figure(
    rows: list[dict[str, Any]], metric: str = "mean_daily_visits"
) -> go.Figure:
    ordered = sorted(rows, key=lambda row: row["month"])
    figure = go.Figure(
        go.Scatter(
            x=[parse_month(row["month"]) for row in ordered],
            y=[row[metric] for row in ordered],
            mode="lines+markers",
            line={"color": RICE_BLUE, "width": 3},
            marker={"size": 5},
            customdata=[
                [row["total_visits"], row["record_count"], row["unique_stores"]]
                for row in ordered
            ],
            hovertemplate=(
                "<b>%{x|%B %Y}</b><br>Selected metric: %{y:,.2f}"
                "<br>Total visits: %{customdata[0]:,.0f}"
                "<br>Records: %{customdata[1]:,.0f}"
                "<br>Unique stores: %{customdata[2]:,.0f}<extra></extra>"
            ),
        )
    )
    figure.update_xaxes(rangeslider={"visible": True})
    label, axis = METRICS[metric]
    return common_layout(
        figure,
        "Monthly historical trend",
        "2020-2024 overall commercial activity; drag the range slider to zoom.",
        axis,
        500,
    ).update_layout(hovermode="x unified")


def dimension_time_series_figure(
    rows: list[dict[str, Any]],
    dimension: str,
    selected: list[str],
    metric: str,
    start_year: int,
    end_year: int,
) -> go.Figure:
    figure = go.Figure()
    for index, item in enumerate(selected):
        item_rows = [
            row
            for row in rows
            if row[dimension] == item
            and start_year <= int(row["month"][:4]) <= end_year
        ]
        item_rows.sort(key=lambda row: row["month"])
        figure.add_trace(
            go.Scatter(
                x=[parse_month(row["month"]) for row in item_rows],
                y=[row[metric] for row in item_rows],
                name=item,
                mode="lines",
                line={"width": 2.5, "color": SERIES[index % len(SERIES)]},
                customdata=[
                    [row["total_visits"], row["mean_daily_visits"], row["unique_stores"]]
                    for row in item_rows
                ],
                hovertemplate=(
                    "<b>%{fullData.name}</b><br>%{x|%B %Y}"
                    "<br>Selected metric: %{y:,.2f}"
                    "<br>Total visits: %{customdata[0]:,.0f}"
                    "<br>Mean per store-day: %{customdata[1]:,.2f}"
                    "<br>Unique stores: %{customdata[2]:,.0f}<extra></extra>"
                ),
            )
        )
    label, axis = METRICS[metric]
    title_dimension = "Brand" if dimension == "brand" else "Category"
    return common_layout(
        figure,
        f"Interactive {title_dimension.lower()} time-series explorer",
        f"{label} by month; each line uses derived records for the selected item.",
        axis,
        520,
    ).update_layout(hovermode="x unified")


def category_scatter_figure(rows: list[dict[str, Any]], limit: int = 35) -> go.Figure:
    selected = sorted(rows, key=lambda row: row["total_visits"], reverse=True)[:limit]
    sizes = [row["total_visits"] for row in selected]
    desired_maximum_px = 52
    size_reference = 2 * max(sizes) / desired_maximum_px**2
    figure = go.Figure(
        go.Scatter(
            x=[row["unique_stores"] for row in selected],
            y=[row["mean_daily_visits"] for row in selected],
            mode="markers",
            text=[row["category"] for row in selected],
            customdata=[[row["total_visits"]] for row in selected],
            marker={
                "size": sizes,
                "sizemode": "area",
                "sizeref": size_reference,
                "sizemin": 7,
                "color": [row["total_visits"] for row in selected],
                "colorscale": [[0, LIGHT_BLUE], [1, RICE_BLUE]],
                "showscale": True,
                "colorbar": {"title": "Total visits"},
                "line": {"width": 1, "color": "rgba(255,255,255,0.65)"},
                "opacity": 0.82,
            },
            hovertemplate=(
                "<b>%{text}</b><br>Unique stores: %{x:,.0f}"
                "<br>Mean per store-day: %{y:,.2f}"
                "<br>Total visits: %{customdata[0]:,.0f}<extra></extra>"
            ),
        )
    )
    figure.update_xaxes(title="Unique stores", type="log")
    return common_layout(
        figure,
        "Category footprint versus daily intensity",
        "Bubble size and color encode total visits; axes separate footprint from typical activity.",
        "Mean visits per store-day",
        520,
    )


def weekday_figure(rows: list[dict[str, Any]]) -> go.Figure:
    ordered = sorted(rows, key=lambda row: row["weekday_number"])
    figure = go.Figure(
        go.Bar(
            x=[row["weekday"] for row in ordered],
            y=[row["mean_daily_visits"] for row in ordered],
            marker_color=[
                WEEKEND_ORANGE if row["is_weekend"] else MID_BLUE for row in ordered
            ],
            customdata=[[row["total_visits"], row["record_count"]] for row in ordered],
            hovertemplate=(
                "<b>%{x}</b><br>Mean per store-day: %{y:,.2f}"
                "<br>Total visits: %{customdata[0]:,.0f}"
                "<br>Records: %{customdata[1]:,.0f}<extra></extra>"
            ),
        )
    )
    return common_layout(
        figure,
        "Weekday pattern",
        "Orange bars are weekend days; mean controls for similar record counts.",
        "Mean visits per store-day",
        440,
    )


def market_figure(rows: list[dict[str, Any]]) -> go.Figure:
    figure = go.Figure(
        go.Scatter(
            x=[row["total_visits"] for row in rows],
            y=[row["mean_daily_visits"] for row in rows],
            mode="markers+text",
            text=[row["market"] for row in rows],
            textposition="top center",
            customdata=[[row["unique_stores"], row["record_count"]] for row in rows],
            marker={
                "size": [max(15, math.sqrt(row["unique_stores"]) / 5) for row in rows],
                "sizemode": "diameter",
                "color": [row["unique_stores"] for row in rows],
                "colorscale": [[0, RICE_GOLD], [1, RICE_BLUE]],
                "showscale": True,
                "colorbar": {"title": "Stores"},
                "opacity": 0.82,
            },
            hovertemplate=(
                "<b>%{text}</b><br>Total visits: %{x:,.0f}"
                "<br>Mean per store-day: %{y:,.2f}"
                "<br>Unique stores: %{customdata[0]:,.0f}"
                "<br>Records: %{customdata[1]:,.0f}<extra></extra>"
            ),
        )
    )
    figure.update_xaxes(title="Total transformed visits")
    return common_layout(
        figure,
        "Market scale versus daily intensity",
        "Bubble size represents unique stores; combined labels are regional groupings.",
        "Mean visits per store-day",
        520,
    )


def percentile_figure(percentiles: dict[str, Any]) -> go.Figure:
    labels = ["P25", "P50", "P75", "P95", "P99", "P99.9"]
    keys = ["p25", "p50", "p75", "p95", "p99", "p999"]
    figure = go.Figure(
        go.Bar(
            x=labels,
            y=[percentiles[key] for key in keys],
            marker_color=[MID_BLUE] * 4 + [RICE_GOLD, WEEKEND_ORANGE],
            text=[f"{percentiles[key]:,}" for key in keys],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Daily visits: %{y:,.0f}<extra></extra>",
        )
    )
    result = common_layout(
        figure,
        "Selected daily-visit percentiles",
        "Log scale makes the strongly skewed distribution readable from P25 to P99.9.",
        "Daily transformed visits",
        430,
    )
    result.update_yaxes(type="log")
    return result


def summarize_scenario_rows(source_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in source_rows:
        item = grouped.setdefault(
            row["scenario_id"],
            {
                "scenario_id": row["scenario_id"],
                "baseline_visits": 0,
                "estimated_visits": 0,
                "record_count": 0,
                "high_risk_records": 0,
            },
        )
        item["baseline_visits"] += row["baseline_visits"]
        item["estimated_visits"] += row["estimated_visits"]
        item["record_count"] += 1
        item["high_risk_records"] += row["mobility_conflict_risk"] == "high"
    for item in grouped.values():
        item["uplift_pct"] = round(
            (item["estimated_visits"] / max(item["baseline_visits"], 1) - 1) * 100,
            1,
        )
        item["high_risk_share_pct"] = round(
            item["high_risk_records"] / item["record_count"] * 100,
            1,
        )
    return sorted(grouped.values(), key=lambda row: row["estimated_visits"], reverse=True)


def scenario_comparison_rows_figure(source_rows: list[dict[str, Any]]) -> go.Figure:
    rows = summarize_scenario_rows(source_rows)
    labels = [row["scenario_id"].replace("_", " ").title() for row in rows]
    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            x=labels,
            y=[row["baseline_visits"] for row in rows],
            name="Synthetic baseline",
            marker_color=LIGHT_BLUE,
        )
    )
    figure.add_trace(
        go.Bar(
            x=labels,
            y=[row["estimated_visits"] for row in rows],
            name="Scenario estimate",
            marker_color=RICE_GOLD,
            customdata=[[row["uplift_pct"], row["high_risk_share_pct"]] for row in rows],
            hovertemplate=(
                "<b>%{x}</b><br>Estimated visits: %{y:,.0f}"
                "<br>Uplift: %{customdata[0]:+.1f}%"
                "<br>High-risk share: %{customdata[1]:.1f}%<extra></extra>"
            ),
        )
    )
    figure.update_layout(barmode="group")
    return common_layout(
        figure,
        "Synthetic scenario comparison",
        "Illustrative totals from documented multipliers; not a World Cup forecast.",
        "Synthetic visits",
        500,
    )


def scenario_comparison_figure(data: DashboardData) -> go.Figure:
    return scenario_comparison_rows_figure(data.scenarios)


def scenario_risk_figure(rows: list[dict[str, Any]]) -> go.Figure:
    grouped: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        grouped[row["scenario_id"]][row["mobility_conflict_risk"]] += 1
    labels = [key.replace("_", " ").title() for key in grouped]
    figure = go.Figure()
    for risk, color in (("low", TEAL), ("medium", RICE_GOLD), ("high", WEEKEND_ORANGE)):
        figure.add_trace(
            go.Bar(
                x=labels,
                y=[grouped[key][risk] for key in grouped],
                name=risk.title(),
                marker_color=color,
            )
        )
    figure.update_layout(barmode="stack")
    return common_layout(
        figure,
        "Illustrative mobility-conflict risk mix",
        "Counts are rule-based synthetic labels for interface testing.",
        "Synthetic records",
        470,
    )


def related_plot(plot_id: str, data: DashboardData) -> go.Figure:
    if plot_id == "brand_ranking":
        return ranking_figure(data.brands, "brand", "total_visits", 10, "Top brands")
    if plot_id == "category_ranking":
        return ranking_figure(
            data.categories, "category", "total_visits", 10, "Top categories"
        )
    if plot_id == "weekday_pattern":
        return weekday_figure(data.weekdays)
    if plot_id == "market_comparison":
        return market_figure(data.markets)
    if plot_id == "scenario_comparison":
        return scenario_comparison_figure(data)
    if plot_id == "visit_distribution":
        return percentile_figure(data.percentiles)
    return overall_monthly_figure(data.monthly)
