"""Prepared teammate evidence kept separate from modeled corridor results."""

from pathlib import Path
import pandas as pd
import streamlit as st

from paddydash.services.data_service import load_dashboard_data, load_spatial_heat_data
from paddydash.services.project_context import selected_context


def render_project_evidence() -> None:
    context = selected_context(st.session_state)
    st.title('Commercial & weather context')
    st.caption(context['scope'] + ' | Mobility: scenario / modeled')
    for decision in context['decisions']:
        st.write(decision)
    data = load_dashboard_data()
    commercial, weather, examples = st.tabs(['Commercial & POI', 'Weather & heat', 'Scenario examples'])
    try:
        locations = pd.DataFrame(load_spatial_heat_data())
    except (OSError, ValueError):
        locations = pd.DataFrame()
    with commercial:
        st.subheader('Store-visit trends')
        st.caption('Derived | Hai Nam | monthly_trends.csv | Transformed visits, not spectator counts.')
        monthly = pd.DataFrame(data.monthly).set_index('month')
        st.line_chart(monthly[['mean_daily_visits']])
        if locations.empty:
            st.info('Reviewed POI evidence is unavailable.')
        else:
            st.subheader('Spending tiers & parking indicators')
            st.caption('Derived | Que Anh | spatial_heat_locations.csv | Exploratory NY/NJ area, not a verified stadium corridor.')
            a, b = st.columns(2)
            a.metric('Reviewed locations', len(locations))
            b.metric('Parking flag present', int(locations['includes_parking'].eq(True).sum()))
            st.bar_chart(locations['spending_level'].value_counts().reindex(['Low', 'Medium', 'High']))
            st.caption('Spending tiers are relative ranks, not revenue forecasts. Parking flags do not measure spaces or availability.')
            st.dataframe(locations[['location_name', 'city', 'spending_level', 'includes_parking', 'heat_concern']].head(30),
                         hide_index=True, use_container_width=True)
            st.caption('First 30 source rows, not a ranked vendor shortlist. Full filtering remains on Spatial & Heat Map.')
    with weather:
        st.subheader('Historical weather risk')
        st.caption('Derived | Tan Dat | weather_risk_summary.csv | 2020-2024 multi-station context, not a forecast.')
        rows = pd.DataFrame(data.weather)
        st.dataframe(rows[['metric_label', 'percentage', 'threshold', 'month_window']], hide_index=True, use_container_width=True)
        st.caption('Percentages count station-date observations. Risk thresholds are project heuristics.')
        path = Path(__file__).resolve().parents[2] / 'notebooks/tan-dat/data/summaries/weather_monthly.csv'
        try:
            monthly_weather = pd.read_csv(path).set_index('month')
            cols = ['temp_avg_mean', 'humidity_avg', 'wind_speed_avg']
            values = monthly_weather[cols]
            if (len(values) != 12 or set(values.index) != set(range(1, 13))
                    or values.isna().any().any()
                    or not values['humidity_avg'].between(0, 100).all()
                    or not values['temp_avg_mean'].between(-90, 60).all()
                    or not values['wind_speed_avg'].between(0, 250).all()):
                raise ValueError('Invalid monthly weather')
            st.caption('Derived | Contributor monthly context: temperature (C), humidity (%), wind (knots). Pooled source table, separate from reviewed risk denominators.')
            st.dataframe(values.rename(columns={'temp_avg_mean': 'Temperature C', 'humidity_avg': 'Humidity %', 'wind_speed_avg': 'Wind knots'}), use_container_width=True)
        except (OSError, ValueError, KeyError):
            st.info('Monthly temperature, humidity and wind context is unavailable.')
        if not locations.empty:
            hot = int(locations['heat_concern'].eq('High').sum())
            st.metric('Locations with high heat concern', hot)
            st.write('Derived | Nearby UHI > 7 heuristic. Consider shade and water at reviewed high-heat locations; verify access and site conditions first.')
            st.caption(f"Missing UHI: {int(locations['nearby_uhi'].isna().sum()):,} locations. Nearest matches within 250 m are not on-site readings.")
    with examples:
        st.subheader('Synthetic vendor-placement examples')
        st.caption('Synthetic | Duc Anh | Not observed demand, verified coordinates, or optimal placements.')
        path = Path(__file__).resolve().parents[2] / 'notebooks/duc-anh/data_clean/finalflow_business_integration.csv'
        try:
            frame = pd.read_csv(path)
            required = ['zone_name', 'placement_class', 'data_type', 'data_confidence', 'scenario_id', 'assumption_note']
            if not set(required).issubset(frame.columns) or not frame['data_type'].eq('synthetic').all() or not frame['data_confidence'].eq('scenario').all():
                raise ValueError('Unreviewed provenance')
            st.dataframe(frame[required], hide_index=True, use_container_width=True)
        except (OSError, ValueError):
            st.info('Reviewed synthetic business examples are unavailable.')
