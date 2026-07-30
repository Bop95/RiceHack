"""Audit local tabular files for basic FinalFlow data-quality signals.

The utility is intentionally focused and beginner-friendly. It reads a local
input file, builds a JSON-serializable report, and never modifies the input.
CSV and JSON Lines use only the Python standard library. Parquet is supported
only when an installed pandas/pyarrow stack is already available.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DATA_TYPE = "provided"
SUPPORTED_TEXT_SUFFIXES = {".csv", ".jsonl", ".ndjson"}
PARQUET_SUFFIX = ".parquet"


def positive_int(value: str) -> int:
    """Parse a non-negative integer for argparse."""
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be an integer") from error
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return parsed


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Audit a CSV, JSON Lines, or supported Parquet file.",
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to the local input file. The input is never modified.",
    )
    parser.add_argument(
        "--name",
        required=True,
        help="Human-readable dataset name for the audit report.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON output path. If omitted, JSON is printed to stdout.",
    )
    parser.add_argument(
        "--sample-rows",
        type=positive_int,
        default=5,
        help="Maximum number of sample rows to include. Default: 5.",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="Text encoding for CSV and JSON Lines files. Default: utf-8.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting an existing output JSON file.",
    )
    return parser.parse_args(argv)


def audit_file(path: Path, dataset_name: str, encoding: str, sample_rows: int) -> dict[str, Any]:
    """Audit a supported file based on its extension."""
    input_path = validate_input_path(path)
    suffix = input_path.suffix.lower()
    if suffix == ".csv":
        return audit_csv(input_path, dataset_name, encoding, sample_rows)
    if suffix in {".jsonl", ".ndjson"}:
        return audit_jsonl(input_path, dataset_name, encoding, sample_rows)
    if suffix == PARQUET_SUFFIX:
        return audit_parquet(input_path, dataset_name, sample_rows)
    raise ValueError(
        "Unsupported file extension. Supported formats are .csv, .jsonl, .ndjson, "
        "and .parquet when pandas with a Parquet engine is installed."
    )


def validate_input_path(path: Path) -> Path:
    """Validate that the input path exists and is a file."""
    input_path = path.expanduser()
    if not input_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_path}")
    if input_path.is_dir():
        raise IsADirectoryError(f"Input path is a directory, not a file: {input_path}")
    if not input_path.is_file():
        raise ValueError(f"Input path is not a regular file: {input_path}")
    return input_path


def audit_csv(path: Path, dataset_name: str, encoding: str = "utf-8", sample_rows: int = 5) -> dict[str, Any]:
    """Audit a CSV file using the standard library."""
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    try:
        with path.open("r", encoding=encoding, newline="") as handle:
            reader = csv.DictReader(handle)
            columns = list(reader.fieldnames or [])
            for line_number, row in enumerate(reader, start=2):
                if None in row:
                    raise ValueError(f"Malformed CSV row at line {line_number}: too many fields.")
                rows.append({column: row.get(column, "") for column in columns})
    except UnicodeDecodeError as error:
        raise ValueError(f"Could not decode file with encoding {encoding}: {path}") from error
    except csv.Error as error:
        raise ValueError(f"Malformed CSV file: {error}") from error

    if path.stat().st_size == 0:
        warnings.append("Input file is empty.")
    if not columns:
        warnings.append("No header row was detected.")
    return build_report(
        dataset_name=dataset_name,
        path=path,
        file_type="csv",
        columns=columns,
        rows=rows,
        sample_rows=sample_rows,
        warnings=warnings,
    )


def audit_jsonl(path: Path, dataset_name: str, encoding: str = "utf-8", sample_rows: int = 5) -> dict[str, Any]:
    """Audit a JSON Lines file using the standard library."""
    rows: list[dict[str, Any]] = []
    columns: list[str] = []
    seen_columns: set[str] = set()
    warnings: list[str] = []
    blank_line_count = 0

    try:
        with path.open("r", encoding=encoding) as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    blank_line_count += 1
                    continue
                try:
                    value = json.loads(stripped)
                except json.JSONDecodeError as error:
                    raise ValueError(f"Malformed JSON Lines file at line {line_number}: {error.msg}") from error
                if not isinstance(value, dict):
                    raise ValueError(f"JSON Lines record at line {line_number} is not an object.")
                row = {str(key): make_json_safe(item) for key, item in value.items()}
                rows.append(row)
                for column in row:
                    if column not in seen_columns:
                        seen_columns.add(column)
                        columns.append(column)
    except UnicodeDecodeError as error:
        raise ValueError(f"Could not decode file with encoding {encoding}: {path}") from error

    if path.stat().st_size == 0:
        warnings.append("Input file is empty.")
    if blank_line_count:
        warnings.append(f"{blank_line_count} blank line(s) were ignored.")
    return build_report(
        dataset_name=dataset_name,
        path=path,
        file_type="jsonl",
        columns=columns,
        rows=rows,
        sample_rows=sample_rows,
        warnings=warnings,
    )


def audit_parquet(path: Path, dataset_name: str, sample_rows: int = 5) -> dict[str, Any]:
    """Audit a Parquet file when pandas and a Parquet engine are already installed."""
    try:
        import pandas as pd  # type: ignore[import-not-found]
    except ImportError as error:
        raise ValueError("Parquet audit requires pandas with a Parquet engine installed.") from error

    try:
        dataframe = pd.read_parquet(path)
    except Exception as error:  # pandas raises optional dependency and engine-specific errors.
        raise ValueError(f"Could not read Parquet file: {error}") from error

    columns = [str(column) for column in dataframe.columns]
    rows = dataframe.astype(object).where(dataframe.notna(), None).to_dict(orient="records")
    safe_rows = [{str(key): make_json_safe(value) for key, value in row.items()} for row in rows]
    return build_report(
        dataset_name=dataset_name,
        path=path,
        file_type="parquet",
        columns=columns,
        rows=safe_rows,
        sample_rows=sample_rows,
        warnings=[],
    )


def build_report(
    dataset_name: str,
    path: Path,
    file_type: str,
    columns: list[str],
    rows: list[dict[str, Any]],
    sample_rows: int,
    warnings: list[str],
) -> dict[str, Any]:
    """Build the shared audit report shape."""
    row_count = len(rows)
    missing_counts = {column: 0 for column in columns}
    values_by_column: dict[str, list[Any]] = {column: [] for column in columns}

    for row in rows:
        for column in columns:
            value = row.get(column)
            if is_missing(value):
                missing_counts[column] += 1
            else:
                values_by_column[column].append(value)

    missing_percentages = {
        column: round((missing_counts[column] / row_count) * 100, 2) if row_count else 0.0
        for column in columns
    }
    duplicate_row_count = count_duplicate_rows(rows, columns)
    column_types = {column: infer_column_type(values_by_column[column]) for column in columns}
    sample = [normalize_row(row, columns) for row in rows[:sample_rows]]

    report_warnings = list(warnings)
    if row_count == 0:
        report_warnings.append("No data rows were detected.")
    if duplicate_row_count:
        report_warnings.append(f"{duplicate_row_count} duplicate row(s) were detected.")
    missing_column_count = sum(1 for count in missing_counts.values() if count > 0)
    if missing_column_count:
        report_warnings.append(f"Missing values were detected in {missing_column_count} column(s).")
    if not columns:
        report_warnings.append("No columns were detected.")

    return {
        "dataset_name": dataset_name,
        "source_file": str(path),
        "file_type": file_type,
        "file_size_bytes": path.stat().st_size,
        "row_count": row_count,
        "column_count": len(columns),
        "columns": columns,
        "column_types": column_types,
        "missing_counts": missing_counts,
        "missing_percentages": missing_percentages,
        "duplicate_row_count": duplicate_row_count,
        "sample_rows": sample,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "data_type": DATA_TYPE,
        "warnings": report_warnings,
    }


def is_missing(value: Any) -> bool:
    """Return whether a value should count as missing."""
    return value is None or (isinstance(value, str) and value.strip() == "")


def infer_column_type(values: list[Any]) -> str:
    """Infer a simple JSON-friendly type label for non-missing values."""
    if not values:
        return "empty"
    inferred = {infer_value_type(value) for value in values}
    if len(inferred) == 1:
        return next(iter(inferred))
    numeric = {"integer", "number"}
    if inferred.issubset(numeric):
        return "number"
    return "mixed"


def infer_value_type(value: Any) -> str:
    """Infer a simple type label for one value."""
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, (dict, list)):
        return "object"
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.lower() in {"true", "false"}:
            return "boolean"
        try:
            int(stripped)
            return "integer"
        except ValueError:
            pass
        try:
            float(stripped)
            return "number"
        except ValueError:
            return "string"
    return "string"


def count_duplicate_rows(rows: list[dict[str, Any]], columns: list[str]) -> int:
    """Count duplicate rows using a deterministic JSON representation."""
    seen: set[str] = set()
    duplicate_count = 0
    for row in rows:
        row_key = json.dumps(normalize_row(row, columns), sort_keys=True, separators=(",", ":"))
        if row_key in seen:
            duplicate_count += 1
        else:
            seen.add(row_key)
    return duplicate_count


def normalize_row(row: dict[str, Any], columns: list[str]) -> dict[str, Any]:
    """Return a JSON-safe row with column order preserved."""
    return {column: make_json_safe(row.get(column)) for column in columns}


def make_json_safe(value: Any) -> Any:
    """Convert common non-JSON-native values to JSON-safe values."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): make_json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [make_json_safe(item) for item in value]
    return str(value)


def write_report(report: dict[str, Any], output_path: Path, overwrite: bool = False) -> None:
    """Write an audit report as formatted UTF-8 JSON."""
    path = output_path.expanduser()
    if path.exists() and not overwrite:
        raise FileExistsError(f"Output already exists. Use --overwrite to replace it: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Run the command-line entry point."""
    args = parse_args(argv)
    try:
        report = audit_file(args.input, args.name, args.encoding, args.sample_rows)
        if args.output:
            write_report(report, args.output, overwrite=args.overwrite)
            print(f"Wrote audit report to {args.output}")
        else:
            print(json.dumps(report, indent=2, ensure_ascii=False))
    except (FileNotFoundError, FileExistsError, IsADirectoryError, OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
