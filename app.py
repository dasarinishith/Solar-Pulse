"""
SolarPulse: AI-Powered Solar Energy Analytics & Revenue Intelligence Platform
Main Streamlit Application Entrypoint & Navigation Router
"""

import os
import streamlit as st
from database.operations import seed_initial_database_if_empty
from components.sidebar import render_sidebar

# 1. Page Configuration
st.set_page_config(
    page_title="SolarPulse | AI Solar Analytics & Revenue Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Inject Custom Enterprise Stylesheet
def load_css():
    css_path = os.path.join(os.path.dirname(__file__), "assets", "styles.css")
    if os.path.exists(css_path):
        with open(css_path, "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

# 3. Ensure Database is seeded with sample multi-plant data
seed_initial_database_if_empty()

# 4. Global Sidebar Filters
selected_plant, start_date, end_date = render_sidebar()

# 5. Clean Modular Navigation Router
with st.sidebar:
    st.markdown("### Navigation Modules")
    page_selection = st.radio(
        "Modules",
        options=[
            "1. Executive Overview",
            "2. Generation & Performance",
            "3. Loss Detection & RCA",
            "4. Revenue Intelligence",
            "5. CleanSense (Soiling)",
            "6. PredictCare (Anomalies)",
            "7. SolarCast (Forecasting)",
            "8. GridWatch (Curtailment)",
            "9. Data Ingestion & Upload",
            "10. Inverter API Connectors",
            "11. Analytical Reports & Exports"
        ],
        index=0,
        label_visibility="collapsed"
    )

# 6. Route to respective page module
if page_selection == "1. Executive Overview":
    import importlib
    mod = importlib.import_module("pages.1_Overview")
    mod.render_overview_page(selected_plant, start_date, end_date)

elif page_selection == "2. Generation & Performance":
    import importlib
    mod = importlib.import_module("pages.2_Performance")
    mod.render_performance_page(selected_plant, start_date, end_date)

elif page_selection == "3. Loss Detection & RCA":
    import importlib
    mod = importlib.import_module("pages.3_Loss_Detection")
    mod.render_loss_detection_page(selected_plant, start_date, end_date)

elif page_selection == "4. Revenue Intelligence":
    import importlib
    mod = importlib.import_module("pages.4_Revenue_Intelligence")
    mod.render_revenue_page(selected_plant, start_date, end_date)

elif page_selection == "5. CleanSense (Soiling)":
    import importlib
    mod = importlib.import_module("pages.5_CleanSense")
    mod.render_cleansense_page(selected_plant, start_date, end_date)

elif page_selection == "6. PredictCare (Anomalies)":
    import importlib
    mod = importlib.import_module("pages.6_PredictCare")
    mod.render_predictcare_page(selected_plant, start_date, end_date)

elif page_selection == "7. SolarCast (Forecasting)":
    import importlib
    mod = importlib.import_module("pages.7_SolarCast")
    mod.render_solarcast_page(selected_plant, start_date, end_date)

elif page_selection == "8. GridWatch (Curtailment)":
    import importlib
    mod = importlib.import_module("pages.8_GridWatch")
    mod.render_gridwatch_page(selected_plant, start_date, end_date)

elif page_selection == "9. Data Ingestion & Upload":
    import importlib
    mod = importlib.import_module("pages.9_Data_Management")
    mod.render_data_management_page()

elif page_selection == "10. Inverter API Connectors":
    import importlib
    mod = importlib.import_module("pages.10_API_Connectors")
    mod.render_api_connectors_page()

elif page_selection == "11. Analytical Reports & Exports":
    import importlib
    mod = importlib.import_module("pages.11_Reports")
    mod.render_reports_page(selected_plant, start_date, end_date)
