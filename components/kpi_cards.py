"""
SolarPulse KPI Cards Component
Renders responsive styled enterprise KPI metric cards.
"""

import streamlit as st

def render_kpi_card(label: str, value: str, delta: str = None, variant: str = "emerald", delta_type: str = "positive"):
    """
    Renders an enterprise KPI card with visual variant (emerald, amber, warning, sky).
    """
    delta_class = f"sp-delta-{delta_type}"
    delta_html = f'<div class="sp-kpi-delta {delta_class}">{delta}</div>' if delta else ''

    html = f"""
    <div class="sp-kpi-card {variant}">
        <div class="sp-kpi-label">{label}</div>
        <div class="sp-kpi-value">{value}</div>
        {delta_html}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def render_top_kpi_grid(
    total_generation_kwh: float,
    avg_daily_kwh: float,
    efficiency_pct: float,
    estimated_revenue_inr: float,
    estimated_annual_inr: float,
    shortfall_kwh: float
):
    """
    Renders the 6 primary executive metrics in a clean grid.
    """
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    # Format numbers cleanly
    gen_fmt = f"{total_generation_kwh / 1e6:.2f} MWh" if total_generation_kwh >= 1e6 else f"{total_generation_kwh:,.0f} kWh"
    daily_fmt = f"{avg_daily_kwh / 1e3:.1f} MWh/d" if avg_daily_kwh >= 1e3 else f"{avg_daily_kwh:,.0f} kWh/d"
    rev_monthly_fmt = f"₹{estimated_revenue_inr / 1e5:.2f} L" if estimated_revenue_inr < 1e7 else f"₹{estimated_revenue_inr / 1e7:.2f} Cr"
    rev_annual_fmt = f"₹{estimated_annual_inr / 1e7:.2f} Cr"
    shortfall_fmt = f"{shortfall_kwh / 1e6:.2f} MWh" if shortfall_kwh >= 1e6 else f"{shortfall_kwh:,.0f} kWh"

    with col1:
        render_kpi_card("Total Generation", gen_fmt, "⚡ Cumulative Output", variant="emerald", delta_type="positive")
    with col2:
        render_kpi_card("Daily Average", daily_fmt, "☀️ 24-hr Mean Yield", variant="emerald", delta_type="neutral")
    with col3:
        eff_variant = "emerald" if efficiency_pct >= 90 else ("amber" if efficiency_pct >= 80 else "warning")
        render_kpi_card("Efficiency", f"{efficiency_pct:.1f}%", "🎯 Actual / Expected", variant=eff_variant, delta_type="positive" if efficiency_pct >= 85 else "negative")
    with col4:
        render_kpi_card("Monthly Est. Revenue", rev_monthly_fmt, "📈 30-Day Run Rate", variant="sky", delta_type="positive")
    with col5:
        render_kpi_card("Annual Est. Revenue", rev_annual_fmt, "🏦 Portfolio Annualized", variant="sky", delta_type="positive")
    with col6:
        render_kpi_card("Energy Shortfall", shortfall_fmt, "⚠️ Monetizable Loss", variant="warning", delta_type="negative")
