"""
SolarPulse Data Validation & Cleansing
Flexible schema mapping, duplicate detection, and missing-value handling for solar CSVs/Excels.
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, List, Any

# Standard expected schema mapping aliases
COLUMN_SYNONYMS = {
    "timestamp": ["timestamp", "date", "datetime", "record_date", "time", "reading_date"],
    "plant_id": ["plant_id", "plantid", "plantcode", "plant_code", "station_id", "site_id", "site_code"],
    "plant_name": ["plant_name", "plant", "site_name", "facility_name", "station_name"],
    "actual_generation_kwh": [
        "actual_generation_kwh", "actual_kwh", "actual_generation", "generation_kwh",
        "energy_kwh", "actual_energy", "kwh_generated", "power_generated_kwh"
    ],
    "expected_generation_kwh": [
        "expected_generation_kwh", "expected_kwh", "expected_generation", "predicted_kwh",
        "budget_kwh", "target_kwh", "modeled_kwh", "theoretical_kwh"
    ],
    "power_kw": ["power_kw", "peak_kw", "power", "kw", "active_power_kw"],
    "temperature_c": ["temperature_c", "temp_c", "temperature", "ambient_temp", "ambient_temperature"],
    "module_temperature_c": ["module_temperature_c", "module_temp", "cell_temp", "panel_temp"],
    "irradiance_wm2": ["irradiance_wm2", "irradiance", "ghi", "poa", "solar_radiation", "ghi_wm2"],
    "rainfall_mm": ["rainfall_mm", "rain_mm", "rainfall", "precipitation"],
    "inverter_status": ["inverter_status", "status", "inv_status", "operational_status"],
    "grid_export_kwh": ["grid_export_kwh", "export_kwh", "grid_feed_kwh", "exported_energy"],
    "self_consumption_kwh": ["self_consumption_kwh", "self_kwh", "captive_kwh", "local_consumption"],
    "curtailed_energy_kwh": ["curtailed_energy_kwh", "curtailment_kwh", "curtailed_kwh"],
    "tariff_inr_per_kwh": ["tariff_inr_per_kwh", "tariff", "rate_inr", "tariff_inr", "ppa_rate"],
    "soiling_ratio": ["soiling_ratio", "soiling_index", "cleanliness_factor"]
}

def map_and_standardize_columns(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str], List[str]]:
    """
    Intelligently maps uploaded dataframe columns to canonical SolarPulse schema.
    Returns: (cleaned_df, mapping_applied, missing_required_columns)
    """
    df = df.copy()
    raw_cols = {str(c).strip().lower(): c for c in df.columns}
    rename_map = {}
    matched_canonical = set()

    for canonical, synonyms in COLUMN_SYNONYMS.items():
        for syn in synonyms:
            syn_lower = syn.lower()
            if syn_lower in raw_cols:
                original_col = raw_cols[syn_lower]
                rename_map[original_col] = canonical
                matched_canonical.add(canonical)
                break

    df = df.rename(columns=rename_map)

    # Required columns for core analytics
    required_cols = ["timestamp", "actual_generation_kwh"]
    missing = [c for c in required_cols if c not in df.columns]

    return df, rename_map, missing

def clean_and_validate_dataset(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Cleans dataset, detects duplicates, parses dates, imputes missing values and returns an audit summary.
    """
    summary = {
        "initial_rows": len(df),
        "initial_cols": len(df.columns),
        "duplicate_rows_dropped": 0,
        "null_counts": {},
        "imputed_columns": [],
        "warnings": [],
        "is_valid": True
    }

    if df.empty:
        summary["is_valid"] = False
        summary["warnings"].append("Dataset is empty.")
        return df, summary

    df, rename_map, missing_req = map_and_standardize_columns(df)
    summary["column_mappings"] = rename_map

    if missing_req:
        summary["is_valid"] = False
        summary["warnings"].append(f"Missing mandatory columns: {', '.join(missing_req)}")
        return df, summary

    # Parse timestamp safely
    try:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        null_dates = df["timestamp"].isna().sum()
        if null_dates > 0:
            df = df.dropna(subset=["timestamp"])
            summary["warnings"].append(f"Dropped {null_dates} rows with invalid dates.")
    except Exception as e:
        summary["is_valid"] = False
        summary["warnings"].append(f"Date parsing failed: {str(e)}")
        return df, summary

    # Check and remove exact or key duplicates
    key_cols = ["plant_id", "timestamp"] if "plant_id" in df.columns else ["timestamp"]
    initial_len = len(df)
    df = df.drop_duplicates(subset=key_cols, keep="last")
    summary["duplicate_rows_dropped"] = initial_len - len(df)

    # Impute or synthesize missing plant_id / plant_name
    if "plant_id" not in df.columns:
        df["plant_id"] = "SP-UPLOAD"
        df["plant_name"] = "Uploaded Plant"
        summary["imputed_columns"].append("plant_id (defaulted to SP-UPLOAD)")
    elif "plant_name" not in df.columns:
        df["plant_name"] = df["plant_id"].apply(lambda x: f"Plant {x}")

    # Numeric sanitization
    numeric_cols = [
        "actual_generation_kwh", "expected_generation_kwh", "power_kw",
        "temperature_c", "irradiance_wm2", "rainfall_mm", "grid_export_kwh",
        "self_consumption_kwh", "curtailed_energy_kwh", "tariff_inr_per_kwh"
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            null_count = int(df[col].isna().sum())
            if null_count > 0:
                summary["null_counts"][col] = null_count
                # Impute reasonable defaults
                if col in ["actual_generation_kwh", "expected_generation_kwh"]:
                    df[col] = df[col].fillna(0.0)
                elif col in ["rainfall_mm", "curtailed_energy_kwh"]:
                    df[col] = df[col].fillna(0.0)
                elif col == "tariff_inr_per_kwh":
                    df[col] = df[col].fillna(3.20)
                elif col == "temperature_c":
                    df[col] = df[col].fillna(df[col].median() if not df[col].dropna().empty else 28.0)
                elif col == "irradiance_wm2":
                    df[col] = df[col].fillna(df[col].median() if not df[col].dropna().empty else 800.0)
                summary["imputed_columns"].append(col)

    # If expected_generation_kwh is missing, construct benchmark expected based on actual median
    if "expected_generation_kwh" not in df.columns:
        mean_actual = df["actual_generation_kwh"].mean()
        df["expected_generation_kwh"] = df["actual_generation_kwh"].apply(
            lambda x: max(x, mean_actual * 1.08)
        )
        summary["imputed_columns"].append("expected_generation_kwh (modeled +8% benchmark)")

    if "grid_export_kwh" not in df.columns:
        df["grid_export_kwh"] = df["actual_generation_kwh"] * 0.85
    if "self_consumption_kwh" not in df.columns:
        df["self_consumption_kwh"] = df["actual_generation_kwh"] - df["grid_export_kwh"]
    if "tariff_inr_per_kwh" not in df.columns:
        df["tariff_inr_per_kwh"] = 3.20
    if "inverter_status" not in df.columns:
        df["inverter_status"] = "Normal"
    if "soiling_ratio" not in df.columns:
        df["soiling_ratio"] = 0.96

    df["data_source"] = "UPLOADED"
    summary["final_rows"] = len(df)
    return df, summary
