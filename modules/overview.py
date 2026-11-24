"""
SolarPulse - Module A: Main Overview Dashboard
Supports Three-Mode Data Source System:
1. Explore with Sample Data (SIMULATED)
2. Upload Your Dataset (UPLOADED)
3. Connect Your Inverter (API_LIVE)
Includes 15-minute diurnal sub-daily curve and multi-inverter telemetry.
"""

import streamlit as st
import pandas as pd
import numpy as np
from database.operations import load_generation_dataframe, load_15min_telemetry_dataframe, get_all_plants, get_available_data_sources
from core.calculations import summarize_generation_dataframe, calculate_environmental_metrics
from core.revenue_engine import RevenueEngine
from components.kpi_cards import render_top_kpi_grid
from components.charts import (
    plot_actual_vs_expected,
    plot_monthly_generation_trends,
    plot_monthly_revenue,
    plot_plant_comparison,
    plot_15min_diurnal_curve,
    plot_multi_inverter_power
)

def render_overview_page(selected_plant: str, start_date, end_date, active_mode: str = "SIMULATED"):
    # Header Banner
    mode_badges = {
        "SIMULATED": '<span class="sp-badge sp-badge-simulated">SIMULATED DATASET</span>',
        "UPLOADED": '<span class="sp-badge sp-badge-uploaded">UPLOADED DATASET</span>',
        "API_LIVE": '<span class="sp-badge sp-badge-unconfigured">NOT CONFIGURED (API)</span>'
    }

    st.markdown(
        f"""
        <div class="sp-header-container">
            <div>
                <h1 class="sp-header-title">⚡ Executive Solar Operations Dashboard</h1>
                <div class="sp-header-subtitle">Real-time solar generation analytics, revenue monetization, and operational asset health</div>
            </div>
            <div>
                {mode_badges.get(active_mode, '')}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 1. Three-Mode Choice Cards
    source_counts = get_available_data_sources()
    c_m1, c_m2, c_m3 = st.columns(3)

    with c_m1:
        is_active = (active_mode == "SIMULATED")
        st.markdown(
            f"""
            <div class="sp-mode-card {'active' if is_active else ''}">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div class="sp-mode-title">🚀 1. Explore Sample Data</div>
                    <span class="sp-badge sp-badge-simulated">SIMULATED</span>
                </div>
                <div class="sp-mode-desc">
                    Explore multi-plant 12-month historical data and 15-minute inverter telemetries.
                </div>
                <div style="font-size:0.75rem; color:var(--sp-text-muted); margin-bottom:0.6rem;">
                    Records Available: <b>{source_counts.get('SIMULATED', 0):,}</b>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        if not is_active:
            if st.button("Switch to Sample Mode", key="btn_mode_sim", use_container_width=True):
                st.session_state["data_source_mode"] = "SIMULATED"
                st.rerun()

    with c_m2:
        is_active = (active_mode == "UPLOADED")
        st.markdown(
            f"""
            <div class="sp-mode-card {'active' if is_active else ''}">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div class="sp-mode-title">📥 2. Upload Your Dataset</div>
                    <span class="sp-badge sp-badge-uploaded">UPLOADED</span>
                </div>
                <div class="sp-mode-desc">
                    Import operational CSV/Excel spreadsheets with automated schema validation.
                </div>
                <div style="font-size:0.75rem; color:var(--sp-text-muted); margin-bottom:0.6rem;">
                    Records Available: <b>{source_counts.get('UPLOADED', 0):,}</b>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        if not is_active:
            if st.button("Switch to Upload Mode", key="btn_mode_upload", use_container_width=True):
                st.session_state["data_source_mode"] = "UPLOADED"
                st.rerun()

    with c_m3:
        is_active = (active_mode == "API_LIVE")
        st.markdown(
            f"""
            <div class="sp-mode-card {'active' if is_active else ''}">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div class="sp-mode-title">🔌 3. Connect Inverter</div>
                    <span class="sp-badge sp-badge-unconfigured">NOT CONFIGURED</span>
                </div>
                <div class="sp-mode-desc">
                    Connect SolarEdge, SMA, Fronius, Sungrow, or Huawei cloud gateways.
                </div>
                <div style="font-size:0.75rem; color:var(--sp-text-muted); margin-bottom:0.6rem;">
                    Status: <b>Not Configured</b> (Requires API Key)
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        if not is_active:
            if st.button("Configure Inverter Mode", key="btn_mode_api", use_container_width=True):
                st.session_state["data_source_mode"] = "API_LIVE"
                st.rerun()

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # 2. Check Data Availability for the active mode
    plant_filter = None if selected_plant == "ALL" else selected_plant
    df = load_generation_dataframe(plant_ids=plant_filter, start_date=start_date, end_date=end_date, data_source=active_mode)

    if df.empty:
        if active_mode == "UPLOADED":
            st.info(
                "📂 **No uploaded dataset found in SQLite.**\n\n"
                "Switch to the **Data Upload & Reports** module in the sidebar to upload a CSV or XLSX file."
            )
        elif active_mode == "API_LIVE":
            st.warning(
                "🔌 **Inverter API Gateway is NOT CONFIGURED.**\n\n"
                "SolarPulse strictly complies with enterprise policy and does not invent fake live connections.\n"
                "To connect a live plant, open the **Data Upload & Reports > Inverter SCADA Gateway** tab and enter manufacturer API credentials."
            )
        else:
            st.warning("No records found for the selected scope.")
        return

    # 3. Enrich with Financials
    rev_engine = RevenueEngine()
    df = rev_engine.calculate_revenue_for_dataframe(df)
    gen_summary = summarize_generation_dataframe(df)
    fin_summary = rev_engine.summarize_financials(df)

    days_in_period = max(1, (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days + 1)
    annual_factor = 365.0 / days_in_period
    est_annual_revenue = fin_summary["total_estimated_revenue_inr"] * annual_factor

    # 4. Render Top KPI Grid
    render_top_kpi_grid(
        total_generation_kwh=gen_summary["total_actual_kwh"],
        avg_daily_kwh=gen_summary["avg_daily_kwh"],
        efficiency_pct=gen_summary["overall_efficiency"],
        estimated_revenue_inr=fin_summary["total_estimated_revenue_inr"],
        estimated_annual_inr=est_annual_revenue,
        shortfall_kwh=gen_summary["total_shortfall_kwh"]
    )

    # 5. Highlights
    if len(df["plant_id"].unique()) > 1:
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
                        <div style="font-size:0.75rem; text-transform:uppercase; font-weight:700;">Top Asset</div>
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
                        <div style="font-size:0.75rem; text-transform:uppercase; font-weight:700;">Needs Tuning</div>
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
                        <div style="font-size:0.75rem; text-transform:uppercase; font-weight:700;">Shortfall Days</div>
                        <div style="font-size:1.05rem; font-weight:700;">{underperforming_days} Days (<80%)</div>
                        <div style="font-size:0.8rem; opacity:0.85;">Logged in Loss Engine</div>
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

    # 6. Macro Charts: Actual vs Expected & Monthly Generation
    row1_c1, row1_c2 = st.columns([1.6, 1.0])
    with row1_c1:
        daily_agg = df.groupby("timestamp").agg({
            "actual_generation_kwh": "sum",
            "expected_generation_kwh": "sum"
        }).reset_index()
        st.plotly_chart(plot_actual_vs_expected(daily_agg), use_container_width=True)

    with row1_c2:
        st.plotly_chart(plot_monthly_generation_trends(df), use_container_width=True)

    # 7. Sub-daily 15-Minute Interval Diurnal Section (Required for Sample Mode & 15m uploads)
    target_plant_15m = selected_plant if selected_plant != "ALL" else "SP-01"
    df_15m = load_15min_telemetry_dataframe(plant_id=target_plant_15m, data_source=active_mode)

    if not df_15m.empty:
        st.markdown("---")
        st.markdown(f"### ⏱️ Sub-Daily 15-Minute Operational Telemetry ({target_plant_15m})")
        st.markdown(
            """
            <div style="font-size:0.825rem; color:var(--sp-text-secondary); margin-bottom:0.75rem;">
                High-resolution sub-daily readings demonstrating solar morning ramp-up (06:00-10:00),
                afternoon solar peak (11:30-13:30), evening decline (15:30-18:30), night zero-standby, and DC-to-AC conversion.
            </div>
            """,
            unsafe_allow_html=True
        )

        col_15a, col_15b = st.columns([1.3, 1.0])
        with col_15a:
            st.plotly_chart(plot_15min_diurnal_curve(df_15m), use_container_width=True)
        with col_15b:
            st.plotly_chart(plot_multi_inverter_power(df_15m), use_container_width=True)

    # 8. Revenue & Asset Contribution
    row2_c1, row2_c2 = st.columns([1.2, 1.0])
    with row2_c1:
        st.plotly_chart(plot_monthly_revenue(df), use_container_width=True)
    with row2_c2:
        if len(df["plant_id"].unique()) > 1:
            st.plotly_chart(plot_plant_comparison(df), use_container_width=True)
        else:
            cuf = (gen_summary["total_actual_kwh"] / (df["capacity_mw"].iloc[0] * 1000 * 24 * days_in_period)) * 100
            st.markdown(
                f"""
                <div class="sp-section-box" style="margin-top: 1.5rem;">
                    <div class="sp-section-title">📊 Asset Operational Health</div>
                    <div style="margin: 1rem 0;">
                        <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem;">
                            <span style="color:var(--sp-text-secondary);">Capacity Utilization Factor (CUF)</span>
                            <span style="font-weight:700; color:#10b981;">{cuf:.2f}%</span>
                        </div>
                        <div style="background:#22312d; border-radius:4px; height:8px; overflow:hidden;">
                            <div style="width:{min(100, cuf*4)}%; background:#10b981; height:100%;"></div>
                        </div>
                    </div>
                    <div style="margin: 1rem 0;">
                        <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem;">
                            <span style="color:var(--sp-text-secondary);">Average Performance Ratio (PR)</span>
                            <span style="font-weight:700; color:#38bdf8;">{min(92.0, gen_summary['overall_efficiency'] * 0.9):.1f}%</span>
                        </div>
                        <div style="background:#22312d; border-radius:4px; height:8px; overflow:hidden;">
                            <div style="width:{min(100, gen_summary['overall_efficiency'] * 0.9)}%; background:#38bdf8; height:100%;"></div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
