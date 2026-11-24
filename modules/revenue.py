"""
SolarPulse - Module D: Revenue Intelligence
Enterprise financial analytics, multi-tier electricity tariffs, revenue shortfalls,
invoiced vs collected projections, tariff sensitivity simulation, and financial reports.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from database.operations import load_generation_dataframe, get_all_plants
from core.revenue_engine import RevenueEngine
from components.charts import style_figure, CHART_THEME

def render_revenue_page(selected_plant: str, start_date, end_date):
    st.markdown(
        """
        <div class="sp-header-container">
            <div>
                <h1 class="sp-header-title">💰 Solar Revenue Intelligence & Financial Modeling</h1>
                <div class="sp-header-subtitle">Multi-tier tariff monetization, shortfall valuation, collection forecasting, and scenario sensitivity</div>
            </div>
            <div>
                <span class="sp-badge sp-badge-live">FINANCIAL ENGINE ACTIVE</span>
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

    # 1. Tariff Configuration Panel
    with st.expander("⚙️ Interactive Tariff & PPA Configuration"):
        st.markdown(
            """
            <div style="font-size:0.8rem; color:#94a3b8; margin-bottom:0.75rem;">
                Adjust PPA feed-in tariffs, captive industrial self-consumption rates, and expected collection efficiency.
            </div>
            """,
            unsafe_allow_html=True
        )
        tc1, tc2, tc3 = st.columns(3)
        with tc1:
            cfg_export_tariff = st.number_input("Grid Export PPA Tariff (₹/kWh)", min_value=1.5, max_value=8.0, value=3.20, step=0.05)
        with tc2:
            cfg_self_tariff = st.number_input("Self-Consumption Offset Value (₹/kWh)", min_value=2.0, max_value=12.0, value=4.50, step=0.10)
        with tc3:
            cfg_collection_rate = st.slider("Historical Collection Efficiency (%)", min_value=80.0, max_value=100.0, value=96.5, step=0.5)

    # Initialize Revenue Engine with configured tariffs
    engine = RevenueEngine(default_export_tariff=cfg_export_tariff, default_self_tariff=cfg_self_tariff)
    df = engine.calculate_revenue_for_dataframe(df)
    fin_summary = engine.summarize_financials(df, collection_rate=cfg_collection_rate / 100.0)

    # 2. Executive Financial KPI Cards
    k1, k2, k3, k4 = st.columns(4)
    total_rev = fin_summary["total_estimated_revenue_inr"]
    exp_rev = fin_summary["expected_revenue_inr"]
    shortfall_rev = fin_summary["total_revenue_shortfall_inr"]
    collected_proj = fin_summary["projected_collected_revenue_inr"]

    k1.metric("Total Estimated Revenue", f"₹{total_rev:,.0f}", delta=f"Realized at ₹{fin_summary['avg_revenue_per_kwh_inr']:.2f}/kWh")
    k2.metric("Contracted Benchmark Target", f"₹{exp_rev:,.0f}", delta="Expected 100% yield")
    k3.metric("Revenue Shortfall (Gap)", f"₹{shortfall_rev:,.0f}", delta=f"-{(shortfall_rev/exp_rev*100 if exp_rev > 0 else 0):.1f}%", delta_color="inverse")
    k4.metric("Projected Inflow (Collected)", f"₹{collected_proj:,.0f}", delta=f"{cfg_collection_rate:.1f}% collection factor")

    st.markdown("---")

    # 3. Revenue Breakdown: Export vs Self Consumption
    col_chart1, col_chart2 = st.columns([1.4, 1.0])
    with col_chart1:
        # Monthly revenue progression
        df["month_str"] = df["timestamp"].dt.strftime("%Y-%m")
        monthly_fin = df.groupby("month_str").agg({
            "estimated_export_revenue_inr": "sum",
            "estimated_self_revenue_inr": "sum",
            "expected_revenue_inr": "sum",
            "revenue_shortfall_inr": "sum"
        }).reset_index()

        fig_rev = go.Figure()
        fig_rev.add_trace(go.Bar(
            x=monthly_fin["month_str"],
            y=monthly_fin["estimated_export_revenue_inr"],
            name="Grid Export Revenue (₹)",
            marker_color=CHART_THEME["sky"],
            hovertemplate="Export: ₹%{y:,.0f}<extra></extra>"
        ))
        fig_rev.add_trace(go.Bar(
            x=monthly_fin["month_str"],
            y=monthly_fin["estimated_self_revenue_inr"],
            name="Self-Consumption Offset (₹)",
            marker_color=CHART_THEME["mint"],
            hovertemplate="Self-Use: ₹%{y:,.0f}<extra></extra>"
        ))
        fig_rev.add_trace(go.Scatter(
            x=monthly_fin["month_str"],
            y=monthly_fin["expected_revenue_inr"],
            name="Target Expected Revenue",
            line={"color": CHART_THEME["rose"], "dash": "dot", "width": 2},
            hovertemplate="Target: ₹%{y:,.0f}<extra></extra>"
        ))

        fig_rev.update_layout(barmode="stack")
        fig_rev = style_figure(fig_rev, "Monthly Revenue Realization vs Benchmark Targets", "Month", "Revenue (INR ₹)")
        st.plotly_chart(fig_rev, use_container_width=True)

    with col_chart2:
        # Donut of Revenue Streams
        fig_donut = px.pie(
            names=["Grid Export PPA", "Captive Self-Consumption", "Monetized Shortfall Loss"],
            values=[
                fin_summary["export_revenue_inr"],
                fin_summary["self_consumption_value_inr"],
                fin_summary["total_revenue_shortfall_inr"]
            ],
            hole=0.5,
            title="Portfolio Financial Realization & Loss Share",
            color_discrete_sequence=[CHART_THEME["sky"], CHART_THEME["mint"], CHART_THEME["rose"]]
        )
        fig_donut.update_layout(
            paper_bgcolor=CHART_THEME["paper_bgcolor"],
            font={"color": CHART_THEME["font_color"]}
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    # 4. Plant-Wise Financial Comparison
    if len(df["plant_id"].unique()) > 1:
        st.markdown("### 🏢 Asset-Level Financial Contribution")
        plant_rev = df.groupby(["plant_id", "plant_name"]).agg({
            "actual_generation_kwh": "sum",
            "total_estimated_revenue_inr": "sum",
            "revenue_shortfall_inr": "sum"
        }).reset_index()

        fig_pbar = px.bar(
            plant_rev,
            x="plant_name",
            y=["total_estimated_revenue_inr", "revenue_shortfall_inr"],
            barmode="group",
            title="Revenue Realized vs Shortfall by Solar Asset",
            color_discrete_sequence=[CHART_THEME["emerald"], CHART_THEME["rose"]],
            labels={"value": "Amount (₹)", "variable": "Financial Metric"}
        )
        fig_pbar.update_layout(
            paper_bgcolor=CHART_THEME["paper_bgcolor"],
            plot_bgcolor=CHART_THEME["plot_bgcolor"],
            font={"color": CHART_THEME["font_color"]}
        )
        st.plotly_chart(fig_pbar, use_container_width=True)

    # 5. Tariff Sensitivity Analysis
    st.markdown("### 📈 Tariff Sensitivity Matrix")
    st.markdown(
        """
        <div style="font-size:0.8rem; color:#94a3b8; margin-bottom:0.75rem;">
            Stress-tests portfolio bottom line against renegotiated PPA tariffs, merchant market fluctuations, and indexation rates.
        </div>
        """,
        unsafe_allow_html=True
    )
    sens_df = engine.simulate_tariff_sensitivity(df)
    st.dataframe(sens_df, use_container_width=True)
