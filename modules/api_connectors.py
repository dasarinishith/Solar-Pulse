"""
SolarPulse - Connect Inverter Mode & Gateway Center
Integrates with commercial solar inverter APIs:
- SolarEdge Monitoring API
- SMA Sunny Portal / ennexOS
- Fronius Solar.web & Solar API
- Sungrow iSolarCloud OpenAPI
- Huawei FusionSolar OpenAPI

Strict Compliance:
- Unconfigured gateways clearly display 'NOT CONFIGURED'.
- Invalid keys display explicit authentication errors.
- No fake live telemetry is generated in this mode.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from core.api_client import get_connector
from database.operations import get_gateway_configs, save_gateway_config, update_gateway_status, get_all_plants

def render_api_connectors_page():
    st.markdown(
        """
        <div class="sp-header-container">
            <div>
                <h1 class="sp-header-title">🔌 Connect Inverter Mode: SCADA & Cloud Gateways</h1>
                <div class="sp-header-subtitle">Direct manufacturer inverter API authentication, SCADA gateway polling, and telemetry normalization</div>
            </div>
            <div>
                <span class="sp-badge sp-badge-unconfigured">INVERTER MODE</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="sp-section-box">
            <div class="sp-section-title">🔒 Enterprise Integration Policy</div>
            <div style="font-size:0.85rem; color:var(--sp-text-secondary); line-height:1.5;">
                SolarPulse strictly maintains data provenance integrity. If no live inverter credentials are provided,
                gateways are displayed as <b>NOT CONFIGURED</b>. No simulated data is ever masqueraded as live readings in this mode.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 1. Gateway Status Overview Table
    st.markdown("### 📡 Registered Inverter Gateway Matrix")
    gw_configs = get_gateway_configs()
    gw_df = pd.DataFrame(gw_configs)

    if not gw_df.empty:
        # Display clean status badges
        st.dataframe(
            gw_df[["manufacturer", "plant_id", "site_id", "status", "api_key_masked", "polling_interval_min", "last_polled"]],
            use_container_width=True
        )

    st.markdown("---")

    # 2. Inverter Credentials Configuration Form
    st.markdown("### ⚙️ Configure Inverter Gateway")
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        manufacturer = st.selectbox(
            "Select Inverter Manufacturer",
            options=["SolarEdge", "SMA", "Fronius", "Sungrow", "Huawei"],
            index=0
        )
        all_plants = get_all_plants()
        plant_ids = [p["plant_id"] for p in all_plants]
        plant_id = st.selectbox("Assign to Solar Asset", options=plant_ids, index=0)

    with col_c2:
        site_id = st.text_input("Manufacturer Site / Asset ID", value="SE-SITE-PVG", placeholder="e.g. 123456 or Site-Code")
        polling_min = st.select_slider("Telemetry Polling Frequency", options=[5, 10, 15, 30, 60], value=15, format_func=lambda x: f"{x} Minutes")

    col_k1, col_k2 = st.columns(2)
    with col_k1:
        api_key = st.text_input("API Key / Client Token", type="password", placeholder="Enter vendor API key")
    with col_k2:
        api_secret = st.text_input("API Secret / App Password (Optional)", type="password", placeholder="If required by vendor")

    base_url = st.text_input("Custom Gateway Endpoint URL (Optional)", placeholder="Leave blank for official manufacturer cloud endpoint")

    # 3. Action Buttons: Test Connection & Save Configuration
    col_btn1, col_btn2 = st.columns([1, 1])
    
    with col_btn1:
        if st.button("🧪 Test Gateway Connection", type="primary", use_container_width=True):
            if not api_key:
                st.warning("⚠️ **NOT CONFIGURED**: Missing API key or bearer token. Enter credentials to initiate authentication handshake.")
            else:
                with st.spinner(f"Initiating authentication handshake with {manufacturer} gateway..."):
                    connector = get_connector(
                        manufacturer=manufacturer,
                        plant_id=plant_id,
                        site_id=site_id,
                        api_key=api_key,
                        api_secret=api_secret,
                        base_url=base_url
                    )
                    success, msg = connector.test_connection()
                    if success:
                        st.success(f"✅ {msg}")
                        update_gateway_status(manufacturer, plant_id, "CONNECTED")
                    else:
                        st.error(f"❌ {msg}")
                        update_gateway_status(manufacturer, plant_id, "AUTH_FAILED", last_error=msg)

    with col_btn2:
        if st.button("💾 Save Gateway Configuration", use_container_width=True):
            status = "CONFIGURED" if api_key else "NOT_CONFIGURED"
            save_gateway_config(
                manufacturer=manufacturer,
                plant_id=plant_id,
                site_id=site_id,
                api_key=api_key,
                api_secret=api_secret,
                base_url=base_url,
                polling_interval=polling_min,
                status=status
            )
            st.success(f"Saved configuration for **{manufacturer} ({plant_id})** in status: **{status}**")
            st.rerun()

    # 4. Telemetry Ingestion Guide
    st.markdown("---")
    st.markdown("### 📖 Inverter API Credentials Reference Guide")
    with st.expander("ℹ️ How to obtain API credentials from supported manufacturers"):
        st.markdown(
            """
            - **SolarEdge**: Sign in to the *SolarEdge Monitoring Portal* ➔ *Site Admin* ➔ *Site Access* ➔ *API Access* ➔ Generate API Key.
            - **SMA**: Access the *SMA Developer Portal* (ennexOS) ➔ Register an Application ➔ Obtain Client ID and Secret.
            - **Fronius**: Access *Solar.web* ➔ *User Settings* ➔ *API Access* ➔ Generate AccessKey ID; or for local LAN datalogger, use inverter local IP.
            - **Sungrow**: Request enterprise access to *iSolarCloud OpenAPI* via your Sungrow distributor ➔ Generate AppKey and Secret.
            - **Huawei**: Enable *Northbound Interface* in *FusionSolar SmartPVMS* ➔ Create API System Account ➔ Use SystemCode as token.
            """
        )
