"""
SolarPulse: AI-Powered Solar Energy Analytics & Revenue Intelligence Platform
Single-Page Unified Executive SaaS Application
Supports Three-Mode Data Source System:
1. Explore with Sample Data (SIMULATED)
2. Upload Your Dataset (UPLOADED)
3. Connect Your Inverter (API_LIVE)
"""

import os
import streamlit as st
import pandas as pd
from datetime import datetime, date
from database.operations import seed_initial_database_if_empty
from components.sidebar import render_sidebar

# 1. Page Configuration
st.set_page_config(
    page_title="SolarPulse | AI Solar Analytics & Revenue Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Inject Enterprise CSS Stylesheet
def load_css():
    css_path = os.path.join(os.path.dirname(__file__), "assets", "styles.css")
    if os.path.exists(css_path):
        with open(css_path, "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

# 3. Ensure Database is seeded with sample multi-plant data
seed_initial_database_if_empty()

# 4. Global Sidebar Scope & Mode Filters
selected_plant, start_date, end_date, active_mode = render_sidebar()

# 5. Primary Application Navigation Menu
with st.sidebar:
    st.markdown("---")
    st.markdown("### Platform Modules")
    main_module = st.radio(
        "Navigation",
        options=[
            "⚡ Executive Overview & Performance",
            "💰 Revenue Intelligence & Financials",
            "🛡️ Diagnostics, Soiling & Maintenance",
            "🔮 SolarCast Generation Forecasting",
            "📁 Data Upload, SCADA & Reports"
        ],
        index=0,
        label_visibility="collapsed"
    )

# 6. Route to Selected Core Module with Active Data Mode
if main_module == "⚡ Executive Overview & Performance":
    from modules.overview import render_overview_page
    from modules.performance import render_performance_page
    
    tab1, tab2 = st.tabs(["📊 Executive Portfolio Overview", "📈 Granular Generation & CUF / PR Analytics"])
    with tab1:
        render_overview_page(selected_plant, start_date, end_date, active_mode=active_mode)
    with tab2:
        render_performance_page(selected_plant, start_date, end_date, active_mode=active_mode)

elif main_module == "💰 Revenue Intelligence & Financials":
    from modules.revenue import render_revenue_page
    render_revenue_page(selected_plant, start_date, end_date, active_mode=active_mode)

elif main_module == "🛡️ Diagnostics, Soiling & Maintenance":
    from modules.loss_detection import render_loss_detection_page
    from modules.cleansense import render_cleansense_page
    from modules.predictcare import render_predictcare_page
    from modules.gridwatch import render_gridwatch_page

    diag_tab1, diag_tab2, diag_tab3, diag_tab4 = st.tabs([
        "⚠️ Loss Detection & RCA",
        "🧹 CleanSense (Soiling)",
        "🛡️ PredictCare (Inverter Health)",
        "🔌 GridWatch (Curtailment)"
    ])
    with diag_tab1:
        render_loss_detection_page(selected_plant, start_date, end_date, active_mode=active_mode)
    with diag_tab2:
        render_cleansense_page(selected_plant, start_date, end_date, active_mode=active_mode)
    with diag_tab3:
        render_predictcare_page(selected_plant, start_date, end_date, active_mode=active_mode)
    with diag_tab4:
        render_gridwatch_page(selected_plant, start_date, end_date, active_mode=active_mode)

elif main_module == "🔮 SolarCast Generation Forecasting":
    from modules.solarcast import render_solarcast_page
    render_solarcast_page(selected_plant, start_date, end_date, active_mode=active_mode)

elif main_module == "📁 Data Upload, SCADA & Reports":
    from modules.data_management import render_data_management_page
    from modules.api_connectors import render_api_connectors_page
    from modules.reports import render_reports_page

    data_tab1, data_tab2, data_tab3 = st.tabs([
        "📥 CSV / Excel Ingestion Center",
        "🔌 Inverter Gateway Connectors",
        "📑 Certified Reports & Exports"
    ])
    with data_tab1:
        render_data_management_page()
    with data_tab2:
        render_api_connectors_page()
    with data_tab3:
        render_reports_page(selected_plant, start_date, end_date, active_mode=active_mode)
