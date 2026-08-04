"""Generate modest, clearly labeled store-visit scenarios for the prototype.

The generated records are for interface testing and scenario exploration. They
are not observed World Cup activity and must never be presented as forecasts.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


SCENARIOS = {
    "ordinary_day": {
        "label": "Ordinary day",
        "match_phase": "ordinary",
        "weather": "Clear",
        "multiplier": 1.00,
        "risk_shift": 0,
    },
    "pre_match": {
        "label": "Pre-match",
        "match_phase": "pre-match",
        "weather": "Clear",
        "multiplier": 1.25,
        "risk_shift": 1,
    },
    "during_match": {
        "label": "During match",
        "match_phase": "during match",
        "weather": "Clear",
        "multiplier": 0.85,
        "risk_shift": 1,
    },
    "post_match": {
        "label": "Post-match",
        "match_phase": "post-match",
        "weather": "Clear",
        "multiplier": 1.45,
        "risk_shift": 2,
    },
    "rainy_post_match": {
        "label": "Rainy post-match",
        "match_phase": "post-match",
        "weather": "Rain",
        "multiplier": 1.20,
        "risk_shift": 2,
    },
    "transit_disruption": {
        "label": "Transit disruption",
        "match_phase": "post-match",
        "weather": "Clear",
        "multiplier": 1.10,
        "risk_shift": 3,
    },
}

ZONE_MULTIPLIERS = {
    "stadium district": 1.30,
    "transit hub": 1.18,
    "fan zone": 1.22,
    "commercial corridor": 1.00,
}
ZONE_NORMALIZER = sum(ZONE_MULTIPLIERS.values()) / len(ZONE_MULTIPLIERS)

FIELDNAMES = [
    "scenario_id",
    "timestamp",
    "match_phase",
    "zone_type",
    "brand",
    "category",
    "baseline_visits",
    "estimated_visits",
    "weather_condition",
    "demand_level",
    "pedestrian_pressure",
    "mobility_conflict_risk",
    "is_synthetic",
    "data_type",
]

DISCLAIMER = (
    "This synthetic dataset is for interface testing, visualization, and "
    "scenario exploration. It does not represent measured World Cup activity "
    "or exact future store demand."
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate synthetic store-visit scenario records."
    )
    parser.add_argument(
        "--brand-summary",
        type=Path,
        default=Path("data/summaries/visits_by_brand.csv"),
    )
    parser.add_argument(
        "--brand-category-summary",
        type=Path,
        default=Path("data/summaries/brand_category_mix.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/synthetic/store_visit_scenarios.csv"),
    )
    parser.add_argument(
        "--dictionary",
        type=Path,
        default=Path("data/synthetic/store_visit_scenarios_dictionary.md"),
    )
    parser.add_argument("--rows", type=int, default=12_000)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def read_ranked_summary(path: Path, label_column: str) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Required summary does not exist: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    required = {label_column, "total_visits", "mean_daily_visits", "data_type"}
    missing = required - set(rows[0] if rows else [])
    if missing:
        raise ValueError(f"{path.name} is missing columns: {', '.join(sorted(missing))}")
    normalized = []
    for row in rows:
        if row["data_type"] != "derived":
            raise ValueError(f"{path.name} must contain only derived rows.")
        normalized.append(
            {
                "label": row[label_column],
                "total_visits": int(row["total_visits"]),
                "mean_daily_visits": float(row["mean_daily_visits"]),
            }
        )
    normalized.sort(key=lambda row: row["total_visits"], reverse=True)
    return normalized


def read_brand_category_mix(path: Path) -> dict[str, list[dict[str, Any]]]:
    if not path.exists():
        raise FileNotFoundError(f"Required brand-category summary does not exist: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    required = {
        "brand",
        "category",
        "record_count",
        "mean_daily_visits",
        "data_type",
    }
    missing = required - set(rows[0] if rows else [])
    if missing:
        raise ValueError(f"{path.name} is missing columns: {', '.join(sorted(missing))}")
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if row["data_type"] != "derived":
            raise ValueError(f"{path.name} must contain only derived rows.")
        grouped.setdefault(row["brand"], []).append(
            {
                "category": row["category"],
                "record_count": int(row["record_count"]),
                "mean_daily_visits": float(row["mean_daily_visits"]),
            }
        )
    return grouped


def weighted_choice(
    rng: random.Random, rows: list[dict[str, Any]]
) -> dict[str, Any]:
    weights = [math.sqrt(max(row["total_visits"], 1)) for row in rows]
    return rng.choices(rows, weights=weights, k=1)[0]


def category_for_brand(
    rng: random.Random,
    brand: str,
    brand_categories: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    options = brand_categories.get(brand)
    if not options:
        raise ValueError(f"No prepared category relationship exists for brand: {brand}")
    return rng.choices(
        options,
        weights=[max(row["record_count"], 1) for row in options],
        k=1,
    )[0]


def classify_demand(value: int) -> str:
    if value < 500:
        return "low"
    if value < 1_500:
        return "medium"
    if value < 4_000:
        return "high"
    return "very high"


def classify_pressure(ratio: float, zone: str) -> str:
    score = ratio + (0.35 if zone in {"stadium district", "transit hub"} else 0)
    if score < 1.05:
        return "low"
    if score < 1.45:
        return "medium"
    return "high"


def classify_risk(scenario: str, zone: str, rng: random.Random) -> str:
    zone_score = {
        "commercial corridor": 0,
        "fan zone": 1,
        "stadium district": 2,
        "transit hub": 2,
    }[zone]
    score = SCENARIOS[scenario]["risk_shift"] + zone_score + rng.choice([0, 0, 1])
    if score <= 1:
        return "low"
    if score <= 3:
        return "medium"
    return "high"


def generate_rows(
    count: int,
    seed: int,
    brands: list[dict[str, Any]],
    brand_categories: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    if count < 5_000 or count > 20_000:
        raise ValueError("--rows must be between 5,000 and 20,000.")
    rng = random.Random(seed)
    scenario_ids = list(SCENARIOS)
    zones = list(ZONE_MULTIPLIERS)
    start = datetime(2026, 1, 5, 8, 0)
    rows: list[dict[str, Any]] = []

    for index in range(count):
        scenario_id = scenario_ids[index % len(scenario_ids)]
        scenario = SCENARIOS[scenario_id]
        zone = rng.choice(zones)
        brand = weighted_choice(rng, brands)
        category = category_for_brand(rng, brand["label"], brand_categories)
        base_mean = math.sqrt(
            max(brand["mean_daily_visits"], 1)
            * max(category["mean_daily_visits"], 1)
        )
        baseline = max(0, round(base_mean * rng.lognormvariate(-0.15, 0.45)))
        noise = max(0.65, min(rng.normalvariate(1.0, 0.10), 1.35))
        estimate = max(
            0,
            round(
                baseline
                * scenario["multiplier"]
                * (ZONE_MULTIPLIERS[zone] / ZONE_NORMALIZER)
                * noise
            ),
        )
        ratio = estimate / max(baseline, 1)
        timestamp = start + timedelta(
            days=index % 18,
            hours=rng.randint(0, 15),
            minutes=rng.choice([0, 15, 30, 45]),
        )
        rows.append(
            {
                "scenario_id": scenario_id,
                "timestamp": timestamp.isoformat(timespec="minutes"),
                "match_phase": scenario["match_phase"],
                "zone_type": zone,
                "brand": brand["label"],
                "category": category["category"],
                "baseline_visits": baseline,
                "estimated_visits": estimate,
                "weather_condition": scenario["weather"],
                "demand_level": classify_demand(estimate),
                "pedestrian_pressure": classify_pressure(ratio, zone),
                "mobility_conflict_risk": classify_risk(scenario_id, zone, rng),
                "is_synthetic": "true",
                "data_type": "synthetic",
            }
        )
    return rows


def write_dictionary(path: Path, rows: int, seed: int) -> None:
    multipliers = "\n".join(
        f"- `{key}` ({item['label']}): {item['multiplier']:.2f}x baseline"
        for key, item in SCENARIOS.items()
    )
    text = f"""# Synthetic Store-Visit Scenario Data Dictionary

