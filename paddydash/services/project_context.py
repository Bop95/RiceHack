"""Shared export-backed facts and contextual evidence, independent of page rendering."""

from dataclasses import replace
from collections.abc import Mapping
import re

from paddydash.services.analytics import EvidenceItem, RetrievalResult, retrieve_for_question
from paddydash.services.mobility_config import default_mobility_config
from paddydash.services.finalflow_data import change_text, current_mobility, evaluate_rules, load_table, load_json_safe, phase_window


def question_context(question: str, context: dict) -> dict:
    """Resolve explicit question scope without changing the global replay selection."""
    text = question.lower()
    phase_id, scenario_id = context['phase_id'], context['scenario_id']
    for phrase, value in [('final whistle', 'final_whistle'), ('post-match', 'post_match'),
                          ('kickoff', 'kickoff'), ('halftime', 'halftime'), ('pre-match', 'pre_match')]:
        if phrase in text:
            phase_id = value
            break
    for phrase, value in [('rail disruption', 'rail_disruption'), ('staggered departure', 'staggered_departure'),
                          ('capacity boost', 'rail_capacity_boost'), ('rain', 'rain')]:
        if phrase in text and not re.search(r'historical|weather chart|observations', text):
            scenario_id = value
            break
    else:
        if 'baseline' in text and not re.search(r'compar|versus|\bvs\b|this scenario', text):
            scenario_id = 'baseline'
    if (phase_id, scenario_id) == (context['phase_id'], context['scenario_id']):
        return context
    state = {'selected_phase_id': phase_id, 'selected_scenario_id': scenario_id}
    if phase_id == context['phase_id']:
        state.update(finalflow_time_minutes=context['time_minutes'],
                     finalflow_time_selection=(phase_id, scenario_id))
    return selected_context(state)


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
    context = question_context(question, context)
    scope = context['scope']
    evidence = []
    if context['available']:
        summary = context['summary']
        clearance = summary['total_clearance_minutes'] if summary else None
        narrative = (f"{scope}. Derived from synthetic inputs. Modeled bottleneck: {context['bottleneck']}; largest queue: "
                     f"{context['queue']:,} people; total corridor queue: {context['pressure']:,}; "
                     f"utilization: {context['utilization']:.0%}; longest estimated wait: "
                     f"{context['wait']} minutes; whole-run clearance after whistle: "
                     f"{clearance if clearance is not None else 'unavailable'} minutes.")
        if context['actions']:
            narrative += '\n\nActions for review: ' + ' '.join(r['recommendation'] for r in context['actions'][:3])
        if re.search(r'why.*(?:node|bottleneck)', question, re.I):
            narrative += '\n\nThe bottleneck is the largest residual node queue at this minute, with corridor-order tie breaking. No residual queue means no queue-based bottleneck. This is a model indicator, not a real-world causal diagnosis.'
        evidence.append(EvidenceItem('Selected replay [derived; synthetic inputs]', scope, 'mobility_node_timeseries.csv / mobility_edge_timeseries.csv'))
        for label, value, source in [('Largest queue (people)', context['queue'], 'mobility_node_timeseries.csv'),
                                     ('Maximum utilization (ratio)', context['utilization'], 'mobility_edge_timeseries.csv'),
                                     ('Longest wait (minutes)', context['wait'], 'mobility_node_timeseries.csv')]:
            evidence.append(EvidenceItem(label, value if value is not None else 'Unavailable', source))
        if re.search(r'secaucus', question, re.I):
            node = next((row for row in context['nodes'] if row['node_id'] == 'secaucus'), None)
            if node:
                narrative += (f" Secaucus residual queue: {node['queue_passengers']} people; "
                              f"incoming: {node['incoming_passengers']}; served: {node['served_passengers']}. "
                              "A residual queue represents demand not yet served at this replay step; "
                              "these exports do not establish a real-world causal diagnosis.")
        if summary:
            evidence.append(EvidenceItem('Peak queue [derived]', summary['peak_queue_passengers'], 'scenario_summary.csv'))
            baseline = context['baseline']['summary']
            if baseline:
                narrative += '\n\nCompared with baseline: ' + ' '.join(
                    change_text(label, baseline[field], summary[field]) for field, label in (
                        ('peak_queue_passengers', 'Whole-run peak queue'),
                        ('peak_post_final_whistle_queue_passengers', 'Post-whistle peak queue'),
                        ('passenger_delay_proxy_person_minutes', 'Delay proxy (person-min)'),
                        ('total_clearance_minutes', 'Clearance (min)')))
    else:
        narrative = f'{scope}. Prepared mobility information is unavailable for this selection.'
    summaries, _ = load_table('scenario_summary.csv')
    if re.search(r'lowest.*queue|compare.*mobility|intervention.*best', question, re.I) and summaries:
        lowest = min(r['peak_queue_passengers'] for r in summaries)
        winners = [r['scenario_id'] for r in summaries if r['peak_queue_passengers'] == lowest]
        tie = 'tied at' if len(winners) > 1 else 'at'
        narrative += f" Lowest whole-run peak queue: {', '.join(winners)} ({tie} {lowest:,}) among the {len(summaries)} available scenario summaries."
        evidence.append(EvidenceItem('Scenario ranking [derived]', ', '.join(winners), 'scenario_summary.csv'))
        if 'intervention' in question.lower():
            narrative += ' No intervention is best across all objectives; these are modeled scenario alternatives, not evaluated effects for every catalog action.'
            for field, label in [('total_clearance_minutes', 'Clearance after whistle (min)'),
                                 ('passenger_delay_proxy_person_minutes', 'Queue delay proxy (person-min)')]:
                best = min(row[field] for row in summaries)
                names = ', '.join(row['scenario_id'] for row in summaries if row[field] == best)
                narrative += f' Lowest {label}: {names}, at {best:,}.'
                evidence.append(EvidenceItem(label, best, 'scenario_summary.csv'))
    if re.search(r'changes? after (?:the )?final whistle', question, re.I):
        whistle = next(p.start_minute for p in default_mobility_config().phases if p.phase_id.value == 'final_whistle')
        before, after = (current_mobility(context['scenario_id'], whistle + offset) for offset in (-5, 5))
        if before['available'] and after['available']:
            narrative += f"\n\nImmediately around final whistle (kickoff {whistle - 5:+d} to {whistle + 5:+d} min): " + change_text('Total queue', before['pressure'], after['pressure'])
            narrative += f" Maximum realized utilization changes from {before['utilization']:.1%} to {after['utilization']:.1%}. This compares two steps, not the eventual departure peak."
            evidence.append(EvidenceItem('Whistle comparison window', f'{whistle - 5} to {whistle + 5} kickoff minutes', 'mobility_node_timeseries.csv / mobility_edge_timeseries.csv'))
    weather, _ = load_table('weather_heat_context.csv')
    rain = next((r for r in weather if r['context_id'] == 'summer_rainy_observation_share'), None)
    if rain and re.search(r'weather|rain|planners|why|recommendation', question, re.I):
        narrative += f" Historical June-July rainy station-date observations: {rain['metric_value']}%; not a venue forecast."
        evidence.append(EvidenceItem('Historical rain [derived]', f"{rain['metric_value']}%", rain['source_file']))
    commercial, _ = load_table('commercial_context.csv')
    if commercial and re.search(r'commercial|vendor|caution|heat|recommendation', question, re.I):
        row = commercial[0]
        narrative += f" Exploratory commercial context: {row['label']}: {row['metric_value']:,} {row['unit']}. Not verified vendor sites."
        evidence.append(EvidenceItem(row['label'] + ' [derived]', row['metric_value'], row['source_file']))
    if re.search(r'commercial|caution|vendor', question, re.I):
        for row in commercial:
            if row['context_id'] in ('business_scenario_avoided', 'business_scenario_controlled'):
                narrative += f" {row['label']}: {row['metric_value']} {row['unit']}. {row['limitation']}"
                evidence.append(EvidenceItem(row['label'], row['metric_value'], row['source_file']))
    if re.search(r'assumption|synthetic|provided|provenance', question, re.I):
        prepared, _ = load_json_safe('exports', 'finalflow_ai_context.json')
        nodes = prepared.get('corridor_nodes', []) if prepared else []
        notes = list(dict.fromkeys(row['assumption_note'] for row in nodes
                                  if isinstance(row, dict) and isinstance(row.get('assumption_note'), str)))[:2] if isinstance(nodes, list) else []
        narrative += ' Provided = source-backed context; derived = calculated; synthetic = scenario assumption; web = external information. ' + ' '.join(notes)
        if notes:
            evidence.append(EvidenceItem('Infrastructure reference provenance', 'synthetic; not official access coordinates', 'finalflow_ai_context.json', 'synthetic'))
        else:
            narrative += ' Prepared infrastructure assumption notes are unavailable.'
        capacities, _ = load_table('transit_service_capacity.csv')
        profiles = [row for row in capacities if row['scenario_id'] == context['scenario_id']
                    and row['time_minutes'] == context['time_minutes']]
        modifiers = sorted({(row['mode'], row['disruption_factor'], row['weather_factor']) for row in profiles})
        if modifiers:
            assumptions = '; '.join(f'{mode}: disruption factor {disruption}, weather factor {weather}'
                                    for mode, disruption, weather in modifiers)
            narrative += ' Synthetic effective-capacity assumptions: ' + assumptions + '.'
            evidence.append(EvidenceItem('Capacity factors at selected replay', assumptions,
                                         'transit_service_capacity.csv', 'synthetic'))
        kpis, _ = load_table('executive_kpis.csv')
        narrative += ' Executive baseline KPIs are reference values, not selected-scenario results.' if kpis else ' Executive KPI references are unavailable.'
    limitation = 'Mobility results are derived from synthetic assumptions. Historical multi-station weather and transformed visits are not match-day measurements.'
    if (re.search(r'ordinary.day|rainy post.match', question, re.I)
            or not re.search(r'bottleneck|queue|utilization|clearance|recommendation|why|match phase|mobility|wait time|rail disruption|staggered departure|capacity boost|this scenario|compar.*baseline|secaucus|planners|commercial|caution|synthetic|assumption|provenance|intervention|changes? after', question, re.I)):
        if data is None:
            return RetrievalResult('', [], None, 'derived', [limitation], 'Historical detail is unavailable.')
        original = retrieve_for_question(question, data)
        if not original.evidence:
            return original
        return replace(original, context=original.context + '\n' + narrative,
                       local_answer=original.local_answer + '\n\nSelected replay [derived]: ' + narrative,
                       evidence=original.evidence + evidence,
                       limitations=original.limitations + [limitation])
    return RetrievalResult(narrative, evidence, None, 'derived', [limitation], narrative,
                           [f"Scope: {scope}", f"Modeled bottleneck: {context['bottleneck']}"],
                           context['decisions'][:3])
