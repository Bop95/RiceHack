"""Smoke tests for the FinalFlow Streamlit pages."""

from __future__ import annotations

import unittest
import os
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


class StreamlitAppTests(unittest.TestCase):
    def test_entrypoint_renders_executive_without_exception(self) -> None:
        with patch.dict(
            os.environ, {"FINALFLOW_DISABLE_OPENAI": "true"}, clear=False
        ):
            app = AppTest.from_file("paddydash/app.py", default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertIn("FinalFlow", [item.value for item in app.title])
        self.assertIn("Executive Overview", [item.value for item in app.title])
        self.assertIn("Recommended actions now", [item.value for item in app.subheader])
        self.assertEqual(len(app.metric), 4)
        self.assertGreaterEqual(len(app.get("plotly_chart")), 1)

    def test_each_page_function_renders_without_exception(self) -> None:
        pages = (
            ("paddydash.pages.overview", "render_overview"),
            ("paddydash.pages.store_visit_explorer", "render_store_visit_explorer"),
            ("paddydash.pages.scenario_explorer", "render_scenario_explorer"),
            ("paddydash.pages.spatial_heat_map", "render_spatial_heat_map"),
            ("paddydash.pages.ask_finalflow", "render_ask_finalflow"),
        )
        with patch.dict(
            os.environ, {"FINALFLOW_DISABLE_OPENAI": "true"}, clear=False
        ):
            for module, function in pages:
                with self.subTest(page=function):
                    source = f"from {module} import {function}\n{function}()\n"
                    app = AppTest.from_string(source, default_timeout=30).run()
                    self.assertFalse(app.exception)
                    self.assertTrue(app.title)

    def test_custom_question_form_submits_a_grounded_answer(self) -> None:
        source = (
            "from paddydash.pages.ask_finalflow import render_ask_finalflow\n"
            "render_ask_finalflow()\n"
        )
        with patch.dict(
            os.environ,
            {"FINALFLOW_DISABLE_OPENAI": "true"},
            clear=False,
        ):
            app = AppTest.from_string(source, default_timeout=30).run()
            self.assertFalse(app.exception)
            app = app.chat_input[0].set_value("Which brand has the highest total visits?").run()

        self.assertFalse(app.exception)
        page_text = " ".join(item.value for item in app.markdown)
        caption_text = " ".join(item.value for item in app.caption)
        self.assertIn("Walmart", page_text)
        self.assertIn("verified prepared-data response", caption_text)
        clear_button = next(
            button for button in app.button if button.label == "Clear conversation"
        )
        self.assertFalse(clear_button.disabled)

    def test_empty_question_shows_feedback(self) -> None:
        source = (
            "from paddydash.pages.ask_finalflow import render_ask_finalflow\n"
            "render_ask_finalflow()\n"
        )
        with patch.dict(
            os.environ, {"FINALFLOW_DISABLE_OPENAI": "true"}, clear=False
        ):
            app = AppTest.from_string(source, default_timeout=30).run()
            app = app.chat_input[0].set_value("   ").run()
        self.assertFalse(app.exception)
        self.assertTrue(
            any("enter a question" in warning.value.lower() for warning in app.warning)
        )

    def test_refusal_has_no_answer_evidence_grid_or_answer_data_label(self) -> None:
        source = (
            "from paddydash.pages.ask_finalflow import render_ask_finalflow\n"
            "render_ask_finalflow()\n"
        )
        with patch.dict(
            os.environ, {"FINALFLOW_DISABLE_OPENAI": "true"}, clear=False
        ):
            app = AppTest.from_string(source, default_timeout=30).run()
            initial_data_type_captions = sum(
                "Data type:" in caption.value for caption in app.caption
            )
            app = app.chat_input[0].set_value("Who won the last Super Bowl?").run()

        self.assertFalse(app.exception)
        self.assertEqual(len(app.dataframe), 0)
        self.assertEqual(
            sum("Data type:" in caption.value for caption in app.caption),
            initial_data_type_captions,
        )


if __name__ == "__main__":
    unittest.main()
