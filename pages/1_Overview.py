"""
SolarPulse - Module A: Main Overview Dashboard
"""

import streamlit as st
import pandas as pd
import numpy as np
from database.operations import load_generation_dataframe, get_all_plants
from core.calculations import summarize_generation_dataframe, calculate_environmental_metrics
from core.revenue_engine import RevenueEngine
from components.kpi_cards import render_top_kpi_grid
from components.charts import (
    plot_actual_vs_expected,
    plot_monthly_generation_trends,
    plot_monthly_revenue,
    plot_plant_comparison
)

def render_overview_page(selected_plant: str, start_date, end_date):
    st.markdown(
        """
        <div class="sp-header-container">
            <div>
                <h1 class="sp-header-title">⚡ Executive Solar Overview</h1>
                <div class="sp-header-subtitle">Real-time asset telemetry, portfolio KPIs, and operational health</div>
            </div>
            <div>
                <span class="sp-badge sp-badge-live">PORTFOLIO ACTIVE</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 1. Load Data
    plant_filter = None if selected_plant == "ALL" else selected_plant
    df = load_generation_dataframe(plant_ids=plant_filter, start_date=start_date, end_date=end_date)

    if df.empty:
        st.warning("No solar generation data found for the selected asset and date range.")
        return

    # Enrich with financials
    rev_engine = RevenueEngine()
    df = rev_engine.calculate_revenue_for_dataframe(df)

    gen_summary = summarize_generation_dataframe(df)
    fin_summary = rev_engine.summarize_financials(df)

    # Annualized estimate
    days_in_period = max(1, (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days + 1)
    annual_factor = 365.0 / days_in_period
    est_annual_revenue = fin_summary["total_estimated_revenue_inr"] * annual_factor

    # 2. Render Top KPI Grid
    render_top_kpi_grid(
        total_generation_kwh=gen_summary["total_actual_kwh"],
        avg_daily_kwh=gen_summary["avg_daily_kwh"],
        efficiency_pct=gen_summary["overall_efficiency"],
        estimated_revenue_inr=fin_summary["total_estimated_revenue_inr"],
        estimated_annual_inr=est_annual_revenue,
        shortfall_kwh=gen_summary["total_shortfall_kwh"]
    )

    # 3. Highlight Cards (Best / Lowest performing plant, critical flags)
    all_plants_meta = get_all_plants()
    if selected_plant == "ALL" and len(df["plant_id"].unique()) > 1:
        plant_agg = df.groupby(["plant_id", "plant_name"]).agg({
            "actual_generation_kwh": "sum",
            "expected_generation_kwh": "sum"
        }).reset_index()
        plant_agg["eff"] = (plant_agg["actual_generation_kwh"] / plant_agg["expected_generation_kwh"].replace(0, np.nan)) * 100

        best_plant = plant_agg.loc[plant_agg["eff"].idxmax()]
        worst_plant = plant_agg.loc[plant_agg["eff"].idxmin()]

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(
                f"""
                <div class="sp-alert-box sp-alert-success">
                    <div>
                        <div style="font-size:0.75rem; text-transform:uppercase; font-weight:700;">Top Performing Asset</div>
                        <div style="font-size:1.05rem; font-weight:700;">{best_plant['plant_name']}</div>
                        <div style="font-size:0.8rem; opacity:0.85;">Efficiency: {best_plant['eff']:.1f}%</div>
                    </div>
                    <span style="font-size:1.5rem;">🏆</span>
                </div>
                """,
                unsafe_allow_html=True
            )
        with c2:
            st.markdown(
                f"""
                <div class="sp-alert-box sp-alert-warning">
                    <div>
                        <div style="font-size:0.75rem; text-transform:uppercase; font-weight:700;">Needs Optimization</div>
                        <div style="font-size:1.05rem; font-weight:700;">{worst_plant['plant_name']}</div>
                        <div style="font-size:0.8rem; opacity:0.85;">Efficiency: {worst_plant['eff']:.1f}%</div>
                    </div>
                    <span style="font-size:1.5rem;">⚠️</span>
                </div>
                """,
                unsafe_allow_html=True
            )
        with c3:
            underperforming_days = len(df[df["actual_generation_kwh"] < df["expected_generation_kwh"] * 0.80])
            st.markdown(
                f"""
                <div class="sp-alert-box sp-alert-critical">
                    <div>
                        <div style="font-size:0.75rem; text-transform:uppercase; font-weight:700;">Underperforming Days</div>
                        <div style="font-size:1.05rem; font-weight:700;">{underperforming_days} Days (<80%)</div>
                        <div style="font-size:0.8rem; opacity:0.85;">Triggered alert logs</div>
                    </div>
                    <span style="font-size:1.5rem;">📉</span>
                </div>
                """,
                unsafe_allow_html=True
            )
        with c4:
            env = calculate_environmental_metrics(gen_summary["total_actual_kwh"])
            st.markdown(
                f"""
                <div class="sp-alert-box sp-alert-info">
                    <div>
                        <div style="font-size:0.75rem; text-transform:uppercase; font-weight:700;">Carbon Offset</div>
                        <div style="font-size:1.05rem; font-weight:700;">{env['co2_offset_tonnes']:,.0f} tCO₂e</div>
                        <div style="font-size:0.8rem; opacity:0.85;">🌳 {env['trees_equivalent']:,} trees equiv.</div>
                    </div>
                    <span style="font-size:1.5rem;">🌱</span>
                </div>
                """,
                unsafe_allow_html=True
            )

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # 4. Charts: Actual vs Expected Generation + Monthly Trends
    row1_c1, row1_c2 = st.columns([1.6, 1.0])
    with row1_c1:
        # Group by date for smooth aggregate display
        daily_agg = df.groupby("timestamp").agg({
            "actual_generation_kwh": "sum",
            "expected_generation_kwh": "sum"
        }).reset_index()
        st.plotly_chart(plot_actual_vs_expected(daily_agg), use_container_width=True)

    with row1_c2:
        st.plotly_chart(plot_monthly_generation_trends(df), use_container_width=True)

    # 5. Charts: Monthly Revenue Breakdown + Plant Comparison
    row2_c1, row2_c2 = st.columns([1.2, 1.0])
    with row2_c1:
        st.plotly_chart(plot_monthly_revenue(df), use_container_width=True)

    with row2_c2:
        if len(df["plant_id"].unique()) > 1:
            st.plotly_chart(plot_plant_comparison(df), use_container_width=True)
        else:
            # Single plant CUF & PR breakdown
            cuf = (gen_summary["total_actual_kwh"] / (df["capacity_mw"].iloc[0] * 1000 * 24 * days_in_period)) * 100
            st.markdown(
                f"""
                <div class="sp-section-box" style="margin-top: 1.5rem;">
                    <div class="sp-section-title">📊 Asset Operational Health</div>
                    <div style="margin: 1rem 0;">
                        <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem;">
                            <span style="color:#94a3b8;">Capacity Utilization Factor (CUF)</span>
                            <span style="font-weight:700; color:#10b981;">{cuf:.2f}%</span>
                        </div>
                        <div style="background:#22312d; border-radius:4px; height:8px; overflow:hidden;">
                            <div style="width:{min(100, cuf*4)}%; background:#10b981; height:100%;"></div>
                        </div>
                    </div>
                    <div style="margin: 1rem 0;">
                        <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem;">
                            <span style="color:#94a3b8;">Average Performance Ratio (PR)</span>
                            <span style="font-weight:700; color:#38bdf8;">{min(92.0, gen_summary['overall_efficiency'] * 0.9):.1f}%</span>
                        </div>
                        <div style="background:#22312d; border-radius:4px; height:8px; overflow:hidden;">
                            <div style="width:{min(100, gen_summary['overall_efficiency'] * 0.9)}%; background:#38bdf8; height:100%;"></div>
                        </div>
                    </div>
                    <div style="font-size:0.75rem; color:#64748b; margin-top:0.75rem;">
                        Industry standard CUF benchmark for Indian utility solar ranges between 19% - 25%.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
