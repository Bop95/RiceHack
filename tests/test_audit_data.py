"""Tests for the FinalFlow data audit utility."""

from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from scripts.data.audit_data import audit_file, main, write_report


class AuditDataTests(unittest.TestCase):
    """Cover dependency-light audit behavior without real Rice data."""

    def test_valid_csv_audit(self) -> None:
        """A valid CSV should produce the required report structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "sample.csv"
            csv_path.write_text("id,name,count\n1,Alpha,10\n2,Beta,20\n", encoding="utf-8")

            report = audit_file(csv_path, "sample-dataset", "utf-8", 5)

        self.assertEqual(report["dataset_name"], "sample-dataset")
        self.assertEqual(report["file_type"], "csv")
        self.assertEqual(report["row_count"], 2)
        self.assertEqual(report["column_count"], 3)
        self.assertEqual(report["columns"], ["id", "name", "count"])
        self.assertEqual(report["column_types"]["count"], "integer")
        self.assertEqual(len(report["sample_rows"]), 2)
        self.assertEqual(report["data_type"], "provided")

    def test_missing_values(self) -> None:
        """Missing values should be counted and converted to safe percentages."""
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "missing.csv"
            csv_path.write_text("id,value\n1,\n2,ok\n3, \n", encoding="utf-8")

            report = audit_file(csv_path, "missing-dataset", "utf-8", 5)

        self.assertEqual(report["missing_counts"]["value"], 2)
        self.assertEqual(report["missing_percentages"]["value"], 66.67)
        self.assertTrue(any("Missing values" in warning for warning in report["warnings"]))

    def test_duplicate_rows(self) -> None:
        """Duplicate rows should be counted deterministically."""
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "duplicates.csv"
            csv_path.write_text("id,value\n1,A\n1,A\n2,B\n", encoding="utf-8")

            report = audit_file(csv_path, "duplicate-dataset", "utf-8", 5)

        self.assertEqual(report["duplicate_row_count"], 1)
        self.assertTrue(any("duplicate row" in warning for warning in report["warnings"]))

    def test_empty_csv(self) -> None:
        """An empty CSV should return a report with empty-dataset warnings."""
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "empty.csv"
            csv_path.write_text("", encoding="utf-8")

            report = audit_file(csv_path, "empty-dataset", "utf-8", 5)

        self.assertEqual(report["row_count"], 0)
        self.assertEqual(report["column_count"], 0)
        self.assertEqual(report["missing_percentages"], {})
        self.assertTrue(any("empty" in warning.lower() for warning in report["warnings"]))
        self.assertTrue(any("No data rows" in warning for warning in report["warnings"]))

    def test_jsonl_audit(self) -> None:
        """JSON Lines files should preserve column order by first appearance."""
        with tempfile.TemporaryDirectory() as temp_dir:
            jsonl_path = Path(temp_dir) / "sample.jsonl"
            jsonl_path.write_text(
                '{"id": 1, "name": "Alpha"}\n'
                '{"id": 2, "score": 3.5}\n',
                encoding="utf-8",
            )

            report = audit_file(jsonl_path, "jsonl-dataset", "utf-8", 1)

        self.assertEqual(report["file_type"], "jsonl")
        self.assertEqual(report["row_count"], 2)
        self.assertEqual(report["columns"], ["id", "name", "score"])
        self.assertEqual(report["missing_counts"]["name"], 1)
        self.assertEqual(len(report["sample_rows"]), 1)

    def test_missing_input_file(self) -> None:
        """Missing input files should return a non-zero CLI exit code."""
        with tempfile.TemporaryDirectory() as temp_dir:
            missing_path = Path(temp_dir) / "missing.csv"
            stderr = StringIO()

            with redirect_stderr(stderr):
                exit_code = main(["--input", str(missing_path), "--name", "missing-dataset"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Input file does not exist", stderr.getvalue())

    def test_unsupported_extension(self) -> None:
        """Unsupported file extensions should fail clearly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            text_path = Path(temp_dir) / "notes.txt"
            text_path.write_text("hello\n", encoding="utf-8")
            stderr = StringIO()

            with redirect_stderr(stderr):
                exit_code = main(["--input", str(text_path), "--name", "notes"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Unsupported file extension", stderr.getvalue())

    def test_output_overwrite_protection(self) -> None:
        """Existing output files should not be overwritten unless requested."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "audit.json"
            output_path.write_text("existing\n", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                write_report({"ok": True}, output_path)

            write_report({"ok": True}, output_path, overwrite=True)

            self.assertEqual(json.loads(output_path.read_text(encoding="utf-8")), {"ok": True})

    def test_negative_sample_rows_argument(self) -> None:
        """Negative sample-row values should be rejected by argparse."""
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "sample.csv"
            csv_path.write_text("id\n1\n", encoding="utf-8")
            stderr = StringIO()

            with redirect_stderr(stderr), self.assertRaises(SystemExit) as context:
                main(["--input", str(csv_path), "--name", "sample", "--sample-rows", "-1"])

        self.assertNotEqual(context.exception.code, 0)
        self.assertIn("must be zero or greater", stderr.getvalue())

    def test_generated_report_is_json_serializable(self) -> None:
        """Generated reports should be JSON serializable."""
        with tempfile.TemporaryDirectory() as temp_dir:
            jsonl_path = Path(temp_dir) / "objects.jsonl"
            jsonl_path.write_text('{"id": 1, "nested": {"ok": true}}\n', encoding="utf-8")

            report = audit_file(jsonl_path, "serializable-dataset", "utf-8", 5)
            encoded = json.dumps(report)

        self.assertIn("serializable-dataset", encoded)

    def test_main_prints_json_to_stdout_when_output_is_omitted(self) -> None:
        """The CLI should print formatted JSON when no output path is provided."""
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "stdout.csv"
            csv_path.write_text("id\n1\n", encoding="utf-8")
            stdout = StringIO()

            with redirect_stdout(stdout):
                exit_code = main(["--input", str(csv_path), "--name", "stdout-dataset"])

            report = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertEqual(report["dataset_name"], "stdout-dataset")


if __name__ == "__main__":
    unittest.main()
