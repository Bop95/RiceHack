"""Controlled analytics functions and grounded response contracts."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from paddydash.services.data_service import DashboardData


LIMITATION = (
    "Store visits are a historical commercial-activity proxy, not World Cup "
    "attendance, pedestrian flow, transit ridership, or a causal forecast."
)
SYNTHETIC_LIMITATION = (
    "Synthetic scenarios are interface-testing assumptions, not measured World "
    "Cup activity or exact future demand."
)


@dataclass(frozen=True)
class EvidenceItem:
    label: str
    value: str | int | float
    source: str


@dataclass(frozen=True)
class ChatResponse:
    answer: str
    evidence: list[EvidenceItem]
    related_plot_id: str | None
    data_type: str
    limitations: list[str]
    mode: str = "prepared-data"

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["relatedPlotId"] = result.pop("related_plot_id")
        result["dataType"] = result.pop("data_type")
        return result


@dataclass(frozen=True)
class RetrievalResult:
    context: str
    evidence: list[EvidenceItem]
    related_plot_id: str | None
    data_type: str
    limitations: list[str]
    local_answer: str


PLOT_CATALOG = {
    "brand_ranking": {
        "title": "Brand ranking",
        "source": "visits_by_brand.csv",
        "data_type": "derived",
    },
    "category_ranking": {
        "title": "Category ranking",
        "source": "visits_by_category.csv",
        "data_type": "derived",
    },
    "monthly_trend": {
        "title": "Monthly store-visit trend",
        "source": "monthly_trends.csv",
        "data_type": "derived",
    },
    "visit_distribution": {
        "title": "Store-visit distribution",
        "source": "visit_percentiles.csv",
        "data_type": "derived",
    },
    "weekday_pattern": {
        "title": "Weekday pattern",
        "source": "weekday_patterns.csv",
        "data_type": "derived",
    },
    "market_comparison": {
        "title": "Market comparison",
        "source": "visits_by_market.csv",
        "data_type": "derived",
    },
    "scenario_comparison": {
        "title": "Synthetic scenario comparison",
        "source": "store_visit_scenarios.csv",
        "data_type": "synthetic",
    },
}


def metric_label(metric: str) -> str:
    return {
        "total_visits": "total transformed visits",
        "mean_daily_visits": "mean visits per store-day",
        "unique_stores": "unique stores",
    }[metric]


def named_scenarios(question: str, data: DashboardData) -> list[str]:
    """Return scenario IDs explicitly named in a question, longest names first."""
    remaining = question.casefold().replace("_", " ").replace("-", " ")
    found: list[str] = []
    scenario_ids = sorted(
        {row["scenario_id"] for row in data.scenarios}, key=len, reverse=True
    )
    for scenario_id in scenario_ids:
        alias = scenario_id.replace("_", " ")
        if alias in remaining:
            found.append(scenario_id)
            remaining = remaining.replace(alias, " ")
    return found


def normalize_entity_text(value: str) -> str:
    """Normalize punctuation and spacing for safe whole-phrase matching."""
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.casefold()).split())


def named_entities(
    question: str,
    values: list[str],
    aliases: dict[str, tuple[str, ...]] | None = None,
) -> list[str]:
    """Return dataset entity values explicitly present in a question."""
    normalized_question = f" {normalize_entity_text(question)} "
    matches: list[str] = []
    for value in values:
        candidates = {normalize_entity_text(value)}
        candidates.update(
            normalize_entity_text(alias) for alias in (aliases or {}).get(value, ())
        )
        if any(
            candidate and f" {candidate} " in normalized_question
            for candidate in candidates
        ):
            matches.append(value)
    return matches


def refusal_result() -> RetrievalResult:
    return RetrievalResult(
        context=(
            "FinalFlow supports questions about prepared store-visit summaries "
            "for brands, categories, dates, weekdays, markets, distributions, "
            "and clearly labeled synthetic scenarios."
        ),
        evidence=[],
        related_plot_id=None,
        data_type="derived",
        limitations=[LIMITATION],
        local_answer=(
            "That question is outside this prototype's approved data scope. "
            "Ask about brands, categories, dates, weekdays, markets, visit "
            "distributions, or the labeled synthetic scenarios."
        ),
    )


def get_top_brands(
    data: DashboardData, metric: str = "total_visits", limit: int = 10
) -> list[dict[str, Any]]:
    if metric not in {"total_visits", "mean_daily_visits", "unique_stores"}:
        raise ValueError("Unsupported brand metric.")
    return sorted(data.brands, key=lambda row: row[metric], reverse=True)[:limit]


def get_top_categories(
    data: DashboardData, metric: str = "total_visits", limit: int = 10
) -> list[dict[str, Any]]:
    if metric not in {"total_visits", "mean_daily_visits", "unique_stores"}:
        raise ValueError("Unsupported category metric.")
    return sorted(data.categories, key=lambda row: row[metric], reverse=True)[:limit]


def get_visit_trend(
    data: DashboardData,
    category: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, Any]]:
    rows = data.monthly if category is None else [
        row for row in data.category_monthly if row["category"] == category
    ]
    if start_date:
        rows = [row for row in rows if row["month"] >= start_date]
    if end_date:
        rows = [row for row in rows if row["month"] <= end_date]
    return sorted(rows, key=lambda row: row["month"])


def get_weekday_pattern(
    data: DashboardData, category: str | None = None
) -> list[dict[str, Any]]:
    if category is not None:
        raise ValueError(
            "Prepared weekday summaries are overall only; category weekday "
            "patterns have not been approved."
        )
    return sorted(data.weekdays, key=lambda row: row["weekday_number"])


def get_market_summary(
    data: DashboardData, market: str | None = None
) -> list[dict[str, Any]]:
    rows = data.markets
    if market:
        rows = [row for row in rows if row["market"].lower() == market.lower()]
    return sorted(rows, key=lambda row: row["total_visits"], reverse=True)


def get_scenario_summary(
    data: DashboardData, scenario_id: str | None = None
) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in data.scenarios:
        if scenario_id and row["scenario_id"] != scenario_id:
            continue
        item = grouped.setdefault(
            row["scenario_id"],
            {
                "scenario_id": row["scenario_id"],
                "baseline_visits": 0,
                "estimated_visits": 0,
                "record_count": 0,
                "high_risk_records": 0,
                "data_type": "synthetic",
            },
        )
        item["baseline_visits"] += row["baseline_visits"]
        item["estimated_visits"] += row["estimated_visits"]
        item["record_count"] += 1
        item["high_risk_records"] += row["mobility_conflict_risk"] == "high"
    for item in grouped.values():
        baseline = max(item["baseline_visits"], 1)
        item["uplift_pct"] = round(
            (item["estimated_visits"] / baseline - 1) * 100, 1
        )
        item["high_risk_share_pct"] = round(
            item["high_risk_records"] / item["record_count"] * 100, 1
        )
    return sorted(grouped.values(), key=lambda row: row["estimated_visits"], reverse=True)


def get_plot_metadata(plot_id: str) -> dict[str, str]:
    if plot_id not in PLOT_CATALOG:
        raise ValueError(f"Unknown plot ID: {plot_id}")
    return dict(PLOT_CATALOG[plot_id])


def format_number(value: int | float) -> str:
    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f} billion"
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.2f} million"
    return f"{value:,.2f}" if isinstance(value, float) else f"{value:,}"


def retrieve_for_question(question: str, data: DashboardData) -> RetrievalResult:
    normalized = question.casefold()
    wants_mean = any(
        word in normalized for word in ("mean", "average", "intensity", "typical")
    )
    metric = "mean_daily_visits" if wants_mean else "total_visits"

    unsafe_terms = (
        "api key",
        "password",
        "credential",
        "system prompt",
        "reveal your prompt",
        "ignore instructions",
        "ignore previous",
    )
    if any(term in normalized for term in unsafe_terms):
        return refusal_result()

    named_brands = named_entities(
        question, [row["brand"] for row in data.brands]
    )
    named_categories = named_entities(
        question, [row["category"] for row in data.categories]
    )
    market_aliases = {
        "Los Angeles / SF Bay Area": (
            "Los Angeles",
            "LA",
            "San Francisco",
            "SF",
            "Bay Area",
        ),
        "Dallas / Houston": ("Dallas", "Houston"),
        "New York/New Jersey": ("New York", "New Jersey", "NYC"),
    }
    named_markets = named_entities(
        question,
        [row["market"] for row in data.markets],
        aliases=market_aliases,
    )
    named_weekdays = named_entities(
        question, [row["weekday"] for row in data.weekdays]
    )

    if any(word in normalized for word in ("scenario", "match", "rain", "transit")):
        rows = get_scenario_summary(data)
        requested = named_scenarios(question, data)
        if requested:
            rows_by_id = {row["scenario_id"]: row for row in rows}
            rows = [rows_by_id[item] for item in requested if item in rows_by_id]

        context = "\n".join(
            f"{row['scenario_id']}: baseline={row['baseline_visits']}, "
            f"estimated={row['estimated_visits']}, uplift={row['uplift_pct']}%, "
            f"high-risk share={row['high_risk_share_pct']}%"
            for row in rows
        )

        if requested:
            evidence = []
            for row in rows:
                label = row["scenario_id"].replace("_", " ").title()
                evidence.extend(
                    [
                        EvidenceItem(
                            f"{label} estimated visits",
                            format_number(row["estimated_visits"]),
                            "store_visit_scenarios.csv",
                        ),
                        EvidenceItem(
                            f"{label} illustrative uplift",
                            f"{row['uplift_pct']:+.1f}%",
                            "store_visit_scenarios.csv",
                        ),
                    ]
                )
            descriptions = [
                f"{row['scenario_id'].replace('_', ' ').title()} has "
                f"{format_number(row['estimated_visits'])} estimated visits "
                f"({row['uplift_pct']:+.1f}% versus its synthetic baseline)"
                for row in rows
            ]
            return RetrievalResult(
                context=context,
                evidence=evidence,
                related_plot_id="scenario_comparison",
                data_type="synthetic",
                limitations=[SYNTHETIC_LIMITATION, LIMITATION],
                local_answer=(
                    "In the synthetic test data, " + "; ".join(descriptions) + "."
                ),
            )

        leader = rows[0]
        evidence = [
            EvidenceItem(
                "Highest estimated scenario",
                leader["scenario_id"].replace("_", " ").title(),
                "store_visit_scenarios.csv",
            ),
            EvidenceItem(
                "Estimated visits",
                format_number(leader["estimated_visits"]),
                "store_visit_scenarios.csv",
            ),
            EvidenceItem(
                "Illustrative uplift",
                f"{leader['uplift_pct']:+.1f}%",
                "store_visit_scenarios.csv",
            ),
        ]
        return RetrievalResult(
            context=context,
            evidence=evidence,
            related_plot_id="scenario_comparison",
            data_type="synthetic",
            limitations=[SYNTHETIC_LIMITATION, LIMITATION],
            local_answer=(
                f"In the synthetic test data, {evidence[0].value} has the largest "
                f"estimated total at {evidence[1].value}, an illustrative "
                f"{evidence[2].value} change from its synthetic baseline."
            ),
        )

    if "brand" in normalized or named_brands:
        rows = (
            [row for row in data.brands if row["brand"] in named_brands]
            if named_brands
            else get_top_brands(data, metric, 8)
        )
        rows = sorted(rows, key=lambda row: row[metric], reverse=True)
        leader = rows[0]
        if named_brands:
            evidence = [
                EvidenceItem(
                    f"{row['brand']} {metric_label(metric)}",
                    format_number(row[metric]),
                    "visits_by_brand.csv",
                )
                for row in rows
            ]
            descriptions = [
                f"{row['brand']} has {format_number(row[metric])} "
                f"{metric_label(metric)}"
                for row in rows
            ]
            local_answer = "; ".join(descriptions) + "."
        else:
            evidence = [
                EvidenceItem("Top brand", leader["brand"], "visits_by_brand.csv"),
                EvidenceItem(
                    metric_label(metric).title(),
                    format_number(leader[metric]),
                    "visits_by_brand.csv",
                ),
                EvidenceItem(
                    "Unique stores", leader["unique_stores"], "visits_by_brand.csv"
                ),
            ]
            local_answer = (
                f"{leader['brand']} ranks first by {metric_label(metric)} at "
                f"{format_number(leader[metric])}. Its footprint includes "
                f"{leader['unique_stores']:,} unique stores in the prepared data."
            )
        context = "\n".join(
            f"{row['brand']}: total={row['total_visits']}, "
            f"mean={row['mean_daily_visits']}, stores={row['unique_stores']}"
            for row in rows
        )
        return RetrievalResult(
            context=context,
            evidence=evidence,
            related_plot_id="brand_ranking",
            data_type="derived",
            limitations=[LIMITATION],
            local_answer=local_answer,
        )

    if (
        any(word in normalized for word in ("category", "categories", "industry"))
        or named_categories
    ):
        rows = (
            [row for row in data.categories if row["category"] in named_categories]
            if named_categories
            else get_top_categories(data, metric, 8)
        )
        rows = sorted(rows, key=lambda row: row[metric], reverse=True)
        leader = rows[0]
        if named_categories:
            evidence = [
                EvidenceItem(
                    f"{row['category']} {metric_label(metric)}",
                    format_number(row[metric]),
                    "visits_by_category.csv",
                )
                for row in rows
            ]
            local_answer = "; ".join(
                f"{row['category']} has {format_number(row[metric])} "
                f"{metric_label(metric)}"
                for row in rows
            ) + "."
        else:
            evidence = [
                EvidenceItem(
                    "Top category", leader["category"], "visits_by_category.csv"
                ),
                EvidenceItem(
                    metric_label(metric).title(),
                    format_number(leader[metric]),
                    "visits_by_category.csv",
                ),
                EvidenceItem(
                    "Unique stores", leader["unique_stores"], "visits_by_category.csv"
                ),
            ]
            local_answer = (
                f"{leader['category']} ranks first by {metric_label(metric)} at "
                f"{format_number(leader[metric])}."
            )
        context = "\n".join(
            f"{row['category']}: total={row['total_visits']}, "
            f"mean={row['mean_daily_visits']}, stores={row['unique_stores']}"
            for row in rows
        )
        return RetrievalResult(
            context=context,
            evidence=evidence,
            related_plot_id="category_ranking",
            data_type="derived",
            limitations=[LIMITATION],
            local_answer=local_answer,
        )

    if (
        any(word in normalized for word in ("weekday", "weekend", "day of week"))
        or named_weekdays
    ):
        rows = get_weekday_pattern(data)
        if named_weekdays:
            rows = [row for row in rows if row["weekday"] in named_weekdays]
        leader = max(rows, key=lambda row: row["mean_daily_visits"])
        low = min(rows, key=lambda row: row["mean_daily_visits"])
        if named_weekdays:
            evidence = [
                EvidenceItem(
                    f"{row['weekday']} mean visits per store-day",
                    f"{row['mean_daily_visits']:,.2f}",
                    "weekday_patterns.csv",
                )
                for row in rows
            ]
            local_answer = "; ".join(
                f"{row['weekday']} averages {row['mean_daily_visits']:,.2f} "
                "visits per store-day"
                for row in rows
            ) + "."
        else:
            evidence = [
                EvidenceItem(
                    "Highest weekday", leader["weekday"], "weekday_patterns.csv"
                ),
                EvidenceItem(
                    "Highest mean visits",
                    leader["mean_daily_visits"],
                    "weekday_patterns.csv",
                ),
                EvidenceItem(
                    "Lowest weekday", low["weekday"], "weekday_patterns.csv"
                ),
            ]
            local_answer = (
                f"{leader['weekday']} has the highest mean activity at "
                f"{leader['mean_daily_visits']:,.2f} visits per store-day; "
                f"{low['weekday']} is lowest."
            )
        context = "\n".join(
            f"{row['weekday']}: mean={row['mean_daily_visits']}, "
            f"total={row['total_visits']}, weekend={row['is_weekend']}"
            for row in rows
        )
        return RetrievalResult(
            context=context,
            evidence=evidence,
            related_plot_id="weekday_pattern",
            data_type="derived",
            limitations=[LIMITATION],
            local_answer=local_answer,
        )

    if (
        any(word in normalized for word in ("market", "region", "city"))
        or named_markets
    ):
        rows = get_market_summary(data)
        if named_markets:
            rows = [row for row in rows if row["market"] in named_markets]
        leader = max(rows, key=lambda row: row[metric])
        if named_markets:
            evidence = [
                EvidenceItem(
                    f"{row['market']} {metric_label(metric)}",
                    format_number(row[metric]),
                    "visits_by_market.csv",
                )
                for row in rows
            ]
            local_answer = "; ".join(
                f"{row['market']} has {format_number(row[metric])} "
                f"{metric_label(metric)}"
                for row in rows
            ) + "."
        else:
            evidence = [
                EvidenceItem(
                    "Leading market", leader["market"], "visits_by_market.csv"
                ),
                EvidenceItem(
                    metric_label(metric).title(),
                    format_number(leader[metric]),
                    "visits_by_market.csv",
                ),
                EvidenceItem(
                    "Unique stores", leader["unique_stores"], "visits_by_market.csv"
                ),
            ]
            local_answer = (
                f"{leader['market']} leads by {metric_label(metric)} at "
                f"{format_number(leader[metric])}."
            )
        context = "\n".join(
            f"{row['market']}: total={row['total_visits']}, "
            f"mean={row['mean_daily_visits']}, stores={row['unique_stores']}"
            for row in rows
        )
        return RetrievalResult(
            context=context,
            evidence=evidence,
            related_plot_id="market_comparison",
            data_type="derived",
            limitations=[
                LIMITATION,
                "Combined market labels must not be interpreted as single cities.",
            ],
            local_answer=local_answer,
        )

    if any(
        term in normalized
        for term in ("distribution", "percentile", "skew", "median", "p99")
    ):
        evidence = [
            EvidenceItem(
                "Median visits per store-day",
                data.summary["median_daily_visits"],
                "summary_statistics.csv",
            ),
            EvidenceItem(
                "Mean visits per store-day",
                f"{data.summary['mean_daily_visits']:,.2f}",
                "summary_statistics.csv",
            ),
            EvidenceItem(
                "99th percentile",
                data.percentiles["p99"],
                "visit_percentiles.csv",
            ),
        ]
        context = (
            f"mean={data.summary['mean_daily_visits']}; "
            f"median={data.summary['median_daily_visits']}; "
            f"p25={data.percentiles['p25']}; p75={data.percentiles['p75']}; "
            f"p95={data.percentiles['p95']}; p99={data.percentiles['p99']}; "
            f"p99.9={data.percentiles['p999']}"
        )
        return RetrievalResult(
            context=context,
            evidence=evidence,
            related_plot_id="visit_distribution",
            data_type="derived",
            limitations=[LIMITATION],
            local_answer=(
                f"The distribution is right-skewed: the median is "
                f"{data.summary['median_daily_visits']:,} visits per store-day, "
                f"below the mean of {data.summary['mean_daily_visits']:,.2f}; "
                f"the 99th percentile is {data.percentiles['p99']:,}."
            ),
        )

    overview_terms = (
        "data",
        "dataset",
        "overview",
        "summary",
        "record",
        "store",
        "visit",
        "trend",
        "month",
        "season",
        "seasonality",
        "time of year",
        "busiest",
        "year",
        "date",
        "coverage",
        "quality",
        "limitation",
    )
    if not any(term in normalized for term in overview_terms):
        return refusal_result()

    monthly = data.monthly
    high = max(monthly, key=lambda row: row["mean_daily_visits"])
    low = min(monthly, key=lambda row: row["mean_daily_visits"])
    evidence = [
        EvidenceItem("Records", data.summary["total_rows"], "summary_statistics.csv"),
        EvidenceItem(
            "Date range",
            f"{data.summary['earliest_date']} to {data.summary['latest_date']}",
            "summary_statistics.csv",
        ),
        EvidenceItem(
            "Highest monthly mean",
            f"{high['month']}: {high['mean_daily_visits']:,.2f}",
            "monthly_trends.csv",
        ),
    ]
    context = (
        f"rows={data.summary['total_rows']}; stores={data.summary['unique_stores']}; "
        f"total transformed visits={data.summary['total_visits']}; "
        f"mean={data.summary['mean_daily_visits']}; "
        f"median={data.summary['median_daily_visits']}; date range="
        f"{data.summary['earliest_date']} to {data.summary['latest_date']}; "
        f"highest monthly mean={high['month']} {high['mean_daily_visits']}; "
        f"lowest monthly mean={low['month']} {low['mean_daily_visits']}"
    )
    return RetrievalResult(
        context=context,
        evidence=evidence,
        related_plot_id="monthly_trend",
        data_type="derived",
        limitations=[LIMITATION],
        local_answer=(
            f"The prepared dataset contains {data.summary['total_rows']:,} store-day "
            f"records across {data.summary['unique_stores']:,} stores from "
            f"{data.summary['earliest_date']} through {data.summary['latest_date']}."
        ),
    )
