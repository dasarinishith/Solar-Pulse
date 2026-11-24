"""
SolarPulse - Module E: Solar Cleaning Analytics (CleanSense)
Soiling loss modeling, rain washing detection, plant cleaning priority ranking,
generation recovery estimation, and cleaning ROI payback calculator.
Supports active data source filtering (SIMULATED, UPLOADED, API_LIVE).
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from database.operations import load_generation_dataframe, get_all_plants
from core.clean_sense import CleanSense
from components.charts import style_figure, get_chart_theme

def render_cleansense_page(selected_plant: str, start_date, end_date, active_mode: str = "SIMULATED"):
    theme = get_chart_theme()
    st.markdown(
        """
        <div class="sp-header-container">
            <div>
                <h1 class="sp-header-title">🧹 CleanSense: Panel Soiling & Cleaning Optimization</h1>
                <div class="sp-header-subtitle">Soiling ratio tracking, rainfall natural wash detection, and ROI-driven cleaning schedule prioritization</div>
            </div>
            <div>
                <span class="sp-badge sp-badge-warning">CLEANSENSE ENGINE</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    plant_filter = None if selected_plant == "ALL" else selected_plant
    df = load_generation_dataframe(plant_ids=plant_filter, start_date=start_date, end_date=end_date, data_source=active_mode)
    plants_meta = get_all_plants()

    if df.empty:
        st.warning(f"No records found for active mode: **{active_mode}**.")
        return

    col_c1, col_c2 = st.columns([1, 1])
    with col_c1:
        cleaning_cost_per_mw = st.number_input("Cleaning Cost per MW (₹)", min_value=1000.0, max_value=25000.0, value=6500.0, step=500.0)
    with col_c2:
        soiling_alert_threshold = st.slider("Critical Soiling Alert Threshold (%)", min_value=3.0, max_value=15.0, value=7.5, step=0.5)

    cleansense = CleanSense(cleaning_cost_per_mw_inr=cleaning_cost_per_mw)
    rankings_df = cleansense.rank_all_plants_cleaning_priority(df, plants_meta)

    st.markdown("### 🏆 Portfolio Cleaning Priority Matrix")
    if not rankings_df.empty:
        st.dataframe(rankings_df, use_container_width=True)
        top_priority_plant = rankings_df.iloc[0]
        st.info(
            f"**Recommendation:** **{top_priority_plant['Plant Name']}** has highest cleaning priority. "
            f"Estimated monthly generation recovery is **{top_priority_plant['Daily Recovery (kWh)']*30:,.0f} kWh** "
            f"(₹{top_priority_plant['Monthly Financial Recovery (₹)']:,.0f} value) with cleaning payback in **{top_priority_plant['Payback (Days)']} days**."
        )

    st.markdown("---")
    st.markdown("### 🌧️ Soiling Ratio Progression & Natural Rainfall Washing")
    
    active_plant_id = selected_plant if selected_plant != "ALL" else rankings_df.iloc[0]["Plant ID"]
    plant_df = df[df["plant_id"] == active_plant_id].sort_values("timestamp")

    if not plant_df.empty:
        fig_soiling = go.Figure()
        fig_soiling.add_trace(go.Bar(
            x=plant_df["timestamp"],
            y=plant_df["rainfall_mm"],
            name="Rainfall (mm)",
            yaxis="y2",
            marker_color="rgba(14, 165, 233, 0.4)",
            hovertemplate="Rainfall: %{y:.1f} mm<extra></extra>"
        ))

        soiling_line = plant_df["soiling_ratio"] if "soiling_ratio" in plant_df.columns else (1.0 - plant_df["deviation_pct"]/100.0)
        fig_soiling.add_trace(go.Scatter(
            x=plant_df["timestamp"],
            y=soiling_line,
            name="Soiling Cleanliness Ratio",
            line={"color": theme["emerald"], "width": 2.2},
            hovertemplate="Cleanliness Ratio: %{y:.3f}<extra></extra>"
        ))

        fig_soiling.update_layout(
            title={
                "text": f"<b>{active_plant_id} Soiling Ratio vs Rainfall Cleaning Events</b>",
                "font": {"size": 13.5, "color": theme["title_color"]}
            },
            paper_bgcolor=theme["paper_bgcolor"],
            plot_bgcolor=theme["plot_bgcolor"],
            font={"color": theme["font_color"]},
            hovermode="x unified",
            yaxis={"title": "Soiling Ratio (1.0 = 100% Clean)", "range": [0.80, 1.02]},
            yaxis2={"title": "Rainfall (mm)", "overlaying": "y", "side": "right", "showgrid": False}
        )
        st.plotly_chart(fig_soiling, use_container_width=True)
