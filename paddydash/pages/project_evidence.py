"""Commercial, POI and clearly separated synthetic placement evidence."""

from pathlib import Path

import pandas as pd
import streamlit as st

from paddydash.components.analytical_views import prepared_table, recommendations, spatial_explorer
from paddydash.pages.store_visit_explorer import render_store_visit_explorer
from paddydash.pages.scenario_explorer import render_commercial_scenarios
from paddydash.services.finalflow_data import evaluate_rules
from paddydash.services.project_context import selected_context


def render_project_evidence() -> None:
    context = selected_context(st.session_state)
    st.title('Commercial & POI Intelligence')
    st.caption(context['scope'] + ' | Historical commercial context does not change with the mobility scenario.')
    recommendations(context)
    rows = prepared_table('commercial_context.csv')
    with st.expander('Commercial context and source coverage'):
        if rows:
            st.dataframe(rows, hide_index=True, width='stretch')
    tab = st.radio('Commercial evidence', ['Store visits', 'POI & heat', 'Synthetic placement'], horizontal=True, key='commercial_view')
    if tab == 'Store visits':
        try:
            render_store_visit_explorer()
        except (OSError, ValueError, KeyError, TypeError):
            st.warning('Prepared store-visit summaries are unavailable. Other commercial evidence remains accessible.')
    elif tab == 'POI & heat':
        spatial_explorer('commercial')
    else:
        st.subheader('Scenario-based vendor placement')
        st.caption('Synthetic | Duc Anh | Coordinates, classifications and scores are scenario examples, not observed demand or verified sites.')
        path = Path(__file__).resolve().parents[2] / 'notebooks/duc-anh/data_clean/finalflow_business_integration.csv'
        try:
            frame = pd.read_csv(path)
            required = ['zone_name', 'placement_class', 'data_type', 'data_confidence', 'scenario_id', 'assumption_note']
            if not set(required).issubset(frame.columns) or not frame['data_type'].eq('synthetic').all() or not frame['data_confidence'].eq('scenario').all():
                raise ValueError('Unreviewed provenance')
            if frame[required].isna().any().any():
                raise ValueError('Incomplete synthetic evidence')
            st.dataframe(frame[required], hide_index=True, width='stretch')
            rules = prepared_table('recommendation_catalog.csv')
            for row in frame[frame.placement_class.eq('Avoided')].to_dict('records'):
                actions = evaluate_rules(rules, {'placement_class': {'value': row['placement_class'], 'source_file': path.name,
                     'scope': f"Synthetic zone {row['zone_name']} / scenario {row['scenario_id']}"}})
                for action in actions:
                    st.write(action['recommendation'])
                    st.caption(f"Synthetic | {action['scope']} | {action['source_file']} | placement_class={action['trigger_value']}")
        except (OSError, ValueError, KeyError):
            st.info('Reviewed synthetic business examples are unavailable.')
        try:
            render_commercial_scenarios()
        except (OSError, ValueError, KeyError, TypeError):
            st.info('Prepared commercial scenario exploration is unavailable.')
