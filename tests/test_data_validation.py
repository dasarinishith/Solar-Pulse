"""
Unit Tests for SolarPulse Data Validation and Cleansing Pipeline
Validates column synonym mapping, duplicate removal, and missing-value imputation.
"""

import pytest
import pandas as pd
from core.validation import clean_and_validate_dataset, map_and_standardize_columns

def test_column_synonyms_mapping():
    # Messy real-world column names
    messy_df = pd.DataFrame([{
        "Date": "2025-05-01",
        "PlantCode": "SP-99",
        "Energy_KWh": 50000.0,
        "Budget_KWh": 55000.0,
        "Ambient_Temp": 32.0,
        "Solar_Radiation": 850.0
    }])

    cleaned, mapping, missing = map_and_standardize_columns(messy_df)
    assert "timestamp" in cleaned.columns
    assert "plant_id" in cleaned.columns
    assert "actual_generation_kwh" in cleaned.columns
    assert "expected_generation_kwh" in cleaned.columns
    assert len(missing) == 0

def test_duplicate_dropping():
    df_with_dupes = pd.DataFrame([
        {"timestamp": "2025-01-01", "plant_id": "SP-01", "actual_generation_kwh": 100.0},
        {"timestamp": "2025-01-01", "plant_id": "SP-01", "actual_generation_kwh": 120.0}, # duplicate key
        {"timestamp": "2025-01-02", "plant_id": "SP-01", "actual_generation_kwh": 150.0}
    ])

    cleaned, summary = clean_and_validate_dataset(df_with_dupes)
    assert summary["duplicate_rows_dropped"] == 1
    assert len(cleaned) == 2

def test_missing_required_column_rejection():
    # Missing actual generation
    invalid_df = pd.DataFrame([
        {"timestamp": "2025-01-01", "temperature_c": 25.0}
    ])

    cleaned, summary = clean_and_validate_dataset(invalid_df)
    assert summary["is_valid"] is False
    assert any("actual_generation_kwh" in w for w in summary["warnings"])

def test_null_value_imputation():
    df_with_nulls = pd.DataFrame([
        {"timestamp": "2025-01-01", "actual_generation_kwh": 500.0, "temperature_c": None, "rainfall_mm": None}
    ])

    cleaned, summary = clean_and_validate_dataset(df_with_nulls)
    assert summary["is_valid"] is True
    # Imputed defaults
    assert pd.notna(cleaned["temperature_c"].iloc[0])
    assert cleaned["rainfall_mm"].iloc[0] == 0.0
