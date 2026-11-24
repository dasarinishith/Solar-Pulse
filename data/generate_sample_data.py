"""
SolarPulse - Realistic Synthetic Solar Data Generator
Generates:
1. 12 months (365 days) of daily historical multi-plant solar data.
2. High-resolution 15-minute interval readings for recent days covering:
   - Multiple solar plants & multiple inverters per plant
   - Morning ramp-up (06:00-10:00), peak (11:30-13:30), evening decline (15:30-18:30), night standby
   - AC power, DC power, AC voltage (415V), DC voltage (650-750V), current, ambient and module temp
   - Inverter faults (trips) and occasional communication lost gaps (comm_status = 'COMM_LOST')
All records are explicitly tagged as data_source = 'SIMULATED'.
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

PLANTS_CONFIG = [
    {
        "plant_id": "SP-01",
        "plant_name": "Pavagada Solar Park",
        "capacity_mw": 50.0,
        "location": "Tumakuru, Karnataka",
        "base_tariff": 3.25,
        "grid_export_ratio": 0.85,
        "inverter_ids": ["INV-01", "INV-02", "INV-03", "INV-04"],
        "inverter_capacity_kw": 12500.0,
        "dust_factor": 1.2
    },
    {
        "plant_id": "SP-02",
        "plant_name": "Bhadla Solar Park",
        "capacity_mw": 75.0,
        "location": "Phalodi, Rajasthan",
        "base_tariff": 2.95,
        "grid_export_ratio": 0.90,
        "inverter_ids": ["INV-01", "INV-02", "INV-03", "INV-04", "INV-05", "INV-06"],
        "inverter_capacity_kw": 12500.0,
        "dust_factor": 2.2
    },
    {
        "plant_id": "SP-03",
        "plant_name": "Rewa Ultra Mega Solar",
        "capacity_mw": 40.0,
        "location": "Rewa, Madhya Pradesh",
        "base_tariff": 3.40,
        "grid_export_ratio": 0.80,
        "inverter_ids": ["INV-01", "INV-02", "INV-03", "INV-04"],
        "inverter_capacity_kw": 10000.0,
        "dust_factor": 1.0
    },
    {
        "plant_id": "SP-04",
        "plant_name": "Charanka Solar Park",
        "capacity_mw": 30.0,
        "location": "Patan, Gujarat",
        "base_tariff": 3.15,
        "grid_export_ratio": 0.88,
        "inverter_ids": ["INV-01", "INV-02", "INV-03"],
        "inverter_capacity_kw": 10000.0,
        "dust_factor": 1.5
    }
]

def generate_daily_dataset(start_date="2025-01-01", days=365):
    """Generates 365 days of plant-level daily records."""
    np.random.seed(42)
    dates = pd.date_range(start=start_date, periods=days, freq="D")
    records = []

    for plant in PLANTS_CONFIG:
        cap_mw = plant["capacity_mw"]
        base_tariff = plant["base_tariff"]
        dust_acc = 0.0

        for i, dt in enumerate(dates):
            doy = dt.timetuple().tm_yday
            month = dt.month

            seasonal_factor = 1.0 + 0.22 * np.sin(2 * np.pi * (doy - 80) / 365)
            is_monsoon = month in [6, 7, 8]
            monsoon_rain_prob = 0.45 if is_monsoon else 0.05
            monsoon_dim = np.random.uniform(0.40, 0.85) if is_monsoon else 1.0

            is_rainy = np.random.rand() < monsoon_rain_prob
            rainfall_mm = round(float(np.random.gamma(shape=2.0, scale=8.0)), 1) if is_rainy else 0.0

            if rainfall_mm > 5.0:
                dust_acc = max(0.0, dust_acc - (rainfall_mm * 0.4))
            else:
                dust_acc = min(18.0, dust_acc + (0.08 * plant["dust_factor"] + np.random.uniform(0, 0.05)))

            if dust_acc > 12.0 and np.random.rand() < 0.25:
                dust_acc = 0.5

            base_irradiance = 5.6 * seasonal_factor * monsoon_dim
            daily_irradiance = max(1.2, base_irradiance + np.random.normal(0, 0.25))

            temp_ambient = 22.0 + 12.0 * np.sin(2 * np.pi * (doy - 110) / 365) + np.random.normal(0, 2.0)
            if is_rainy:
                temp_ambient -= 4.0
            temp_module = temp_ambient + (daily_irradiance / 6.0) * 22.0
            temp_derating = max(0.82, 1.0 - (temp_module - 25.0) * 0.0038)

            peak_sun_hours = daily_irradiance
            design_pr = 0.81
            expected_generation_kwh = round((cap_mw * 1000) * peak_sun_hours * design_pr, 2)

            soiling_loss_ratio = dust_acc / 100.0
            annual_degradation = 0.007 * (i / 365.0)

            anomaly_chance = np.random.rand()
            curtailed_energy_kwh = 0.0
            inverter_status = "Normal"

            if anomaly_chance < 0.03:
                inverter_status = "Curtailed"
                curtailed_energy_kwh = round(expected_generation_kwh * np.random.uniform(0.20, 0.60), 2)
            elif anomaly_chance < 0.05:
                inverter_status = "Fault"
            elif anomaly_chance < 0.09:
                inverter_status = "Warning"

            actual_factor = (1.0 - soiling_loss_ratio) * (1.0 - annual_degradation) * (temp_derating / 0.95)
            if inverter_status == "Fault":
                actual_factor *= np.random.uniform(0.30, 0.60)
            elif inverter_status == "Warning":
                actual_factor *= np.random.uniform(0.75, 0.88)

            actual_gen = expected_generation_kwh * actual_factor
            if curtailed_energy_kwh > 0:
                actual_gen = max(0.0, actual_gen - curtailed_energy_kwh)

            actual_generation_kwh = round(max(50.0, actual_gen + np.random.normal(0, cap_mw * 80)), 2)
            if actual_generation_kwh > expected_generation_kwh * 1.15:
                actual_generation_kwh = round(expected_generation_kwh * 1.05, 2)

            power_kw = round((actual_generation_kwh / 7.5) * np.random.uniform(1.2, 1.4), 2)
            dc_power_kw = round(power_kw / 0.98, 2)

            export_ratio = plant["grid_export_ratio"] + np.random.uniform(-0.02, 0.02)
            grid_export_kwh = round(actual_generation_kwh * export_ratio, 2)
            self_consumption_kwh = round(actual_generation_kwh - grid_export_kwh, 2)

            records.append({
                "timestamp": dt.strftime("%Y-%m-%d 00:00:00"),
                "plant_id": plant["plant_id"],
                "plant_name": plant["plant_name"],
                "inverter_id": "CENTRAL",
                "actual_generation_kwh": actual_generation_kwh,
                "expected_generation_kwh": expected_generation_kwh,
                "power_kw": power_kw,
                "dc_power_kw": dc_power_kw,
                "ac_voltage_v": round(415.0 + np.random.normal(0, 3.0), 1),
                "dc_voltage_v": round(720.0 + np.random.normal(0, 8.0), 1),
                "current_a": round((power_kw * 1000) / (415.0 * 1.732 * 0.95), 1) if power_kw > 0 else 0.0,
                "temperature_c": round(temp_ambient, 1),
                "module_temperature_c": round(temp_module, 1),
                "irradiance_wm2": round(daily_irradiance * 180, 1),
                "rainfall_mm": rainfall_mm,
                "inverter_status": inverter_status,
                "comm_status": "ONLINE",
                "grid_export_kwh": grid_export_kwh,
                "self_consumption_kwh": self_consumption_kwh,
                "curtailed_energy_kwh": curtailed_energy_kwh,
                "tariff_inr_per_kwh": base_tariff,
                "soiling_ratio": round(1.0 - soiling_loss_ratio, 3),
                "is_interval_15m": False,
                "data_source": "SIMULATED"
            })

    return pd.DataFrame(records)

def generate_15min_interval_dataset(days_back=7, end_date="2025-12-31"):
    """
    Generates 15-minute sub-daily intervals for each inverter in each plant.
    Captures:
    - 06:00 - 10:00 Morning ramp-up
    - 11:30 - 13:30 Afternoon peak
    - 15:30 - 18:30 Evening decline
    - 19:00 - 05:45 Night standby (zero generation)
    - Realistic inverter faults and communication lost gaps (comm_status='COMM_LOST')
    """
    np.random.seed(42)
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    start_dt = end_dt - timedelta(days=days_back)
    
    interval_range = pd.date_range(start=start_dt, end=end_dt + timedelta(days=1), freq="15min", inclusive="left")
    records = []

    for plant in PLANTS_CONFIG:
        for inv_id in plant["inverter_ids"]:
            inv_cap_kw = plant["inverter_capacity_kw"]
            
            # Seed specific intermittent fault days for demonstration
            fault_hours_set = {(2, 13), (4, 11)} # day 2 at 13h, day 4 at 11h
            comm_gap_set = {(3, 14), (5, 9)} # comm timeout gap

            for dt in interval_range:
                hour = dt.hour + (dt.minute / 60.0)
                day_offset = (dt - start_dt).days

                # Diurnal Curve (Solar zenith model)
                if 6.0 <= hour <= 18.5:
                    # Solar curve from 0 at 6am to peak at 12:30pm to 0 at 6:30pm
                    sun_angle = np.sin((hour - 6.0) / 12.5 * np.pi)
                    # Add cloud variance
                    cloud_noise = np.random.normal(0, 0.05)
                    poa_irradiance = max(0.0, float(sun_angle * 1000.0 + cloud_noise * 150))
                    
                    ambient_t = 24.0 + 10.0 * np.sin((hour - 8.0) / 12.0 * np.pi)
                    module_t = ambient_t + (poa_irradiance / 1000.0) * 28.0
                    temp_derate = max(0.85, 1.0 - (module_t - 25.0) * 0.0038)
                    
                    # Ideal expected generation for this 15-min block (0.25h)
                    expected_kw = inv_cap_kw * (poa_irradiance / 1000.0) * 0.82
                    expected_kwh = expected_kw * 0.25

                    # Anomaly injection
                    inv_status = "Normal"
                    comm_status = "ONLINE"
                    actual_kw = expected_kw * temp_derate * np.random.uniform(0.96, 1.01)

                    if (day_offset, int(hour)) in fault_hours_set and inv_id == "INV-02":
                        inv_status = "Fault"
                        actual_kw = 0.0 # tripped

                    elif (day_offset, int(hour)) in comm_gap_set and inv_id == "INV-01":
                        comm_status = "COMM_LOST"
                        actual_kw = 0.0 # telemetry packet drop

                    elif np.random.rand() < 0.015:
                        inv_status = "Warning" # thermal clipping
                        actual_kw *= 0.78

                    ac_power_kw = round(max(0.0, actual_kw), 2)
                    dc_power_kw = round(ac_power_kw / 0.982, 2) if ac_power_kw > 0 else 0.0
                    actual_kwh = round(ac_power_kw * 0.25, 2)
                    ac_volt = round(415.0 + np.random.normal(0, 2.5), 1) if ac_power_kw > 0 else 415.0
                    dc_volt = round(680.0 + (sun_angle * 80.0) + np.random.normal(0, 5.0), 1) if ac_power_kw > 0 else 0.0
                    current_a = round((ac_power_kw * 1000) / (ac_volt * 1.732 * 0.95), 1) if ac_power_kw > 0 else 0.0

                else:
                    # Night Standby
                    poa_irradiance = 0.0
                    ambient_t = 19.5 + np.random.normal(0, 0.5)
                    module_t = ambient_t
                    expected_kw = 0.0
                    expected_kwh = 0.0
                    ac_power_kw = 0.0
                    dc_power_kw = 0.0
                    actual_kwh = 0.0
                    ac_volt = 415.0
                    dc_volt = 0.0
                    current_a = 0.0
                    inv_status = "Standby"
                    comm_status = "ONLINE"

                records.append({
                    "timestamp": dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "plant_id": plant["plant_id"],
                    "plant_name": plant["plant_name"],
                    "inverter_id": inv_id,
                    "actual_generation_kwh": actual_kwh,
                    "expected_generation_kwh": round(expected_kwh, 2),
                    "power_kw": ac_power_kw,
                    "dc_power_kw": dc_power_kw,
                    "ac_voltage_v": ac_volt,
                    "dc_voltage_v": dc_volt,
                    "current_a": current_a,
                    "temperature_c": round(ambient_t, 1),
                    "module_temperature_c": round(module_t, 1),
                    "irradiance_wm2": round(poa_irradiance, 1),
                    "rainfall_mm": 0.0,
                    "inverter_status": inv_status,
                    "comm_status": comm_status,
                    "grid_export_kwh": round(actual_kwh * 0.88, 2),
                    "self_consumption_kwh": round(actual_kwh * 0.12, 2),
                    "curtailed_energy_kwh": 0.0,
                    "tariff_inr_per_kwh": plant["base_tariff"],
                    "soiling_ratio": 0.97,
                    "is_interval_15m": True,
                    "data_source": "SIMULATED"
                })

    return pd.DataFrame(records)

def generate_multi_plant_dataset(output_csv="data/sample_solar_data.csv", include_15min=True):
    """Generates and bundles both daily historical and 15-minute interval readings."""
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    
    daily_df = generate_daily_dataset()
    if include_15min:
        interval_df = generate_15min_interval_dataset(days_back=7)
        combined_df = pd.concat([daily_df, interval_df], ignore_index=True)
    else:
        combined_df = daily_df

    combined_df.to_csv(output_csv, index=False)
    print(f"Generated {len(combined_df)} records (Daily: {len(daily_df)}, 15-min: {len(combined_df)-len(daily_df)}) at {output_csv}")
    return combined_df

if __name__ == "__main__":
    generate_multi_plant_dataset()
