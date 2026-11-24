"""
SolarPulse Sidebar & Global Filter Component
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date
from database.operations import get_all_plants

def render_sidebar():
    """
    Renders enterprise header in sidebar with plant selector, date filter,
    data source badge, and last updated timestamp.
    Returns: (selected_plant_id, start_date, end_date)
    """
    with st.sidebar:
        st.markdown(
            """
            <div style="padding: 0.5rem 0 1.25rem 0;">
                <div style="display:flex; align-items:center; gap: 0.6rem;">
                    <span style="font-size: 1.6rem; color: #10b981;">⚡</span>
                    <span style="font-size: 1.4rem; font-weight: 800; letter-spacing: -0.03em; color: #f8fafc;">SolarPulse</span>
                </div>
                <div style="font-size: 0.75rem; color: #94a3b8; font-weight: 500; margin-top: 0.2rem;">
                    Solar Analytics & Revenue Intelligence
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("### Operational Scope")
        
        # Load available plants
        all_plants = get_all_plants()
        plant_options = {"ALL": "🌐 All Plants Portfolio (195 MW)"}
        for p in all_plants:
            plant_options[p["plant_id"]] = f"{p['plant_id']} - {p['plant_name']} ({p['capacity_mw']} MW)"

        selected_plant_key = st.selectbox(
            "Select Solar Asset",
            options=list(plant_options.keys()),
            format_func=lambda x: plant_options[x],
            index=0
        )

        st.markdown("---")
        st.markdown("### Reporting Period")

        # Date range picker
        min_date = date(2025, 1, 1)
        max_date = date(2025, 12, 31)

        date_selection = st.date_input(
            "Analysis Horizon",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )

        if isinstance(date_selection, tuple) and len(date_selection) == 2:
            start_date, end_date = date_selection
        elif isinstance(date_selection, tuple) and len(date_selection) == 1:
            start_date, end_date = date_selection[0], max_date
        else:
            start_date, end_date = min_date, max_date

        st.markdown("---")
        
        # Data source indicator
        st.markdown(
            """
            <div style="background: rgba(24, 35, 33, 0.8); border: 1px solid #233631; border-radius: 8px; padding: 0.85rem; margin-top: 0.5rem;">
                <div style="font-size: 0.72rem; text-transform: uppercase; color: #94a3b8; font-weight: 600; letter-spacing: 0.05em; margin-bottom: 0.35rem;">
                    Data Source Status
                </div>
                <div style="display:flex; align-items:center; justify-content:space-between;">
                    <span class="sp-badge sp-badge-simulated">SIMULATED DATASET</span>
                    <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#10b981;"></span>
                </div>
                <div style="font-size: 0.7rem; color: #64748b; margin-top: 0.5rem; line-height: 1.3;">
                    Physics-modeled irradiance & weather data for portfolio demonstration.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            f"""
            <div style="font-size: 0.7rem; color: #64748b; margin-top: 1.5rem; text-align: center;">
                Engine v2.4 • Last Refresh: {datetime.now().strftime('%H:%M:%S IST')}
            </div>
            """,
            unsafe_allow_html=True
        )

        return selected_plant_key, start_date, end_date
