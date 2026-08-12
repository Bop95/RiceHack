"""Tests for the non-secret Streamlit deployment readiness checks."""

from __future__ import annotations

import os
import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.validation.check_streamlit_deployment import (
    MAX_DEPLOYABLE_BUNDLE_BYTES,
    run_checks,
    validate_artifact_manifest,
)


class StreamlitDeploymentTests(unittest.TestCase):
    def test_current_bundle_has_no_blocking_deployment_errors(self) -> None:
        report = run_checks()
        self.assertEqual(report["errors"], [])
        self.assertGreater(report["bundle_size_mb"], 0)
        self.assertLess(
            report["bundle_size_mb"], MAX_DEPLOYABLE_BUNDLE_BYTES / 1_000_000
        )
        self.assertEqual(report["entrypoint"], "paddydash/app.py")
        self.assertEqual(report["prepared_row_counts"]["scenarios"], 12000)

    def test_openai_can_be_required_without_exposing_a_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            report = run_checks(require_openai=True)
        self.assertEqual(report["openai_configured"], False)
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any("OPENAI_API_KEY" in item for item in report["errors"]))

    def test_artifact_manifest_detects_hash_and_row_count_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            artifact = root / "artifact.csv"
            with artifact.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=["value"])
                writer.writeheader()
                writer.writerow({"value": "approved"})
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            manifest = root / "artifact.metadata.json"
            manifest.write_text(
                json.dumps(
                    {
                        "artifact": "artifact.csv",
                        "artifact_sha256": digest,
                        "accepted_rows": 1,
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                validate_artifact_manifest(
                    root, "artifact.csv", "artifact.metadata.json"
                ),
                [],
            )
            artifact.write_text("value\ntampered\nextra\n", encoding="utf-8")
            errors = validate_artifact_manifest(
                root, "artifact.csv", "artifact.metadata.json"
            )
            self.assertTrue(any("SHA-256" in item for item in errors))
            self.assertTrue(any("row count" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
