"""Historical station context, exploratory heat and exported rain effects."""

import pandas as pd
import plotly.express as px
import streamlit as st

from paddydash.components.analytical_views import plot, prepared_table, spatial_explorer
from paddydash.services.finalflow_data import change_text, current_mobility, evaluate_rules
from paddydash.services.project_context import selected_context


def render_weather_heat() -> None:
    context = selected_context(st.session_state)
    st.title('Weather & Heat')
    st.caption(context['scope'] + ' | Historical weather remains unchanged across mobility scenarios.')
    rows = prepared_table('weather_heat_context.csv')
    risk = [r for r in rows if r['unit'] == 'percent of station-date observations']
    if risk:
        st.subheader('Historical June-July context')
        cards = st.columns(3)
        for card, row in zip(cards, risk[:3]):
            card.metric(row['label'], f"{row['metric_value']:.2f}%", help=row['threshold'])
        st.caption('Derived | weather_risk_summary.csv | Historical multi-station observations, not venue-specific weather or a forecast.')
    reviewed_risk = prepared_table('weather_risk_summary.csv')
    if reviewed_risk:
        window = st.selectbox('Historical risk window', ['June-July', 'All months'], key='weather_window')
        frame = pd.DataFrame([r for r in reviewed_risk if r['month_window'] == window])
        frame['Indicator'] = frame.metric_label.str.replace(' June-July observations', '', regex=False).str.replace(' observations', '', regex=False)
        plot(px.bar(frame, x='percentage', y='Indicator', orientation='h',
                    labels={'percentage': 'Observations (%)'},
                    hover_data=['threshold', 'numerator', 'denominator', 'month_window']), 'weather_risks')
        st.caption(f'Derived | {window}, 2020-2024 | Denominator: station-date observations within this window. Risk bands are project heuristics.')
    monthly = prepared_table('weather_monthly.csv')
    if monthly:
        st.subheader('Monthly historical weather')
        measures = {'Mean temperature (C)': 'temp_avg_mean', 'Mean maximum temperature (C)': 'temp_max_avg',
                    'Mean minimum temperature (C)': 'temp_min_avg', 'Humidity (%)': 'humidity_avg',
                    'Wind (knots)': 'wind_speed_avg', 'Pooled precipitation total (mm)': 'total_precip_mm'}
        measure = st.selectbox('Weather measure', list(measures), key='weather_measure')
        plot(px.line(pd.DataFrame(monthly).sort_values('month'), x='month', y=measures[measure], markers=True,
                    labels={'month': 'Calendar month', measures[measure]: measure}), 'weather_monthly')
        st.caption('Derived | Tan Dat weather_monthly.csv | Pooled historical station observations; precipitation is a sum across source observations, not monthly rainfall at the stadium.')
    st.caption('Mean visibility distance: unavailable. Low-visibility observation share is available in the historical risk chart.')
    st.subheader('Rain and mobility')
    rain = current_mobility('rain', context['time_minutes'])
    base = context['baseline']
    if context['scenario_id'] != 'rain':
        st.caption('Rain-versus-baseline preview at the selected minute; the global scenario remains unchanged.')
    if rain['available'] and base['available']:
        st.write(change_text('Current total queue', base['pressure'], rain['pressure']))
        st.write(change_text('Longest wait (min)', base['wait'], rain['wait']))
        capacity = prepared_table('transit_service_capacity.csv')
        factors = [r for r in capacity if r['scenario_id'] == 'rain' and r['time_minutes'] == context['time_minutes']]
        if factors:
            st.caption('Synthetic rain inputs at this minute: ' + '; '.join(
                f"{mode}: effective weather factor {min(r['weather_factor'] for r in factors if r['mode'] == mode):.0%}"
                for mode in sorted({r['mode'] for r in factors})))
        comparison = []
        base_edges = {r['edge_id']: r for r in base['edges']}
        for row in rain['edges']:
            if row['edge_id'] in base_edges:
                comparison.append({'Edge': row['edge_id'], 'Baseline throughput': base_edges[row['edge_id']]['throughput'],
                                   'Rain throughput': row['throughput'], 'Baseline capacity': base_edges[row['edge_id']]['capacity'], 'Rain capacity': row['capacity']})
        st.dataframe(comparison, hide_index=True, width='stretch')
        st.caption('Derived | mobility_edge_timeseries.csv | People per 5-minute interval. Realized throughput can be demand-limited; lower capacity does not always reduce throughput.')
    access = prepared_table('mobility_access_summary.csv')
    rain_access = next((r for r in access if r['scenario_id'] == 'rain'), None)
    base_access = next((r for r in access if r['scenario_id'] == 'baseline'), None)
    if rain_access and base_access:
        st.write(f"Whole-run peak pedestrian load ratio: baseline {base_access['peak_pedestrian_load_ratio']:.3f}; rain {rain_access['peak_pedestrian_load_ratio']:.3f}.")
    if context['scenario_id'] == 'rain':
        st.info('Rain scenario: prioritize covered waiting and transfer staging. This is a synthetic-scenario review prompt, not a forecast.')
    st.subheader('Urban heat and location review')
    spatial_explorer('weather')
    rules = prepared_table('recommendation_catalog.csv')
    from paddydash.services.data_service import load_spatial_heat_data
    try:
        hot = sum(r['heat_concern'] == 'High' for r in load_spatial_heat_data())
    except (OSError, ValueError, TypeError, KeyError):
        hot = 0
    if hot:
        actions = evaluate_rules(rules, {'heat_concern': dict(value='High', source_file='spatial_heat_locations.csv',
                                  scope=f'{hot:,} exploratory NY/NJ locations; not verified corridor sites')})
        for action in actions:
            st.write(action['recommendation'])
            st.caption(f"Derived | heat_concern=High | {action['scope']} | {action['source_file']}")
