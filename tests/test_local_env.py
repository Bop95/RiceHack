"""Tests for local .env validation without credential disclosure."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.validation.check_local_env import validate_local_env


class LocalEnvironmentTests(unittest.TestCase):
    def test_valid_local_configuration_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            path = Path(temp_directory) / ".env"
            path.write_text(
                "OPENAI_API_KEY=test-local-credential-value-123456\n"
                "OPENAI_MODEL=test-model\n"
                "FINALFLOW_MAX_AI_REQUESTS_PER_SESSION=10\n",
                encoding="utf-8",
            )
            self.assertEqual(validate_local_env(path), [])

    def test_empty_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            path = Path(temp_directory) / ".env"
            path.write_text(
                "OPENAI_API_KEY=\n"
                "OPENAI_MODEL=test-model\n"
                "FINALFLOW_MAX_AI_REQUESTS_PER_SESSION=10\n",
                encoding="utf-8",
            )
            errors = validate_local_env(path)
            self.assertTrue(any("missing or empty" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
