"""
SolarPulse Sidebar & 3-Mode Data Source Selector Component
Provides seamless switching between:
1. SIMULATED (Sample Data Mode)
2. UPLOADED (Upload Data Mode)
3. API_LIVE (Connect Inverter Mode)
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date
from database.operations import get_all_plants, get_available_data_sources, reset_and_reload_sample_data

def render_sidebar():
    """
    Renders enterprise header, 3-mode data source selector, plant filter,
    date filter, and data status indicator.
    Returns: (selected_plant_id, start_date, end_date, active_mode)
    """
    with st.sidebar:
        st.markdown(
            """
            <div style="padding: 0.25rem 0 1rem 0;">
                <div style="display:flex; align-items:center; gap: 0.6rem;">
                    <span style="font-size: 1.6rem; color: #10b981;">⚡</span>
                    <span style="font-size: 1.4rem; font-weight: 800; letter-spacing: -0.03em;">SolarPulse</span>
                </div>
                <div style="font-size: 0.75rem; color: var(--sp-text-secondary); font-weight: 500; margin-top: 0.15rem;">
                    AI Solar Analytics & Revenue Intelligence
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # 1. Three-Mode Data Source Selector
        st.markdown("### 📡 Data Source Mode")
        source_counts = get_available_data_sources()

        mode_options = {
            "SIMULATED": f"🚀 Sample Data ({source_counts.get('SIMULATED', 0):,} rec)",
            "UPLOADED": f"📥 Uploaded Data ({source_counts.get('UPLOADED', 0):,} rec)",
            "API_LIVE": f"🔌 Inverter Gateway ({source_counts.get('API_LIVE', 0)} rec)"
        }

        # Initialize session state if not set
        if "data_source_mode" not in st.session_state:
            st.session_state["data_source_mode"] = "SIMULATED"

        selected_mode = st.radio(
            "Select Data Mode",
            options=["SIMULATED", "UPLOADED", "API_LIVE"],
            format_func=lambda x: mode_options[x],
            key="data_source_mode"
        )

        # Reset / Reload Sample Data Button if in SIMULATED mode
        if selected_mode == "SIMULATED":
            if st.button("🔄 Reload / Reset Sample Data", use_container_width=True, help="Refreshes multi-plant and 15-minute interval sample datasets in SQLite"):
                with st.spinner("Regenerating physics-based multi-plant dataset..."):
                    reloaded = reset_and_reload_sample_data()
                    st.success(f"Reloaded {reloaded:,} sample records!")
                    st.rerun()

        st.markdown("---")

        # 2. Plant / Asset Scope
        st.markdown("### Asset Scope")
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

        # 3. Reporting Horizon
        st.markdown("### Reporting Horizon")
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

        # 4. Visible Data Source Indicator Badge
        if selected_mode == "SIMULATED":
            badge_html = """
            <div style="background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 8px; padding: 0.85rem;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span class="sp-badge sp-badge-simulated">SIMULATED DATASET</span>
                    <span style="font-size:0.75rem;">☀️</span>
                </div>
                <div style="font-size: 0.72rem; color: var(--sp-text-secondary); margin-top: 0.4rem; line-height: 1.35;">
                    Realistic synthetic multi-plant data with 15-min inverter telemetry. <i>Clearly labeled as simulated.</i>
                </div>
            </div>
            """
        elif selected_mode == "UPLOADED":
            badge_html = """
            <div style="background: rgba(14, 165, 233, 0.08); border: 1px solid rgba(14, 165, 233, 0.3); border-radius: 8px; padding: 0.85rem;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span class="sp-badge sp-badge-uploaded">UPLOADED DATASET</span>
                    <span style="font-size:0.75rem;">📥</span>
                </div>
                <div style="font-size: 0.72rem; color: var(--sp-text-secondary); margin-top: 0.4rem; line-height: 1.35;">
                    User-imported CSV / Excel operational generation dataset.
                </div>
            </div>
            """
        else:
            badge_html = """
            <div style="background: rgba(100, 116, 139, 0.08); border: 1px solid rgba(100, 116, 139, 0.3); border-radius: 8px; padding: 0.85rem;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span class="sp-badge sp-badge-unconfigured">NOT CONFIGURED</span>
                    <span style="font-size:0.75rem;">🔌</span>
                </div>
                <div style="font-size: 0.72rem; color: var(--sp-text-secondary); margin-top: 0.4rem; line-height: 1.35;">
                    Live SCADA API gateway. Configure vendor keys in the <b>Connect Inverter</b> tab to activate.
                </div>
            </div>
            """
        st.markdown(badge_html, unsafe_allow_html=True)

        st.markdown(
            f"""
            <div style="font-size: 0.7rem; color: var(--sp-text-muted); margin-top: 1.25rem; text-align: center;">
                SolarPulse Enterprise v2.5 • {datetime.now().strftime('%H:%M:%S IST')}
            </div>
            """,
            unsafe_allow_html=True
        )

        return selected_plant_key, start_date, end_date, selected_mode
