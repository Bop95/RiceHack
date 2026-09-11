"""Responsive rendering across local and declared Streamlit runtimes."""

import os
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from paddydash.components.ui import stretch_width


class StreamlitSizingTests(unittest.TestCase):
    def test_legacy_integer_width(self):
        def element(width=None, use_container_width=False):
            pass
        self.assertEqual(stretch_width(element), {'use_container_width': True})

    def test_legacy_button_without_width(self):
        def element(use_container_width=False):
            pass
        self.assertEqual(stretch_width(element), {'use_container_width': True})

    def test_modern_string_width(self):
        def element(width='content'):
            pass
        self.assertEqual(stretch_width(element), {'width': 'stretch'})

    @patch.dict(os.environ, {'FINALFLOW_DISABLE_OPENAI': 'true',
                            'FINALFLOW_DISABLE_SEARCH': 'true'})
    def test_affected_views_render_beyond_first_table(self):
        pages = [('mobility', 'render_mobility'),
                 ('project_evidence', 'render_project_evidence'),
                 ('weather_heat', 'render_weather_heat'),
                 ('scenario_explorer', 'render_scenario_explorer')]
        for module, renderer in pages:
            with self.subTest(page=module):
                app = AppTest.from_string(
                    f'from paddydash.pages.{module} import {renderer}\n'
                    f'{renderer}()', default_timeout=45).run()
                self.assertFalse(app.exception)
                self.assertFalse(app.warning)
                self.assertGreater(len(app.dataframe), 0)
                self.assertGreater(len(app.get('plotly_chart')), 0)


if __name__ == '__main__':
    unittest.main()
