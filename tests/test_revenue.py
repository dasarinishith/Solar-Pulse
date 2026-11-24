"""
Unit Tests for SolarPulse Revenue Intelligence Engine
Validates multi-tier tariffs, shortfall monetization, and invoiced vs collected revenue.
"""

import pytest
import pandas as pd
from core.revenue_engine import RevenueEngine

@pytest.fixture
def sample_revenue_df():
    return pd.DataFrame([
        {
            "plant_id": "SP-01",
            "timestamp": "2025-01-01",
            "actual_generation_kwh": 100000.0,
            "expected_generation_kwh": 120000.0,
            "grid_export_kwh": 80000.0,
            "self_consumption_kwh": 20000.0,
            "curtailed_energy_kwh": 5000.0,
            "tariff_inr_per_kwh": 3.20
        },
        {
            "plant_id": "SP-02",
            "timestamp": "2025-01-01",
            "actual_generation_kwh": 200000.0,
            "expected_generation_kwh": 200000.0,
            "grid_export_kwh": 180000.0,
            "self_consumption_kwh": 20000.0,
            "curtailed_energy_kwh": 0.0,
            "tariff_inr_per_kwh": 3.00
        }
    ])

def test_revenue_calculation(sample_revenue_df):
    engine = RevenueEngine(default_export_tariff=3.20, default_self_tariff=4.50)
    enriched = engine.calculate_revenue_for_dataframe(sample_revenue_df)

    # Check that financial columns are created
    assert "total_estimated_revenue_inr" in enriched.columns
    assert "revenue_shortfall_inr" in enriched.columns
    assert "curtailment_revenue_loss_inr" in enriched.columns

    row1 = enriched.iloc[0]
    # Export rev = 80,000 * 3.20 = 256,000
    assert row1["estimated_export_revenue_inr"] == 256000.0
    # Shortfall = (120,000 - 100,000) * 3.20 = 64,000
    assert row1["revenue_shortfall_inr"] == 64000.0
    # Curtailment loss = 5,000 * 3.20 = 16,000
    assert row1["curtailment_revenue_loss_inr"] == 16000.0

def test_financial_summary_and_collection_rate(sample_revenue_df):
    engine = RevenueEngine()
    summary = engine.summarize_financials(sample_revenue_df, collection_rate=0.95)

    assert summary["total_estimated_revenue_inr"] > 0
    assert summary["projected_collected_revenue_inr"] == round(summary["total_estimated_revenue_inr"] * 0.95, 2)
    assert summary["collection_efficiency_assumed"] == 95.0

def test_tariff_sensitivity(sample_revenue_df):
    engine = RevenueEngine()
    sens_df = engine.simulate_tariff_sensitivity(sample_revenue_df, delta_percentages=[-10, 0, 10])

    assert len(sens_df) == 3
    base_val = sens_df[sens_df["Tariff Adjustment (%)"] == "0%"]["Estimated Total Revenue (₹)"].iloc[0]
    high_val = sens_df[sens_df["Tariff Adjustment (%)"] == "+10%"]["Estimated Total Revenue (₹)"].iloc[0]
    assert high_val > base_val
