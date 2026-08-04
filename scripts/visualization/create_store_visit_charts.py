"""Create the Step-3 store-visit charts and interpretation notes.

The script reads the compact summary CSV files produced by
``scripts/data/clean_store_visits.py``. Only the distribution chart touches the
large clean Parquet file, and it scans just the ``daily_visits`` column.

Outputs
-------
reports/figures/store_visits_top_brands.png
reports/figures/store_visits_top_categories.png
reports/figures/store_visits_weekday_pattern.png
reports/figures/store_visits_distribution.png
reports/interactive/store_visits_monthly_trend.html
reports/interactive/store_visits_market_comparison.html
reports/summaries/store_visits_visualization_notes.md
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from textwrap import fill
from typing import Any

os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "finalflow_matplotlib")
)

try:
    import duckdb
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import plotly.graph_objects as go
except ImportError as error:  # pragma: no cover - only reached without dependencies.
    raise SystemExit(
        "Chart dependencies are required. Install them with: "
        "python -m pip install -r requirements.txt"
    ) from error


RICE_BLUE = "#00205B"
MID_BLUE = "#4C78A8"
LIGHT_BLUE = "#8FB9D9"
RICE_GOLD = "#C69214"
WEEKEND_ORANGE = "#E07A5F"
DARK_TEXT = "#1F2933"
MUTED_TEXT = "#52606D"
GRID = "#D9E2EC"

SUMMARY_REQUIREMENTS = {
    "visits_by_brand.csv": {
        "brand",
        "total_visits",
        "record_count",
        "unique_stores",
        "mean_daily_visits",
    },
    "visits_by_category.csv": {
        "category",
        "total_visits",
        "record_count",
        "unique_stores",
        "mean_daily_visits",
    },
    "visits_by_market.csv": {
        "market",
        "total_visits",
        "record_count",
        "unique_stores",
        "mean_daily_visits",
    },
    "weekday_patterns.csv": {
        "weekday_number",
        "weekday",
        "is_weekend",
        "total_visits",
        "record_count",
        "mean_daily_visits",
    },
    "monthly_trends.csv": {
        "month",
        "total_visits",
        "record_count",
        "unique_stores",
        "mean_daily_visits",
    },
    "summary_statistics.csv": {
        "total_rows",
        "total_visits",
        "mean_daily_visits",
        "median_daily_visits",
        "zero_visit_rows",
    },
    "visit_percentiles.csv": {
        "p25",
        "p50",
        "p75",
        "p95",
        "p99",
        "p999",
        "high_visit_threshold",
    },
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create static and interactive store-visit charts."
    )
    parser.add_argument(
        "--summary-dir",
        type=Path,
        default=Path("data/summaries"),
        help="Directory containing Step-2 summary CSV files.",
    )
    parser.add_argument(
        "--clean-data",
        type=Path,
        default=Path("data/processed/store_visits_clean.parquet"),
        help="Clean Parquet used only for the visit-distribution chart.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("reports"),
        help="Root containing figures/, interactive/, and summaries/.",
    )
    parser.add_argument("--top-brands", type=int, default=15)
    parser.add_argument("--top-categories", type=int, default=12)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace this script's existing chart and note outputs.",
    )
    return parser.parse_args(argv)


def validate_options(args: argparse.Namespace) -> None:
    if args.top_brands < 1:
        raise ValueError("--top-brands must be at least 1.")
    if args.top_categories < 1:
        raise ValueError("--top-categories must be at least 1.")


def read_csv_rows(path: Path, required_columns: set[str]) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Required summary file does not exist: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = set(reader.fieldnames or [])
        missing = sorted(required_columns - headers)
        if missing:
            raise ValueError(
                f"{path.name} is missing required columns: {', '.join(missing)}"
            )
        rows = list(reader)
    if not rows:
        raise ValueError(f"Required summary file has no data rows: {path}")
    return rows


def load_summary_inputs(summary_dir: Path) -> dict[str, list[dict[str, str]]]:
    return {
        filename: read_csv_rows(summary_dir / filename, columns)
        for filename, columns in SUMMARY_REQUIREMENTS.items()
    }


def output_paths(output_root: Path) -> dict[str, Path]:
    return {
        "brands": output_root / "figures" / "store_visits_top_brands.png",
        "categories": output_root
        / "figures"
        / "store_visits_top_categories.png",
        "weekdays": output_root / "figures" / "store_visits_weekday_pattern.png",
        "distribution": output_root
        / "figures"
        / "store_visits_distribution.png",
        "monthly": output_root
        / "interactive"
        / "store_visits_monthly_trend.html",
        "markets": output_root
        / "interactive"
        / "store_visits_market_comparison.html",
        "notes": output_root
        / "summaries"
        / "store_visits_visualization_notes.md",
    }


def prepare_outputs(paths: dict[str, Path], overwrite: bool) -> None:
    existing = [path for path in paths.values() if path.exists()]
    if existing and not overwrite:
        raise FileExistsError(
            f"Output already exists: {existing[0]}. Use --overwrite to replace charts."
        )
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)


def configure_matplotlib() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": GRID,
            "axes.labelcolor": DARK_TEXT,
            "axes.titlecolor": DARK_TEXT,
            "axes.titlesize": 15,
            "axes.titleweight": "bold",
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "text.color": DARK_TEXT,
            "xtick.color": MUTED_TEXT,
            "ytick.color": DARK_TEXT,
        }
    )


def simplify_axes(axis: Any, grid_axis: str = "x") -> None:
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.spines["left"].set_visible(False)
    axis.grid(axis=grid_axis, color=GRID, linewidth=0.8, alpha=0.8)
    axis.set_axisbelow(True)
    axis.tick_params(axis="y", length=0)


def save_figure(figure: Any, destination: Path) -> None:
    figure.savefig(
        destination,
        dpi=180,
        bbox_inches="tight",
        facecolor="white",
        metadata={"Software": "FinalFlow store-visit visualization pipeline"},
    )
    plt.close(figure)


def plot_top_brands(
    rows: list[dict[str, str]], destination: Path, top_n: int
) -> list[dict[str, Any]]:
    selected = sorted(rows, key=lambda row: int(row["total_visits"]), reverse=True)[
        :top_n
    ]
    display = list(reversed(selected))
    labels = [fill(row["brand"], width=24) for row in display]
    totals = [int(row["total_visits"]) / 1_000_000_000 for row in display]

    figure, axis = plt.subplots(figsize=(11.5, 8.2))
    bars = axis.barh(labels, totals, color=MID_BLUE, height=0.68)
    axis.set_title(
        f"Top {len(selected)} brands by total transformed visits",
        loc="left",
        pad=30,
    )
    axis.text(
        0,
        1.01,
        "Totals combine business footprint and activity across 2020–2024",
        transform=axis.transAxes,
        color=MUTED_TEXT,
        va="bottom",
    )
    axis.set_xlabel("Total transformed visits (billions)")
    axis.set_xlim(0, max(totals) * 1.18)
    axis.bar_label(bars, labels=[f"{value:.2f}B" for value in totals], padding=4)
    simplify_axes(axis)
    figure.tight_layout()
    save_figure(figure, destination)
    return selected


def plot_top_categories(
    rows: list[dict[str, str]], destination: Path, top_n: int
) -> list[dict[str, Any]]:
    selected = sorted(rows, key=lambda row: int(row["total_visits"]), reverse=True)[
        :top_n
    ]
    display = list(reversed(selected))
    labels = [fill(row["category"], width=31) for row in display]
    totals = [int(row["total_visits"]) / 1_000_000_000 for row in display]
    means = [float(row["mean_daily_visits"]) for row in display]

    figure, (total_axis, mean_axis) = plt.subplots(
        1,
        2,
        figsize=(15.5, 9),
        sharey=True,
        gridspec_kw={"width_ratios": [1.15, 1]},
    )
    total_bars = total_axis.barh(labels, totals, color=RICE_BLUE, height=0.68)
    mean_bars = mean_axis.barh(labels, means, color=LIGHT_BLUE, height=0.68)
    figure.suptitle(
        f"Top {len(selected)} categories: total scale versus daily intensity",
        x=0.04,
        ha="left",
        fontsize=16,
        fontweight="bold",
    )
    total_axis.set_title("Total transformed visits", loc="left")
    mean_axis.set_title("Mean visits per store-day record", loc="left")
    total_axis.set_xlabel("Billions")
    mean_axis.set_xlabel("Mean daily visits")
    total_axis.set_xlim(0, max(totals) * 1.20)
    mean_axis.set_xlim(0, max(means) * 1.20)
    total_axis.bar_label(
        total_bars, labels=[f"{value:.2f}B" for value in totals], padding=3
    )
    mean_axis.bar_label(
        mean_bars, labels=[f"{value:,.0f}" for value in means], padding=3
    )
    simplify_axes(total_axis)
    simplify_axes(mean_axis)
    figure.subplots_adjust(left=0.31, right=0.98, top=0.89, bottom=0.09, wspace=0.24)
    save_figure(figure, destination)
    return selected


def plot_weekdays(
    rows: list[dict[str, str]], destination: Path
) -> list[dict[str, Any]]:
    ordered = sorted(rows, key=lambda row: int(row["weekday_number"]))
    labels = [row["weekday"] for row in ordered]
    means = [float(row["mean_daily_visits"]) for row in ordered]
    colors = [
        WEEKEND_ORANGE if row["is_weekend"].lower() == "true" else MID_BLUE
        for row in ordered
    ]

    figure, axis = plt.subplots(figsize=(11, 6.3))
    bars = axis.bar(labels, means, color=colors, width=0.68)
    axis.set_title("Average transformed visits by weekday", loc="left", pad=30)
    axis.text(
        0,
        1.01,
        "Orange marks weekend days; record counts are nearly equal across weekdays",
        transform=axis.transAxes,
        color=MUTED_TEXT,
        va="bottom",
    )
    axis.set_ylabel("Mean visits per store-day record")
    axis.set_ylim(0, max(means) * 1.18)
    axis.bar_label(bars, labels=[f"{value:,.0f}" for value in means], padding=4)
    axis.grid(axis="y", color=GRID, linewidth=0.8, alpha=0.8)
    axis.set_axisbelow(True)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    figure.tight_layout()
    save_figure(figure, destination)
    return ordered


def calculate_distribution_bins(
    clean_data: Path, percentiles: dict[str, str]
) -> list[dict[str, Any]]:
    if not clean_data.exists():
        raise FileNotFoundError(f"Clean Parquet does not exist: {clean_data}")
    p25 = int(percentiles["p25"])
    p50 = int(percentiles["p50"])
    p75 = int(percentiles["p75"])
    p95 = int(percentiles["p95"])
    p99 = int(percentiles["p99"])
    p999 = int(percentiles["p999"])
    connection = duckdb.connect()
    try:
        row = connection.execute(
            f"""
            SELECT
                COUNT(*)::BIGINT,
                COUNT_IF(daily_visits = 0)::BIGINT,
                COUNT_IF(daily_visits BETWEEN 1 AND {p25})::BIGINT,
                COUNT_IF(daily_visits BETWEEN {p25 + 1} AND {p50})::BIGINT,
                COUNT_IF(daily_visits BETWEEN {p50 + 1} AND {p75})::BIGINT,
                COUNT_IF(daily_visits BETWEEN {p75 + 1} AND {p95})::BIGINT,
                COUNT_IF(daily_visits BETWEEN {p95 + 1} AND {p99})::BIGINT,
                COUNT_IF(daily_visits BETWEEN {p99 + 1} AND {p999})::BIGINT,
                COUNT_IF(daily_visits > {p999})::BIGINT
            FROM read_parquet(?)
            """,
            [str(clean_data.resolve())],
        ).fetchone()
    finally:
        connection.close()

    total = int(row[0])
    labels = [
        "0 visits",
        f"1–{p25:,}",
        f"{p25 + 1:,}–{p50:,}",
        f"{p50 + 1:,}–{p75:,}",
        f"{p75 + 1:,}–{p95:,}",
        f"{p95 + 1:,}–{p99:,}",
        f"{p99 + 1:,}–{p999:,}",
        f"> {p999:,}",
    ]
    return [
        {
            "label": label,
            "count": int(count),
            "percent": int(count) / total * 100,
        }
        for label, count in zip(labels, row[1:], strict=True)
    ]


def plot_distribution(
    bins: list[dict[str, Any]],
    summary: dict[str, str],
    destination: Path,
) -> None:
    labels = [item["label"] for item in bins]
    percentages = [item["percent"] for item in bins]
    colors = [RICE_GOLD if index == 0 else MID_BLUE for index in range(len(bins))]

    figure, axis = plt.subplots(figsize=(11.5, 6.8))
    bars = axis.barh(labels, percentages, color=colors, height=0.68)
    axis.invert_yaxis()
    axis.set_title("Distribution of daily transformed visits", loc="left", pad=30)
    axis.text(
        0,
        1.01,
        "Percentile-based bins have unequal widths and do not treat high values as errors",
        transform=axis.transAxes,
        color=MUTED_TEXT,
        va="bottom",
    )
    axis.set_xlabel("Share of store-day records (%)")
    axis.set_xlim(0, max(percentages) * 1.18)
    axis.bar_label(
        bars, labels=[f"{value:.2f}%" for value in percentages], padding=4
    )
    axis.text(
        0.99,
        0.02,
        "Mean: "
        f"{float(summary['mean_daily_visits']):,.2f}  |  "
        f"Median: {int(summary['median_daily_visits']):,}",
        transform=axis.transAxes,
        ha="right",
        color=MUTED_TEXT,
    )
    simplify_axes(axis)
    figure.tight_layout()
    save_figure(figure, destination)


def write_monthly_interactive(
    rows: list[dict[str, str]], destination: Path
) -> list[dict[str, Any]]:
    ordered = sorted(rows, key=lambda row: row["month"])
    dates = [datetime.strptime(row["month"], "%Y-%m-%d") for row in ordered]
    mean_values = [float(row["mean_daily_visits"]) for row in ordered]
    total_values = [int(row["total_visits"]) / 1_000_000_000 for row in ordered]
    custom_data = [
        [
            int(row["total_visits"]),
            int(row["record_count"]),
            int(row["unique_stores"]),
            float(row["mean_daily_visits"]),
        ]
        for row in ordered
    ]

    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=dates,
            y=mean_values,
            mode="lines+markers",
            name="Mean daily visits",
            line={"color": RICE_BLUE, "width": 3},
            marker={"size": 6},
            customdata=custom_data,
            hovertemplate=(
                "%{x|%B %Y}<br>Mean daily visits: %{y:,.2f}"
                "<br>Total visits: %{customdata[0]:,.0f}"
                "<br>Records: %{customdata[1]:,.0f}"
                "<br>Unique stores: %{customdata[2]:,.0f}<extra></extra>"
            ),
        )
    )
    figure.add_trace(
        go.Scatter(
            x=dates,
            y=total_values,
            mode="lines+markers",
            name="Total visits",
            line={"color": RICE_GOLD, "width": 3},
            marker={"size": 6},
            customdata=custom_data,
            visible=False,
            hovertemplate=(
                "%{x|%B %Y}<br>Total visits: %{y:.2f}B"
                "<br>Mean daily visits: %{customdata[3]:,.2f}"
                "<br>Records: %{customdata[1]:,.0f}"
                "<br>Unique stores: %{customdata[2]:,.0f}<extra></extra>"
            ),
        )
    )
    figure.update_layout(
        title={
            "text": "Monthly store-visit activity, 2020–2024"
            "<br><sup>Totals vary with month length; means remove that calendar effect</sup>",
            "x": 0.02,
        },
        template="plotly_white",
        hovermode="x unified",
        margin={"l": 70, "r": 30, "t": 115, "b": 70},
        yaxis={"title": "Mean visits per store-day record", "rangemode": "tozero"},
        xaxis={"title": "Month", "rangeslider": {"visible": True}},
        updatemenus=[
            {
                "type": "buttons",
                "direction": "right",
                "x": 0.02,
                "y": 1.12,
                "buttons": [
                    {
                        "label": "Mean daily visits",
                        "method": "update",
                        "args": [
                            {"visible": [True, False]},
                            {"yaxis.title.text": "Mean visits per store-day record"},
                        ],
                    },
                    {
                        "label": "Total visits",
                        "method": "update",
                        "args": [
                            {"visible": [False, True]},
                            {
                                "yaxis.title.text": (
                                    "Total transformed visits (billions)"
                                )
                            },
                        ],
                    },
                ],
            }
        ],
        showlegend=False,
    )
    figure.write_html(
        destination,
        include_plotlyjs=True,
        full_html=True,
        config={"displaylogo": False, "responsive": True},
        auto_open=False,
    )
    return ordered


def write_market_interactive(
    rows: list[dict[str, str]], destination: Path
) -> list[dict[str, Any]]:
    ordered = sorted(rows, key=lambda row: int(row["total_visits"]), reverse=True)
    means = [float(row["mean_daily_visits"]) for row in ordered]
    totals = [int(row["total_visits"]) / 1_000_000_000 for row in ordered]
    stores = [int(row["unique_stores"]) for row in ordered]
    size_reference = 2 * max(stores) / 54**2
    label_positions = {
        "Seattle": "middle right",
        "Boston": "bottom center",
    }

    figure = go.Figure(
        go.Scatter(
            x=means,
            y=totals,
            mode="markers+text",
            text=[row["market"] for row in ordered],
            textposition=[
                label_positions.get(row["market"], "top center") for row in ordered
            ],
            customdata=[
                [
                    row["market"],
                    int(row["unique_stores"]),
                    int(row["record_count"]),
                    int(row["total_visits"]),
                ]
                for row in ordered
            ],
            marker={
                "size": stores,
                "sizemode": "area",
                "sizeref": size_reference,
                "sizemin": 14,
                "color": MID_BLUE,
                "line": {"color": "white", "width": 1.5},
                "opacity": 0.82,
            },
            hovertemplate=(
                "%{customdata[0]}<br>Total visits: %{customdata[3]:,.0f}"
                "<br>Mean daily visits: %{x:,.2f}"
                "<br>Unique stores: %{customdata[1]:,.0f}"
                "<br>Records: %{customdata[2]:,.0f}<extra></extra>"
            ),
        )
    )
    figure.update_layout(
        title={
            "text": "Market scale versus daily visit intensity"
            "<br><sup>Bubble area represents the number of unique stores</sup>",
            "x": 0.02,
        },
        template="plotly_white",
        margin={"l": 75, "r": 45, "t": 105, "b": 70},
        xaxis={"title": "Mean visits per store-day record", "rangemode": "tozero"},
        yaxis={"title": "Total transformed visits (billions)", "rangemode": "tozero"},
        showlegend=False,
    )
    figure.write_html(
        destination,
        include_plotlyjs=True,
        full_html=True,
        config={"displaylogo": False, "responsive": True},
        auto_open=False,
    )
    return ordered


def format_month(value: str) -> str:
    return datetime.strptime(value, "%Y-%m-%d").strftime("%B %Y")


def write_interpretation_notes(
    destination: Path,
    brand_rows: list[dict[str, Any]],
    category_rows: list[dict[str, Any]],
    weekday_rows: list[dict[str, Any]],
    monthly_rows: list[dict[str, Any]],
    market_rows: list[dict[str, Any]],
    distribution_bins: list[dict[str, Any]],
    summary: dict[str, str],
    percentiles: dict[str, str],
) -> None:
    total_visits = int(summary["total_visits"])
    top_brand = brand_rows[0]
    top_category = category_rows[0]
    highest_category_mean = max(
        category_rows, key=lambda row: float(row["mean_daily_visits"])
    )
    highest_weekday = max(
        weekday_rows, key=lambda row: float(row["mean_daily_visits"])
    )
    lowest_weekday = min(
        weekday_rows, key=lambda row: float(row["mean_daily_visits"])
    )
    weekday_difference = (
        float(highest_weekday["mean_daily_visits"])
        / float(lowest_weekday["mean_daily_visits"])
        - 1
    ) * 100
    lowest_month = min(monthly_rows, key=lambda row: float(row["mean_daily_visits"]))
    highest_month = max(monthly_rows, key=lambda row: float(row["mean_daily_visits"]))
    top_market = market_rows[0]
    highest_market_mean = max(
        market_rows, key=lambda row: float(row["mean_daily_visits"])
    )
    zero_bin = distribution_bins[0]

    note = f"""# Store Visits: Visualization Interpretations

