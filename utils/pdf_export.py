# utils/pdf_export.py
"""
PDF Export Utilities — Workforce Intelligence System
- Safe for empty tables
- Handles non-ASCII & emoji text
- Compatible with matplotlib / PNG plots
"""

import io
import re
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, Image, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

# --------------------------
# SANITIZE TEXT (EMOJI SAFE)
# --------------------------
def _sanitize(value):
    if value is None:
        return ""
    text = str(value)
    text = text.replace("😊", "Happy").replace("😐", "Neutral")
    text = text.replace("😔", "Sad").replace("😡", "Angry")
    text = re.sub(r"[^\x00-\x7F]+", " ", text)
    return text.strip()

# --------------------------
# BUILD SAFE TABLE
# --------------------------
def _build_table(df, header_color=colors.lightgrey):
    if df is None or df.empty:
        return None
    df = df.copy()
    for col in df.columns:
        df[col] = df[col].apply(_sanitize)

    data = [list(df.columns)] + df.values.tolist()
    table = Table(data, repeatRows=1)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), header_color),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
    ]))
    return table

# --------------------------
# CONVERT PNG OR BYTES TO IMAGE
# --------------------------
def _png_to_image(png_input, width=6.5, height=3.2):
    """
    Accepts BytesIO, bytes, or matplotlib figure converted to PNG.
    Returns ReportLab Image or None if invalid.
    """
    if png_input is None:
        return None

    if hasattr(png_input, "savefig"):  # matplotlib figure
        buf = io.BytesIO()
        png_input.savefig(buf, format="png", bbox_inches='tight')
        buf.seek(0)
        return Image(buf, width * inch, height * inch)

    if isinstance(png_input, bytes):
        buf = io.BytesIO(png_input)
        return Image(buf, width * inch, height * inch)

    if isinstance(png_input, io.BytesIO):
        return Image(png_input, width * inch, height * inch)

    return None

# --------------------------
# MASTER PDF GENERATOR
# --------------------------
def generate_master_report(
    buffer,
    employees_df=None,
    attendance_df=None,
    mood_df=None,
    projects_df=None,
    notifications_df=None,
    mood_fig=None,
    project_fig=None,
    title="MASTER WORKFORCE REPORT"
):
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    elements = []

    # Title
    title_style = ParagraphStyle(
        name="Title",
        fontSize=20,
        alignment=1,
        spaceAfter=25
    )
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 20))

    # Employees Table
    if employees_df is not None and not employees_df.empty:
        table = _build_table(employees_df, colors.lightblue)
        if table:
            elements.append(Paragraph("Employees", styles["Heading2"]))
            elements.append(Spacer(1, 10))
            elements.append(table)
            elements.append(PageBreak())

    # Attendance Table
    if attendance_df is not None and not attendance_df.empty:
        table = _build_table(attendance_df, colors.lavender)
        if table:
            elements.append(Paragraph("Attendance", styles["Heading2"]))
            elements.append(Spacer(1, 10))
            elements.append(table)
            elements.append(PageBreak())

    # Mood Analytics
    if mood_df is not None and not mood_df.empty:
        table = _build_table(mood_df, colors.lightgreen)
        elements.append(Paragraph("Mood Analytics", styles["Heading2"]))
        elements.append(Spacer(1, 10))
        if table:
            elements.append(table)
        img = _png_to_image(mood_fig)
        if img:
            elements.append(Spacer(1, 15))
            elements.append(img)
        elements.append(PageBreak())

    # Projects
    if projects_df is not None and not projects_df.empty:
        table = _build_table(projects_df, colors.orange)
        elements.append(Paragraph("Projects", styles["Heading2"]))
        elements.append(Spacer(1, 10))
        if table:
            elements.append(table)
        img = _png_to_image(project_fig)
        if img:
            elements.append(Spacer(1, 15))
            elements.append(img)
        elements.append(PageBreak())

    # Notifications Summary
    if notifications_df is not None and not notifications_df.empty:
        elements.append(Paragraph("Notifications Summary", styles["Heading2"]))
        elements.append(Spacer(1, 10))
        if "type" in notifications_df.columns:
            summary = notifications_df.groupby("type").size().reset_index(name="Count")
        else:
            summary = notifications_df
        table = _build_table(summary, colors.pink)
        if table:
            elements.append(table)
        elements.append(PageBreak())

    # Build PDF
    doc.build(elements)
    buffer.seek(0)

# --------------------------
# LEGACY SUMMARY PDF (FOR COMPATIBILITY)
# --------------------------
def generate_summary_pdf(buffer, total=0, active=0, resigned=0, df=None, title="Summary Report"):
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(title, styles["Title"]))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(f"Total Records: {total}", styles["Normal"]))
    elements.append(Paragraph(f"Active: {active}", styles["Normal"]))
    elements.append(Paragraph(f"Closed / Resigned: {resigned}", styles["Normal"]))
    elements.append(Spacer(1, 15))

    if df is not None and not df.empty:
        table = _build_table(df, colors.lightgrey)
        if table:
            elements.append(table)

    doc.build(elements)
    buffer.seek(0)
