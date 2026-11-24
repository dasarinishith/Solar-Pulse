"""
SolarPulse - Data Management & Upload Center
Allows users to upload custom CSV / Excel datasets, validates schemas,
detects duplicates, imputes missing values, and persists to SQLite.
"""

import streamlit as st
import pandas as pd
import io
from core.validation import clean_and_validate_dataset
from database.operations import bulk_insert_generation_records, get_all_plants

def render_data_management_page():
    st.markdown(
        """
        <div class="sp-header-container">
            <div>
                <h1 class="sp-header-title">📥 Data Management & Telemetry Ingestion Center</h1>
                <div class="sp-header-subtitle">Upload operational CSV/Excel spreadsheets, validate data schemas, and synchronize to SQLite database</div>
            </div>
            <div>
                <span class="sp-badge sp-badge-live">DATA PIPELINE ACTIVE</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Template download
    with st.expander("📄 Download Standard SolarPulse Ingestion Template (CSV)"):
        st.markdown("Download a sample CSV structure with recommended column headers.")
        sample_template = pd.DataFrame([{
            "timestamp": "2025-01-01",
            "plant_id": "SP-01",
            "plant_name": "Pavagada Solar Park",
            "actual_generation_kwh": 215400.0,
            "expected_generation_kwh": 224000.0,
            "power_kw": 32000.0,
            "temperature_c": 28.5,
            "module_temperature_c": 46.2,
            "irradiance_wm2": 920.0,
            "rainfall_mm": 0.0,
            "inverter_status": "Normal",
            "grid_export_kwh": 183000.0,
            "self_consumption_kwh": 32400.0,
            "curtailed_energy_kwh": 0.0,
            "tariff_inr_per_kwh": 3.25
        }])
        csv_bytes = sample_template.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download CSV Template",
            data=csv_bytes,
            file_name="solarpulse_template.csv",
            mime="text/csv"
        )

    # File uploader
    uploaded_file = st.file_uploader(
        "Upload Plant Telemetry File",
        type=["csv", "xlsx", "xls"],
        help="Upload CSV or Excel file containing solar plant power or energy records."
    )

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".csv"):
                raw_df = pd.read_csv(uploaded_file)
            else:
                raw_df = pd.read_excel(uploaded_file)

            st.success(f"Successfully uploaded: **{uploaded_file.name}** ({len(raw_df)} rows, {len(raw_df.columns)} columns)")

            # Run cleaning & validation
            cleaned_df, summary = clean_and_validate_dataset(raw_df)

            # Display Validation Audit Summary
            st.markdown("### 🔍 Ingestion Validation Audit")
            col_v1, col_v2, col_v3 = st.columns(3)
            col_v1.metric("Rows Validated", f"{summary['final_rows']}")
            col_v2.metric("Duplicates Dropped", f"{summary['duplicate_rows_dropped']}")
            col_v3.metric("Status", "VALID" if summary["is_valid"] else "INVALID")

            if summary["column_mappings"]:
                with st.expander("🔗 Column Schema Mappings Applied"):
                    for orig, can in summary["column_mappings"].items():
                        st.write(f"• `{orig}` ➔ **`{can}`**")

            if summary["warnings"]:
                st.warning("Validation Notes:\n" + "\n".join([f"- {w}" for w in summary["warnings"]]))

            # Preview Cleaned Data
            st.markdown("### 📋 Ingestion Preview")
            st.dataframe(cleaned_df.head(10), use_container_width=True)

            # Persist to SQLite
            if summary["is_valid"]:
                if st.button("💾 Save Dataset to SolarPulse Database", type="primary"):
                    try:
                        inserted_count = bulk_insert_generation_records(cleaned_df, source="UPLOADED")
                        st.balloons()
                        st.success(f"🎉 Successfully persisted {inserted_count} records to SQLite database!")
                        st.info("Navigate to the Overview or Performance dashboards to analyze the newly uploaded data.")
                    except Exception as e:
                        st.error(f"Database insertion failed: {str(e)}")
            else:
                st.error("Please resolve the schema validation errors before importing.")

        except Exception as e:
            st.error(f"Error processing uploaded file: {str(e)}")

    # Database Status Overview
    st.markdown("---")
    st.markdown("### 🗄️ Database Portfolio Status")
    plants = get_all_plants()
    plants_df = pd.DataFrame(plants)
    st.dataframe(plants_df, use_container_width=True)
