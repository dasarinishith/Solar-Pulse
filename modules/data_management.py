"""
SolarPulse - Data Ingestion & Upload Center
Supports CSV, XLSX, and XLS uploads with automatic column mapping,
multi-plant and multi-inverter support, duplicate detection,
and Replace vs Append persistence options.
"""

import streamlit as st
import pandas as pd
import io
from core.validation import clean_and_validate_dataset
from database.operations import bulk_insert_generation_records, get_all_plants, get_available_data_sources

def render_data_management_page():
    st.markdown(
        """
        <div class="sp-header-container">
            <div>
                <h1 class="sp-header-title">📥 Upload Data Mode: Telemetry Ingestion Center</h1>
                <div class="sp-header-subtitle">Import operational CSV/Excel spreadsheets, validate data schemas, and synchronize to SQLite database</div>
            </div>
            <div>
                <span class="sp-badge sp-badge-uploaded">UPLOAD DATA MODE</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 1. Template Download Section
    with st.expander("📄 Download Standard SolarPulse Ingestion Template (CSV)"):
        st.markdown("Download a sample CSV structure with recommended column headers.")
        sample_template = pd.DataFrame([
            {
                "timestamp": "2025-01-01 00:00:00",
                "plant_id": "SP-01",
                "plant_name": "Pavagada Solar Park",
                "inverter_id": "INV-01",
                "actual_generation_kwh": 215400.0,
                "expected_generation_kwh": 224000.0,
                "power_kw": 32000.0,
                "dc_power_kw": 32650.0,
                "ac_voltage_v": 415.0,
                "temperature_c": 28.5,
                "irradiance_wm2": 920.0,
                "rainfall_mm": 0.0,
                "inverter_status": "Normal",
                "tariff_inr_per_kwh": 3.25
            },
            {
                "timestamp": "2025-01-01 00:00:00",
                "plant_id": "SP-01",
                "plant_name": "Pavagada Solar Park",
                "inverter_id": "INV-02",
                "actual_generation_kwh": 209000.0,
                "expected_generation_kwh": 224000.0,
                "power_kw": 31200.0,
                "dc_power_kw": 31800.0,
                "ac_voltage_v": 415.0,
                "temperature_c": 28.5,
                "irradiance_wm2": 920.0,
                "rainfall_mm": 0.0,
                "inverter_status": "Normal",
                "tariff_inr_per_kwh": 3.25
            }
        ])
        csv_bytes = sample_template.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download Sample CSV Template",
            data=csv_bytes,
            file_name="solarpulse_template.csv",
            mime="text/csv"
        )

    # 2. File Upload Interface
    st.markdown("### 📁 Select Local Spreadsheet")
    uploaded_file = st.file_uploader(
        "Upload Plant Telemetry File",
        type=["csv", "xlsx", "xls"],
        help="Upload CSV or Excel file containing solar generation or power records."
    )

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".csv"):
                raw_df = pd.read_csv(uploaded_file)
            else:
                raw_df = pd.read_excel(uploaded_file)

            st.success(f"Loaded: **{uploaded_file.name}** ({len(raw_df):,} rows, {len(raw_df.columns)} columns)")

            # Run cleaning & validation
            cleaned_df, summary = clean_and_validate_dataset(raw_df)

            # Ingestion Audit Summary
            st.markdown("### 🔍 Validation Audit Summary")
            col_v1, col_v2, col_v3, col_v4 = st.columns(4)
            col_v1.metric("Validated Rows", f"{summary['final_rows']:,}")
            col_v2.metric("Duplicates Dropped", f"{summary['duplicate_rows_dropped']}")
            col_v3.metric("Data Frequency", "15-Minute Interval" if summary.get("is_interval_15m") else "Daily Aggregate")
            col_v4.metric("Schema Status", "VALID" if summary["is_valid"] else "INVALID")

            if summary["plants_found"]:
                st.caption(f"📍 Plants detected: **{', '.join(summary['plants_found'])}** | Inverters: **{', '.join(summary['inverters_found'][:6])}**")

            with st.expander("🔗 Applied Column Schema Mappings"):
                for orig, can in summary["column_mappings"].items():
                    st.write(f"• Raw: `{orig}` ➔ Canonical: **`{can}`**")

            if summary["warnings"]:
                st.warning("Validation Notes:\n" + "\n".join([f"- {w}" for w in summary["warnings"]]))

            # Preview Data
            st.markdown("### 📋 Preview Cleaned Dataset")
            st.dataframe(cleaned_df.head(8), use_container_width=True)

            # Ingestion Options: Replace vs Append
            st.markdown("### 💾 Persistence Options")
            col_opt1, col_opt2 = st.columns([1.5, 1.0])
            with col_opt1:
                import_mode = st.radio(
                    "Import Mode",
                    options=["APPEND", "REPLACE"],
                    format_func=lambda x: "Append to existing uploaded records" if x == "APPEND" else "Replace all previous uploaded records (Fresh Import)",
                    horizontal=True
                )

            with col_opt2:
                if summary["is_valid"]:
                    if st.button("💾 Persist to SolarPulse Database", type="primary", use_container_width=True):
                        try:
                            inserted_count = bulk_insert_generation_records(cleaned_df, source="UPLOADED", mode=import_mode)
                            st.balloons()
                            st.success(f"🎉 Successfully saved {inserted_count:,} records as UPLOADED dataset!")
                            
                            # Switch active mode to UPLOADED
                            st.session_state["data_source_mode"] = "UPLOADED"
                            st.info("Switched active view to **UPLOADED** mode. Navigate to Executive Overview to analyze.")
                        except Exception as e:
                            st.error(f"Database insertion failed: {str(e)}")
                else:
                    st.error("Please fix schema validation errors before proceeding.")

        except Exception as e:
            st.error(f"Error reading file: {str(e)}")

    # Current Database Status
    st.markdown("---")
    st.markdown("### 🗄️ Database Storage Status")
    source_counts = get_available_data_sources()
    s1, s2, s3 = st.columns(3)
    s1.metric("SIMULATED Records", f"{source_counts.get('SIMULATED', 0):,}")
    s2.metric("UPLOADED Records", f"{source_counts.get('UPLOADED', 0):,}")
    s3.metric("API_LIVE Records", f"{source_counts.get('API_LIVE', 0):,}")