## Scope

These charts describe **relative historical commercial activity** in the transformed
Rice store-visit data. They do not measure World Cup attendance, pedestrian counts,
transit ridership, causality, or exact future demand. All chart inputs are labeled
`derived` and come from the Step-2 clean dataset and summary tables.

## Static plots

### 1. Top brands by total visits

File: `reports/figures/store_visits_top_brands.png`

- `{top_brand['brand']}` has the largest total among the displayed brands at
  {int(top_brand['total_visits']) / 1_000_000_000:.2f} billion transformed visits.
- Across its {int(top_brand['unique_stores']):,} stores, the mean is
  {float(top_brand['mean_daily_visits']):,.2f} visits per store-day. This shows why
  total rankings combine business footprint and activity intensity.
- Brand totals are useful for prioritization, but they should not be interpreted as
  evidence that a brand causes higher mobility demand.

### 2. Category scale versus daily intensity

File: `reports/figures/store_visits_top_categories.png`

- `{top_category['category']}` accounts for
  {int(top_category['total_visits']) / total_visits * 100:.1f}% of all transformed
  visits, making it the dominant category by total scale.
- Among the displayed high-total categories,
  `{highest_category_mean['category']}` has the highest mean daily intensity at
  {float(highest_category_mean['mean_daily_visits']):,.2f} visits per store-day.
