"""Edge-case tests for FinalFlow's server-side OpenAI configuration and fallback."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from paddydash.services.ai_service import (
    AIServiceError,
    DEFAULT_MAX_AI_REQUESTS_PER_SESSION,
    DEFAULT_MODEL,
    answer_with_fallback,
    answer_with_openai,
    api_is_configured,
    get_max_ai_requests_per_session,
    get_model_name,
)
from paddydash.services.analytics import EvidenceItem, RetrievalResult
from scripts.validation.check_local_env import validate_local_env


def sample_retrieval() -> RetrievalResult:
    """Return a compact approved-data result without loading dashboard files."""
    return RetrievalResult(
        context="Walmart: total=5347685565, mean=8043.57, stores=368",
        evidence=[
            EvidenceItem("Top brand", "Walmart", "visits_by_brand.csv"),
        ],
        related_plot_id="brand_ranking",
        data_type="derived",
        limitations=["Store visits are a commercial-activity proxy."],
        local_answer="Walmart ranks first by total transformed visits.",
    )


class APIKeyEdgeCaseTests(unittest.TestCase):
    def test_missing_blank_and_whitespace_keys_disable_openai(self) -> None:
        for configured in ({}, {"OPENAI_API_KEY": ""}, {"OPENAI_API_KEY": "   "}):
            with self.subTest(configured=configured):
                with patch.dict(os.environ, configured, clear=True):
                    self.assertFalse(api_is_configured())

    def test_all_documented_disable_flag_variants_take_precedence(self) -> None:
        for value in ("1", "true", "TRUE", " yes ", "On"):
            with self.subTest(value=value):
                with patch.dict(
                    os.environ,
                    {
                        "OPENAI_API_KEY": "test-key-that-must-not-be-used",
                        "FINALFLOW_DISABLE_OPENAI": value,
                    },
                    clear=True,
                ):
                    self.assertFalse(api_is_configured())

    def test_non_disable_values_leave_a_nonblank_key_enabled(self) -> None:
        for value in ("", "0", "false", "no", "off"):
            with self.subTest(value=value):
                with patch.dict(
                    os.environ,
                    {
                        "OPENAI_API_KEY": "test-key-that-enables-server-mode",
                        "FINALFLOW_DISABLE_OPENAI": value,
                    },
                    clear=True,
                ):
                    self.assertTrue(api_is_configured())

    def test_model_name_is_trimmed_and_blank_values_use_the_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_model_name(), DEFAULT_MODEL)
        with patch.dict(os.environ, {"OPENAI_MODEL": "   "}, clear=True):
            self.assertEqual(get_model_name(), DEFAULT_MODEL)
        with patch.dict(
            os.environ, {"OPENAI_MODEL": "  test-model  "}, clear=True
        ):
            self.assertEqual(get_model_name(), "test-model")

    def test_request_limit_handles_spacing_negative_and_large_values(self) -> None:
        cases = (
            (" 7 ", 7),
            ("-25", 1),
            ("0", 1),
            ("101", 100),
            ("999999999999", 100),
            ("3.5", DEFAULT_MAX_AI_REQUESTS_PER_SESSION),
            ("", DEFAULT_MAX_AI_REQUESTS_PER_SESSION),
        )
        for raw_value, expected in cases:
            with self.subTest(raw_value=raw_value):
                with patch.dict(
                    os.environ,
                    {"FINALFLOW_MAX_AI_REQUESTS_PER_SESSION": raw_value},
                    clear=True,
                ):
                    self.assertEqual(get_max_ai_requests_per_session(), expected)

    def test_no_key_returns_prepared_data_without_constructing_a_client(self) -> None:
        retrieval = sample_retrieval()
        with patch.dict(os.environ, {}, clear=True):
            with patch("openai.OpenAI") as mock_openai:
                response = answer_with_openai("Which brand leads?", retrieval)
        mock_openai.assert_not_called()
        self.assertEqual(response.mode, "prepared-data")
        self.assertEqual(response.answer, retrieval.local_answer)
        self.assertEqual(response.evidence, retrieval.evidence)

    def test_openai_request_uses_bounded_client_and_never_includes_the_key(self) -> None:
        retrieval = sample_retrieval()
        parsed = SimpleNamespace(answer="Walmart leads.", limitations=[])
        fake_response = SimpleNamespace(output_parsed=parsed)
        secret_value = "test-secret-value-that-must-not-enter-the-request"
        with patch.dict(
            os.environ,
            {"OPENAI_API_KEY": secret_value, "OPENAI_MODEL": " test-model "},
            clear=True,
        ):
            with patch("openai.OpenAI") as mock_openai:
                mock_openai.return_value.responses.parse.return_value = fake_response
                response = answer_with_openai(
                    "Which brand leads?", retrieval, safety_identifier="safe-id"
                )

        mock_openai.assert_called_once_with(timeout=20.0, max_retries=1)
        request = mock_openai.return_value.responses.parse.call_args.kwargs
        self.assertEqual(request["model"], "test-model")
        self.assertEqual(request["safety_identifier"], "safe-id")
        self.assertFalse(request["store"])
        self.assertEqual(request["max_output_tokens"], 500)
        self.assertIn("<approved_data>", request["input"][0]["content"])
        self.assertEqual(request["input"][1]["content"], "Which brand leads?")
        self.assertNotIn(secret_value, repr(request))
        system_prompt = request["input"][0]["content"]
        self.assertIn("mean visits per store-day", system_prompt)
        self.assertIn("Never describe it as visits per store", system_prompt)
        self.assertIn("share of synthetic scenario records", system_prompt)
        self.assertIn("Every scenario answer must explicitly use", system_prompt)
        self.assertIn("Verify comparison direction", system_prompt)
        self.assertIn("<validated_answer>", system_prompt)
        self.assertIn(retrieval.local_answer, system_prompt)
        self.assertIn("deterministic local", system_prompt)
        self.assertIn("analytics. You may make it clearer", system_prompt)
        self.assertEqual(response.mode, "openai")

    def test_safety_identifier_is_omitted_when_not_supplied(self) -> None:
        retrieval = sample_retrieval()
        parsed = SimpleNamespace(answer="Walmart leads.", limitations=[])
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            with patch("openai.OpenAI") as mock_openai:
                mock_openai.return_value.responses.parse.return_value = SimpleNamespace(
                    output_parsed=parsed
                )
                answer_with_openai("Which brand leads?", retrieval)
        request = mock_openai.return_value.responses.parse.call_args.kwargs
        self.assertNotIn("safety_identifier", request)

    def test_empty_structured_response_raises_a_safe_service_error(self) -> None:
        retrieval = sample_retrieval()
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            with patch("openai.OpenAI") as mock_openai:
                mock_openai.return_value.responses.parse.return_value = SimpleNamespace(
                    output_parsed=None
                )
                with self.assertRaisesRegex(AIServiceError, "no structured answer"):
                    answer_with_openai("Which brand leads?", retrieval)

    def test_sdk_error_is_sanitized_and_falls_back_to_verified_data(self) -> None:
        retrieval = sample_retrieval()
        sensitive_detail = "secret backend token and provider stack trace"
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            with patch("openai.OpenAI") as mock_openai:
                mock_openai.return_value.responses.parse.side_effect = RuntimeError(
                    sensitive_detail
                )
                response, warning = answer_with_fallback(
                    "Which brand leads?", retrieval
                )
        self.assertEqual(response.mode, "prepared-data")
        self.assertEqual(response.answer, retrieval.local_answer)
        self.assertNotIn("secret", (warning or "").lower())
        self.assertNotIn("stack trace", (warning or "").lower())

    def test_model_and_local_limitations_are_deduplicated(self) -> None:
        retrieval = sample_retrieval()
        parsed = SimpleNamespace(
            answer="Walmart leads.",
            limitations=[
                "Store visits are a commercial-activity proxy.",
                "Totals combine footprint and intensity.",
            ],
        )
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            with patch("openai.OpenAI") as mock_openai:
                mock_openai.return_value.responses.parse.return_value = SimpleNamespace(
                    output_parsed=parsed
                )
                response = answer_with_openai("Which brand leads?", retrieval)
        self.assertEqual(
            response.limitations,
            [
                "Store visits are a commercial-activity proxy.",
                "Totals combine footprint and intensity.",
            ],
        )


class LocalEnvironmentEdgeCaseTests(unittest.TestCase):
    def test_missing_environment_file_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            missing = Path(temp_directory) / ".env"
            self.assertEqual(
                validate_local_env(missing),
                [f"Local environment file is missing: {missing}"],
            )

    def test_invalid_local_values_are_all_reported_without_echoing_the_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            path = Path(temp_directory) / ".env"
            short_key = "short"
            path.write_text(
                f"OPENAI_API_KEY={short_key}\n"
                "OPENAI_MODEL=\n"
                "FINALFLOW_MAX_AI_REQUESTS_PER_SESSION=101\n",
                encoding="utf-8",
            )
            errors = validate_local_env(path)
        combined = " ".join(errors)
        self.assertTrue(any("appears incomplete" in error for error in errors))
        self.assertTrue(any("OPENAI_MODEL" in error for error in errors))
        self.assertTrue(any("between 1 and 100" in error for error in errors))
        self.assertNotIn(short_key, combined)

    def test_non_integer_request_limit_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_directory:
            path = Path(temp_directory) / ".env"
            path.write_text(
                "OPENAI_API_KEY=test-local-credential-value-123456\n"
                "OPENAI_MODEL=test-model\n"
                "FINALFLOW_MAX_AI_REQUESTS_PER_SESSION=ten\n",
                encoding="utf-8",
            )
            errors = validate_local_env(path)
        self.assertTrue(any("must be an integer" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
