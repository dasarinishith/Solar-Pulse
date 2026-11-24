"""
SolarPulse - Downloadable Analytical Reports
Allows users to generate and download comprehensive executive PDF reports
and curated CSV data exports for compliance, investor, and operational reviews.
Supports active data source filtering (SIMULATED, UPLOADED, API_LIVE).
"""

import streamlit as st
import pandas as pd
from database.operations import load_generation_dataframe, get_all_plants
from core.calculations import summarize_generation_dataframe
from core.revenue_engine import RevenueEngine
from core.anomaly_detection import EquipmentAnomalyDetector
from components.report_generator import generate_csv_export, generate_executive_pdf_report

def render_reports_page(selected_plant: str, start_date, end_date, active_mode: str = "SIMULATED"):
    st.markdown(
        """
        <div class="sp-header-container">
            <div>
                <h1 class="sp-header-title">📑 Analytical Reports & Executive Export Center</h1>
                <div class="sp-header-subtitle">Generate certified operational summaries, financial audit trails, and PDF/CSV documentation</div>
            </div>
            <div>
                <span class="sp-badge sp-badge-live">EXPORT READY</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    plant_filter = None if selected_plant == "ALL" else selected_plant
    df = load_generation_dataframe(plant_ids=plant_filter, start_date=start_date, end_date=end_date, data_source=active_mode)

    if df.empty:
        st.warning(f"No records found for active mode: **{active_mode}**.")
        return

    rev_engine = RevenueEngine()
    df = rev_engine.calculate_revenue_for_dataframe(df)
    gen_summary = summarize_generation_dataframe(df)
    fin_summary = rev_engine.summarize_financials(df)

    detector = EquipmentAnomalyDetector()
    anomalies_df = detector.detect_anomalies(df)

    plant_rankings = df.groupby(["plant_id", "plant_name"]).agg({
        "capacity_mw": "first",
        "actual_generation_kwh": "sum",
        "expected_generation_kwh": "sum"
    }).reset_index()
    plant_rankings["efficiency"] = (plant_rankings["actual_generation_kwh"] / plant_rankings["expected_generation_kwh"].replace(0, 1)) * 100
    plant_rankings = plant_rankings.rename(columns={"actual_generation_kwh": "actual_kwh"})

    st.markdown("### 📄 Certified Executive PDF Report")
    st.markdown(
        """
        <div class="sp-section-box">
            <div class="sp-section-title">📊 Executive Monthly / Annual Performance Dossier</div>
            <div style="font-size:0.85rem; color:var(--sp-text-secondary); line-height:1.5;">
                Includes executive KPI cards, generation efficiency benchmarks, revenue monetization breakdowns,
                asset comparison matrices, and flagged anomaly event logs. Formatted for executive C-suite and investor distribution.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    report_title = f"SolarPulse Analytics Report - {selected_plant} ({start_date} to {end_date}) [{active_mode}]"

    try:
        pdf_bytes = generate_executive_pdf_report(
            summary_metrics=gen_summary,
            plant_rankings=plant_rankings,
            loss_events=anomalies_df,
            financial_summary=fin_summary,
            report_title=report_title
        )

        st.download_button(
            label="⬇️ Download Executive PDF Report",
            data=pdf_bytes,
            file_name=f"SolarPulse_Report_{selected_plant}_{start_date}_{active_mode}.pdf",
            mime="application/pdf",
            type="primary"
        )
    except Exception as e:
        st.error(f"Error generating PDF report: {str(e)}")

    st.markdown("---")

    st.markdown("### 📥 Granular CSV Analytical Exports")
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        st.markdown("#### 1. Full Calculated Generation & Revenue Dataset")
        csv_full = generate_csv_export(df)
        st.download_button(
            label="⬇️ Export Generation & Financials (CSV)",
            data=csv_full,
            file_name=f"solarpulse_generation_{start_date}_to_{end_date}_{active_mode}.csv",
            mime="text/csv"
        )

    with col_e2:
        st.markdown("#### 2. Flagged Operational Anomalies & Loss Events")
        csv_anom = generate_csv_export(anomalies_df) if not anomalies_df.empty else b"No anomalies"
        st.download_button(
            label="⬇️ Export Flagged Anomalies Log (CSV)",
            data=csv_anom,
            file_name=f"solarpulse_anomalies_{start_date}_to_{end_date}_{active_mode}.csv",
            mime="text/csv"
        )
