"""Validate the local .env configuration without printing credential values."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import dotenv_values


def validate_local_env(path: Path) -> list[str]:
    if not path.is_file():
        return [f"Local environment file is missing: {path}"]

    values = dotenv_values(path)
    errors: list[str] = []
    key = values.get("OPENAI_API_KEY")
    if not isinstance(key, str) or not key.strip():
        errors.append("OPENAI_API_KEY is missing or empty in .env.")
    elif len(key.strip()) < 20:
        errors.append("OPENAI_API_KEY appears incomplete in .env.")

    model = values.get("OPENAI_MODEL")
    if not isinstance(model, str) or not model.strip():
        errors.append("OPENAI_MODEL must be set in .env.")

    request_limit = values.get("FINALFLOW_MAX_AI_REQUESTS_PER_SESSION")
    try:
        parsed_limit = int(request_limit)
    except (TypeError, ValueError):
        errors.append("FINALFLOW_MAX_AI_REQUESTS_PER_SESSION must be an integer.")
    else:
        if not 1 <= parsed_limit <= 100:
            errors.append(
                "FINALFLOW_MAX_AI_REQUESTS_PER_SESSION must be between 1 and 100."
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    errors = validate_local_env(args.path)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Local .env is configured. Credential values were not printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
