"""
SolarPulse - Module H: Grid and Energy Loss Analytics (GridWatch)
Grid export analytics, transmission constraints, DISCOM curtailment logs, and financial impacts.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from database.operations import load_generation_dataframe
from components.charts import style_figure, CHART_THEME

def render_gridwatch_page(selected_plant: str, start_date, end_date):
    st.markdown(
        """
        <div class="sp-header-container">
            <div>
                <h1 class="sp-header-title">⚡ GridWatch: Grid Analytics & Curtailment Tracking</h1>
                <div class="sp-header-subtitle">Evacuation reliability, DISCOM curtailment orders, and uncompensated transmission loss monetization</div>
            </div>
            <div>
                <span class="sp-badge sp-badge-live">GRIDWATCH ACTIVE</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    plant_filter = None if selected_plant == "ALL" else selected_plant
    df = load_generation_dataframe(plant_ids=plant_filter, start_date=start_date, end_date=end_date)

    if df.empty:
        st.warning("No records found for the selected filters.")
        return

    # Filter Curtailment Records
    curtailed_records = df[df["curtailed_energy_kwh"] > 0].copy()
    total_curtailed_kwh = df["curtailed_energy_kwh"].sum()
    total_gen_kwh = df["actual_generation_kwh"].sum()
    total_export_kwh = df["grid_export_kwh"].sum()
    curtailment_rate_pct = (total_curtailed_kwh / (total_gen_kwh + total_curtailed_kwh) * 100) if (total_gen_kwh + total_curtailed_kwh) > 0 else 0
    curtailment_cost_inr = total_curtailed_kwh * 3.20

    # 1. Top KPI Row
    g1, g2, g3, g4 = st.columns(4)
    g1.metric("Total Grid Export", f"{total_export_kwh:,.0f} kWh", delta=f"{total_export_kwh/max(1, total_gen_kwh)*100:.1f}% of generation")
    g2.metric("Total Energy Curtailed", f"{total_curtailed_kwh:,.0f} kWh", delta=f"-{curtailment_rate_pct:.2f}% loss rate", delta_color="inverse")
    g3.metric("Curtailment Financial Loss", f"₹{curtailment_cost_inr:,.0f}", delta="Monetized at ₹3.20/kWh", delta_color="inverse")
    g4.metric("Curtailment Incidents", f"{len(curtailed_records)} events", delta="State SLDC Backdown Orders")

    st.markdown("---")

    # 2. Monthly Curtailment Progression
    col_c1, col_c2 = st.columns([1.4, 1.0])
    with col_c1:
        df["month_str"] = df["timestamp"].dt.strftime("%Y-%m")
        monthly_grid = df.groupby("month_str").agg({
            "grid_export_kwh": "sum",
            "self_consumption_kwh": "sum",
            "curtailed_energy_kwh": "sum"
        }).reset_index()

        fig_grid = go.Figure()
        fig_grid.add_trace(go.Bar(
            x=monthly_grid["month_str"],
            y=monthly_grid["grid_export_kwh"],
            name="Successfully Exported",
            marker_color=CHART_THEME["emerald"],
            hovertemplate="Export: %{y:,.0f} kWh<extra></extra>"
        ))
        fig_grid.add_trace(go.Bar(
            x=monthly_grid["month_str"],
            y=monthly_grid["curtailed_energy_kwh"],
            name="Curtailed (Forced Backdown)",
            marker_color=CHART_THEME["rose"],
            hovertemplate="Curtailed: %{y:,.0f} kWh<extra></extra>"
        ))
        fig_grid.update_layout(barmode="stack")
        fig_grid = style_figure(fig_grid, "Monthly Grid Export vs Forced Curtailment", "Month", "Energy (kWh)")
        st.plotly_chart(fig_grid, use_container_width=True)

    with col_c2:
        # Plant-wise Curtailment Share
        if len(df["plant_id"].unique()) > 1:
            plant_curt = df.groupby(["plant_id", "plant_name"])["curtailed_energy_kwh"].sum().reset_index()
            fig_curt_share = px.pie(
                plant_curt,
                names="plant_name",
                values="curtailed_energy_kwh",
                title="Curtailment Burden by Solar Park",
                hole=0.45,
                color_discrete_sequence=[CHART_THEME["rose"], CHART_THEME["amber"], CHART_THEME["purple"], CHART_THEME["sky"]]
            )
            fig_curt_share.update_layout(
                paper_bgcolor=CHART_THEME["paper_bgcolor"],
                font={"color": CHART_THEME["font_color"]}
            )
            st.plotly_chart(fig_curt_share, use_container_width=True)
        else:
            st.markdown(
                """
                <div class="sp-section-box" style="margin-top:1.5rem;">
                    <div class="sp-section-title">🔌 Substation & Grid Connection</div>
                    <div style="font-size:0.85rem; color:#94a3b8; margin-top:0.75rem; line-height:1.6;">
                        Interconnection: <b>220 kV State Grid Substation</b><br>
                        Feeder Capacity: <b>100 MVA</b><br>
                        Grid Backdown Protocol: <b>SLDC Meritorious Merit Order</b><br>
                        Deemed Generation Compensation: <b>Claimable under PPA Clause 14.2</b>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    # 3. Incident Log of Curtailment Events
    st.markdown("### 📋 Grid Curtailment & SLDC Order Log")
    if not curtailed_records.empty:
        st.dataframe(
            curtailed_records[[
                "timestamp", "plant_id", "plant_name", "actual_generation_kwh",
                "curtailed_energy_kwh", "grid_export_kwh", "inverter_status"
            ]].sort_values("curtailed_energy_kwh", ascending=False).reset_index(drop=True),
            use_container_width=True
        )
    else:
        st.info("No grid curtailment incidents recorded during this operational window.")
