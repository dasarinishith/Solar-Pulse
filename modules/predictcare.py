"""
SolarPulse - Module F: Predictive Maintenance (PredictCare)
Equipment telemetry diagnostics, inverter performance, thermal clipping,
and statistical & Isolation Forest anomaly detection for proactive repairs.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from database.operations import load_generation_dataframe
from core.anomaly_detection import EquipmentAnomalyDetector
from components.charts import style_figure, CHART_THEME

def render_predictcare_page(selected_plant: str, start_date, end_date):
    st.markdown(
        """
        <div class="sp-header-container">
            <div>
                <h1 class="sp-header-title">🛡️ PredictCare: Equipment Anomaly Detection</h1>
                <div class="sp-header-subtitle">Inverter health monitoring, thermal derating diagnostics, and Isolation Forest ML failure prevention</div>
            </div>
            <div>
                <span class="sp-badge sp-badge-warning">PREDICTCARE ACTIVE</span>
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

    # Configuration
    col_c1, col_c2 = st.columns([1, 1])
    with col_c1:
        contamination = st.slider("ML Anomaly Sensitivity (Contamination Rate)", min_value=0.01, max_value=0.10, value=0.04, step=0.01,
                                  help="Expected proportion of outliers in the multivariate feature space.")
    with col_c2:
        severity_filter = st.multiselect("Severity Levels to Display", options=["CRITICAL", "WARNING", "INFO"], default=["CRITICAL", "WARNING"])

    detector = EquipmentAnomalyDetector(contamination_rate=contamination)
    anomalies_df = detector.detect_anomalies(df)

    if not anomalies_df.empty and severity_filter:
        anomalies_df = anomalies_df[anomalies_df["severity"].isin(severity_filter)]

    # Anomaly KPI Counters
    crit_count = len(anomalies_df[anomalies_df["severity"] == "CRITICAL"]) if not anomalies_df.empty else 0
    warn_count = len(anomalies_df[anomalies_df["severity"] == "WARNING"]) if not anomalies_df.empty else 0
    info_count = len(anomalies_df[anomalies_df["severity"] == "INFO"]) if not anomalies_df.empty else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Critical Inverter Alerts", f"{crit_count}", delta="Requires immediate dispatch" if crit_count > 0 else "All Clear", delta_color="inverse")
    k2.metric("Warning Anomalies", f"{warn_count}", delta="Performance degraded", delta_color="inverse")
    k3.metric("Multivariate Statistical Flags", f"{info_count}", delta="Subtle efficiency drift")
    k4.metric("Inverter Uptime Availability", "98.4%", delta="Nominal utility target >98.0%")

    st.markdown("---")

    # Inverter Telemetry Scatter (Efficiency vs Module Temp)
    col_v1, col_v2 = st.columns([1.3, 1.0])
    with col_v1:
        df["efficiency"] = (df["actual_generation_kwh"] / df["expected_generation_kwh"].replace(0, np.nan)) * 100
        fig_scatter = px.scatter(
            df,
            x="module_temperature_c",
            y="efficiency",
            color="inverter_status",
            hover_data=["plant_name", "timestamp", "irradiance_wm2"],
            title="Inverter Efficiency vs Module Temperature (°C)",
            color_discrete_map={"Normal": CHART_THEME["emerald"], "Warning": CHART_THEME["amber"], "Fault": CHART_THEME["rose"], "Curtailed": CHART_THEME["purple"]}
        )
        fig_scatter.update_layout(
            paper_bgcolor=CHART_THEME["paper_bgcolor"],
            plot_bgcolor=CHART_THEME["plot_bgcolor"],
            font={"color": CHART_THEME["font_color"]}
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    with col_v2:
        if not anomalies_df.empty:
            cat_counts = anomalies_df["category"].value_counts().reset_index()
            cat_counts.columns = ["Category", "Count"]
            fig_bar = px.bar(
                cat_counts,
                x="Count",
                y="Category",
                orientation="h",
                title="Anomaly Diagnostic Categories",
                color_discrete_sequence=[CHART_THEME["rose"]]
            )
            fig_bar.update_layout(
                paper_bgcolor=CHART_THEME["paper_bgcolor"],
                plot_bgcolor=CHART_THEME["plot_bgcolor"],
                font={"color": CHART_THEME["font_color"]}
            )
            st.plotly_chart(fig_bar, use_container_width=True)

    # Detailed Anomaly Log Table
    st.markdown("### 📋 Predictive Maintenance Alert Registry")
    st.markdown(
        """
        <div style="font-size:0.8rem; color:#94a3b8; margin-bottom:0.75rem;">
            <b>Operational Action:</b> Engineers should check physical inverter trip logs, string combiners, and DC string currents for critical flags.
        </div>
        """,
        unsafe_allow_html=True
    )

    if not anomalies_df.empty:
        st.dataframe(
            anomalies_df[[
                "timestamp", "plant_id", "plant_name", "severity", "category",
                "efficiency_percent", "expected_kwh", "actual_kwh", "shortfall_kwh",
                "explanation"
            ]].sort_values("shortfall_kwh", ascending=False).reset_index(drop=True),
            use_container_width=True
        )
    else:
        st.info("No equipment anomalies detected within selected parameters.")
