"""One editable, illustrative corridor configuration; no simulation is run here."""

from paddydash.services.mobility_contract import (
    CorridorEdge, CorridorNode, DemandAssumptions, MatchPhase, MobilityConfig,
    Scenario,
)


def default_mobility_config() -> MobilityConfig:
    """Return a fresh validated configuration with explicit synthetic assumptions."""
    nodes = (
        CorridorNode(node_id='midtown', name='Midtown Manhattan', node_type='origin', order=0),
        CorridorNode(node_id='penn_station', name='Penn Station', node_type='station', order=1),
        CorridorNode(node_id='secaucus', name='Secaucus Junction', node_type='station', order=2),
        CorridorNode(node_id='meadowlands', name='Meadowlands Station', node_type='station', order=3),
        CorridorNode(node_id='stadium', name='Stadium', node_type='venue', order=4),
    )
    legs = (
        ('midtown', 'penn_station', 'walk', 600, 15),
        ('penn_station', 'secaucus', 'rail', 900, 15),
        ('secaucus', 'meadowlands', 'rail', 600, 15),
        ('meadowlands', 'stadium', 'walk', 600, 10),
    )
    edges = tuple(
        CorridorEdge(edge_id=f'{origin}_to_{destination}', from_node=origin,
                     to_node=destination, mode=mode, base_capacity_per_step=capacity,
                     travel_time_minutes=travel)
        for start, end, mode, capacity, travel in legs
        for origin, destination in ((start, end), (end, start))
    )
    phase_rows = (
        ('pre_match', 'Pre-match', -180, 'Before kickoff', 'interval', 'Begin inbound arrival window and empty-system initialization.'),
        ('gates_open', 'Gates open', -120, 'Before kickoff', 'event', 'Allow arrivals at the venue to enter stadium holding.'),
        ('ceremony', 'Closing ceremony', -30, 'Before kickoff', 'interval', 'Continue inbound movement; ceremony timing is an assumption.'),
        ('kickoff', 'Kickoff', 0, "0'", 'event', 'Mark kickoff without adding a simulation step.'),
        ('first_half', 'First half', 0, "0'-45'", 'interval', 'Hold venue arrivals; allow late passengers to finish inbound trips.'),
        ('first_half_end', "45'", 45, "45'", 'event', 'Mark the end of the first half.'),
        ('halftime', 'Halftime', 45, "45' clock paused", 'interval', 'Hold spectators; internal stadium circulation is not modeled.'),
        ('second_half', 'Second half', 60, "45'-90'", 'interval', 'Resume play after an assumed 15-minute halftime.'),
        ('regulation_end', "90'", 105, "90'", 'event', 'Mark regulation end; this default replay proceeds to extra time.'),
        ('extra_time', 'Extra time', 105, "90'-120'", 'interval', 'Continue stadium holding for an assumed 30 minutes.'),
        ('extra_time_end', "120'", 135, "120'", 'event', 'Mark the end of extra time.'),
        ('final_whistle', 'Final whistle', 135, "120'", 'event', 'Enable release of the existing held cohort, not new arrivals.'),
        ('post_match', 'Post-match', 135, 'After final whistle', 'interval', 'Release spectators and follow return edges until the system clears.'),
    )
    phases = tuple(
        MatchPhase(phase_id=phase_id, display_label=label, order=order,
                   start_minute=minute, clock_reference=clock, kind=kind,
                   simulation_meaning=meaning)
        for order, (phase_id, label, minute, clock, kind, meaning) in enumerate(phase_rows)
    )
    scenarios = (
        Scenario(scenario_id='baseline', display_label='Baseline',
                 assumptions=('Use the illustrative base capacities, travel times, and uniform release.',)),
        Scenario(scenario_id='rail_disruption', display_label='Rail disruption',
                 affected_modes=('rail',), capacity_multiplier=0.5,
                 assumptions=('Halve capacity on all rail edges in both directions for the whole run.',)),
        Scenario(scenario_id='rail_capacity_boost', display_label='Increased rail capacity',
                 affected_modes=('rail',), capacity_multiplier=1.5,
                 assumptions=('Increase capacity on all rail edges by 50%; no new route is implied.',)),
        Scenario(scenario_id='rain', display_label='Bad weather',
                 affected_modes=('walk', 'rail'), capacity_multiplier=0.8,
                 travel_time_multiplier=1.25,
                 assumptions=('Illustrative rain reduces walk/rail capacity by 20% and increases travel times by 25%.',)),
        Scenario(scenario_id='staggered_departure', display_label='Staggered departure',
                 departure_duration_multiplier=2.0,
                 assumptions=('Double the post-match release window without adding passengers; commercial dwell is assumed, not measured.',)),
    )
    return MobilityConfig(
        config_id='finalflow_corridor_v1', time_step_minutes=5,
        nodes=nodes, edges=edges, phases=phases, scenarios=scenarios,
        demand=DemandAssumptions(
            cohort_size=6000, arrival_node='midtown', venue_node='stadium',
            exit_node='midtown', arrival_start_minute=-150, arrival_end_minute=-30,
            departure_duration_minutes=60,
        ),
        assumptions=(
            'All capacities, travel times, demand, and phase timings are illustrative, not operator or event measurements.',
            'Track one 6000-person corridor cohort through inbound travel, stadium holding, and outbound travel.',
            'Start empty; inject the cohort once, uniformly over 120 minutes. Release holding after final whistle.',
            'The default replay assumes extra time, a 15-minute halftime, no stoppage time, no extra-time breaks, and no penalties.',
            'Reverse edges have independent symmetric capacities; shared train and platform resources are not modeled.',
            'Store visits and commercial scores are not converted to observed passenger counts.',
        ),
    )
