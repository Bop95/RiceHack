"""Interactive spatial and urban-heat view built from validated derived data."""

from __future__ import annotations

import streamlit as st

from paddydash.components.charts import spatial_heat_map_figure
from paddydash.components.ui import interpretation, page_intro
from paddydash.services.data_service import load_spatial_heat_data


def render_spatial_heat_map() -> None:
    page_intro(
        "Spatial & Heat Map",
        "Explore reviewed NY/NJ business locations joined to nearby urban-heat "
        "evidence. Raw spend and customer values are not published.",
        "derived",
    )
    try:
        rows = load_spatial_heat_data()
    except (FileNotFoundError, KeyError, TypeError, ValueError):
        st.error("The approved spatial data could not be loaded.")
        st.info(
            "Run the documented spatial build and deployment validation, then "
            "restart the app. No unvalidated map records are displayed."
        )
        return

    high_count = sum(row["heat_concern"] == "High" for row in rows)
    missing_count = sum(row["nearby_uhi"] is None for row in rows)
    parking_count = sum(row["includes_parking"] is True for row in rows)
    metric_columns = st.columns(4)
    metric_columns[0].metric("Approved locations", f"{len(rows):,}")
    metric_columns[1].metric("High heat concern", f"{high_count:,}")
    metric_columns[2].metric("Insufficient UHI evidence", f"{missing_count:,}")
    metric_columns[3].metric("Tagged with parking", f"{parking_count:,}")

    with st.expander("Filters", expanded=True):
        first, second = st.columns(2)
        cities = first.multiselect(
            "City",
            sorted({row["city"] for row in rows}),
            placeholder="All cities",
        )
        categories = second.multiselect(
            "Business category",
            sorted({row["top_category"] for row in rows}),
            placeholder="All categories",
        )
        third, fourth, fifth = st.columns(3)
        heat_options = sorted({row["heat_concern"] for row in rows})
        heat = third.multiselect("Heat concern", heat_options, default=heat_options)
        recommendation_options = sorted({row["recommendation"] for row in rows})
        recommendations = fourth.multiselect(
            "Recommendation",
            recommendation_options,
            default=recommendation_options,
        )
        parking = fifth.selectbox(
            "Parking evidence",
            ("All", "Has parking", "No parking", "Unknown"),
        )

    filtered = [
        row
        for row in rows
        if (not cities or row["city"] in cities)
        and (not categories or row["top_category"] in categories)
        and row["heat_concern"] in heat
        and row["recommendation"] in recommendations
        and (
            parking == "All"
            or (parking == "Has parking" and row["includes_parking"] is True)
            or (parking == "No parking" and row["includes_parking"] is False)
            or (parking == "Unknown" and row["includes_parking"] is None)
        )
    ]
    st.caption(f"Displaying {len(filtered):,} of {len(rows):,} approved records.")
    if not filtered:
        st.warning("No approved locations match the selected filters.")
        return

    st.plotly_chart(
        spatial_heat_map_figure(filtered),
        use_container_width=True,
        config={"displaylogo": False},
    )
    st.markdown("### Filtered evidence table")
    st.dataframe(
        [
            {
                "Location": row["location_name"],
                "City": row["city"],
                "Category": row["top_category"],
                "Commercial tier": row["spending_level"],
                "Nearby UHI": row["nearby_uhi"],
                "Heat concern": row["heat_concern"],
                "Recommendation": row["recommendation"],
                "UHI match distance (m)": row["uhi_match_distance_m"],
            }
            for row in filtered
        ],
        use_container_width=True,
        hide_index=True,
    )
    interpretation(
        "The map separates high heat concern, lower heat concern, and missing UHI evidence.",
        "Operators can identify commercial corridors that need heat mitigation or further evidence.",
        "The rectangular scope is an implementation default, spend/customer values are aggregated "
        "into tiers, UHI uses a 250 m nearest-point rule, and the map is not a crowd or demand forecast.",
    )
