"""Check whether the FinalFlow Streamlit bundle is ready to deploy.

This command validates local files and configuration without making an OpenAI
request or printing secret values.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from paddydash.services.ai_service import api_is_configured, get_model_name
from paddydash.services.data_service import load_dashboard_data, load_spatial_heat_data


DEPLOYABLE_FILES = (
    "paddydash/pages/project_evidence.py",
    "paddydash/services/project_context.py",
    "paddydash/services/search_service.py",
    "paddydash/services/search_models.py",
    "notebooks/tan-dat/data/summaries/weather_monthly.csv",
    "notebooks/duc-anh/data_clean/finalflow_business_integration.csv",
    "paddydash/app.py",
    "paddydash/components/charts.py",
    "paddydash/components/analytical_views.py",
    "paddydash/components/finalflow_shell.py",
    "paddydash/components/ui.py",
    "paddydash/components/match_controls.py",
    "paddydash/components/mobility_charts.py",
    "paddydash/pages/mobility.py",
    "paddydash/pages/matchday_timeline.py",
    "paddydash/pages/overview.py",
    "paddydash/pages/weather_heat.py",
    "paddydash/pages/store_visit_explorer.py",
    "paddydash/pages/scenario_explorer.py",
    "paddydash/pages/spatial_heat_map.py",
    "paddydash/pages/ask_finalflow.py",
    "paddydash/services/ai_service.py",
    "paddydash/services/analytics.py",
    "paddydash/services/data_service.py",
    "paddydash/services/finalflow_data.py",
    "paddydash/services/mobility_contract.py",
    "paddydash/services/mobility_config.py",
    "paddydash/services/mobility_simulator.py",
    "asset/rice_hack.png",
    "paddydash/DEPLOYMENT_GUIDE.md",
    "requirements.txt",
    ".streamlit/config.toml",
    ".env.example",
    "data/summaries/summary_statistics.csv",
    "data/summaries/visit_percentiles.csv",
    "data/summaries/visits_by_brand.csv",
    "data/summaries/visits_by_category.csv",
    "data/summaries/visits_by_market.csv",
    "data/summaries/weekday_patterns.csv",
    "data/summaries/monthly_trends.csv",
    "data/summaries/brand_monthly_trends.csv",
    "data/summaries/category_monthly_trends.csv",
    "data/summaries/spatial_heat_locations.csv",
    "data/summaries/spatial_heat_locations.metadata.json",
    "data/summaries/weather_risk_summary.csv",
    "data/summaries/weather_risk_summary.metadata.json",
    "data/synthetic/store_visit_scenarios.csv",
    "data/synthetic/store_visit_scenarios_dictionary.md",
    "data/exports/executive_kpis.csv",
    "data/exports/match_timeline_summary.csv",
    "data/exports/scenario_comparison.csv",
    "data/exports/commercial_context.csv",
    "data/exports/weather_heat_context.csv",
    "data/exports/mobility_node_timeseries.csv",
    "data/exports/mobility_edge_timeseries.csv",
    "data/exports/mobility_access_summary.csv",
    "data/exports/scenario_summary.csv",
    "data/exports/recommendation_catalog.csv",
    "data/exports/intervention_comparison.csv",
    "data/synthetic/corridor_reference.csv",
    "data/synthetic/transit_service_capacity.csv",
    "reports/figures/store_visits_distribution.png",
    "reports/figures/store_visits_top_brands.png",
    "reports/figures/store_visits_top_categories.png",
    "reports/figures/store_visits_weekday_pattern.png",
)
MAX_DEPLOYABLE_FILE_BYTES = 10_000_000
MAX_DEPLOYABLE_BUNDLE_BYTES = 20_000_000
ARTIFACT_MANIFESTS = {
    "data/summaries/spatial_heat_locations.csv": (
        "data/summaries/spatial_heat_locations.metadata.json"
    ),
    "data/summaries/weather_risk_summary.csv": (
        "data/summaries/weather_risk_summary.metadata.json"
    ),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_artifact_manifest(
    root: Path,
    artifact: str,
    manifest: str,
) -> list[str]:
    errors: list[str] = []
    artifact_path = root / artifact
    manifest_path = root / manifest
    try:
        metadata = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return [f"Artifact manifest is invalid ({manifest}): {error}"]
    if str(metadata.get("artifact", "")).replace("\\", "/") != artifact:
        errors.append(f"Artifact manifest path does not match {artifact}.")
    expected_hash = str(metadata.get("artifact_sha256", "")).casefold()
    if not expected_hash or expected_hash != _sha256(artifact_path).casefold():
        errors.append(f"Artifact SHA-256 does not match {artifact}.")
    try:
        with artifact_path.open("r", encoding="utf-8-sig", newline="") as stream:
            row_count = sum(1 for _ in csv.DictReader(stream))
    except (OSError, UnicodeError, csv.Error) as error:
        errors.append(f"Artifact rows could not be counted ({artifact}): {error}")
    else:
        if metadata.get("accepted_rows") != row_count:
            errors.append(f"Artifact row count does not match {manifest}.")
    return errors


def _tracked_files(root: Path) -> set[str] | None:
    try:
        completed = subprocess.run(
            ["git", "ls-files"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return {line.replace("\\", "/") for line in completed.stdout.splitlines()}


def run_checks(
    root: Path = REPOSITORY_ROOT,
    *,
    require_openai: bool = False,
    require_tracked: bool = False,
) -> dict[str, object]:
    root = root.resolve()
    errors: list[str] = []
    warnings: list[str] = []

    missing = [item for item in DEPLOYABLE_FILES if not (root / item).is_file()]
    if missing:
        errors.append("Missing deployable files: " + ", ".join(missing))

    bundle_size = sum(
        (root / item).stat().st_size
        for item in DEPLOYABLE_FILES
        if (root / item).is_file()
    )
    oversized_files = [
        item
        for item in DEPLOYABLE_FILES
        if (root / item).is_file()
        and (root / item).stat().st_size > MAX_DEPLOYABLE_FILE_BYTES
    ]
    if oversized_files:
        errors.append(
            "Deployable files exceed the 10 MB per-file limit: "
            + ", ".join(oversized_files)
        )
    if bundle_size > MAX_DEPLOYABLE_BUNDLE_BYTES:
        errors.append("Deployable bundle exceeds the 20 MB release limit.")

    if not missing:
        for artifact, manifest in ARTIFACT_MANIFESTS.items():
            errors.extend(validate_artifact_manifest(root, artifact, manifest))

    if not missing:
        try:
            load_dashboard_data.cache_clear()
            data = load_dashboard_data(str(root))
            spatial = load_spatial_heat_data(str(root))
        except (FileNotFoundError, KeyError, TypeError, ValueError) as error:
            errors.append(f"Prepared dashboard data failed validation: {error}")
        else:
            row_counts = {
                "brands": len(data.brands),
                "categories": len(data.categories),
                "markets": len(data.markets),
                "monthly": len(data.monthly),
                "scenarios": len(data.scenarios),
                "weather_metrics": len(data.weather),
                "spatial_locations": len(spatial),
            }
    else:
        row_counts = {}

    requirements_text = (root / "requirements.txt").read_text(
        encoding="utf-8"
    ) if (root / "requirements.txt").is_file() else ""
    for package in ("streamlit", "plotly", "openai", "pydantic"):
        if package not in requirements_text.lower():
            errors.append(f"requirements.txt does not list {package}.")

    gitignore_text = (root / ".gitignore").read_text(
        encoding="utf-8"
    ) if (root / ".gitignore").is_file() else ""
    if ".env" not in gitignore_text:
        errors.append(".env is not excluded by .gitignore.")

    tracked = _tracked_files(root)
    untracked_required: list[str] = []
    if tracked is None:
        warnings.append("Git tracking could not be checked in this environment.")
    else:
        untracked_required = [item for item in DEPLOYABLE_FILES if item not in tracked]
        if untracked_required:
            message = "Deployable files are not tracked in the Git index: " + ", ".join(
                untracked_required
            )
            (errors if require_tracked else warnings).append(message)

        unsafe_tracked = sorted(
            item
            for item in tracked
            if item.endswith(".parquet")
            or (
                item.startswith(("data/raw/", "data/external/", "data/processed/"))
                and not item.endswith(".gitkeep")
            )
        )
        if unsafe_tracked:
            errors.append(
                "Restricted or oversized data is tracked: " + ", ".join(unsafe_tracked)
            )

    openai_configured = api_is_configured()
    if not openai_configured:
        message = (
            "OPENAI_API_KEY is not configured; the deployed app will use "
            "prepared-data mode until the server-side secret is added."
        )
        (errors if require_openai else warnings).append(message)

    return {
        "status": "failed" if errors else ("ready_with_warnings" if warnings else "ready"),
        "entrypoint": "paddydash/app.py",
        "branch": "main",
        "bundle_size_mb": round(bundle_size / 1_000_000, 2),
        "bundle_limit_mb": MAX_DEPLOYABLE_BUNDLE_BYTES / 1_000_000,
        "prepared_row_counts": row_counts,
        "openai_configured": openai_configured,
        "openai_model": get_model_name(),
        "untracked_required_files": untracked_required,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-openai",
        action="store_true",
        help="Fail unless the server-side OPENAI_API_KEY is configured.",
    )
    parser.add_argument(
        "--require-tracked",
        action="store_true",
        help="Fail unless every deployable file is tracked in the Git index.",
    )
    args = parser.parse_args()
    report = run_checks(
        require_openai=args.require_openai,
        require_tracked=args.require_tracked,
    )
    print(json.dumps(report, indent=2))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
