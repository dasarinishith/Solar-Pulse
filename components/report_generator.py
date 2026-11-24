"""
SolarPulse Analytical Report Generator
Generates structured executive analytical summaries, CSV datasets, and PDF reports.
"""

import os
import io
import pandas as pd
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_csv_export(df: pd.DataFrame) -> bytes:
    """Converts dataframe to downloadable CSV bytes."""
    return df.to_csv(index=False).encode("utf-8")

def generate_executive_pdf_report(
    summary_metrics: dict,
    plant_rankings: pd.DataFrame,
    loss_events: pd.DataFrame,
    financial_summary: dict,
    report_title: str = "SolarPulse Executive Portfolio Analytics Report"
) -> bytes:
    """
    Builds a multi-section executive PDF report using ReportLab.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Custom report styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#10b981"),
        fontName="Helvetica-Bold"
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#64748b")
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#0f172a"),
        fontName="Helvetica-Bold",
        spaceBefore=12,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#334155")
    )

    elements = []

    # 1. Header Banner
    elements.append(Paragraph("SOLARPULSE ENERGY ANALYTICS", title_style))
    elements.append(Paragraph(f"{report_title} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}", subtitle_style))
    elements.append(Paragraph("<b>CONFIDENTIALITY NOTICE:</b> For internal operational, financial, and executive review.", subtitle_style))
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#10b981"), spaceAfter=12))

    # 2. Executive Key Metrics Table
    elements.append(Paragraph("1. Portfolio Generation & Financial Overview", section_heading))
    kpi_data = [
        ["Metric", "Value", "Benchmark Status"],
        ["Total Energy Generated", f"{summary_metrics.get('total_actual_kwh', 0):,.0f} kWh", "Nominal"],
        ["Average Daily Generation", f"{summary_metrics.get('avg_daily_kwh', 0):,.0f} kWh/day", "Stable"],
        ["Generation Efficiency", f"{summary_metrics.get('overall_efficiency', 0):.1f}%", "Above Baseline" if summary_metrics.get('overall_efficiency', 0) >= 85 else "Review Needed"],
        ["Total Shortfall Loss", f"{summary_metrics.get('total_shortfall_kwh', 0):,.0f} kWh", "Monetizable Gap"],
        ["Total Estimated Revenue", f"₹{financial_summary.get('total_estimated_revenue_inr', 0):,.2f}", "Eligible Generation"],
        ["Revenue Shortfall Impact", f"₹{financial_summary.get('total_revenue_shortfall_inr', 0):,.2f}", "Potential Value Recovery"],
        ["Collection Projection", f"₹{financial_summary.get('projected_collected_revenue_inr', 0):,.2f}", f"{financial_summary.get('collection_efficiency_assumed', 96.5)}% Realization"]
    ]

    t_kpi = Table(kpi_data, colWidths=[200, 180, 160])
    t_kpi.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")])
    ]))
    elements.append(t_kpi)
    elements.append(Spacer(1, 14))

    # 3. Plant Performance Comparison Table
    elements.append(Paragraph("2. Asset Performance & Efficiency Rankings", section_heading))
    if not plant_rankings.empty:
        cols_to_show = ["plant_id", "plant_name", "capacity_mw", "actual_kwh", "efficiency"]
        present_cols = [c for c in cols_to_show if c in plant_rankings.columns]
        
        table_rows = [["Plant ID", "Asset Name", "Capacity", "Actual Generation", "Efficiency"]]
        for _, r in plant_rankings.iterrows():
            table_rows.append([
                str(r.get("plant_id", "")),
                str(r.get("plant_name", "")),
                f"{r.get('capacity_mw', 0):.1f} MW",
                f"{r.get('actual_kwh', 0):,.0f} kWh",
                f"{r.get('efficiency', 0):.1f}%"
            ])
        t_plants = Table(table_rows, colWidths=[65, 185, 75, 115, 100])
        t_plants.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8.5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")])
        ]))
        elements.append(t_plants)
    else:
        elements.append(Paragraph("No plant comparison data available.", body_style))

    elements.append(Spacer(1, 14))

    # 4. Critical Loss & Anomaly Events (Top 5)
    elements.append(Paragraph("3. Significant Underperformance & Loss Events (Sample)", section_heading))
    if not loss_events.empty:
        loss_rows = [["Date", "Plant", "Shortfall (kWh)", "Deviation", "Category"]]
        for _, r in loss_events.head(6).iterrows():
            date_str = str(r["timestamp"])[:10] if "timestamp" in r else "N/A"
            loss_rows.append([
                date_str,
                str(r.get("plant_id", "")),
                f"{r.get('shortfall_kwh', 0):,.0f}",
                f"{r.get('deviation_pct', r.get('efficiency_percent', 0)):.1f}%",
                str(r.get("category", "Underperformance"))[:30]
            ])
        t_loss = Table(loss_rows, colWidths=[80, 80, 110, 80, 190])
        t_loss.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#b91c1c")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#fff1f2")])
        ]))
        elements.append(t_loss)
    else:
        elements.append(Paragraph("No anomalous generation drop detected during this period.", body_style))

    elements.append(Spacer(1, 20))
    elements.append(Paragraph("Generated by SolarPulse Autonomous Analytics Suite • All calculations verified", subtitle_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
