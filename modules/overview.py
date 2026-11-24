"""
SolarPulse - Module A: Main Overview Dashboard
Supports Three-Mode Data Source System:
1. Explore with Sample Data (SIMULATED)
2. Upload Your Dataset (UPLOADED) - with inline ingestion if empty or expandable
3. Connect Your Inverter (API_LIVE) - with inline gateway configuration & testing
"""

import streamlit as st
import pandas as pd
import numpy as np
from database.operations import (
    load_generation_dataframe, load_15min_telemetry_dataframe,
    get_all_plants, get_available_data_sources, bulk_insert_generation_records,
    get_gateway_configs, save_gateway_config, update_gateway_status
)
from core.calculations import summarize_generation_dataframe, calculate_environmental_metrics
from core.revenue_engine import RevenueEngine
from core.validation import clean_and_validate_dataset
from core.api_client import get_connector
from components.kpi_cards import render_top_kpi_grid
from components.charts import (
    plot_actual_vs_expected,
    plot_monthly_generation_trends,
    plot_monthly_revenue,
    plot_plant_comparison,
    plot_15min_diurnal_curve,
    plot_multi_inverter_power
)

def set_active_mode(new_mode: str):
    """Safely updates session state for both radio and active_mode."""
    st.session_state["data_source_mode"] = new_mode
    st.session_state["sb_data_source_radio"] = new_mode
    st.rerun()

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
                set_active_mode("SIMULATED")

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
                set_active_mode("UPLOADED")

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
                set_active_mode("API_LIVE")

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # ----------------------------------------------------
    # MODE 2: UPLOAD DATA MODE HANDLING
    # ----------------------------------------------------
    if active_mode == "UPLOADED":
        plant_filter = None if selected_plant == "ALL" else selected_plant
        df = load_generation_dataframe(plant_ids=plant_filter, start_date=start_date, end_date=end_date, data_source="UPLOADED")

        # If empty or user wants to upload, show upload tool
        show_uploader = df.empty
        if not df.empty:
            with st.expander("📤 Upload New Spreadsheet / Replace Dataset", expanded=False):
                _render_inline_uploader()
        else:
            st.info("📂 **Upload Your Solar Dataset**: Select a CSV or Excel file below to validate and import your operational data.")
            _render_inline_uploader()
            return

    # ----------------------------------------------------
    # MODE 3: CONNECT INVERTER MODE HANDLING
    # ----------------------------------------------------
    elif active_mode == "API_LIVE":
        st.markdown(
            """
            <div class="sp-section-box">
                <div class="sp-section-title">🔌 Inverter API Gateway Configuration</div>
                <div style="font-size:0.85rem; color:var(--sp-text-secondary); line-height:1.5;">
                    SolarPulse strictly maintains data provenance integrity. If no live inverter credentials are provided,
                    gateways are displayed as <b>NOT CONFIGURED</b>. No simulated data is ever masqueraded as live readings in this mode.
                    Enter vendor credentials below to test live gateway connectivity.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        _render_inline_gateway_manager()
        return

    # ----------------------------------------------------
    # MODE 1: SAMPLE DATA MODE HANDLING
    # ----------------------------------------------------
    else:
        plant_filter = None if selected_plant == "ALL" else selected_plant
        df = load_generation_dataframe(plant_ids=plant_filter, start_date=start_date, end_date=end_date, data_source="SIMULATED")
        if df.empty:
            st.warning("No sample data found. Click 'Reload / Reset Sample Data' in the sidebar.")
            return

    # ----------------------------------------------------
    # UNIFIED ANALYTICS RENDERING (Used by both Sample & Uploaded data!)
    # ----------------------------------------------------
    rev_engine = RevenueEngine()
    df = rev_engine.calculate_revenue_for_dataframe(df)
    gen_summary = summarize_generation_dataframe(df)
    fin_summary = rev_engine.summarize_financials(df)

    days_in_period = max(1, (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days + 1)
    annual_factor = 365.0 / days_in_period
    est_annual_revenue = fin_summary["total_estimated_revenue_inr"] * annual_factor

    # Top KPI Grid
    render_top_kpi_grid(
        total_generation_kwh=gen_summary["total_actual_kwh"],
        avg_daily_kwh=gen_summary["avg_daily_kwh"],
        efficiency_pct=gen_summary["overall_efficiency"],
        estimated_revenue_inr=fin_summary["total_estimated_revenue_inr"],
        estimated_annual_inr=est_annual_revenue,
        shortfall_kwh=gen_summary["total_shortfall_kwh"]
    )

    # Highlights
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

    # Macro Charts
    row1_c1, row1_c2 = st.columns([1.6, 1.0])
    with row1_c1:
        daily_agg = df.groupby("timestamp").agg({
            "actual_generation_kwh": "sum",
            "expected_generation_kwh": "sum"
        }).reset_index()
        st.plotly_chart(plot_actual_vs_expected(daily_agg), use_container_width=True)

    with row1_c2:
        st.plotly_chart(plot_monthly_generation_trends(df), use_container_width=True)

    # 15-Minute Sub-Daily Telemetry (for Sample mode or 15m uploads)
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

    # Revenue Breakdown
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
                </div>
                """,
                unsafe_allow_html=True
            )


