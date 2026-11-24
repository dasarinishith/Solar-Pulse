"""
Unit Tests for SolarCast Forecasting Engine
"""

import pytest
import pandas as pd
import numpy as np
from core.forecasting import SolarForecaster

def test_forecasting_pipeline():
    # 45 days of simulated history
    dates = pd.date_range("2025-01-01", periods=45)
    hist_df = pd.DataFrame({
        "timestamp": dates,
        "actual_generation_kwh": 100000 + np.random.normal(0, 5000, 45),
        "temperature_c": 28.0,
        "irradiance_wm2": 850.0
    })

    forecaster = SolarForecaster(horizon_days=7)
    
    # Baseline
    forecast_baseline, meta_b = forecaster.generate_forecast(hist_df, method="Statistical Baseline (7-Day MA)")
    assert len(forecast_baseline) == 7
    assert "forecast_kwh" in forecast_baseline.columns
    assert "lower_bound_kwh" in forecast_baseline.columns
    assert "upper_bound_kwh" in forecast_baseline.columns

    # ML Model
    forecast_ml, meta_ml = forecaster.generate_forecast(hist_df, method="ML (Random Forest)")
    assert len(forecast_ml) == 7
    assert meta_ml["method"] == "Machine Learning (Random Forest)"
    assert "MAPE_percent" in meta_ml["metrics"]
