"""
SolarPulse - Inverter API Connectors & Real-Time Telemetry Gateway
Provides direct integration testing and polling for commercial inverter gateways:
SolarEdge, SMA Sunny Portal, Fronius Solar.web, Sungrow iSolarCloud, and Huawei FusionSolar.
Includes a live real-time simulated telemetry feed with interactive polling.
"""

import time
import streamlit as st
import pandas as pd
from core.api_client import InverterAPIClient

def render_api_connectors_page():
    st.markdown(
        """
        <div class="sp-header-container">
            <div>
                <h1 class="sp-header-title">🔌 Inverter API Connectors & Real-Time Gateway</h1>
                <div class="sp-header-subtitle">Direct SCADA telemetry streaming, cloud inverter polling, and edge gateway synchronization</div>
            </div>
            <div>
                <span class="sp-badge sp-badge-live">GATEWAY SERVICE</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="sp-section-box">
            <div class="sp-section-title">📡 Commercial Inverter Gateway Support</div>
            <div style="font-size:0.85rem; color:#94a3b8; line-height:1.5;">
                SolarPulse natively interfaces with standard utility inverter REST/MQTT endpoints.
                Select an inverter provider below to test authenticated live polling, or use the <b>Simulated Real-Time Stream</b>
                to verify high-frequency SCADA telemetry ingestion without requiring physical hardware credentials.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    col_gw1, col_gw2 = st.columns(2)
    with col_gw1:
        provider = st.selectbox(
            "Inverter Manufacturer / SCADA Gateway",
            options=["Simulated Live SCADA Stream (Default)", "SolarEdge Monitoring API", "SMA Sunny Portal", "Fronius Solar.web", "Sungrow iSolarCloud"]
        )

    with col_gw2:
        site_id = st.text_input("Asset / Site Identifier", value="SP-SITE-001")

    api_key = None
    if provider != "Simulated Live SCADA Stream (Default)":
        api_key = st.text_input("Gateway API Key / Token", type="password", placeholder="Enter manufacturer API token")
        st.caption("🔒 API keys are kept in transient session memory and never logged to external disks.")

    # Inverter Client instantiation
    provider_code = "SIMULATED" if "Simulated" in provider else provider.split()[0].upper()
    client = InverterAPIClient(provider=provider_code, api_key=api_key, site_id=site_id)

    st.markdown("---")
    st.markdown("### ⚡ Live Telemetry Poller")

    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        poll_clicked = st.button("🔄 Poll Live Gateway", type="primary")

    telemetry = client.fetch_current_telemetry(plant_capacity_mw=50.0)

    # Render telemetry gauges
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Instantaneous Power", f"{telemetry.get('current_power_kw', 0):,.1f} kW", delta="AC Active Power")
    p2.metric("Solar Irradiance", f"{telemetry.get('irradiance_wm2', 0):.1f} W/m²", delta="Pyranometer POA")
    p3.metric("Module Temp", f"{telemetry.get('module_temperature_c', 25):.1f} °C", delta="Back of Module")
    p4.metric("Grid Voltage", f"{telemetry.get('grid_voltage_v', 415):.1f} V", delta=f"{telemetry.get('grid_frequency_hz', 50):.2f} Hz")

    st.markdown(
        f"""
        <div style="background:#131c1a; border:1px solid #233631; border-radius:8px; padding:1rem; margin-top:1rem;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span style="font-size:0.8rem; color:#94a3b8;">Gateway Connection Status:</span>
                    <span style="font-weight:700; color:#10b981; margin-left:0.5rem;">{telemetry.get('connection_health', 'ONLINE')}</span>
                </div>
                <div style="font-size:0.75rem; color:#64748b;">
                    Source: <b>{telemetry.get('source')}</b> • Latency: {telemetry.get('latency_ms', 40)} ms • {telemetry.get('timestamp')}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    with st.expander("🔍 View Raw JSON Inverter Payload"):
        st.json(telemetry)
