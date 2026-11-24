"""
SolarPulse - Module C: Generation Loss Detection
Identifies when actual generation is significantly below expected generation,
categorizes root causes (Weather, Soiling, Inverter Fault, Curtailment), and provides alert management.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from database.operations import load_generation_dataframe
from components.charts import style_figure, CHART_THEME

def render_loss_detection_page(selected_plant: str, start_date, end_date):
    st.markdown(
        """
        <div class="sp-header-container">
            <div>
                <h1 class="sp-header-title">⚠️ Generation Loss Detection & Root Cause Analysis</h1>
                <div class="sp-header-subtitle">Underperformance identification, deviation thresholding, and diagnostic categorization</div>
            </div>
            <div>
                <span class="sp-badge sp-badge-warning">LOSS ENGINE ACTIVE</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    plant_filter = None if selected_plant == "ALL" else selected_plant
    df = load_generation_dataframe(plant_ids=plant_filter, start_date=start_date, end_date=end_date)

    if df.empty:
        st.warning("No records found for the selected filters.")
        return

    # User-Configurable Thresholds
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        deviation_threshold_pct = st.slider("Deviation Alert Threshold (%)", min_value=5, max_value=50, value=15, step=5,
                                            help="Flag days where actual generation is below (100 - threshold)% of expected.")
    with col_f2:
        min_loss_kwh = st.number_input("Minimum Shortfall Filter (kWh)", min_value=0, value=2000, step=1000)
    with col_f3:
        filter_cause = st.selectbox("Filter Diagnostic Category", options=["All Causes", "Weather / Low Irradiance", "Panel Soiling", "Inverter Malfunction", "Grid Curtailment"])

    # Calculate losses & classify probable root cause
    df["shortfall_kwh"] = np.maximum(0.0, df["expected_generation_kwh"] - df["actual_generation_kwh"])
    df["deviation_pct"] = np.where(
        df["expected_generation_kwh"] > 0,
        (df["shortfall_kwh"] / df["expected_generation_kwh"]) * 100.0,
        0.0
    )

    # Probable Cause Classifier based on operational parameters
    def classify_loss_cause(row):
        curtailed = row.get("curtailed_energy_kwh", 0)
        inv_status = str(row.get("inverter_status", "Normal"))
        irr = row.get("irradiance_wm2", 800)
        soiling_ratio = row.get("soiling_ratio", 1.0)
        temp = row.get("temperature_c", 25)

        if curtailed > 0 or inv_status == "Curtailed":
            return "Grid Curtailment"
        if inv_status == "Fault" or (row["deviation_pct"] > 45 and irr > 600):
            return "Inverter Malfunction"
        if soiling_ratio < 0.90 or (row["deviation_pct"] > 12 and irr > 750 and inv_status == "Normal"):
            return "Panel Soiling"
        if irr < 500:
            return "Weather / Low Irradiance"
        return "Equipment Downtime / String Fault"

    df["probable_cause"] = df.apply(classify_loss_cause, axis=1)

    # Filter underperforming records
    underperforming = df[
        (df["deviation_pct"] >= deviation_threshold_pct) &
        (df["shortfall_kwh"] >= min_loss_kwh)
    ].copy()

    if filter_cause != "All Causes":
        underperforming = underperforming[underperforming["probable_cause"] == filter_cause]

    # Metrics Summary
    total_shortfall_flagged = underperforming["shortfall_kwh"].sum()
    flagged_days = len(underperforming)
    est_financial_loss = total_shortfall_flagged * 3.20 # Base average tariff

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Flagged Loss Incidents", f"{flagged_days} days", delta=f"{flagged_days/max(1, len(df))*100:.1f}% of days", delta_color="inverse")
    c2.metric("Cumulative Energy Lost", f"{total_shortfall_flagged:,.0f} kWh")
    c3.metric("Est. Revenue Impact (₹)", f"₹{est_financial_loss:,.0f}", delta="Monetized shortfall", delta_color="inverse")
    c4.metric("Avg. Deviation on Event Days", f"{underperforming['deviation_pct'].mean():.1f}%" if not underperforming.empty else "0.0%")

    st.markdown("---")

    # Visual Breakdown of Loss Categories
    if not underperforming.empty:
        col_chart1, col_chart2 = st.columns([1.2, 1.0])
        with col_chart1:
            # Loss timeline bubble chart
            fig_bubble = px.scatter(
                underperforming,
                x="timestamp",
                y="deviation_pct",
                size="shortfall_kwh",
                color="probable_cause",
                hover_data=["plant_name", "actual_generation_kwh", "expected_generation_kwh"],
                title="Underperformance Severity Over Time (Bubble Size = Shortfall kWh)",
                color_discrete_map={
                    "Weather / Low Irradiance": CHART_THEME["sky"],
                    "Inverter Malfunction": CHART_THEME["rose"],
                    "Panel Soiling": CHART_THEME["amber"],
                    "Grid Curtailment": CHART_THEME["purple"],
                    "Equipment Downtime / String Fault": "#f97316"
                }
            )
            fig_bubble.update_layout(
                paper_bgcolor=CHART_THEME["paper_bgcolor"],
                plot_bgcolor=CHART_THEME["plot_bgcolor"],
                font={"color": CHART_THEME["font_color"]}
            )
            st.plotly_chart(fig_bubble, use_container_width=True)

        with col_chart2:
            # Donut chart of cause distribution
            cause_counts = underperforming.groupby("probable_cause")["shortfall_kwh"].sum().reset_index()
            fig_pie = px.pie(
                cause_counts,
                names="probable_cause",
                values="shortfall_kwh",
                hole=0.45,
                title="Shortfall Distribution by Probable Root Cause",
                color="probable_cause",
                color_discrete_map={
                    "Weather / Low Irradiance": CHART_THEME["sky"],
                    "Inverter Malfunction": CHART_THEME["rose"],
                    "Panel Soiling": CHART_THEME["amber"],
                    "Grid Curtailment": CHART_THEME["purple"],
                    "Equipment Downtime / String Fault": "#f97316"
                }
            )
            fig_pie.update_layout(
                paper_bgcolor=CHART_THEME["paper_bgcolor"],
                font={"color": CHART_THEME["font_color"]}
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    # Detailed Incident Log
    st.markdown("### 📋 Generation Loss Incident Registry")
    st.markdown(
        """
        <div style="font-size:0.8rem; color:#94a3b8; margin-bottom:0.75rem;">
            <b>Investigation Notice:</b> Diagnostic categories are derived from telemetry correlation (irradiance, inverter logs, curtailment signals). 
            Confirm with on-site inspection before logging technical warranty claims.
        </div>
        """,
        unsafe_allow_html=True
    )

    if not underperforming.empty:
        display_cols = [
            "timestamp", "plant_id", "plant_name", "expected_generation_kwh",
            "actual_generation_kwh", "shortfall_kwh", "deviation_pct",
            "probable_cause", "inverter_status"
        ]
        st.dataframe(
            underperforming[display_cols].sort_values("shortfall_kwh", ascending=False).reset_index(drop=True),
            use_container_width=True
        )
    else:
        st.info("No records exceeded the current underperformance thresholds. Assets are operating within nominal tolerance.")
