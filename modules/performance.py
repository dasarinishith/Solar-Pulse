"""
SolarPulse - Module B: Solar Performance Analytics (SolarPulse)
Detailed generation calculations, efficiency decomposition, PR, CUF, and temporal aggregations.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from database.operations import load_generation_dataframe
from core.calculations import (
    calculate_efficiency,
    calculate_shortfall,
    calculate_cuf,
    calculate_performance_ratio,
    summarize_generation_dataframe
)
from components.charts import style_figure, CHART_THEME

def render_performance_page(selected_plant: str, start_date, end_date):
    st.markdown(
        """
        <div class="sp-header-container">
            <div>
                <h1 class="sp-header-title">☀️ Solar Generation & Performance Analytics</h1>
                <div class="sp-header-subtitle">IEC 61724 compliant yield analysis, CUF benchmarks, and multi-temporal granularity</div>
            </div>
            <div>
                <span class="sp-badge sp-badge-live">ANALYTICS ENGINE</span>
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

    # Add core calculation columns
    df["generation_efficiency_pct"] = calculate_efficiency(df["actual_generation_kwh"], df["expected_generation_kwh"])
    df["shortfall_kwh"] = calculate_shortfall(df["actual_generation_kwh"], df["expected_generation_kwh"])
    df["specific_yield_kwh_kwp"] = df["actual_generation_kwh"] / (df["capacity_mw"] * 1000.0)

    # 1. Temporal Aggregation Controls
    col_t1, col_t2 = st.columns([1, 3])
    with col_t1:
        granularity = st.selectbox("Temporal Granularity", options=["Daily", "Weekly", "Monthly", "Annual"], index=0)

    # Prepare aggregated series
    df_agg = df.copy()
    if granularity == "Weekly":
        df_agg["period"] = df_agg["timestamp"].dt.to_period("W").dt.start_time
    elif granularity == "Monthly":
        df_agg["period"] = df_agg["timestamp"].dt.to_period("M").dt.start_time
    elif granularity == "Annual":
        df_agg["period"] = df_agg["timestamp"].dt.to_period("Y").dt.start_time
    else:
        df_agg["period"] = df_agg["timestamp"]

    period_data = df_agg.groupby("period").agg({
        "actual_generation_kwh": "sum",
        "expected_generation_kwh": "sum",
        "shortfall_kwh": "sum",
        "irradiance_wm2": "mean",
        "temperature_c": "mean"
    }).reset_index()

    period_data["efficiency"] = (period_data["actual_generation_kwh"] / period_data["expected_generation_kwh"].replace(0, np.nan)) * 100

    # 2. Key Metrics Bar
    total_gen = period_data["actual_generation_kwh"].sum()
    total_exp = period_data["expected_generation_kwh"].sum()
    total_shortfall = period_data["shortfall_kwh"].sum()
    avg_eff = (total_gen / total_exp * 100) if total_exp > 0 else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Yield (Actual)", f"{total_gen:,.0f} kWh")
    m2.metric("Benchmark Target (Expected)", f"{total_exp:,.0f} kWh")
    m3.metric("Portfolio Efficiency", f"{avg_eff:.2f}%")
    m4.metric("Generation Shortfall", f"{total_shortfall:,.0f} kWh", delta=f"-{(total_shortfall/total_exp*100 if total_exp > 0 else 0):.1f}%", delta_color="inverse")

    st.markdown("---")

    # 3. Interactive Main Chart
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=period_data["period"],
        y=period_data["actual_generation_kwh"],
        name="Actual Output (kWh)",
        marker_color=CHART_THEME["emerald"],
        hovertemplate="%{x|%Y-%m-%d}<br>Actual: %{y:,.0f} kWh<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=period_data["period"],
        y=period_data["expected_generation_kwh"],
        name="Target Expected (kWh)",
        line={"color": CHART_THEME["amber"], "width": 2.5, "dash": "dash"},
        hovertemplate="%{x|%Y-%m-%d}<br>Target: %{y:,.0f} kWh<extra></extra>"
    ))

    fig = style_figure(fig, f"{granularity} Solar Generation Performance vs Targets", "Time Period", "Energy Output (kWh)")
    st.plotly_chart(fig, use_container_width=True)

    # 4. Deep Dive: Performance Ratio vs Irradiance & Module Temperature
    c1, c2 = st.columns(2)
    with c1:
        fig_scatter = px.scatter(
            df,
            x="irradiance_wm2",
            y="actual_generation_kwh",
            color="plant_id",
            size="capacity_mw",
            hover_data=["plant_name", "temperature_c"],
            title="Yield vs Solar Irradiance Curve (GHI W/m²)",
            color_discrete_sequence=[CHART_THEME["emerald"], CHART_THEME["sky"], CHART_THEME["amber"], CHART_THEME["purple"]]
        )
        fig_scatter.update_layout(
            paper_bgcolor=CHART_THEME["paper_bgcolor"],
            plot_bgcolor=CHART_THEME["plot_bgcolor"],
            font={"color": CHART_THEME["font_color"]}
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    with c2:
        # Efficiency Distribution Histogram
        fig_hist = px.histogram(
            df,
            x="generation_efficiency_pct",
            nbins=35,
            title="Generation Efficiency Distribution (%)",
            color_discrete_sequence=[CHART_THEME["emerald"]]
        )
        fig_hist.update_layout(
            paper_bgcolor=CHART_THEME["paper_bgcolor"],
            plot_bgcolor=CHART_THEME["plot_bgcolor"],
            font={"color": CHART_THEME["font_color"]}
        )
        st.plotly_chart(fig_hist, use_container_width=True)

    # 5. Tabular Data View with Export
    with st.expander("🔍 View Detailed Generation Records Table"):
        st.dataframe(
            df[[
                "timestamp", "plant_id", "plant_name", "actual_generation_kwh",
                "expected_generation_kwh", "generation_efficiency_pct", "shortfall_kwh",
                "temperature_c", "irradiance_wm2", "inverter_status"
            ]].sort_values("timestamp", ascending=False),
            use_container_width=True
        )
