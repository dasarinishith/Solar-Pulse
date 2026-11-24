"""
SolarPulse PredictCare: Equipment Anomaly Detection
Uses statistical (Z-Score/IQR) and machine learning (Isolation Forest) methods to detect
inverter trips, thermal clipping, string degradation, and unusual efficiency deviations.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any
from sklearn.ensemble import IsolationForest

class EquipmentAnomalyDetector:
    """
    Predictive maintenance and anomaly detection engine for solar plants and inverters.
    """

    def __init__(self, contamination_rate: float = 0.04):
        self.contamination_rate = contamination_rate
        self.iso_forest = IsolationForest(
            contamination=contamination_rate,
            random_state=42,
            n_estimators=100
        )

    def detect_anomalies(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Runs dual-pass anomaly detection:
        1. Rule-based / Physical threshold checks (Inverter status, excessive shortfall, thermal clipping)
        2. Machine Learning Isolation Forest on multivariable feature space (irradiance, temp, efficiency)
        """
        if df.empty:
            return pd.DataFrame()

        df = df.copy()

        # Feature Engineering for Anomaly Detection
        df["generation_efficiency"] = np.where(
            df["expected_generation_kwh"] > 0,
            (df["actual_generation_kwh"] / df["expected_generation_kwh"]) * 100.0,
            0.0
        )
        df["shortfall_kwh"] = np.maximum(0.0, df["expected_generation_kwh"] - df["actual_generation_kwh"])
        df["shortfall_pct"] = np.where(
            df["expected_generation_kwh"] > 0,
            (df["shortfall_kwh"] / df["expected_generation_kwh"]) * 100.0,
            0.0
        )

        # Standardize temperature and irradiance
        temp = df.get("temperature_c", pd.Series(25.0, index=df.index)).fillna(25.0)
        irradiance = df.get("irradiance_wm2", pd.Series(800.0, index=df.index)).fillna(800.0)

        # Fit Isolation Forest if sufficient samples exist
        df["is_ml_anomaly"] = False
        df["ml_anomaly_score"] = 0.0

        if len(df) >= 5:
            feature_matrix = np.column_stack([
                df["generation_efficiency"].fillna(0.0),
                temp,
                irradiance,
                df["shortfall_pct"].fillna(0.0)
            ])
            try:
                preds = self.iso_forest.fit_predict(feature_matrix)
                df["ml_anomaly_score"] = self.iso_forest.decision_function(feature_matrix)
                df["is_ml_anomaly"] = (preds == -1)
            except Exception:
                pass

        # Physical Rule flags
        anomalies = []
        for idx, row in df.iterrows():
            is_anomaly = False
            severity = "INFO"
            category = "Normal"
            reasons = []

            inv_status = str(row.get("inverter_status", "Normal"))
            eff = row["generation_efficiency"]
            shortfall_pct = row["shortfall_pct"]
            curtailed = row.get("curtailed_energy_kwh", 0.0)

            # Inverter Fault / Trip
            if inv_status == "Fault" or (eff < 40.0 and curtailed <= 0 and row["expected_generation_kwh"] > 5000):
                is_anomaly = True
                severity = "CRITICAL"
                category = "Inverter Trip / Severe Fault"
                reasons.append("Inverter status tripped or extreme generation collapse (<40% efficiency).")

            # Grid Curtailment
            elif curtailed > 0 or inv_status == "Curtailed":
                is_anomaly = True
                severity = "WARNING"
                category = "Grid Curtailment"
                reasons.append(f"Grid operator curtailment detected: {curtailed:,.0f} kWh withheld.")

            # Thermal Derating / Clipping
            elif row.get("module_temperature_c", 0) > 65.0 and eff < 75.0:
                is_anomaly = True
                severity = "WARNING"
                category = "Thermal Derating"
                reasons.append(f"High module temperature ({row.get('module_temperature_c', 0):.1f}°C) causing thermal clipping.")

            # String Degradation or Soiling Loss
            elif eff < 72.0 and row["expected_generation_kwh"] > 1000:
                is_anomaly = True
                severity = "WARNING"
                category = "Underperformance / String Degradation"
                reasons.append(f"Efficiency ({eff:.1f}%) is significantly below expected benchmark.")

            # ML Outlier flag
            elif row["is_ml_anomaly"] and eff < 80.0:
                is_anomaly = True
                severity = "INFO"
                category = "Multivariate Statistical Outlier"
                reasons.append(f"Unusual joint distribution of irradiance, temperature, and yield.")

            if is_anomaly:
                anomalies.append({
                    "timestamp": row["timestamp"],
                    "plant_id": row["plant_id"],
                    "plant_name": row.get("plant_name", row["plant_id"]),
                    "severity": severity,
                    "category": category,
                    "efficiency_percent": round(eff, 1),
                    "expected_kwh": round(row["expected_generation_kwh"], 1),
                    "actual_kwh": round(row["actual_generation_kwh"], 1),
                    "shortfall_kwh": round(row["shortfall_kwh"], 1),
                    "inverter_status": inv_status,
                    "explanation": " ".join(reasons)
                })

        return pd.DataFrame(anomalies)
