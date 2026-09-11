"""Deterministic flow, scenario and termination checks using no external data."""

import unittest

from paddydash.services.mobility_config import default_mobility_config
from paddydash.services.mobility_contract import MobilityConfig, ScenarioId
from paddydash.services.mobility_simulator import default_run, run_simulation


class MobilitySimulatorTests(unittest.TestCase):
    def test_all_scenarios_conserve_people_and_respect_capacity(self):
        config = default_mobility_config()
        for scenario in ScenarioId:
            with self.subTest(scenario=scenario):
                run = default_run(scenario.value)
                self.assertTrue(run.completed)
                self.assertEqual(run.snapshots[-1].total_served, config.demand.cohort_size)
                previous_entered = previous_exited = 0
                for snapshot in run.snapshots:
                    snapshot.validate_against(config)
                    self.assertGreaterEqual(snapshot.total_entered, previous_entered)
                    self.assertGreaterEqual(snapshot.total_served, previous_exited)
                    previous_entered, previous_exited = snapshot.total_entered, snapshot.total_served
                    self.assertEqual(snapshot.total_entered, snapshot.total_people_in_system + snapshot.total_served)
                    for edge in snapshot.edge_states:
                        self.assertLessEqual(edge.throughput, min(edge.capacity, edge.demand))

    def test_phase_behavior_and_travel_delay(self):
        run = default_run('baseline')
        by_time = {s.time_minutes: s for s in run.snapshots}
        self.assertEqual(by_time[-180].total_entered, 0)
        self.assertEqual(by_time[-150].edge_states[0].in_transit_passengers, 250)
        self.assertEqual(by_time[-145].node_states[1].incoming_passengers, 0)
        self.assertEqual(by_time[-135].node_states[1].incoming_passengers, 250)
        self.assertEqual(by_time[45].node_states[-1].holding_passengers, 6000)
        self.assertEqual(by_time[45].total_served, 0)
        self.assertEqual(by_time[135].node_states[-1].departing_passengers, 500)
        self.assertEqual(by_time[135].node_states[-1].holding_passengers, 5500)
        self.assertEqual(by_time[135].total_entered, 6000)
        self.assertEqual(run.snapshots[-1].total_people_in_system, 0)

    def test_deterministic_and_scenario_differences(self):
        config = default_mobility_config()
        baseline = run_simulation(config, 'baseline')
        self.assertEqual(baseline, run_simulation(config, 'baseline'))
        disrupted = default_run('rail_disruption')
        self.assertGreater(disrupted.peak_queue, baseline.peak_queue)
        self.assertGreater(disrupted.clearance_minutes, baseline.clearance_minutes)
        self.assertGreater(disrupted.delay_person_minutes, baseline.delay_person_minutes)
        self.assertGreater(default_run('rain').clearance_minutes, baseline.clearance_minutes)
        self.assertGreater(default_run('staggered_departure').clearance_minutes, baseline.clearance_minutes)

    def test_closed_edge_terminates_without_claiming_clearance(self):
        payload = default_mobility_config().model_dump(mode='json')
        payload['scenarios'][1]['capacity_multiplier'] = 0
        run = run_simulation(MobilityConfig.model_validate(payload), 'rail_disruption', 60)
        self.assertFalse(run.completed)
        self.assertIsNone(run.clearance_minutes)
        self.assertTrue(any(n.queue and n.estimated_wait_minutes is None for n in run.snapshots[-1].node_states))

    def test_rounding_does_not_duplicate_or_drop_people(self):
        payload = default_mobility_config().model_dump(mode='json')
        payload['demand']['cohort_size'] = 6011
        run = run_simulation(MobilityConfig.model_validate(payload), 'staggered_departure')
        self.assertEqual(run.snapshots[-1].total_entered, 6011)
        self.assertEqual(run.snapshots[-1].total_served, 6011)

    def test_invalid_scenario_is_rejected(self):
        with self.assertRaises(ValueError):
            run_simulation(default_mobility_config(), 'unknown')


if __name__ == '__main__':
    unittest.main()
