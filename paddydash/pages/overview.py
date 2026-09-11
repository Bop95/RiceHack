"""Executive readiness from prepared mobility and contextual evidence."""

import streamlit as st
from paddydash.components.ui import stretch_width

from paddydash.components.analytical_views import current_metrics, plot, prepared_table, pressure_figure, recommendations
from paddydash.services.project_context import selected_context


def render_overview() -> None:
    context = selected_context(st.session_state)
    st.title('Executive Overview')
    st.caption(context['scope'])
    current_metrics(context)
    recommendations(context)
    st.markdown('**Decision insight:** queue relief and departure clearance are different objectives. A staggered release can reduce pressure while extending the departure window.')
    st.subheader('Corridor pressure')
    rows = prepared_table('mobility_node_timeseries.csv')
    if rows:
        plot(pressure_figure(rows, context['scenario_id'], context['time_minutes']), 'executive_pressure')
    st.subheader('Context for this decision')
    left, right = st.columns(2)
    with left:
        weather = prepared_table('weather_heat_context.csv')
        rain = next((r for r in weather if r['context_id'] == 'summer_rainy_observation_share'), None)
        if rain:
            st.markdown(f"**Historical rain:** {rain['metric_value']:.2f}% of June-July station-date observations.")
            st.caption(f"Derived | {rain['source_file']} | {rain['limitation']}")
    with right:
        commercial = prepared_table('commercial_context.csv')
        row = next((r for r in commercial if r['context_id'] == 'spatial_high_high'), None)
        if row:
            st.markdown(f"**Commercial review:** {row['metric_value']:,} locations with high opportunity and high heat concern.")
            st.caption(f"Derived | {row['source_file']} | {row['limitation']}")
    with st.expander('Prepared baseline references and source coverage'):
        kpis = prepared_table('executive_kpis.csv')
        if kpis:
            st.dataframe(kpis, hide_index=True, **stretch_width(st.dataframe))
        st.caption('Baseline reference values do not change with the selected scenario. Historical evidence remains exploratory.')
