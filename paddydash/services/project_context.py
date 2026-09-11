"""Deterministic replay context and contextual evidence, independent of Streamlit."""

from dataclasses import replace
from collections.abc import Mapping

from paddydash.services.analytics import EvidenceItem, RetrievalResult, retrieve_for_question
from paddydash.services.mobility_config import default_mobility_config
from paddydash.services.mobility_simulator import default_run


def selected_context(state: Mapping) -> dict:
    """Resolve a fresh snapshot; ignore stale time after a control change."""
    config = default_mobility_config()
    phases = {p.phase_id.value: p for p in config.phases}
    scenarios = {s.scenario_id.value: s for s in config.scenarios}
    phase_id = state.get('finalflow_phase_id', 'pre_match')
    scenario_id = state.get('finalflow_scenario_id', 'baseline')
    phase_id = phase_id if phase_id in phases else 'pre_match'
    scenario_id = scenario_id if scenario_id in scenarios else 'baseline'
    phase = phases[phase_id]
    run = default_run(scenario_id)
    start = phase.start_minute
    end = start
    if phase.kind == 'interval':
        following = [p.start_minute for p in config.phases
                     if p.kind == 'interval' and p.start_minute > start]
        end = min(following) - config.time_step_minutes if following else run.snapshots[-1].time_minutes
    minute = min(end, config.demand.arrival_start_minute + 15) if phase_id == 'pre_match' else start
    if phase_id == 'post_match':
        minute = min(end, start + 30)
    saved = state.get('finalflow_time_minutes')
    if (state.get('finalflow_time_selection') == (phase_id, scenario_id)
            and isinstance(saved, int) and start <= saved <= end
            and saved % config.time_step_minutes == 0):
        minute = saved
    snapshot = next(s for s in run.snapshots if s.time_minutes == minute)
    node = max(snapshot.node_states, key=lambda n: n.queue)
    names = {n.node_id: n.name for n in config.nodes}
    baseline = default_run('baseline')
    decisions = []
    if node.queue:
        decisions.append(f'Keep vendor queues clear of {names[node.node_id]} exits; '
                         f'the modeled residual queue is {node.queue:,} people. [synthetic; operational heuristic]')
    if scenario_id == 'rain':
        decisions.append('Consider covered waiting and extra staging. Rain uses 80% of baseline '
                         'effective capacity and 1.25x travel time, not a weather forecast. [synthetic]')
    boost = default_run('rail_capacity_boost')
    if boost.peak_queue < run.peak_queue:
        decisions.append(f'Compare rail capacity boost: peak queue {boost.peak_queue:,} versus '
                         f'{run.peak_queue:,} in this scenario. These are alternative runs, not combined interventions. [synthetic]')
    if not decisions:
        decisions.append('No residual queue at this moment. Retain clear exit paths; '
                         'zero modeled queue does not establish safety or optimal capacity. [synthetic; operational heuristic]')
    return dict(phase_id=phase_id, scenario_id=scenario_id,
                scope=f'{phase.display_label} / {scenarios[scenario_id].display_label} / kickoff {minute:+d} min',
                snapshot=snapshot, run=run, baseline=baseline,
                bottleneck=names[node.node_id] if node.queue else 'None', queue=node.queue,
                utilization=max(e.utilization for e in snapshot.edge_states),
                wait=node.estimated_wait_minutes, decisions=decisions)


def project_retrieval(question: str, data, context: dict) -> RetrievalResult:
    """Keep factual answers deterministic while attaching current replay evidence."""
    import re
    scope = context['scope']
    run = context['run']
    narrative = (f"{scope}. Modeled bottleneck: {context['bottleneck']}; largest queue: "
                 f"{context['queue']:,} people; utilization: {context['utilization']:.0%}; "
                 f"bottleneck wait: {context['wait']} minutes; whole-run clearance after whistle: "
                 f"{run.clearance_minutes} minutes. " + ' '.join(context['decisions']))
    narrative += (f" Baseline whole-run clearance: {context['baseline'].clearance_minutes} minutes; "
                  f"selected peak queue: {run.peak_queue:,}; baseline peak queue: {context['baseline'].peak_queue:,}. ")
    evidence = [EvidenceItem('Selected replay [synthetic]', scope, 'mobility_config.py / mobility_simulator.py'),
                EvidenceItem('Peak queue [synthetic]', run.peak_queue, 'mobility_simulator.py')]
    for row in data.weather:
        if row['metric_id'] in ('summer_rainy_observation_share', 'summer_hot_observation_share'):
            evidence.append(EvidenceItem(row['metric_label'] + ' [derived; historical]',
                                         f"{row['percentage']}%", 'weather_risk_summary.csv'))
    evidence.append(EvidenceItem('Prepared monthly visit periods [derived]', len(data.monthly), 'monthly_trends.csv'))
    from paddydash.services.data_service import load_spatial_heat_data
    try:
        locations = load_spatial_heat_data()
        hot = sum(row['heat_concern'] == 'High' for row in locations)
        evidence.append(EvidenceItem('High heat concern locations [derived]', hot, 'spatial_heat_locations.csv'))
        narrative += (f'Commercial context: {len(locations):,} reviewed exploratory NY/NJ locations, '
                      f'{hot:,} with high heat concern under the UHI > 7 heuristic. '
                      'Consider shade and water after site review; these are not verified stadium vendor sites. ')
    except (OSError, ValueError):
        narrative += 'Reviewed spatial context is unavailable. '
    for row in data.weather:
        if row['metric_id'] == 'summer_rainy_observation_share':
            narrative += f"Historical June-July rain observations: {row['percentage']}% (derived, multi-station; not a forecast). "
    limitation = 'Simulated passengers are synthetic. Historical multi-station weather and transformed visits are not match-day measurements.'
    if re.search(r'lowest.*queue|compare.*mobility', question, re.I):
        runs = {s.scenario_id.value: default_run(s.scenario_id.value) for s in default_mobility_config().scenarios}
        lowest = min(r.peak_queue for r in runs.values())
        narrative += ' Lowest whole-run peak queue: ' + ', '.join(k for k, r in runs.items() if r.peak_queue == lowest) + f' (tied at {lowest:,}).'
    elif not re.search(r'bottleneck|queue|utilization|clearance|recommendation|why.*chang|match phase|mobility|wait time', question, re.I):
        original = retrieve_for_question(question, data)
        if not original.evidence:
            return original
        return replace(original, context=original.context + '\n' + narrative,
                       local_answer=original.local_answer + '\n\nSelected replay [synthetic]: ' + narrative,
                       evidence=original.evidence + evidence,
                       limitations=original.limitations + [limitation])
    return RetrievalResult(narrative, evidence, None, 'synthetic', [limitation], narrative)
