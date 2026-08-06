"""Repository-level checks for the FinalFlow CI/CD configuration."""

from __future__ import annotations

import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml"
GUIDE_PATH = REPOSITORY_ROOT / "docs" / "engineering" / "ci-cd-guide.md"
BEGINNER_GUIDE_PATH = (
    REPOSITORY_ROOT / "docs" / "engineering" / "ci-cd-beginner-guide.md"
)


class CIConfigurationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        cls.guide = GUIDE_PATH.read_text(encoding="utf-8")
        cls.beginner_guide = BEGINNER_GUIDE_PATH.read_text(encoding="utf-8")

    def test_workflow_has_expected_events_and_concurrency(self) -> None:
        self.assertIn("pull_request:", self.workflow)
        self.assertIn("workflow_dispatch:", self.workflow)
        self.assertIn("- main", self.workflow)
        self.assertNotIn("- HaiNam", self.workflow)
        self.assertIn("cancel-in-progress: true", self.workflow)

    def test_workflow_is_read_only_and_does_not_receive_secrets(self) -> None:
        self.assertIn("permissions:\n  contents: read", self.workflow)
        self.assertNotIn("contents: write", self.workflow)
        self.assertNotIn("secrets.", self.workflow)
        self.assertNotIn("OPENAI_API_KEY", self.workflow)
        self.assertIn('FINALFLOW_DISABLE_OPENAI: "true"', self.workflow)
        self.assertIn("persist-credentials: false", self.workflow)

    def test_workflow_uses_current_python_gate_and_required_commands(self) -> None:
        expected_fragments = (
            "actions/checkout@v7",
            "actions/setup-python@v7",
            'python-version: "3.12"',
            "python -m pip check",
            "python -m ruff check paddydash scripts tests",
            "python -m compileall -q paddydash scripts tests",
            "check_streamlit_deployment.py --require-tracked",
            "python -m unittest discover -s tests -v",
        )
        for fragment in expected_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.workflow)

    def test_guide_documents_the_manual_cd_and_secret_boundary(self) -> None:
        self.assertIn("Streamlit Community Cloud", self.guide)
        self.assertIn("Python 3.12 quality gate", self.guide)
        self.assertIn("Branch protection is what makes CI a gate", self.guide)
        self.assertIn("GitHub Actions and Streamlit secrets are separate", self.guide)
        self.assertIn("Do not run `run_live_openai_tests.py` in normal CI", self.guide)

    def test_beginner_guide_explains_the_actual_pipeline(self) -> None:
        expected_fragments = (
            "The four systems involved",
            "Understanding the actual workflow file",
            "Why branch protection matters",
            "How CD works in this project",
            "Where the OpenAI key belongs",
            "Reading a GitHub Actions failure",
            "Safe beginner exercises",
            "Frequently asked questions",
        )
        for fragment in expected_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.beginner_guide)


if __name__ == "__main__":
    unittest.main()
