"""
SolarPulse - Module G: Generation Forecasting (SolarCast)
Machine learning and baseline statistical day-ahead & multi-week generation forecasting,
uncertainty interval estimation, and model performance metrics (MAE, RMSE, MAPE, R²).
Supports active data source filtering (SIMULATED, UPLOADED, API_LIVE).
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from database.operations import load_generation_dataframe
from core.forecasting import SolarForecaster
from components.charts import plot_forecast_with_confidence

def render_solarcast_page(selected_plant: str, start_date, end_date, active_mode: str = "SIMULATED"):
    st.markdown(
        """
        <div class="sp-header-container">
            <div>
                <h1 class="sp-header-title">🔮 SolarCast: Generation Forecasting & Machine Learning</h1>
                <div class="sp-header-subtitle">Weather-aware Random Forest regression, statistical baseline benchmarks, and prediction confidence intervals</div>
            </div>
            <div>
                <span class="sp-badge sp-badge-live">SOLARCAST AI</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    plant_filter = None if selected_plant == "ALL" else selected_plant
    df = load_generation_dataframe(plant_ids=plant_filter, start_date=start_date, end_date=end_date, data_source=active_mode)

    if df.empty or len(df) < 14:
        st.warning(f"Insufficient historical data in **{active_mode}** mode (minimum 14 daily records required) to train forecasting models.")
        return

    col_fc1, col_fc2, col_fc3 = st.columns(3)
    with col_fc1:
        method = st.selectbox("Forecasting Algorithm", options=["ML (Random Forest)", "Statistical Baseline (7-Day MA)"], index=0)
    with col_fc2:
        horizon = st.slider("Forecast Horizon (Days Ahead)", min_value=7, max_value=30, value=14, step=1)
    with col_fc3:
        include_weather = st.checkbox("Include Irradiance & Temperature Covariates", value=True)

    df_daily = df.groupby("timestamp").agg({
        "actual_generation_kwh": "sum",
        "expected_generation_kwh": "sum",
        "temperature_c": "mean",
        "irradiance_wm2": "mean"
    }).reset_index()

    forecaster = SolarForecaster(horizon_days=horizon)
    forecast_df, meta = forecaster.generate_forecast(df_daily, method=method)

    if method == "ML (Random Forest)" and meta.get("metrics"):
        m = meta["metrics"]
        st.markdown("### 📊 Model Validation Performance (Out-of-Sample Test Set)")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Mean Absolute Error (MAE)", f"{m.get('MAE_kwh', 0):,.0f} kWh", delta="Avg. daily error")
        k2.metric("Mean Abs % Error (MAPE)", f"{m.get('MAPE_percent', 0):.2f}%", delta="Target < 8%")
        k3.metric("Root Mean Squared Error", f"{m.get('RMSE_kwh', 0):,.0f} kWh")
        k4.metric("Coefficient of Det. (R²)", f"{m.get('R2_score', 0):.3f}", delta="Variance explained")
        st.markdown("---")

    st.plotly_chart(plot_forecast_with_confidence(df_daily, forecast_df), use_container_width=True)

    total_forecasted_kwh = forecast_df["forecast_kwh"].sum()
    avg_forecast_daily_kwh = forecast_df["forecast_kwh"].mean()
    est_tariff = 3.20
    est_forecast_revenue = total_forecasted_kwh * est_tariff

    f1, f2, f3 = st.columns(3)
    f1.metric(f"Total Projected Generation ({horizon} Days)", f"{total_forecasted_kwh:,.0f} kWh")
    f2.metric("Projected Daily Average", f"{avg_forecast_daily_kwh:,.0f} kWh/day")
    f3.metric("Estimated Forecast Revenue (₹)", f"₹{est_forecast_revenue:,.0f}", delta=f"At ₹{est_tariff:.2f}/kWh PPA")

    st.markdown("---")
    with st.expander("📋 Detailed Daily Forecast Output & Confidence Intervals"):
        st.dataframe(forecast_df, use_container_width=True)
        st.caption("Note: Upper and lower bounds represent empirical 95% confidence intervals based on residual error distributions.")
