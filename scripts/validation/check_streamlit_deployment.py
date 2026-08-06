"""Check whether the FinalFlow Streamlit bundle is ready to deploy.

This command validates local files and configuration without making an OpenAI
request or printing secret values.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from paddydash.services.ai_service import api_is_configured, get_model_name
from paddydash.services.data_service import load_dashboard_data


DEPLOYABLE_FILES = (
    "paddydash/app.py",
    "paddydash/components/charts.py",
    "paddydash/components/ui.py",
    "paddydash/pages/overview.py",
    "paddydash/pages/store_visit_explorer.py",
    "paddydash/pages/scenario_explorer.py",
    "paddydash/pages/ask_finalflow.py",
    "paddydash/services/ai_service.py",
    "paddydash/services/analytics.py",
    "paddydash/services/data_service.py",
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
    "data/synthetic/store_visit_scenarios.csv",
    "data/synthetic/store_visit_scenarios_dictionary.md",
    "reports/figures/store_visits_distribution.png",
    "reports/figures/store_visits_top_brands.png",
    "reports/figures/store_visits_top_categories.png",
    "reports/figures/store_visits_weekday_pattern.png",
)


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

    if not missing:
        try:
            load_dashboard_data.cache_clear()
            data = load_dashboard_data(str(root))
        except (FileNotFoundError, KeyError, TypeError, ValueError) as error:
            errors.append(f"Prepared dashboard data failed validation: {error}")
        else:
            row_counts = {
                "brands": len(data.brands),
                "categories": len(data.categories),
                "markets": len(data.markets),
                "monthly": len(data.monthly),
                "scenarios": len(data.scenarios),
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
            message = "Deployable files are not committed yet: " + ", ".join(
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
        "branch": "HaiNam",
        "bundle_size_mb": round(bundle_size / 1_000_000, 2),
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
        help="Fail unless every deployable file has been committed to Git.",
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
