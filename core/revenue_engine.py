"""
SolarPulse Revenue Intelligence Engine
Specialized financial computations for renewable energy plants:
- Multi-tier tariffs (Grid Export vs Self Consumption vs PPA)
- Generation loss monetization & shortfall financial impact
- Monthly, quarterly, and annual financial estimations
- Invoiced vs Collected projections with payment collection efficiencies
- Tariff sensitivity models
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

class RevenueEngine:
    """
    Financial engine for calculating solar energy revenue and monetized losses.
    """

    def __init__(self, default_export_tariff: float = 3.20, default_self_tariff: float = 4.50):
        self.default_export_tariff = default_export_tariff
        self.default_self_tariff = default_self_tariff

    def calculate_revenue_for_dataframe(
        self,
        df: pd.DataFrame,
        tariff_mapping: Optional[Dict[str, float]] = None
    ) -> pd.DataFrame:
        """
        Enriches a generation DataFrame with detailed financial calculations:
        - estimated_export_revenue_inr
        - estimated_self_revenue_inr
        - total_estimated_revenue_inr
        - expected_revenue_inr
        - revenue_shortfall_inr
        - curtailment_revenue_loss_inr
        """
        if df.empty:
            return df

        df = df.copy()

        # Determine effective tariff per row
        if tariff_mapping:
            df["effective_tariff"] = df["plant_id"].map(tariff_mapping).fillna(
                df.get("tariff_inr_per_kwh", self.default_export_tariff)
            )
        elif "tariff_inr_per_kwh" in df.columns:
            df["effective_tariff"] = df["tariff_inr_per_kwh"].fillna(self.default_export_tariff)
        else:
            df["effective_tariff"] = self.default_export_tariff

        # Energy streams
        export_kwh = df.get("grid_export_kwh", df["actual_generation_kwh"] * 0.85)
        self_kwh = df.get("self_consumption_kwh", df["actual_generation_kwh"] - export_kwh)
        curtailed_kwh = df.get("curtailed_energy_kwh", 0.0)

        # Self-consumption usually saves industrial commercial retail tariffs (~4.5 - 6.5 INR/kWh)
        self_tariff = np.maximum(df["effective_tariff"] * 1.35, self.default_self_tariff)

        df["estimated_export_revenue_inr"] = export_kwh * df["effective_tariff"]
        df["estimated_self_revenue_inr"] = self_kwh * self_tariff
        df["total_estimated_revenue_inr"] = df["estimated_export_revenue_inr"] + df["estimated_self_revenue_inr"]

        # Expected revenue if plant operated at 100% expected generation
        df["expected_revenue_inr"] = df["expected_generation_kwh"] * df["effective_tariff"]

        # Financial shortfall: Loss due to underperformance
        shortfall_kwh = np.maximum(0.0, df["expected_generation_kwh"] - df["actual_generation_kwh"])
        df["revenue_shortfall_inr"] = shortfall_kwh * df["effective_tariff"]

        # Revenue lost specifically due to grid curtailment orders
        df["curtailment_revenue_loss_inr"] = curtailed_kwh * df["effective_tariff"]

        return df

    def summarize_financials(self, df: pd.DataFrame, collection_rate: float = 0.965) -> Dict[str, Any]:
        """
        Aggregates financial KPIs with assumptions clearly declared.
        """
        if df.empty or "total_estimated_revenue_inr" not in df.columns:
            df = self.calculate_revenue_for_dataframe(df)

        if df.empty:
            return {
                "total_estimated_revenue_inr": 0.0,
                "export_revenue_inr": 0.0,
                "self_consumption_value_inr": 0.0,
                "expected_revenue_inr": 0.0,
                "total_revenue_shortfall_inr": 0.0,
                "curtailment_financial_loss_inr": 0.0,
                "projected_collected_revenue_inr": 0.0,
                "avg_revenue_per_kwh_inr": 0.0,
                "collection_efficiency_assumed": collection_rate * 100.0,
            }

        total_est = float(df["total_estimated_revenue_inr"].sum())
        export_rev = float(df["estimated_export_revenue_inr"].sum())
        self_rev = float(df["estimated_self_revenue_inr"].sum())
        exp_rev = float(df["expected_revenue_inr"].sum())
        rev_shortfall = float(df["revenue_shortfall_inr"].sum())
        curtailment_loss = float(df["curtailment_revenue_loss_inr"].sum())
        
        # Invoiced vs Collected logic
        projected_collected = total_est * collection_rate

        actual_gen_total = float(df["actual_generation_kwh"].sum())
        avg_realized_tariff = total_est / actual_gen_total if actual_gen_total > 0 else 0.0

        return {
            "total_estimated_revenue_inr": round(total_est, 2),
            "export_revenue_inr": round(export_rev, 2),
            "self_consumption_value_inr": round(self_rev, 2),
            "expected_revenue_inr": round(exp_rev, 2),
            "total_revenue_shortfall_inr": round(rev_shortfall, 2),
            "curtailment_financial_loss_inr": round(curtailment_loss, 2),
            "projected_collected_revenue_inr": round(projected_collected, 2),
            "avg_revenue_per_kwh_inr": round(avg_realized_tariff, 2),
            "collection_efficiency_assumed": round(collection_rate * 100.0, 1),
        }

    def simulate_tariff_sensitivity(self, df: pd.DataFrame, delta_percentages: list = [-15, -10, -5, 0, 5, 10, 15]) -> pd.DataFrame:
        """
        Runs sensitivity analysis showing impact of tariff shifts on annual/monthly revenue.
        """
        if df.empty:
            return pd.DataFrame()

        base_summary = self.summarize_financials(df)
        base_revenue = base_summary["total_estimated_revenue_inr"]

        results = []
        for pct in delta_percentages:
            multiplier = 1.0 + (pct / 100.0)
            adjusted_revenue = base_revenue * multiplier
            diff = adjusted_revenue - base_revenue
            results.append({
                "Tariff Adjustment (%)": f"{'+' if pct > 0 else ''}{pct}%",
                "Estimated Total Revenue (₹)": round(adjusted_revenue, 2),
                "Variance from Baseline (₹)": round(diff, 2)
            })

        return pd.DataFrame(results)