- The two panels prevent a large category footprint from being confused with a high
  activity level at the typical store-day record.

### 3. Weekday pattern

File: `reports/figures/store_visits_weekday_pattern.png`

- `{highest_weekday['weekday']}` is highest at
  {float(highest_weekday['mean_daily_visits']):,.2f} mean visits per store-day;
  `{lowest_weekday['weekday']}` is lowest at
  {float(lowest_weekday['mean_daily_visits']):,.2f}.
- The high day is {weekday_difference:.1f}% above the low day.
- Because weekday record counts are nearly equal, the mean comparison is more useful
  here than comparing raw totals.

### 4. Visit distribution

File: `reports/figures/store_visits_distribution.png`

- {zero_bin['percent']:.2f}% of records have zero visits and are retained rather than
  deleted.
- The median is {int(summary['median_daily_visits']):,}, well below the mean of
  {float(summary['mean_daily_visits']):,.2f}; this confirms a strongly right-skewed
  distribution.
- The exact p99 is {int(percentiles['p99']):,} and p99.9 is
  {int(percentiles['p999']):,}. Values above p99.9 are review candidates, not
  automatically invalid observations.

## Interactive plots

### 5. Monthly trend

File: `reports/interactive/store_visits_monthly_trend.html`

- The selector switches between mean daily intensity and total monthly scale; hover
  shows totals, records, and unique stores for each month.
