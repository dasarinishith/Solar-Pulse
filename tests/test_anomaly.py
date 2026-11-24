"""
Unit Tests for PredictCare Anomaly Detection Engine
"""

import pytest
import pandas as pd
from core.anomaly_detection import EquipmentAnomalyDetector

def test_anomaly_detection_rules():
    df = pd.DataFrame([
        {
            "timestamp": "2025-01-01",
            "plant_id": "SP-01",
            "expected_generation_kwh": 100000.0,
            "actual_generation_kwh": 20000.0, # 80% collapse
            "inverter_status": "Fault",
            "temperature_c": 32.0,
            "irradiance_wm2": 900.0
        },
        {
            "timestamp": "2025-01-02",
            "plant_id": "SP-01",
            "expected_generation_kwh": 100000.0,
            "actual_generation_kwh": 96000.0, # Normal
            "inverter_status": "Normal",
            "temperature_c": 28.0,
            "irradiance_wm2": 850.0
        }
    ])

    detector = EquipmentAnomalyDetector()
    anomalies = detector.detect_anomalies(df)

    assert not anomalies.empty
    # First row must be flagged as Critical Inverter Fault
    crit_anomaly = anomalies[anomalies["severity"] == "CRITICAL"]
    assert len(crit_anomaly) >= 1
