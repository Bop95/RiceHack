"""Release documentation and deployment-package regression checks."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from dotenv import dotenv_values

from scripts.validation.check_streamlit_deployment import run_checks


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
RELEASE_DOCS = (
    REPOSITORY_ROOT / "README.md",
    REPOSITORY_ROOT / "docs" / "api" / "application-api.md",
    REPOSITORY_ROOT / "docs" / "handoff" / "minh-tue-deployment-handoff.md",
    REPOSITORY_ROOT / "paddydash" / "DEPLOYMENT_GUIDE.md",
)
DEPLOYMENT_DOCS = (
    REPOSITORY_ROOT / "README.md",
    REPOSITORY_ROOT / "docs" / "handoff" / "minh-tue-deployment-handoff.md",
    REPOSITORY_ROOT / "paddydash" / "DEPLOYMENT_GUIDE.md",
)


class ReleaseHandoffTests(unittest.TestCase):
    def test_release_documents_exist_and_are_not_placeholders(self) -> None:
        for path in RELEASE_DOCS:
            with self.subTest(path=path):
                self.assertTrue(path.is_file())
                text = path.read_text(encoding="utf-8")
                self.assertGreater(len(text), 500)
                self.assertNotIn("stephen-develop", text)

    def test_runtime_dependencies_have_one_source_of_truth(self) -> None:
        self.assertTrue((REPOSITORY_ROOT / "requirements.txt").is_file())
        self.assertFalse((REPOSITORY_ROOT / "paddydash" / "requirements.txt").exists())

    def test_environment_example_matches_supported_application_variables(self) -> None:
        values = dotenv_values(REPOSITORY_ROOT / ".env.example")
        self.assertEqual(
            set(values),
            {
                "OPENAI_API_KEY",
                "OPENAI_MODEL",
                "FINALFLOW_MAX_AI_REQUESTS_PER_SESSION",
                "FINALFLOW_DISABLE_OPENAI",
            },
        )
        self.assertFalse(values["OPENAI_API_KEY"])
        self.assertEqual(values["FINALFLOW_DISABLE_OPENAI"], "false")

    def test_deployment_documents_use_main_as_the_release_branch(self) -> None:
        for path in DEPLOYMENT_DOCS:
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("HaiNam", text)
                self.assertIn("`main`", text)

    def test_deployment_report_names_main_and_has_no_bundle_errors(self) -> None:
        with patch.dict("os.environ", {"FINALFLOW_DISABLE_OPENAI": "true"}):
            report = run_checks(require_tracked=True)
        self.assertEqual(report["branch"], "main")
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["untracked_required_files"], [])


if __name__ == "__main__":
    unittest.main()
