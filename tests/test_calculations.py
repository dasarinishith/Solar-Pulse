"""
Unit Tests for SolarPulse Core Calculations
Validates division-by-zero protection, zero generation, CUF, PR, and environmental metrics.
"""

import pytest
import pandas as pd
import numpy as np
from core.calculations import (
    calculate_efficiency,
    calculate_shortfall,
    calculate_cuf,
    calculate_performance_ratio,
    calculate_environmental_metrics,
    summarize_generation_dataframe
)

def test_calculate_efficiency_scalar():
    # Normal case
    assert calculate_efficiency(80.0, 100.0) == 80.0
    # Zero expected (Must NOT divide by zero or raise exception)
    assert calculate_efficiency(50.0, 0.0) == 0.0
    # Negative expected
    assert calculate_efficiency(50.0, -10.0) == 0.0
    # None expected
    assert calculate_efficiency(50.0, None) == 0.0
    # Capped at 200% for physical safety
    assert calculate_efficiency(300.0, 100.0) == 200.0

def test_calculate_efficiency_series():
    actual = pd.Series([100.0, 0.0, 50.0, 150.0])
    expected = pd.Series([100.0, 0.0, 100.0, 100.0])
    res = calculate_efficiency(actual, expected)
    assert list(res) == [100.0, 0.0, 50.0, 150.0]

def test_calculate_shortfall():
    # Actual below expected
    assert calculate_shortfall(70.0, 100.0) == 30.0
    # Actual above expected (no shortfall)
    assert calculate_shortfall(120.0, 100.0) == 0.0
    # Exact match
    assert calculate_shortfall(100.0, 100.0) == 0.0
    # Series test
    s_actual = pd.Series([80.0, 120.0, 0.0])
    s_expected = pd.Series([100.0, 100.0, 50.0])
    res = calculate_shortfall(s_actual, s_expected)
    assert list(res) == [20.0, 0.0, 50.0]

def test_calculate_cuf():
    # 50 MW plant generating 240,000 kWh in 24 hours
    # CUF = 240,000 / (50,000 * 24) = 240,000 / 1,200,000 = 20.0%
    cuf = calculate_cuf(240000.0, 50.0, hours=24.0)
    assert round(cuf, 1) == 20.0

    # Zero capacity division protection
    assert calculate_cuf(1000.0, 0.0) == 0.0

def test_calculate_performance_ratio():
    # 50 MW plant (50,000 kWp), 200,000 kWh yield, 5,000 W/m2 (5 PSH)
    # Specific yield = 200,000 / 50,000 = 4.0 kWh/kWp
    # Ref yield = 5,000 / 1000 = 5.0
    # PR = 4.0 / 5.0 = 80.0%
    pr = calculate_performance_ratio(200000.0, 5000.0, 50.0)
    assert round(pr, 1) == 80.0
    # Zero irradiance protection
    assert calculate_performance_ratio(200000.0, 0.0, 50.0) == 0.0

def test_environmental_metrics():
    metrics = calculate_environmental_metrics(100000.0) # 100,000 kWh
    # 100,000 * 0.82 = 82,000 kg = 82 metric tonnes
    assert metrics["co2_offset_tonnes"] == 82.0
    assert metrics["trees_equivalent"] > 0
    assert metrics["vehicles_avoided"] > 0

def test_summarize_empty_dataframe():
    summary = summarize_generation_dataframe(pd.DataFrame())
    assert summary["total_actual_kwh"] == 0.0
    assert summary["overall_efficiency"] == 0.0
