"""Shell state and compact export reader checks for the FinalFlow app."""

from __future__ import annotations

import unittest

from streamlit.testing.v1 import AppTest

from paddydash.services.finalflow_data import load_csv_safe, load_json_safe


class FinalFlowShellTests(unittest.TestCase):
    """Keep global controls canonical while preserving existing widget keys."""

    def test_match_controls_sync_requested_and_legacy_state_keys(self) -> None:
        source = "from paddydash.components.match_controls import render_match_controls\nrender_match_controls()\n"
        app = AppTest.from_string(source, default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["selected_phase_id"], "pre_match")
        self.assertEqual(app.session_state["selected_scenario_id"], "baseline")
        app.selectbox(key="finalflow_phase_id").set_value("final_whistle").run()
        app.selectbox(key="finalflow_scenario_id").set_value("rain").run()
        self.assertEqual(app.session_state["selected_phase_id"], "final_whistle")
        self.assertEqual(app.session_state["selected_scenario_id"], "rain")

    def test_safe_readers_report_missing_files_without_raising(self) -> None:
        rows, csv_error = load_csv_safe("exports", "not_available.csv")
        payload, json_error = load_json_safe("exports", "not_available.json")
        self.assertEqual(rows, [])
        self.assertIsNone(payload)
        self.assertIn("unavailable", csv_error or "")
        self.assertIn("unavailable", json_error or "")

    def test_new_timeline_and_weather_views_render(self) -> None:
        pages = (
            ("paddydash.pages.matchday_timeline", "render_matchday_timeline"),
            ("paddydash.pages.weather_heat", "render_weather_heat"),
        )
        for module, function in pages:
            with self.subTest(page=function):
                app = AppTest.from_string(
                    f"from {module} import {function}\n{function}()\n",
                    default_timeout=30,
                ).run()
                self.assertFalse(app.exception)
                self.assertTrue(app.title)


if __name__ == "__main__":
    unittest.main()
