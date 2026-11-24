"""
SolarPulse Core Calculations
Rigorous, zero-division safe engineering and analytics formulas for solar energy plants.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Union

def calculate_efficiency(actual: Union[float, pd.Series], expected: Union[float, pd.Series]) -> Union[float, pd.Series]:
    """
    Calculates Generation Efficiency percentage: (actual / expected) * 100
    Guards against zero-division and missing values.
    """
    if isinstance(actual, pd.Series) or isinstance(expected, pd.Series):
        expected_safe = np.where(expected <= 0, np.nan, expected)
        eff = (actual / expected_safe) * 100.0
        return np.clip(np.nan_to_num(eff, nan=0.0), 0.0, 200.0)
    
    if expected is None or expected <= 0:
        return 0.0
    val = (actual / expected) * 100.0
    return float(np.clip(val, 0.0, 200.0))

def calculate_shortfall(actual: Union[float, pd.Series], expected: Union[float, pd.Series]) -> Union[float, pd.Series]:
    """
    Calculates Generation Shortfall: MAX(expected - actual, 0)
    """
    if isinstance(actual, pd.Series) or isinstance(expected, pd.Series):
        diff = expected - actual
        return np.maximum(0.0, np.nan_to_num(diff, nan=0.0))
    
    if actual is None or expected is None:
        return 0.0
    return float(max(0.0, expected - actual))

def calculate_cuf(generation_kwh: float, capacity_mw: float, hours: float = 24.0) -> float:
    """
    Capacity Utilization Factor (CUF %):
    CUF = (Generation in kWh / (Installed Capacity in kW * Operating Hours)) * 100
    Standard for Indian & International renewable benchmark (typically 18% - 26%).
    """
    capacity_kw = capacity_mw * 1000.0
    max_theoretical = capacity_kw * hours
    if max_theoretical <= 0:
        return 0.0
    cuf = (generation_kwh / max_theoretical) * 100.0
    return float(np.clip(cuf, 0.0, 100.0))

def calculate_performance_ratio(actual_kwh: float, irradiance_wm2: float, capacity_mw: float) -> float:
    """
    Performance Ratio (PR %): IEC 61724 standard definition
    PR = (Actual Yield (kWh/kWp) / Reference Yield (Irradiance / 1000 W/m2)) * 100
    Typically 75% - 84% for well-maintained utility plants.
    """
    capacity_kw = capacity_mw * 1000.0
    if capacity_kw <= 0 or irradiance_wm2 <= 0:
        return 0.0
    
    # Specific yield in kWh/kWp
    specific_yield = actual_kwh / capacity_kw
    # Reference yield in Peak Sun Hours
    ref_yield = irradiance_wm2 / 1000.0
    if ref_yield <= 0:
        return 0.0
    
    pr = (specific_yield / ref_yield) * 100.0
    return float(np.clip(pr, 0.0, 100.0))

def calculate_environmental_metrics(total_kwh: float) -> Dict[str, float]:
    """
    Calculates environmental impacts:
    - CO2 emissions offset (CEA baseline in India: ~0.82 kg CO2 / kWh)
    - Equivalent mature trees planted (~21.77 kg CO2 / tree / year)
    - Standard passenger vehicles removed equivalent (~4.6 metric tons CO2 / vehicle / year)
    """
    co2_kg = total_kwh * 0.82
    co2_tonnes = co2_kg / 1000.0
    trees_equivalent = co2_kg / 21.77
    vehicles_avoided = co2_tonnes / 4.6

    return {
        "co2_offset_tonnes": round(co2_tonnes, 2),
        "trees_equivalent": int(trees_equivalent),
        "vehicles_avoided": round(vehicles_avoided, 1)
    }

def summarize_generation_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Aggregates full summary dictionary from a filtered generation DataFrame.
    """
    if df.empty:
        return {
            "total_actual_kwh": 0.0,
            "total_expected_kwh": 0.0,
            "avg_daily_kwh": 0.0,
            "overall_efficiency": 0.0,
            "total_shortfall_kwh": 0.0,
            "total_curtailed_kwh": 0.0,
            "total_export_kwh": 0.0,
            "total_self_consumed_kwh": 0.0,
            "record_count": 0
        }

    actual_sum = float(df["actual_generation_kwh"].sum())
    expected_sum = float(df["expected_generation_kwh"].sum())
    
    # Calculate shortfall safely per-row
    shortfalls = np.maximum(0.0, df["expected_generation_kwh"] - df["actual_generation_kwh"])
    total_shortfall = float(shortfalls.sum())
    
    efficiency = calculate_efficiency(actual_sum, expected_sum)
    days_count = max(1, df["timestamp"].nunique())
    avg_daily = actual_sum / days_count

    curtailed_sum = float(df["curtailed_energy_kwh"].sum()) if "curtailed_energy_kwh" in df.columns else 0.0
    export_sum = float(df["grid_export_kwh"].sum()) if "grid_export_kwh" in df.columns else actual_sum * 0.85
    self_consumed_sum = float(df["self_consumption_kwh"].sum()) if "self_consumption_kwh" in df.columns else actual_sum - export_sum

    return {
        "total_actual_kwh": round(actual_sum, 2),
        "total_expected_kwh": round(expected_sum, 2),
        "avg_daily_kwh": round(avg_daily, 2),
        "overall_efficiency": round(efficiency, 2),
        "total_shortfall_kwh": round(total_shortfall, 2),
        "total_curtailed_kwh": round(curtailed_sum, 2),
        "total_export_kwh": round(export_sum, 2),
        "total_self_consumed_kwh": round(self_consumed_sum, 2),
        "record_count": len(df)
    }
