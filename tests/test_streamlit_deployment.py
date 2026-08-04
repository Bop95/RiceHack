"""Tests for the non-secret Streamlit deployment readiness checks."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from scripts.validation.check_streamlit_deployment import run_checks


class StreamlitDeploymentTests(unittest.TestCase):
    def test_current_bundle_has_no_blocking_deployment_errors(self) -> None:
        report = run_checks()
        self.assertEqual(report["errors"], [])
        self.assertGreater(report["bundle_size_mb"], 0)
        self.assertEqual(report["entrypoint"], "paddydash/app.py")
        self.assertEqual(report["prepared_row_counts"]["scenarios"], 12000)

    def test_openai_can_be_required_without_exposing_a_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            report = run_checks(require_openai=True)
        self.assertEqual(report["openai_configured"], False)
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any("OPENAI_API_KEY" in item for item in report["errors"]))


if __name__ == "__main__":
    unittest.main()
