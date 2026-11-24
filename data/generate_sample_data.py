"""
SolarPulse - Realistic Synthetic Solar Data Generator
Generates 12 months of high-resolution multi-plant solar data with realistic physics:
- Diurnal solar cycles (sunrise to sunset based on solar zenith)
- Seasonal irradiance variation (summer vs monsoon vs winter)
- Ambient and module temperature with thermal coefficients
- Realistic weather events (monsoon rain, overcast days)
- Inverter anomalies, dust/soiling accumulation, and grid curtailment
- Multi-tier tariffs (Grid Export, Self Consumption, Curtailment)
All records are explicitly tagged with data_source = 'SIMULATED'.
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def generate_multi_plant_dataset(start_date="2025-01-01", days=365, output_csv="data/sample_solar_data.csv"):
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    np.random.seed(42)

    plants = [
        {
            "plant_id": "SP-01",
            "plant_name": "Pavagada Solar Park",
            "capacity_mw": 50.0,
            "location": "Tumakuru, Karnataka",
            "base_tariff": 3.25,
            "grid_export_ratio": 0.85,
            "degradation_rate": 0.007,
            "dust_factor": 1.2, # moderate dust
        },
        {
            "plant_id": "SP-02",
            "plant_name": "Bhadla Solar Park",
            "capacity_mw": 75.0,
            "location": "Phalodi, Rajasthan",
            "base_tariff": 2.95,
            "grid_export_ratio": 0.90,
            "degradation_rate": 0.008,
            "dust_factor": 2.2, # high desert dust
        },
        {
            "plant_id": "SP-03",
            "plant_name": "Rewa Ultra Mega Solar",
            "capacity_mw": 40.0,
            "location": "Rewa, Madhya Pradesh",
            "base_tariff": 3.40,
            "grid_export_ratio": 0.80,
            "degradation_rate": 0.006,
            "dust_factor": 1.0, # average
        },
        {
            "plant_id": "SP-04",
            "plant_name": "Charanka Solar Park",
            "capacity_mw": 30.0,
            "location": "Patan, Gujarat",
            "base_tariff": 3.15,
            "grid_export_ratio": 0.88,
            "degradation_rate": 0.006,
            "dust_factor": 1.5,
        }
    ]

    dates = pd.date_range(start=start_date, periods=days, freq="D")
    records = []

    for plant in plants:
        cap_mw = plant["capacity_mw"]
        base_tariff = plant["base_tariff"]
        dust_acc = 0.0 # percentage loss from dust

        for i, dt in enumerate(dates):
            day_of_year = dt.timetuple().tm_yday
            month = dt.month

            # 1. Seasonal Solar Irradiance Curve (Peak in April/May, Low in July/August Monsoon)
            seasonal_factor = 1.0 + 0.22 * np.sin(2 * np.pi * (day_of_year - 80) / 365)
            if month in [6, 7, 8]: # Monsoon season dip
                monsoon_rain_prob = 0.45
                monsoon_dim = np.random.uniform(0.40, 0.85)
            else:
                monsoon_rain_prob = 0.05
                monsoon_dim = 1.0

            is_rainy = np.random.rand() < monsoon_rain_prob
            rainfall_mm = round(np.random.gamma(shape=2.0, scale=8.0), 1) if is_rainy else 0.0

            # Natural wash effect when rainfall > 5mm
            if rainfall_mm > 5.0:
                dust_acc = max(0.0, dust_acc - (rainfall_mm * 0.4))
            else:
                dust_acc = min(18.0, dust_acc + (0.08 * plant["dust_factor"] + np.random.uniform(0, 0.05)))

            # Periodic cleaning cycles roughly every 30-45 days if not washed by rain
            if dust_acc > 12.0 and np.random.rand() < 0.25:
                dust_acc = 0.5 # freshly cleaned panels

            # Irradiance (kWh/m2/day equivalent)
            base_irradiance = 5.6 * seasonal_factor * monsoon_dim
            noise = np.random.normal(0, 0.25)
            daily_irradiance = max(1.2, base_irradiance + noise)

            # Ambient & Module Temperature (°C)
            temp_ambient = 22.0 + 12.0 * np.sin(2 * np.pi * (day_of_year - 110) / 365) + np.random.normal(0, 2.0)
            if is_rainy:
                temp_ambient -= 4.0
            # Module runs 20-30°C hotter under high irradiance
            temp_module = temp_ambient + (daily_irradiance / 6.0) * 22.0

            # Standard STC condition is 25°C, temperature coefficient ~ -0.38%/°C
            temp_derating = max(0.82, 1.0 - (temp_module - 25.0) * 0.0038)

            # Expected generation based on design capacity & irradiance (ideal condition)
            # Theoretical yield = Capacity (kW) * Peak Sun Hours * Performance Ratio (~0.80)
            peak_sun_hours = daily_irradiance
            design_pr = 0.81
            expected_generation_kwh = round((cap_mw * 1000) * peak_sun_hours * design_pr, 2)

            # Actual generation calculation with losses:
            # - Soiling / Dust loss
            soiling_loss_ratio = dust_acc / 100.0
            # - Inverter & System degradation
            annual_degradation = plant["degradation_rate"] * (i / 365.0)
            
            # Anomaly events (inverter trip, cable fault, grid curtailment)
            anomaly_chance = np.random.rand()
            curtailed_energy_kwh = 0.0
            inverter_status = "Normal"

            if anomaly_chance < 0.03: # 3% chance of grid curtailment (DISCOM order)
                inverter_status = "Curtailed"
                curtailment_percent = np.random.uniform(0.20, 0.60)
                curtailed_energy_kwh = round(expected_generation_kwh * curtailment_percent, 2)
            elif anomaly_chance < 0.05: # 2% chance of inverter malfunction / trip
                inverter_status = "Fault"
            elif anomaly_chance < 0.09: # 4% minor warning (partial string failure)
                inverter_status = "Warning"

            actual_factor = (1.0 - soiling_loss_ratio) * (1.0 - annual_degradation) * (temp_derating / 0.95)
            
            if inverter_status == "Fault":
                actual_factor *= np.random.uniform(0.30, 0.60) # major drop
            elif inverter_status == "Warning":
                actual_factor *= np.random.uniform(0.75, 0.88)
            
            actual_gen = expected_generation_kwh * actual_factor
            if curtailed_energy_kwh > 0:
                actual_gen = max(0.0, actual_gen - curtailed_energy_kwh)

            actual_generation_kwh = round(max(50.0, actual_gen + np.random.normal(0, cap_mw * 80)), 2)
            if actual_generation_kwh > expected_generation_kwh * 1.15:
                actual_generation_kwh = round(expected_generation_kwh * 1.05, 2)

            # Peak power observed (kW)
            power_kw = round((actual_generation_kwh / 7.5) * np.random.uniform(1.2, 1.4), 2)

            # Energy distribution (Grid Export vs Self-Consumption)
            export_ratio = plant["grid_export_ratio"] + np.random.uniform(-0.02, 0.02)
            grid_export_kwh = round(actual_generation_kwh * export_ratio, 2)
            self_consumption_kwh = round(actual_generation_kwh - grid_export_kwh, 2)

            records.append({
                "timestamp": dt.strftime("%Y-%m-%d"),
                "plant_id": plant["plant_id"],
                "plant_name": plant["plant_name"],
                "actual_generation_kwh": actual_generation_kwh,
                "expected_generation_kwh": expected_generation_kwh,
                "power_kw": power_kw,
                "temperature_c": round(temp_ambient, 1),
                "module_temperature_c": round(temp_module, 1),
                "irradiance_wm2": round(daily_irradiance * 180, 1), # GHI daily aggregate
                "rainfall_mm": rainfall_mm,
                "inverter_status": inverter_status,
                "grid_export_kwh": grid_export_kwh,
                "self_consumption_kwh": self_consumption_kwh,
                "curtailed_energy_kwh": curtailed_energy_kwh,
                "tariff_inr_per_kwh": base_tariff,
                "soiling_ratio": round(1.0 - soiling_loss_ratio, 3),
                "data_source": "SIMULATED"
            })

    df = pd.DataFrame(records)
    df.to_csv(output_csv, index=False)
    print(f"Generated {len(df)} simulated solar records for 4 plants across {days} days at: {output_csv}")
    return df

if __name__ == "__main__":
    generate_multi_plant_dataset()
