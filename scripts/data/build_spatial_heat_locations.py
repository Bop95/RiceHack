"""Build the compact, validated spatial-heat table used by Streamlit.

The command reads the spatial collaborator's cleaned POI/UHI and spending ZIPs without
extracting them into the repository. It deliberately publishes spend/customer
tiers rather than raw values and excludes provided rows that are synthetic or
have an unknown synthetic flag.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable
from zipfile import ZipFile


DEFAULT_BOUNDS = (40.4, 41.1, -74.5, -73.5)
DEFAULT_MAX_UHI_DISTANCE_M = 250.0
GRID_SIZE_DEGREES = 0.005
RISK_RULE_VERSION = "spatial_heat_rules_v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--poi-uhi-zip", type=Path, required=True)
    parser.add_argument("--spending-zip", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/summaries/spatial_heat_locations.csv"),
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=None,
        help="Defaults to <output stem>.metadata.json beside --output.",
    )
    parser.add_argument("--generated-at", required=True)
    parser.add_argument("--source-commit", default="8b54df4")
    parser.add_argument("--min-lat", type=float, default=DEFAULT_BOUNDS[0])
    parser.add_argument("--max-lat", type=float, default=DEFAULT_BOUNDS[1])
    parser.add_argument("--min-lon", type=float, default=DEFAULT_BOUNDS[2])
    parser.add_argument("--max-lon", type=float, default=DEFAULT_BOUNDS[3])
    parser.add_argument(
        "--max-uhi-distance-m",
        type=float,
        default=DEFAULT_MAX_UHI_DISTANCE_M,
    )
    args = parser.parse_args()
    if args.metadata is None:
        args.metadata = args.output.with_suffix(".metadata.json")
    return args


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def zip_csv_rows(
    zip_path: Path,
    member: str,
    required_columns: set[str],
) -> Iterable[dict[str, str]]:
    with ZipFile(zip_path) as archive:
        with archive.open(member) as binary:
            import io

            with io.TextIOWrapper(binary, encoding="utf-8-sig", newline="") as text:
                reader = csv.DictReader(text)
                missing = required_columns - set(reader.fieldnames or [])
                if missing:
                    raise ValueError(
                        f"{member} is missing columns: {', '.join(sorted(missing))}"
                    )
                yield from reader


def parse_float(value: str | None) -> float | None:
    if value is None or not value.strip():
        return None
    try:
        result = float(value)
    except ValueError:
        return None
    return result if math.isfinite(result) else None


def parse_source_bool(value: str | None) -> bool | None:
    normalized = (value or "").strip().casefold()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    return None


def clean_text(value: str | None, fallback: str) -> str:
    return (value or "").strip() or fallback


def in_bounds(
    latitude: float,
    longitude: float,
    bounds: tuple[float, float, float, float],
) -> bool:
    min_lat, max_lat, min_lon, max_lon = bounds
    return min_lat <= latitude <= max_lat and min_lon <= longitude <= max_lon


def load_candidate_pois(
    source_zip: Path,
    bounds: tuple[float, float, float, float],
) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    candidates: dict[str, dict[str, Any]] = {}
    counts: defaultdict[str, int] = defaultdict(int)
    required = {
        "PLACEKEY",
        "LOCATION_NAME",
        "TOP_CATEGORY",
        "LATITUDE",
        "LONGITUDE",
        "CITY",
        "REGION",
        "INCLUDES_PARKING_LOT",
        "IS_SYNTHETIC",
    }
    for row in zip_csv_rows(source_zip, "poi_summary.csv", required):
        counts["poi_input_rows"] += 1
        latitude = parse_float(row.get("LATITUDE"))
        longitude = parse_float(row.get("LONGITUDE"))
        if latitude is None or longitude is None:
            counts["rejected_invalid_coordinates"] += 1
            continue
        if not in_bounds(latitude, longitude, bounds):
            counts["rejected_outside_bounds"] += 1
            continue
        synthetic = parse_source_bool(row.get("IS_SYNTHETIC"))
        if synthetic is True:
            counts["rejected_synthetic"] += 1
            continue
        if synthetic is None:
            counts["rejected_unknown_synthetic_status"] += 1
            continue
        placekey = (row.get("PLACEKEY") or "").strip()
        if not placekey:
            counts["rejected_missing_placekey"] += 1
            continue
        if placekey in candidates:
            counts["rejected_duplicate_placekey"] += 1
            continue
        candidates[placekey] = {
            "placekey": placekey,
            "location_name": clean_text(row.get("LOCATION_NAME"), "Unknown location"),
            "market": "New York/New Jersey exploratory corridor",
            "city": clean_text(row.get("CITY"), "Unknown"),
            "region": (row.get("REGION") or "").strip(),
            "latitude": latitude,
            "longitude": longitude,
            "top_category": clean_text(row.get("TOP_CATEGORY"), "Unknown"),
            "includes_parking": parse_source_bool(row.get("INCLUDES_PARKING_LOT")),
        }
    counts["candidate_pois"] = len(candidates)
    return candidates, dict(counts)


def aggregate_spending(
    source_zip: Path, candidate_keys: set[str]
) -> tuple[dict[str, dict[str, float | int]], dict[str, int]]:
    spending: defaultdict[str, dict[str, float | int]] = defaultdict(
        lambda: {"spend": 0.0, "customers": 0.0, "rows": 0}
    )
    counts: defaultdict[str, int] = defaultdict(int)
    required = {"PLACEKEY", "RAW_TOTAL_SPEND", "RAW_NUM_CUSTOMERS"}
    for row in zip_csv_rows(source_zip, "spending_summary.csv", required):
        counts["spending_input_rows"] += 1
        placekey = (row.get("PLACEKEY") or "").strip()
        if placekey not in candidate_keys:
            continue
        spend = parse_float(row.get("RAW_TOTAL_SPEND"))
        customers = parse_float(row.get("RAW_NUM_CUSTOMERS"))
        if spend is None or customers is None or spend < 0 or customers < 0:
            counts["rejected_invalid_spending_rows"] += 1
            continue
        item = spending[placekey]
        item["spend"] = float(item["spend"]) + spend
        item["customers"] = float(item["customers"]) + customers
        item["rows"] = int(item["rows"]) + 1
        counts["accepted_spending_rows"] += 1
    counts["places_with_spending"] = len(spending)
    return dict(spending), dict(counts)


def grid_key(latitude: float, longitude: float) -> tuple[int, int]:
    return (
        math.floor(latitude / GRID_SIZE_DEGREES),
        math.floor(longitude / GRID_SIZE_DEGREES),
    )


def load_uhi_grid(
    source_zip: Path,
    bounds: tuple[float, float, float, float],
) -> tuple[dict[tuple[int, int], list[tuple[float, float, float]]], dict[str, int]]:
    min_lat, max_lat, min_lon, max_lon = bounds
    padding = 0.01
    expanded = (
        min_lat - padding,
        max_lat + padding,
        min_lon - padding,
        max_lon + padding,
    )
    coordinate_values: defaultdict[tuple[float, float], list[float]] = defaultdict(list)
    counts: defaultdict[str, int] = defaultdict(int)
    required = {"LATITUDE", "LONGITUDE", "UHI"}
    for row in zip_csv_rows(source_zip, "uhi_summary.csv", required):
        counts["uhi_input_rows"] += 1
        latitude = parse_float(row.get("LATITUDE"))
        longitude = parse_float(row.get("LONGITUDE"))
        uhi = parse_float(row.get("UHI"))
        if latitude is None or longitude is None or uhi is None:
            counts["rejected_invalid_uhi_rows"] += 1
            continue
        if not in_bounds(latitude, longitude, expanded):
            continue
        coordinate_values[(latitude, longitude)].append(uhi)

    grid: defaultdict[tuple[int, int], list[tuple[float, float, float]]] = defaultdict(list)
    for (latitude, longitude), values in sorted(coordinate_values.items()):
        grid[grid_key(latitude, longitude)].append(
            (latitude, longitude, sum(values) / len(values))
        )
    counts["uhi_points_in_expanded_bounds"] = sum(map(len, grid.values()))
    counts["uhi_duplicate_rows_collapsed"] = sum(
        max(0, len(values) - 1) for values in coordinate_values.values()
    )
    return dict(grid), dict(counts)


def haversine_meters(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    radius_m = 6_371_008.8
    lat_a = math.radians(latitude_a)
    lat_b = math.radians(latitude_b)
    delta_lat = lat_b - lat_a
    delta_lon = math.radians(longitude_b - longitude_a)
    term = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat_a) * math.cos(lat_b) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * radius_m * math.asin(math.sqrt(term))


def nearest_uhi(
    latitude: float,
    longitude: float,
    grid: dict[tuple[int, int], list[tuple[float, float, float]]],
    maximum_distance_m: float,
) -> tuple[float | None, float | None]:
    base_lat, base_lon = grid_key(latitude, longitude)
    candidates: list[tuple[float, float, float, float]] = []
    for delta_lat in (-1, 0, 1):
        for delta_lon in (-1, 0, 1):
            for candidate_lat, candidate_lon, uhi in grid.get(
                (base_lat + delta_lat, base_lon + delta_lon), []
            ):
                distance = haversine_meters(
                    latitude, longitude, candidate_lat, candidate_lon
                )
                candidates.append((distance, candidate_lat, candidate_lon, uhi))
    if not candidates:
        return None, None
    distance, _, _, uhi = min(candidates)
    if distance > maximum_distance_m:
        return None, None
    return uhi, distance


def assign_terciles(
    values: dict[str, float],
) -> dict[str, str]:
    ordered = sorted(values, key=lambda key: (values[key], key))
    total = len(ordered)
    labels = ("Low", "Medium", "High")
    return {
        key: labels[min(2, index * 3 // total)]
        for index, key in enumerate(ordered)
    } if total else {}


def output_fields() -> list[str]:
    return [
        "placekey",
        "location_name",
        "market",
        "city",
        "region",
        "latitude",
        "longitude",
        "top_category",
        "includes_parking",
        "spending_level",
        "customer_activity_level",
        "nearby_uhi",
        "uhi_match_method",
        "uhi_match_distance_m",
        "evidence_status",
        "commercial_opportunity",
        "heat_concern",
        "recommendation",
        "reason",
        "is_synthetic",
        "data_type",
        "source_file",
        "generated_at",
    ]


def build(args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    bounds = (args.min_lat, args.max_lat, args.min_lon, args.max_lon)
    if not all(math.isfinite(value) for value in bounds):
        raise ValueError("Spatial bounds must be finite.")
    if args.min_lat >= args.max_lat or args.min_lon >= args.max_lon:
        raise ValueError("Spatial minimum bounds must be below maximum bounds.")
    if not math.isfinite(args.max_uhi_distance_m) or args.max_uhi_distance_m <= 0:
        raise ValueError("Maximum UHI distance must be a positive finite value.")
    candidates, poi_counts = load_candidate_pois(args.poi_uhi_zip, bounds)
    spending, spending_counts = aggregate_spending(
        args.spending_zip, set(candidates)
    )
    grid, uhi_counts = load_uhi_grid(args.poi_uhi_zip, bounds)

    accepted_keys = sorted(set(candidates) & set(spending))
    spend_levels = assign_terciles(
        {key: float(spending[key]["spend"]) for key in accepted_keys}
    )
    customer_levels = assign_terciles(
        {key: float(spending[key]["customers"]) for key in accepted_keys}
    )

    rows: list[dict[str, Any]] = []
    missing_uhi = 0
    for key in accepted_keys:
        item = candidates[key]
        nearby_uhi, distance = nearest_uhi(
            item["latitude"],
            item["longitude"],
            grid,
            args.max_uhi_distance_m,
        )
        if nearby_uhi is None:
            missing_uhi += 1
            evidence_status = "missing_uhi"
            heat_concern = "Insufficient evidence"
            recommendation = "Insufficient evidence"
            reason = "No UHI point matched within the approved distance"
        elif nearby_uhi > 7:
            evidence_status = "complete"
            heat_concern = "High"
            recommendation = "Avoid outdoor concentration"
            reason = "High heat concern under FinalFlow's UHI > 7 heuristic"
        else:
            evidence_status = "complete"
            heat_concern = "Low/Moderate"
            recommendation = "Controlled use"
            reason = "Heat evidence is below the high-concern heuristic; monitor conditions"

        parking = item["includes_parking"]
        rows.append(
            {
                **item,
                "includes_parking": "" if parking is None else str(parking).lower(),
                "spending_level": spend_levels[key],
                "customer_activity_level": customer_levels[key],
                "nearby_uhi": "" if nearby_uhi is None else round(nearby_uhi, 3),
                "uhi_match_method": "nearest_haversine_wgs84_within_limit",
                "uhi_match_distance_m": "" if distance is None else round(distance, 2),
                "evidence_status": evidence_status,
                "commercial_opportunity": spend_levels[key],
                "heat_concern": heat_concern,
                "recommendation": recommendation,
                "reason": reason,
                "is_synthetic": "false",
                "data_type": "derived",
                "source_file": "poi_summary.csv; spending_summary.csv; uhi_summary.csv",
                "generated_at": args.generated_at,
            }
        )

    rejection_counts = {
        key: value
        for key, value in poi_counts.items()
        if key.startswith("rejected_")
    }
    rejection_counts["candidate_pois_without_spending"] = len(candidates) - len(
        accepted_keys
    )
    metadata = {
        "artifact": args.output.as_posix(),
        "source_branch": "que-anh",
        "source_commit": args.source_commit,
        "source_files": {
            args.poi_uhi_zip.name: sha256(args.poi_uhi_zip),
            args.spending_zip.name: sha256(args.spending_zip),
        },
        "generated_at": args.generated_at,
        "risk_rule_version": RISK_RULE_VERSION,
        "geographic_scope": {
            "name": "New York/New Jersey exploratory corridor",
            "bounds": {
                "min_latitude": args.min_lat,
                "max_latitude": args.max_lat,
                "min_longitude": args.min_lon,
                "max_longitude": args.max_lon,
            },
            "status": "implementation default approved by team lead; replace with polygon when supplied",
        },
        "uhi_match": {
            "method": "nearest_haversine_wgs84_within_limit",
            "maximum_distance_m": args.max_uhi_distance_m,
            "duplicate_coordinates": "mean UHI before matching",
            "tie_break": "distance, latitude, longitude, UHI ascending",
        },
        "spending_aggregation": (
            "sum all provided rows per PLACEKEY, then derive deterministic "
            "rank-based terciles with PLACEKEY tie-breaking"
        ),
        "public_fields": "raw spend and raw customer values omitted",
        "input_counts": {**poi_counts, **spending_counts, **uhi_counts},
        "accepted_rows": len(rows),
        "rejected_rows": sum(rejection_counts.values()),
        "rejected_by_reason": rejection_counts,
        "missing_uhi_rows": missing_uhi,
    }
    return rows, metadata


def main() -> int:
    args = parse_args()
    rows, metadata = build(args)
    if not rows:
        raise SystemExit("No spatial rows passed the approved filters.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=output_fields())
        writer.writeheader()
        writer.writerows(rows)
    metadata["artifact_sha256"] = sha256(args.output)
    args.metadata.parent.mkdir(parents=True, exist_ok=True)
    args.metadata.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"Wrote {len(rows):,} spatial rows to {args.output}; "
        f"{metadata['missing_uhi_rows']:,} have insufficient UHI evidence."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
