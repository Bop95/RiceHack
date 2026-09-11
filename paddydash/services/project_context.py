"""Shared export-backed facts and contextual evidence, independent of page rendering."""

from dataclasses import replace
from collections.abc import Mapping
import re

from paddydash.services.analytics import EvidenceItem, RetrievalResult, retrieve_for_question
from paddydash.services.mobility_config import default_mobility_config
from paddydash.services.finalflow_data import change_text, current_mobility, evaluate_rules, load_table, phase_window


def selected_context(state: Mapping) -> dict:
    """Resolve fresh prepared facts; never reuse an old simulator snapshot."""
    config = default_mobility_config()
    phases = {p.phase_id.value: p for p in config.phases}
    scenarios = {s.scenario_id.value: s for s in config.scenarios}
    phase_id = state.get('finalflow_phase_id', state.get('selected_phase_id', 'pre_match'))
    scenario_id = state.get('finalflow_scenario_id', state.get('selected_scenario_id', 'baseline'))
    phase_id = phase_id if phase_id in phases else 'pre_match'
    scenario_id = scenario_id if scenario_id in scenarios else 'baseline'
    start, end, minute = phase_window(phase_id)
    saved = state.get('finalflow_time_minutes')
    identity = state.get('finalflow_time_selection')
    if identity == (phase_id, scenario_id) and isinstance(saved, int) and start <= saved <= end and saved % 5 == 0:
        minute = saved
    context = current_mobility(scenario_id, minute)
    scope = f'{phases[phase_id].display_label} / {scenarios[scenario_id].display_label} / kickoff {minute:+d} min'
    evidence = {
        'queue_passengers': dict(value=context['queue'], source_file='mobility_node_timeseries.csv', scope=scope),
        'estimated_wait_minutes': dict(value=context['wait'], source_file='mobility_node_timeseries.csv', scope=scope),
        'scenario_id': dict(value=scenario_id, source_file='scenario_summary.csv', scope=scope),
    }
    rules, _ = load_table('recommendation_catalog.csv')
    actions = evaluate_rules(rules, evidence)
    decisions = [f"{r['recommendation']} [{r['evidence_type']}; {r['metric']}={r['trigger_value']}; {r['source_file']}]" for r in actions]
    context.update(phase_id=phase_id, scope=scope, phase=phases[phase_id], scenario=scenarios[scenario_id],
                   actions=actions, decisions=decisions,
                   baseline=current_mobility('baseline', minute))
    return context


def project_retrieval(question: str, data, context: dict) -> RetrievalResult:
    """Explain prepared values; preserve separate historical and web evidence."""
    scope = context['scope']
    evidence = []
    if context['available']:
        summary = context['summary']
        clearance = summary['total_clearance_minutes'] if summary else None
        narrative = (f"{scope}. Modeled bottleneck: {context['bottleneck']}; largest queue: "
                     f"{context['queue']:,} people; total corridor queue: {context['pressure']:,}; "
                     f"utilization: {context['utilization']:.0%}; longest estimated wait: "
                     f"{context['wait']} minutes; whole-run clearance after whistle: "
                     f"{clearance if clearance is not None else 'unavailable'} minutes. " + ' '.join(context['decisions']))
        evidence.append(EvidenceItem('Selected replay [derived; synthetic inputs]', scope, 'mobility_node_timeseries.csv / mobility_edge_timeseries.csv'))
        if summary:
            evidence.append(EvidenceItem('Peak queue [derived]', summary['peak_queue_passengers'], 'scenario_summary.csv'))
            baseline = context['baseline']['summary']
            if baseline:
                narrative += ' Compared with baseline: ' + ' '.join(
                    change_text(label, baseline[field], summary[field]) for field, label in (
                        ('peak_queue_passengers', 'Whole-run peak queue'),
                        ('passenger_delay_proxy_person_minutes', 'Delay proxy (person-min)'),
                        ('total_clearance_minutes', 'Clearance (min)')))
    else:
        narrative = f'{scope}. Prepared mobility information is unavailable for this selection.'
    summaries, _ = load_table('scenario_summary.csv')
    if re.search(r'lowest.*queue|compare.*mobility', question, re.I) and summaries:
        lowest = min(r['peak_queue_passengers'] for r in summaries)
        winners = [r['scenario_id'] for r in summaries if r['peak_queue_passengers'] == lowest]
        tie = 'tied at' if len(winners) > 1 else 'at'
        narrative += f" Lowest whole-run peak queue: {', '.join(winners)} ({tie} {lowest:,}) among the {len(summaries)} available scenario summaries."
        evidence.append(EvidenceItem('Scenario ranking [derived]', ', '.join(winners), 'scenario_summary.csv'))
    weather, _ = load_table('weather_heat_context.csv')
    rain = next((r for r in weather if r['context_id'] == 'summer_rainy_observation_share'), None)
    if rain:
        narrative += f" Historical June-July rainy station-date observations: {rain['metric_value']}%; not a venue forecast."
        evidence.append(EvidenceItem('Historical rain [derived]', f"{rain['metric_value']}%", rain['source_file']))
    commercial, _ = load_table('commercial_context.csv')
    if commercial:
        row = commercial[0]
        narrative += f" Exploratory commercial context: {row['label']}: {row['metric_value']:,} {row['unit']}. Not verified vendor sites."
        evidence.append(EvidenceItem(row['label'] + ' [derived]', row['metric_value'], row['source_file']))
    limitation = 'Mobility results are derived from synthetic assumptions. Historical multi-station weather and transformed visits are not match-day measurements.'
    if not re.search(r'bottleneck|queue|utilization|clearance|recommendation|why.*chang|match phase|mobility|wait time', question, re.I):
        original = retrieve_for_question(question, data)
        if not original.evidence:
            return original
        return replace(original, context=original.context + '\n' + narrative,
                       local_answer=original.local_answer + '\n\nSelected replay [derived]: ' + narrative,
                       evidence=original.evidence + evidence,
                       limitations=original.limitations + [limitation])
    return RetrievalResult(narrative, evidence, None, 'derived', [limitation], narrative)
