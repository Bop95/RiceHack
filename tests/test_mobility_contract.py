"""Schema/configuration checks only; these tests do not run a simulator."""

import json
import unittest

from pydantic import ValidationError

from paddydash.services.mobility_config import default_mobility_config
from paddydash.services.mobility_contract import (
    CorridorEdge, EdgeState, MobilityConfig, NodeState, PhaseId, ScenarioId,
    SimulationSnapshot,
)


class MobilityContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = default_mobility_config()
        self.payload = self.config.model_dump(mode='json')

    def snapshot_payload(self) -> dict:
        return {
            'config_id': self.config.config_id,
            'scenario_id': 'baseline', 'phase_id': 'pre_match', 'time_minutes': -180,
            'node_states': [
                {'node_id': node.node_id, 'incoming_passengers': 0, 'queue': 0,
                 'served_passengers': 0, 'departing_passengers': 0,
                 'utilization': None, 'estimated_wait_minutes': None}
                for node in self.config.nodes
            ],
            'edge_states': [
                {'edge_id': edge.edge_id, 'demand': 0,
                 'capacity': edge.base_capacity_per_step, 'throughput': 0, 'utilization': 0}
                for edge in self.config.edges
            ],
            'total_entered': 0, 'total_people_in_system': 0, 'total_served': 0,
            'data_type': 'synthetic', 'assumptions': ['Empty contract test fixture.'],
        }

    def test_unique_ordered_nodes_and_explicit_reverse_edges(self) -> None:
        self.assertEqual([n.node_id for n in self.config.nodes],
                         ['midtown', 'penn_station', 'secaucus', 'meadowlands', 'stadium'])
        self.assertEqual(len(self.config.edges), 8)
        pairs = {(e.from_node, e.to_node) for e in self.config.edges}
        for origin, destination in pairs:
            self.assertIn((destination, origin), pairs)
        for key, id_field in [('nodes', 'node_id'), ('edges', 'edge_id'),
                              ('phases', 'phase_id'), ('scenarios', 'scenario_id')]:
            with self.subTest(key=key):
                payload = self.config.model_dump(mode='json')
                payload[key][1][id_field] = payload[key][0][id_field]
                with self.assertRaises(ValidationError):
                    MobilityConfig.model_validate(payload)

    def test_edge_endpoints_must_exist(self) -> None:
        self.payload['edges'][0]['to_node'] = 'missing_station'
        with self.assertRaisesRegex(ValidationError, 'endpoint'):
            MobilityConfig.model_validate(self.payload)

    def test_edges_cannot_be_self_loops(self) -> None:
        edge = self.payload['edges'][0]
        edge['to_node'] = edge['from_node']
        with self.assertRaises(ValidationError):
            CorridorEdge.model_validate(edge)

    def test_positive_capacities_and_nonnegative_travel_times(self) -> None:
        for field, invalid in [('base_capacity_per_step', 0), ('base_capacity_per_step', -1),
                               ('base_capacity_per_step', True), ('travel_time_minutes', -1),
                               ('travel_time_minutes', float('inf'))]:
            with self.subTest(field=field, invalid=invalid):
                edge = dict(self.payload['edges'][0], **{field: invalid})
                with self.assertRaises(ValidationError):
                    CorridorEdge.model_validate(edge)
        edge = dict(self.payload['edges'][0], travel_time_minutes=0)
        self.assertEqual(CorridorEdge.model_validate(edge).travel_time_minutes, 0)

    def test_phase_clock_and_order(self) -> None:
        phases = {p.phase_id: p for p in self.config.phases}
        self.assertEqual(phases[PhaseId.KICKOFF].start_minute, 0)
        self.assertEqual(phases[PhaseId.REGULATION_END].start_minute, 105)
        self.assertEqual(phases[PhaseId.EXTRA_TIME_END].start_minute, 135)
        self.assertEqual(phases[PhaseId.HALFTIME].start_minute, 45)
        self.payload['phases'][1]['start_minute'] = -185
        with self.assertRaisesRegex(ValidationError, 'ordered'):
            MobilityConfig.model_validate(self.payload)

    def test_phase_display_order_and_canonical_order(self) -> None:
        self.payload['phases'][1]['order'] = 0
        with self.assertRaises(ValidationError):
            MobilityConfig.model_validate(self.payload)
        payload = self.config.model_dump(mode='json')
        payload['phases'][3]['phase_id'] = 'first_half'
        payload['phases'][4]['phase_id'] = 'kickoff'
        with self.assertRaisesRegex(ValidationError, 'canonical'):
            MobilityConfig.model_validate(payload)

    def test_regulation_only_configuration_is_supported(self) -> None:
        self.payload['phases'] = [p for p in self.payload['phases']
                                  if p['phase_id'] not in ('extra_time', 'extra_time_end')]
        for order, phase in enumerate(self.payload['phases']):
            phase['order'] = order
            if phase['phase_id'] in ('final_whistle', 'post_match'):
                phase['start_minute'] = 105
                phase['clock_reference'] = "90'"
        config = MobilityConfig.model_validate(self.payload)
        self.assertEqual(config.phases[-1].start_minute, 105)

    def test_all_canonical_scenarios_and_explicit_modifiers(self) -> None:
        scenarios = {s.scenario_id: s for s in self.config.scenarios}
        self.assertEqual(set(scenarios), set(ScenarioId))
        self.assertEqual(scenarios[ScenarioId.RAIL_DISRUPTION].affected_modes, ('rail',))
        self.assertEqual(scenarios[ScenarioId.RAIL_DISRUPTION].capacity_multiplier, 0.5)
        self.assertEqual(scenarios[ScenarioId.RAIL_CAPACITY_BOOST].capacity_multiplier, 1.5)
        self.assertEqual(scenarios[ScenarioId.STAGGERED_DEPARTURE].departure_duration_multiplier, 2)
        self.payload['scenarios'][0]['scenario_id'] = 'unrecognized'
        with self.assertRaises(ValidationError):
            MobilityConfig.model_validate(self.payload)

    def test_baseline_must_exist_and_preserve_base_values(self) -> None:
        self.payload['scenarios'] = self.payload['scenarios'][1:]
        with self.assertRaisesRegex(ValidationError, 'baseline'):
            MobilityConfig.model_validate(self.payload)
        payload = self.config.model_dump(mode='json')
        payload['scenarios'][0]['capacity_multiplier'] = 2
        with self.assertRaises(ValidationError):
            MobilityConfig.model_validate(payload)

    def test_demand_units_endpoints_and_step_alignment(self) -> None:
        self.assertEqual(self.config.demand.cohort_size, 6000)
        self.assertEqual(self.config.time_step_minutes, 5)
        for field, value in [('arrival_node', 'missing'), ('cohort_size', -1),
                             ('arrival_end_minute', -150), ('arrival_start_minute', -151)]:
            with self.subTest(field=field):
                payload = self.config.model_dump(mode='json')
                payload['demand'][field] = value
                with self.assertRaises(ValidationError):
                    MobilityConfig.model_validate(payload)

    def test_derived_inputs_require_source_reference(self) -> None:
        for group in ('edge', 'demand'):
            with self.subTest(group=group):
                payload = self.config.model_dump(mode='json')
                target = payload['edges'][0] if group == 'edge' else payload['demand']
                target['data_type'] = 'derived'
                with self.assertRaises(ValidationError):
                    MobilityConfig.model_validate(payload)
                target['source_reference'] = 'Reviewed input reference used only for this schema test'
                MobilityConfig.model_validate(payload)

    def test_configuration_json_roundtrip_and_schema(self) -> None:
        restored = MobilityConfig.model_validate_json(self.config.model_dump_json())
        self.assertEqual(restored, self.config)
        json.dumps(self.config.model_dump(mode='json'), allow_nan=False)
        self.assertIn('nodes', MobilityConfig.model_json_schema()['properties'])
        with self.assertRaises(ValidationError):
            self.config.time_step_minutes = 10

    def test_snapshot_json_roundtrip(self) -> None:
        snapshot = SimulationSnapshot.model_validate(self.snapshot_payload())
        snapshot.validate_against(self.config)
        restored = SimulationSnapshot.model_validate_json(snapshot.model_dump_json())
        self.assertEqual(restored, snapshot)
        self.assertEqual(json.loads(snapshot.model_dump_json())['data_type'], 'synthetic')

    def test_snapshot_accounts_for_holding_and_transit(self) -> None:
        payload = self.snapshot_payload()
        payload['node_states'][0]['queue'] = 2
        payload['node_states'][-1]['holding_passengers'] = 3
        payload['edge_states'][0]['in_transit_passengers'] = 5
        payload.update(total_people_in_system=10, total_entered=11, total_served=1)
        SimulationSnapshot.model_validate(payload)
        payload['total_people_in_system'] = 5
        with self.assertRaisesRegex(ValidationError, 'inventory'):
            SimulationSnapshot.model_validate(payload)
        payload.update(total_people_in_system=10, total_entered=10)
        with self.assertRaisesRegex(ValidationError, 'Entered cohort'):
            SimulationSnapshot.model_validate(payload)

    def test_snapshot_rejects_observed_or_derived_labels(self) -> None:
        for label in ('provided', 'derived', 'web'):
            with self.subTest(label=label):
                payload = self.snapshot_payload()
                payload['data_type'] = label
                with self.assertRaises(ValidationError):
                    SimulationSnapshot.model_validate(payload)

    def test_snapshot_references_and_timing(self) -> None:
        for field, value in [('config_id', 'other'), ('time_minutes', -181),
                             ('time_minutes', -30), ('phase_id', 'kickoff')]:
            with self.subTest(field=field, value=value):
                payload = self.snapshot_payload()
                payload[field] = value
                snapshot = SimulationSnapshot.model_validate(payload)
                with self.assertRaises(ValueError):
                    snapshot.validate_against(self.config)
        payload = self.snapshot_payload()
        payload['node_states'].pop()
        with self.assertRaisesRegex(ValueError, 'every configured node'):
            SimulationSnapshot.model_validate(payload).validate_against(self.config)

    def test_edge_state_capacity_and_utilization(self) -> None:
        state = dict(edge_id='test_edge', demand=10, capacity=5, throughput=5, utilization=1)
        EdgeState.model_validate(state)
        for change in ({'throughput': 6}, {'demand': 4}, {'utilization': 0.5},
                       {'utilization': float('nan')}, {'throughput': -1}):
            with self.subTest(change=change):
                with self.assertRaises(ValidationError):
                    EdgeState.model_validate(dict(state, **change))
        EdgeState(edge_id='closed', demand=10, capacity=0, throughput=0, utilization=0)

    def test_node_counts_and_unknown_fields(self) -> None:
        state = self.snapshot_payload()['node_states'][0]
        for change in ({'queue': -1}, {'departing_passengers': 1},
                       {'estimated_wait_minutes': float('inf')}, {'queue': 0.5},
                       {'unrecognized': 10}):
            with self.subTest(change=change):
                with self.assertRaises(ValidationError):
                    NodeState.model_validate(dict(state, **change))


if __name__ == '__main__':
    unittest.main()