{DISCLAIMER}

## Reproducibility

- Rows: {rows:,}
- Fixed random seed: {seed}
- Negative values: prevented by construction
- Data label: `synthetic`

## Scenario multipliers

{multipliers}

Zone weights are 1.30 for stadium districts, 1.18 for transit hubs, 1.22 for
fan zones, and 1.00 for commercial corridors. They are divided by their 1.175
mean so the average zone effect is 1.00x; the stated scenario multiplier remains
the expected overall effect. A bounded random factor from 0.65 to 1.35 adds
variation. Brands are sampled from the top 25 using square-root total-visit
weights. Each sampled brand's category is then drawn from that brand's observed
prepared category mix using record-count weights. These assumptions are
illustrative, not predictions.

## Fields

| Field | Meaning |
| --- | --- |
| `scenario_id` | Stable identifier for one of six hypothetical scenarios. |
| `timestamp` | Hypothetical interface-testing timestamp, not a match schedule. |
| `match_phase` | Ordinary, pre-match, during-match, or post-match phase. |
| `zone_type` | Hypothetical stadium, transit, fan-zone, or commercial context. |
| `brand` | Brand sampled from the derived store-visit brand summary. |
| `category` | Category sampled from the selected brand's derived category mix. |
| `baseline_visits` | Synthetic baseline based on historical mean intensities. |
| `estimated_visits` | Baseline after documented scenario, zone, and noise factors. |
| `weather_condition` | Simplified clear or rain scenario condition. |
| `demand_level` | Low, medium, high, or very-high synthetic demand band. |
| `pedestrian_pressure` | Low, medium, or high illustrative pressure band. |
| `mobility_conflict_risk` | Low, medium, or high illustrative conflict-risk band. |
| `is_synthetic` | Always `true`. |
| `data_type` | Always `synthetic`. |
"""
    path.write_text(text, encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    output = args.output.resolve()
    dictionary = args.dictionary.resolve()
    existing = [path for path in (output, dictionary) if path.exists()]
    if existing and not args.overwrite:
        raise FileExistsError(
            "Outputs already exist; pass --overwrite to replace them: "
            + ", ".join(str(path) for path in existing)
        )
    brands = read_ranked_summary(args.brand_summary.resolve(), "brand")[:25]
    brand_categories = read_brand_category_mix(args.brand_category_summary.resolve())
    rows = generate_rows(args.rows, args.seed, brands, brand_categories)
    output.parent.mkdir(parents=True, exist_ok=True)
    dictionary.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    write_dictionary(dictionary, args.rows, args.seed)
    return {
        "output": str(output),
        "dictionary": str(dictionary),
        "rows": len(rows),
        "seed": args.seed,
        "scenarios": list(SCENARIOS),
        "disclaimer": DISCLAIMER,
    }


def main(argv: list[str] | None = None) -> int:
    try:
        result = run(parse_args(argv))
    except (OSError, ValueError) as error:
        print(f"Error: {error}", flush=True)
        return 1
    print(json.dumps(result, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