- Monthly totals are affected by the number of days in each month; the mean view
  removes that calendar-length effect.
- The lowest monthly mean is {float(lowest_month['mean_daily_visits']):,.2f} in
  {format_month(lowest_month['month'])}; the highest is
  {float(highest_month['mean_daily_visits']):,.2f} in
  {format_month(highest_month['month'])}.
- The chart reveals timing and recovery patterns, but the dataset alone cannot prove
  what caused any rise or decline.

### 6. Market comparison

File: `reports/interactive/store_visits_market_comparison.html`

- `{top_market['market']}` has the largest total at
  {int(top_market['total_visits']) / 1_000_000_000:.2f} billion transformed visits.
- `{highest_market_mean['market']}` has the highest mean daily intensity at
  {float(highest_market_mean['mean_daily_visits']):,.2f} visits per store-day.
- Bubble size represents unique stores, making it possible to distinguish market
  footprint from per-record intensity. Combined market labels such as
  `Los Angeles / SF Bay Area` must not be treated as single cities.

## Recommended use

Use the static plots in reports or presentations and the interactive plots for
exploration or dashboard prototyping. For later World Cup scenarios, use these
patterns as transparent historical baselines—not direct forecasts—and combine them
with event schedules, transport, weather, and approved geographic data.
"""
    destination.write_text(note, encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    validate_options(args)
    summary_dir = args.summary_dir.resolve()
    clean_data = args.clean_data.resolve()
    destinations = output_paths(args.output_root.resolve())
    inputs = load_summary_inputs(summary_dir)
    prepare_outputs(destinations, args.overwrite)
    configure_matplotlib()

    summary = inputs["summary_statistics.csv"][0]
    percentiles = inputs["visit_percentiles.csv"][0]
    distribution_bins = calculate_distribution_bins(clean_data, percentiles)

    brand_rows = plot_top_brands(
        inputs["visits_by_brand.csv"], destinations["brands"], args.top_brands
    )
    category_rows = plot_top_categories(
        inputs["visits_by_category.csv"],
        destinations["categories"],
        args.top_categories,
    )
    weekday_rows = plot_weekdays(
        inputs["weekday_patterns.csv"], destinations["weekdays"]
    )
    plot_distribution(
        distribution_bins,
        summary,
        destinations["distribution"],
    )
    monthly_rows = write_monthly_interactive(
        inputs["monthly_trends.csv"], destinations["monthly"]
    )
    market_rows = write_market_interactive(
        inputs["visits_by_market.csv"], destinations["markets"]
    )
    write_interpretation_notes(
        destinations["notes"],
        brand_rows,
        category_rows,
        weekday_rows,
        monthly_rows,
        market_rows,
        distribution_bins,
        summary,
        percentiles,
    )

    result = {
        "static_plots": [
            str(destinations[name])
            for name in ("brands", "categories", "weekdays", "distribution")
        ],
        "interactive_plots": [
            str(destinations[name]) for name in ("monthly", "markets")
        ],
        "interpretation_notes": str(destinations["notes"]),
        "distribution_bins": distribution_bins,
    }
    return result


def main(argv: list[str] | None = None) -> int:
    try:
        result = run(parse_args(argv))
    except (
        duckdb.Error,
        OSError,
        ValueError,
    ) as error:
        print(f"Error: {error}", flush=True)
        return 1
    print(json.dumps(result, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
