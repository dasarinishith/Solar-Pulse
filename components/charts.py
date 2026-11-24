"""
SolarPulse Chart Library
Enterprise-grade Plotly visualisations styled for dark renewable aesthetic.
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

CHART_THEME = {
    "paper_bgcolor": "#131c1a",
    "plot_bgcolor": "#131c1a",
    "font_family": "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif",
    "font_color": "#cbd5e1",
    "grid_color": "#22312d",
    "emerald": "#10b981",
    "mint": "#34d399",
    "amber": "#f59e0b",
    "rose": "#f43f5e",
    "sky": "#0ea5e9",
    "purple": "#a855f7"
}

def style_figure(fig: go.Figure, title: str = "", x_title: str = "", y_title: str = "", height: int = 380) -> go.Figure:
    """Applies unified enterprise dark-theme styling to any Plotly figure."""
    fig.update_layout(
        title={
            "text": f"<b>{title}</b>",
            "font": {"size": 14, "color": "#f8fafc"},
            "x": 0.02,
            "y": 0.95
        },
        height=height,
        paper_bgcolor=CHART_THEME["paper_bgcolor"],
        plot_bgcolor=CHART_THEME["plot_bgcolor"],
        font={"family": CHART_THEME["font_family"], "color": CHART_THEME["font_color"], "size": 11},
        margin={"l": 50, "r": 30, "t": 55, "b": 45},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1.0,
            "font": {"size": 11, "color": "#94a3b8"}
        },
        hovermode="x unified",
        xaxis={
            "title": x_title,
            "showgrid": True,
            "gridcolor": CHART_THEME["grid_color"],
            "gridwidth": 0.8,
            "zeroline": False
        },
        yaxis={
            "title": y_title,
            "showgrid": True,
            "gridcolor": CHART_THEME["grid_color"],
            "gridwidth": 0.8,
            "zeroline": False
        }
    )
    return fig

def plot_actual_vs_expected(df: pd.DataFrame) -> go.Figure:
    """Line & Area comparison of Actual vs Expected Daily Generation."""
    fig = go.Figure()
    
    # Expected as subtle dashed line
    fig.add_trace(go.Scatter(
        x=df["timestamp"],
        y=df["expected_generation_kwh"],
        name="Expected (kWh)",
        line={"color": "#64748b", "width": 1.8, "dash": "dash"},
        hovertemplate="Expected: %{y:,.0f} kWh<extra></extra>"
    ))

    # Actual as glowing emerald line with subtle area
    fig.add_trace(go.Scatter(
        x=df["timestamp"],
        y=df["actual_generation_kwh"],
        name="Actual (kWh)",
        fill="tozeroy",
        fillcolor="rgba(16, 185, 129, 0.12)",
        line={"color": CHART_THEME["emerald"], "width": 2.2},
        hovertemplate="Actual: %{y:,.0f} kWh<extra></extra>"
    ))

    return style_figure(fig, "Actual vs Expected Energy Generation", "Date", "Energy (kWh)")

def plot_monthly_generation_trends(df: pd.DataFrame) -> go.Figure:
    """Monthly aggregated bar and shortfall breakdown."""
    df_copy = df.copy()
    df_copy["month_year"] = pd.to_datetime(df_copy["timestamp"]).dt.strftime("%Y-%m")
    
    monthly = df_copy.groupby("month_year").agg({
        "actual_generation_kwh": "sum",
        "expected_generation_kwh": "sum"
    }).reset_index()

    monthly["shortfall_kwh"] = np.maximum(0, monthly["expected_generation_kwh"] - monthly["actual_generation_kwh"])

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=monthly["month_year"],
        y=monthly["actual_generation_kwh"],
        name="Delivered Generation",
        marker_color=CHART_THEME["emerald"],
        hovertemplate="Delivered: %{y:,.0f} kWh<extra></extra>"
    ))
    fig.add_trace(go.Bar(
        x=monthly["month_year"],
        y=monthly["shortfall_kwh"],
        name="Generation Shortfall",
        marker_color=CHART_THEME["rose"],
        hovertemplate="Shortfall: %{y:,.0f} kWh<extra></extra>"
    ))

    fig.update_layout(barmode="stack")
    return style_figure(fig, "Monthly Energy Generation & Shortfall Profile", "Month", "Energy (kWh)")

def plot_monthly_revenue(df: pd.DataFrame) -> go.Figure:
    """Monthly financial revenue trend (Export Revenue vs Self-Consumption vs Shortfall)."""
    df_copy = df.copy()
    df_copy["month_year"] = pd.to_datetime(df_copy["timestamp"]).dt.strftime("%Y-%m")
    
    monthly_rev = df_copy.groupby("month_year").agg({
        "estimated_export_revenue_inr": "sum",
        "estimated_self_revenue_inr": "sum",
        "revenue_shortfall_inr": "sum"
    }).reset_index()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=monthly_rev["month_year"],
        y=monthly_rev["estimated_export_revenue_inr"],
        name="Grid Export Revenue (₹)",
        marker_color=CHART_THEME["sky"],
        hovertemplate="Export: ₹%{y:,.0f}<extra></extra>"
    ))
    fig.add_trace(go.Bar(
        x=monthly_rev["month_year"],
        y=monthly_rev["estimated_self_revenue_inr"],
        name="Self-Consumption Value (₹)",
        marker_color=CHART_THEME["mint"],
        hovertemplate="Self-Use: ₹%{y:,.0f}<extra></extra>"
    ))

    fig.update_layout(barmode="stack")
    return style_figure(fig, "Monthly Revenue Realization & Monetization", "Month", "Revenue (INR ₹)")

def plot_plant_comparison(df: pd.DataFrame) -> go.Figure:
    """Horizontal bar comparison of plant capacities and efficiency."""
    plant_summary = df.groupby(["plant_id", "plant_name"]).agg({
        "actual_generation_kwh": "sum",
        "expected_generation_kwh": "sum",
        "capacity_mw": "first"
    }).reset_index()

    plant_summary["efficiency"] = (plant_summary["actual_generation_kwh"] / plant_summary["expected_generation_kwh"].replace(0, np.nan)) * 100

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=plant_summary["efficiency"],
        y=plant_summary["plant_name"],
        orientation="h",
        marker_color=[
            CHART_THEME["emerald"] if e >= 88 else (CHART_THEME["amber"] if e >= 80 else CHART_THEME["rose"])
            for e in plant_summary["efficiency"]
        ],
        text=[f"{e:.1f}% ({c} MW)" for e, c in zip(plant_summary["efficiency"], plant_summary["capacity_mw"])],
        textposition="inside",
        hovertemplate="%{y}<br>Efficiency: %{x:.2f}%<extra></extra>"
    ))

    return style_figure(fig, "Plant Generation Efficiency Comparison", "Efficiency (%)", "", height=280)

def plot_forecast_with_confidence(hist_df: pd.DataFrame, forecast_df: pd.DataFrame) -> go.Figure:
    """Historical trail with forecasted values and shaded 95% confidence intervals."""
    fig = go.Figure()

    # Last 30 days of historical actuals
    recent_hist = hist_df.sort_values("timestamp").iloc[-30:]
    fig.add_trace(go.Scatter(
        x=recent_hist["timestamp"],
        y=recent_hist["actual_generation_kwh"],
        name="Historical Generation",
        line={"color": "#64748b", "width": 1.8},
        hovertemplate="Actual: %{y:,.0f} kWh<extra></extra>"
    ))

    # Upper Bound
    fig.add_trace(go.Scatter(
        x=forecast_df["date"],
        y=forecast_df["upper_bound_kwh"],
        name="Upper Bound (95%)",
        mode="lines",
        line={"width": 0},
        showlegend=False,
        hoverinfo="skip"
    ))

    # Shaded band + Lower Bound
    fig.add_trace(go.Scatter(
        x=forecast_df["date"],
        y=forecast_df["lower_bound_kwh"],
        name="Confidence Interval",
        fill="tonexty",
        fillcolor="rgba(16, 185, 129, 0.15)",
        mode="lines",
        line={"width": 0},
        hovertemplate="Lower: %{y:,.0f} kWh<extra></extra>"
    ))

    # Point Forecast
    fig.add_trace(go.Scatter(
        x=forecast_df["date"],
        y=forecast_df["forecast_kwh"],
        name="Forecast (kWh)",
        line={"color": CHART_THEME["emerald"], "width": 2.5, "dash": "dashdot"},
        hovertemplate="Forecast: %{y:,.0f} kWh<extra></extra>"
    ))

    return style_figure(fig, "Solar Generation Horizon Forecast (SolarCast)", "Horizon Date", "Generation (kWh)")