# ----------------------------------------------------
# HELPER FUNCTIONS: INLINE UPLOADER & GATEWAY MANAGER
# ----------------------------------------------------
def _render_inline_uploader():
    """Renders the file uploader and validation directly on the Overview page."""
    col_u1, col_u2 = st.columns([1.5, 1.0])
    with col_u1:
        uploaded_file = st.file_uploader(
            "Select CSV or Excel Spreadsheet",
            type=["csv", "xlsx", "xls"],
            key="overview_inline_uploader",
            help="Upload a solar generation CSV or Excel file."
        )

    with col_u2:
        # Sample template generator
        sample_template = pd.DataFrame([
            {
                "timestamp": "2025-01-01 00:00:00",
                "plant_id": "SP-01",
                "plant_name": "Pavagada Solar Park",
                "inverter_id": "INV-01",
                "actual_generation_kwh": 215400.0,
                "expected_generation_kwh": 224000.0,
                "power_kw": 32000.0,
                "tariff_inr_per_kwh": 3.25
            }
        ])
        csv_bytes = sample_template.to_csv(index=False).encode("utf-8")
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        st.download_button("⬇️ Download Sample CSV", data=csv_bytes, file_name="solarpulse_template.csv", mime="text/csv", use_container_width=True)

    if uploaded_file is not None:
        try:
            raw_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
            cleaned_df, summary = clean_and_validate_dataset(raw_df)

            col_a1, col_a2, col_a3, col_a4 = st.columns(4)
            col_a1.metric("Rows Validated", f"{summary['final_rows']:,}")
            col_a2.metric("Duplicates Dropped", f"{summary['duplicate_rows_dropped']}")
            col_a3.metric("Interval Frequency", "15-Minute" if summary.get("is_interval_15m") else "Daily")
            col_a4.metric("Validation Status", "VALID" if summary["is_valid"] else "INVALID")

            st.dataframe(cleaned_df.head(5), use_container_width=True)

            col_p1, col_p2 = st.columns([1.5, 1.0])
            with col_p1:
                import_mode = st.radio("Persistence Mode", options=["APPEND", "REPLACE"], format_func=lambda x: "Append to existing records" if x == "APPEND" else "Replace previous uploaded records", horizontal=True)

            with col_p2:
                if summary["is_valid"]:
                    if st.button("💾 Save and Load Dashboard", type="primary", use_container_width=True):
                        inserted = bulk_insert_generation_records(cleaned_df, source="UPLOADED", mode=import_mode)
                        st.success(f"Saved {inserted:,} records! Loading dashboard...")
                        set_active_mode("UPLOADED")
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")


def _render_inline_gateway_manager():
    """Renders gateway connection tester and configuration directly on the Overview page."""
    gw_configs = get_gateway_configs()
    gw_df = pd.DataFrame(gw_configs)

    st.markdown("#### Registered Gateways")
    st.dataframe(
        gw_df[["manufacturer", "plant_id", "site_id", "status", "api_key_masked", "polling_interval_min", "last_polled"]],
        use_container_width=True
    )

    st.markdown("#### Test or Configure Inverter Gateway")
    c1, c2 = st.columns(2)
    with c1:
        manufacturer = st.selectbox("Manufacturer", options=["SolarEdge", "SMA", "Fronius", "Sungrow", "Huawei"], key="gw_ov_mfg")
        all_plants = get_all_plants()
        plant_id = st.selectbox("Assign to Asset", options=[p["plant_id"] for p in all_plants], key="gw_ov_plt")
    with c2:
        site_id = st.text_input("Site / Asset ID", value="SE-SITE-PVG", key="gw_ov_site")
        api_key = st.text_input("API Key / Bearer Token", type="password", placeholder="Enter manufacturer API token", key="gw_ov_key")

    b1, b2 = st.columns(2)
    with b1:
        if st.button("🧪 Test Connection", type="primary", use_container_width=True):
            if not api_key:
                st.warning("⚠️ **NOT CONFIGURED**: Missing API key or bearer token. Enter credentials to test connection.")
            else:
                with st.spinner(f"Authenticating with {manufacturer} gateway..."):
                    connector = get_connector(manufacturer=manufacturer, plant_id=plant_id, site_id=site_id, api_key=api_key)
                    success, msg = connector.test_connection()
                    if success:
                        st.success(f"✅ {msg}")
                        update_gateway_status(manufacturer, plant_id, "CONNECTED")
                    else:
                        st.error(f"❌ {msg}")
                        update_gateway_status(manufacturer, plant_id, "AUTH_FAILED", last_error=msg)
    with b2:
        if st.button("💾 Save Gateway Config", use_container_width=True):
            status = "CONFIGURED" if api_key else "NOT_CONFIGURED"
            save_gateway_config(manufacturer=manufacturer, plant_id=plant_id, site_id=site_id, api_key=api_key, status=status)
            st.success(f"Saved {manufacturer} configuration!")
            st.rerun()
