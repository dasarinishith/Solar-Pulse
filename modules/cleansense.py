"""
SolarPulse - Module E: Solar Cleaning Analytics (CleanSense)
Soiling loss modeling, rain washing detection, plant cleaning priority ranking,
generation recovery estimation, and cleaning ROI payback calculator.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from database.operations import load_generation_dataframe, get_all_plants
from core.clean_sense import CleanSense
from components.charts import style_figure, CHART_THEME

def render_cleansense_page(selected_plant: str, start_date, end_date):
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
    df = load_generation_dataframe(plant_ids=plant_filter, start_date=start_date, end_date=end_date)
    plants_meta = get_all_plants()

    if df.empty:
        st.warning("No records found for the selected filters.")
        return

    # User input for cleaning parameters
    col_c1, col_c2 = st.columns([1, 1])
    with col_c1:
        cleaning_cost_per_mw = st.number_input("Cleaning Cost per MW (₹)", min_value=1000.0, max_value=25000.0, value=6500.0, step=500.0,
                                               help="Water-truck, manual labor, or automated robotic brush costs per MW.")
    with col_c2:
        soiling_alert_threshold = st.slider("Critical Soiling Alert Threshold (%)", min_value=3.0, max_value=15.0, value=7.5, step=0.5)

    cleansense = CleanSense(cleaning_cost_per_mw_inr=cleaning_cost_per_mw)

    # 1. Portfolio Rankings Table
    rankings_df = cleansense.rank_all_plants_cleaning_priority(df, plants_meta)

    st.markdown("### 🏆 Portfolio Cleaning Priority Matrix")
    st.markdown(
        """
        <div style="font-size:0.8rem; color:#94a3b8; margin-bottom:0.75rem;">
            Plants ranked by <b>Urgency Score</b> (combining cumulative soiling loss, payback turnaround time, and net monthly financial gain).
        </div>
        """,
        unsafe_allow_html=True
    )

    if not rankings_df.empty:
        st.dataframe(rankings_df, use_container_width=True)

        top_priority_plant = rankings_df.iloc[0]
        st.info(
            f"**Recommendation:** **{top_priority_plant['Plant Name']}** has highest cleaning priority. "
            f"Estimated monthly generation recovery is **{top_priority_plant['Daily Recovery (kWh)']*30:,.0f} kWh** "
            f"(₹{top_priority_plant['Monthly Financial Recovery (₹)']:,.0f} value) with cleaning payback in **{top_priority_plant['Payback (Days)']} days**."
        )

    st.markdown("---")

    # 2. Deep Dive: Soiling Ratio & Rainfall Timeline
    st.markdown("### 🌧️ Soiling Ratio Progression & Natural Rainfall Washing")
    
    # Focus on selected plant or first plant in portfolio
    active_plant_id = selected_plant if selected_plant != "ALL" else rankings_df.iloc[0]["Plant ID"]
    plant_df = df[df["plant_id"] == active_plant_id].sort_values("timestamp")

    if not plant_df.empty:
        fig_soiling = go.Figure()

        # Rainfall bars on secondary axis
        fig_soiling.add_trace(go.Bar(
            x=plant_df["timestamp"],
            y=plant_df["rainfall_mm"],
            name="Rainfall (mm)",
            yaxis="y2",
            marker_color="rgba(14, 165, 233, 0.4)",
            hovertemplate="Rainfall: %{y:.1f} mm<extra></extra>"
        ))

        # Soiling Ratio Line (1.0 = clean, 0.85 = 15% dirty)
        soiling_line = plant_df["soiling_ratio"] if "soiling_ratio" in plant_df.columns else (1.0 - plant_df["deviation_pct"]/100.0)
        fig_soiling.add_trace(go.Scatter(
            x=plant_df["timestamp"],
            y=soiling_line,
            name="Soiling Cleanliness Ratio",
            line={"color": CHART_THEME["emerald"], "width": 2.2},
            hovertemplate="Cleanliness Ratio: %{y:.3f}<extra></extra>"
        ))

        fig_soiling.update_layout(
            title={
                "text": f"<b>{active_plant_id} Soiling Ratio vs Rainfall Cleaning Events</b>",
                "font": {"size": 14, "color": "#f8fafc"}
            },
            paper_bgcolor=CHART_THEME["paper_bgcolor"],
            plot_bgcolor=CHART_THEME["plot_bgcolor"],
            font={"color": CHART_THEME["font_color"]},
            hovermode="x unified",
            yaxis={"title": "Soiling Ratio (1.0 = 100% Clean)", "range": [0.80, 1.02]},
            yaxis2={"title": "Rainfall (mm)", "overlaying": "y", "side": "right", "showgrid": False}
        )
        st.plotly_chart(fig_soiling, use_container_width=True)

    # 3. Payback & Financial Trade-Off Calculator
    st.markdown("### 💡 Cleaning ROI Sensitivity Simulator")
    s_col1, s_col2 = st.columns([1, 1])
    with s_col1:
        sim_days_since_clean = st.slider("Simulated Days Without Cleaning", min_value=10, max_value=90, value=35)
        sim_soiling_rate_per_day = st.slider("Daily Dust Accumulation Rate (% / day)", min_value=0.05, max_value=0.35, value=0.15, step=0.02)
    
    with s_col2:
        accumulated_loss_pct = min(22.0, sim_days_since_clean * sim_soiling_rate_per_day)
        st.markdown(
            f"""
            <div class="sp-section-box">
                <div class="sp-section-title">📊 Simulated Soiling Impact</div>
                <div style="font-size:1.4rem; font-weight:700; color:#f43f5e; margin:0.5rem 0;">
                    {accumulated_loss_pct:.2f}% Yield Loss
                </div>
                <div style="font-size:0.85rem; color:#94a3b8; line-height:1.5;">
                    Over <b>{sim_days_since_clean} days</b>, dust reduces power output by {accumulated_loss_pct:.1f}%.
                    For a 50 MW plant generating 220,000 kWh/day, this equals a daily loss of 
                    <b>~{220000 * accumulated_loss_pct / 100:,.0f} kWh (₹{220000 * (accumulated_loss_pct / 100) * 3.2:,.0f}/day)</b>.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
