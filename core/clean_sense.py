"""
SolarPulse CleanSense: Solar Panel Soiling & Cleaning Analytics
Identifies panel dusting trends, rainfall natural wash events, soiling ratios,
and estimates generation and financial recovery achievable through panel cleaning.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List

class CleanSense:
    """
    Analytics engine for solar panel soiling degradation and cleaning schedule optimization.
    """

    def __init__(self, cleaning_cost_per_mw_inr: float = 6500.0):
        # Average utility panel water/robotic cleaning cost per MW in India ~ ₹5,000 - ₹8,000
        self.cleaning_cost_per_mw = cleaning_cost_per_mw_inr

    def analyze_plant_soiling(self, df: pd.DataFrame, plant_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyzes a single plant's generation trend for soiling losses.
        """
        if df.empty:
            return {"status": "NO_DATA"}

        df = df.sort_values("timestamp").copy()

        # Soiling ratio calculation or approximation
        # If soiling_ratio not directly measured, estimate from PR trend relative to clear-sky
        if "soiling_ratio" in df.columns and df["soiling_ratio"].notna().any():
            current_soiling_ratio = float(df["soiling_ratio"].iloc[-7:].mean())
        else:
            # Estimate from recent efficiency drop relative to top 90th percentile
            eff = (df["actual_generation_kwh"] / df["expected_generation_kwh"].replace(0, np.nan)) * 100
            rolling_eff = eff.rolling(window=14, min_periods=3).mean()
            max_eff = float(eff.quantile(0.92))
            recent_eff = float(rolling_eff.iloc[-1]) if pd.notna(rolling_eff.iloc[-1]) else float(eff.mean())
            current_soiling_ratio = min(1.0, max(0.80, recent_eff / max_eff if max_eff > 0 else 0.95))

        soiling_loss_percent = max(0.0, (1.0 - current_soiling_ratio) * 100.0)

        # Plant capacity
        cap_mw = plant_metadata.get("capacity_mw", 50.0) if plant_metadata else 50.0
        tariff = plant_metadata.get("default_tariff_inr", 3.20) if plant_metadata else 3.20

        # Estimated recovery
        avg_daily_kwh = float(df["actual_generation_kwh"].iloc[-30:].mean()) if len(df) >= 30 else float(df["actual_generation_kwh"].mean())
        # Recovery = kWh lost due to soiling that cleaning restores
        daily_recovery_kwh = avg_daily_kwh * (soiling_loss_percent / 100.0)
        monthly_recovery_kwh = daily_recovery_kwh * 30.0

        monthly_financial_recovery_inr = monthly_recovery_kwh * tariff
        cleaning_cost_inr = cap_mw * self.cleaning_cost_per_mw
        net_financial_benefit_inr = monthly_financial_recovery_inr - cleaning_cost_inr
        roi_days = round((cleaning_cost_inr / (daily_recovery_kwh * tariff)), 1) if (daily_recovery_kwh * tariff) > 0 else 999.0

        # Rainfall analysis: Natural washing history
        rain_days = df[df["rainfall_mm"] > 5.0] if "rainfall_mm" in df.columns else pd.DataFrame()
        last_rain_date = str(rain_days["timestamp"].iloc[-1].strftime("%Y-%m-%d")) if not rain_days.empty else "No heavy rain in records"

        # Cleaning Priority score (1 - 100)
        # Higher if soiling loss is high and net benefit is positive
        urgency_score = min(100.0, (soiling_loss_percent * 5.5) + (30.0 if net_financial_benefit_inr > 0 else 0.0))

        priority_level = "CRITICAL" if urgency_score > 70 else ("HIGH" if urgency_score > 45 else "ROUTINE")

        return {
            "current_soiling_ratio": round(current_soiling_ratio, 3),
            "soiling_loss_percent": round(soiling_loss_percent, 2),
            "daily_recovery_kwh": round(daily_recovery_kwh, 2),
            "monthly_recovery_kwh": round(monthly_recovery_kwh, 2),
            "monthly_financial_recovery_inr": round(monthly_financial_recovery_inr, 2),
            "cleaning_cost_estimate_inr": round(cleaning_cost_inr, 2),
            "net_monthly_benefit_inr": round(net_financial_benefit_inr, 2),
            "payback_days": roi_days,
            "last_rain_wash_date": last_rain_date,
            "urgency_score": round(urgency_score, 1),
            "priority_level": priority_level,
            "recommendation": (
                f"Schedule cleaning: Payback expected in {roi_days} days. "
                f"Potential monthly net gain: ₹{net_financial_benefit_inr:,.0f}."
                if net_financial_benefit_inr > 0
                else "Cleaning currently not cost-optimal; monitor until soiling exceeds 6%."
            )
        }

    def rank_all_plants_cleaning_priority(self, df: pd.DataFrame, plants_meta: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Ranks all plants in portfolio by cleaning urgency.
        """
        meta_dict = {p["plant_id"]: p for p in plants_meta}
        rankings = []

        for p_id in df["plant_id"].unique():
            plant_df = df[df["plant_id"] == p_id]
            meta = meta_dict.get(p_id, {"plant_id": p_id, "plant_name": p_id, "capacity_mw": 50.0, "default_tariff_inr": 3.20})
            analysis = self.analyze_plant_soiling(plant_df, meta)
            if analysis.get("status") == "NO_DATA":
                continue

            rankings.append({
                "Plant ID": p_id,
                "Plant Name": meta.get("plant_name", p_id),
                "Capacity (MW)": meta.get("capacity_mw", 50.0),
                "Soiling Loss (%)": analysis["soiling_loss_percent"],
                "Daily Recovery (kWh)": analysis["daily_recovery_kwh"],
                "Monthly Financial Recovery (₹)": analysis["monthly_financial_recovery_inr"],
                "Cleaning Cost (₹)": analysis["cleaning_cost_estimate_inr"],
                "Net Benefit (₹)": analysis["net_monthly_benefit_inr"],
                "Payback (Days)": analysis["payback_days"],
                "Priority": analysis["priority_level"],
                "Urgency Score": analysis["urgency_score"]
            })

        res_df = pd.DataFrame(rankings)
        if not res_df.empty:
            res_df = res_df.sort_values("Urgency Score", ascending=False).reset_index(drop=True)
        return res_df
