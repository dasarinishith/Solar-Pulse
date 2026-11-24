"""
Automated Verification Suite for SolarPulse Three-Mode Data Source System
Tests:
1. Sample Data Mode: Multi-plant, 15-min interval, and multi-inverter telemetry
2. Upload Data Mode: Column mapping, Replace vs Append, and UPLOADED isolation
3. Connect Inverter Mode: Unconfigured status, credential validation error handling, no fake data
4. Cross-Mode Isolation: Switching data sources strictly separates datasets
"""

import pytest
import pandas as pd
from database.operations import (
    load_generation_dataframe,
    load_15min_telemetry_dataframe,
    bulk_insert_generation_records,
    get_available_data_sources,
    get_gateway_configs,
    save_gateway_config,
    update_gateway_status
)
from core.api_client import get_connector, SolarEdgeConnector, SMAConnector, FroniusConnector

def test_sample_data_mode_and_telemetry():
    # Verify daily records load strictly with SIMULATED tag
    daily_df = load_generation_dataframe(data_source="SIMULATED")
    assert not daily_df.empty
    assert (daily_df["data_source"] == "SIMULATED").all()
    assert daily_df["plant_id"].nunique() >= 4

    # Verify 15-minute interval sub-daily telemetry exists
    df_15m = load_15min_telemetry_dataframe(plant_id="SP-01", data_source="SIMULATED")
    assert not df_15m.empty
    assert "power_kw" in df_15m.columns
    assert "dc_power_kw" in df_15m.columns
    assert "inverter_id" in df_15m.columns
    # Check multiple inverters are present
    assert df_15m["inverter_id"].nunique() >= 2
    # Verify DC power >= AC power during daylight
    daylight = df_15m[df_15m["power_kw"] > 100]
    if not daylight.empty:
        assert (daylight["dc_power_kw"] >= daylight["power_kw"]).all()

def test_upload_mode_append_and_replace():
    # Create sample upload batch 1
    batch_1 = pd.DataFrame([
        {
            "timestamp": "2025-03-01",
            "plant_id": "SP-USER",
            "plant_name": "Rooftop Commercial Plant",
            "inverter_id": "INV-A",
            "actual_generation_kwh": 5000.0,
            "expected_generation_kwh": 5500.0,
            "tariff_inr_per_kwh": 4.0
        }
    ])
    count_1 = bulk_insert_generation_records(batch_1, source="UPLOADED", mode="REPLACE")
    assert count_1 == 1

    uploaded_df = load_generation_dataframe(data_source="UPLOADED")
    assert len(uploaded_df) == 1
    assert uploaded_df["plant_id"].iloc[0] == "SP-USER"
    assert uploaded_df["data_source"].iloc[0] == "UPLOADED"

    # Append batch 2
    batch_2 = pd.DataFrame([
        {
            "timestamp": "2025-03-02",
            "plant_id": "SP-USER",
            "plant_name": "Rooftop Commercial Plant",
            "inverter_id": "INV-B",
            "actual_generation_kwh": 6000.0,
            "expected_generation_kwh": 6500.0,
            "tariff_inr_per_kwh": 4.0
        }
    ])
    count_2 = bulk_insert_generation_records(batch_2, source="UPLOADED", mode="APPEND")
    assert count_2 == 1

    appended_df = load_generation_dataframe(data_source="UPLOADED")
    assert len(appended_df) == 2

    # Replace mode resets uploaded records
    count_3 = bulk_insert_generation_records(batch_1, source="UPLOADED", mode="REPLACE")
    replaced_df = load_generation_dataframe(data_source="UPLOADED")
    assert len(replaced_df) == 1

def test_connect_inverter_unconfigured_policy():
    # SolarEdge without key must report NOT CONFIGURED
    se = get_connector("SolarEdge", plant_id="SP-01", site_id="TEST-SITE", api_key=None)
    success, msg = se.test_connection()
    assert success is False
    assert "NOT CONFIGURED" in msg

    # SMA without key must report NOT CONFIGURED
    sma = get_connector("SMA", plant_id="SP-02", site_id="TEST-SITE", api_key=None)
    success_sma, msg_sma = sma.test_connection()
    assert success_sma is False
    assert "NOT CONFIGURED" in msg_sma

    # Invalid SolarEdge test credentials must return error, not fake success
    se_invalid = get_connector("SolarEdge", plant_id="SP-01", site_id="999999", api_key="INVALID_MOCK_KEY_12345")
    success_inv, msg_inv = se_invalid.test_connection()
    assert success_inv is False
    assert any(err in msg_inv for err in ["AUTH_FAILED", "GATEWAY_ERROR", "NETWORK_ERROR", "HTTP 403"])

def test_strict_mode_isolation():
    # Verify SIMULATED query returns zero UPLOADED records
    sim_df = load_generation_dataframe(data_source="SIMULATED")
    assert "SP-USER" not in sim_df["plant_id"].values

    # Verify UPLOADED query returns zero SIMULATED records
    up_df = load_generation_dataframe(data_source="UPLOADED")
    assert "SP-01" not in up_df["plant_id"].values
    assert (up_df["data_source"] == "UPLOADED").all()

    # Verify API_LIVE has zero fake records
    live_df = load_generation_dataframe(data_source="API_LIVE")
    assert live_df.empty
