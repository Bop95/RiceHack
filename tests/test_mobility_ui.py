"""Match controls and deterministic UI updates exercised with Streamlit AppTest."""

import unittest

from streamlit.testing.v1 import AppTest

from paddydash.services.mobility_config import default_mobility_config
from paddydash.services.mobility_simulator import default_run


SOURCE = '''
from paddydash.components.match_controls import render_match_controls
from paddydash.pages.mobility import render_mobility
render_match_controls()
render_mobility()
'''


class MobilityUITests(unittest.TestCase):
    def test_every_canonical_phase_and_scenario_renders(self):
        app = AppTest.from_string(SOURCE, default_timeout=30).run()
        config = default_mobility_config()
        for phase in config.phases:
            app.selectbox(key='finalflow_phase_id').set_value(phase.phase_id.value).run()
            self.assertFalse(app.exception, phase.phase_id)
            self.assertEqual(app.session_state['finalflow_phase_id'], phase.phase_id.value)
        for scenario in config.scenarios:
            app.selectbox(key='finalflow_scenario_id').set_value(scenario.scenario_id.value).run()
            self.assertFalse(app.exception, scenario.scenario_id)
            snapshot = app.session_state['finalflow_mobility_snapshot']
            self.assertEqual(snapshot['scenario_id'], scenario.scenario_id.value)
            self.assertEqual(snapshot['data_type'], 'synthetic')

    def test_comparison_and_corridor_use_simulator_values(self):
        app = AppTest.from_string(SOURCE, default_timeout=30).run()
        app.selectbox(key='finalflow_phase_id').set_value('post_match').run()
        app.selectbox(key='finalflow_scenario_id').set_value('rail_disruption').run()
        self.assertFalse(app.exception)
        metrics = {item.label: item.value for item in app.metric}
        self.assertNotEqual(metrics['Largest node queue'], '0')
        self.assertEqual(metrics['Modeled status'], 'Queueing')
        self.assertEqual(metrics['Post-match clearance'], f"{default_run('rail_disruption').clearance_minutes} min")
        comparison = app.dataframe[1].value
        self.assertEqual(comparison.iloc[0]['Selected scenario'], default_run('rail_disruption').peak_queue)
        app.slider(key='finalflow_time_widget').set_value(default_run('rail_disruption').snapshots[-1].time_minutes).run()
        self.assertFalse(app.exception)
        self.assertEqual(next(m.value for m in app.metric if m.label == 'Modeled status'), 'Cleared')

    def test_invalid_saved_ids_are_reset_and_old_snapshot_cleared(self):
        app = AppTest.from_string(SOURCE, default_timeout=30)
        app.session_state['finalflow_phase_id'] = 'invalid'
        app.session_state['finalflow_scenario_id'] = 'invalid'
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['finalflow_phase_id'], 'pre_match')
        self.assertEqual(app.session_state['finalflow_scenario_id'], 'baseline')
        controls = AppTest.from_string('from paddydash.components.match_controls import render_match_controls\nrender_match_controls()').run()
        controls.session_state['finalflow_mobility_snapshot'] = {'scenario_id': 'baseline'}
        controls.selectbox(key='finalflow_scenario_id').set_value('rain').run()
        self.assertNotIn('finalflow_mobility_snapshot', controls.session_state)

    def test_capacity_boost_does_not_claim_uncomputed_improvement(self):
        app = AppTest.from_string(SOURCE, default_timeout=30).run()
        app.selectbox(key='finalflow_scenario_id').set_value('rail_capacity_boost').run()
        self.assertFalse(app.exception)
        self.assertTrue(any('unchanged at zero' in item.value for item in app.markdown))


if __name__ == '__main__':
    unittest.main()
