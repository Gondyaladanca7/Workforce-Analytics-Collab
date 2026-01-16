# utils/pdf_export.py
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import io
import pandas as pd
import re

# ---------------------------
# SANITIZE TEXT
# ---------------------------
def _sanitize(s):
    if s is None:
        return ""
    s = str(s)
    s = s.replace("😊", "Happy").replace("😐", "Neutral")
    s = s.replace("😔", "Sad").replace("😡", "Angry")
    s = re.sub(r"[^\x00-\x7F]+", " ", s)
    return s.strip()

# ---------------------------
# CONVERT MATPLOTLIB FIG TO IMAGE
# ---------------------------
def _fig_to_image(fig, width=6.5, height=3.2):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    return Image(buf, width=width * inch, height=height * inch)

# ---------------------------
# BUILD TABLE
# ---------------------------
def _build_table(df, header_color=colors.lightblue):
    df_copy = df.copy()
    for col in df_copy.columns:
        df_copy[col] = df_copy[col].apply(_sanitize)

    data = [list(df_copy.columns)] + df_copy.values.tolist()
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), header_color),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,0), 9),
        ("FONTSIZE", (0,1), (-1,-1), 8),
        ("GRID", (0,0), (-1,-1), 0.25, colors.black),
        ("ALIGN", (0,0), (-1,-1), "LEFT"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    return table

# ---------------------------
# MASTER PDF GENERATOR
# ---------------------------
def generate_master_report(
    buffer,
    employees_df=None,
    attendance_df=None,
    mood_df=None,
    projects_df=None,
    notifications_df=None,
    dept_fig=None,
    mood_fig=None,
    project_fig=None,
    title="MASTER WORKFORCE REPORT"
):
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=36, leftMargin=36,
                            topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    elements = []

    # ---------------- TITLE ----------------
    title_style = ParagraphStyle(
        name="Title",
        fontSize=20,
        alignment=1,
        spaceAfter=20
    )
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 20))

    # ---------------- EMPLOYEES ----------------
    if employees_df is not None and not employees_df.empty:
        elements.append(Paragraph("👩‍💼 Employees", styles["Heading2"]))
        elements.append(Spacer(1,10))
        elements.append(_build_table(employees_df, header_color=colors.lightblue))
        elements.append(PageBreak())

    # ---------------- ATTENDANCE ----------------
    if attendance_df is not None and not attendance_df.empty:
        elements.append(Paragraph("⏰ Attendance", styles["Heading2"]))
        elements.append(Spacer(1,10))
        elements.append(_build_table(attendance_df, header_color=colors.lavender))
        elements.append(PageBreak())

    # ---------------- MOOD ----------------
    if mood_df is not None and not mood_df.empty:
        elements.append(Paragraph("📊 Mood Analytics", styles["Heading2"]))
        elements.append(Spacer(1,10))
        elements.append(_build_table(mood_df, header_color=colors.lightgreen))
        elements.append(Spacer(1,10))

        if mood_fig:
            elements.append(_fig_to_image(mood_fig))
            elements.append(PageBreak())

    # ---------------- PROJECTS ----------------
    if projects_df is not None and not projects_df.empty:
        elements.append(Paragraph("🗂️ Projects", styles["Heading2"]))
        elements.append(Spacer(1,10))
        elements.append(_build_table(projects_df, header_color=colors.orange))
        elements.append(Spacer(1,10))

        if project_fig:
            elements.append(_fig_to_image(project_fig))
            elements.append(PageBreak())

    # ---------------- NOTIFICATIONS ----------------
    if notifications_df is not None and not notifications_df.empty:
        elements.append(Paragraph("🔔 Notifications Summary", styles["Heading2"]))
        elements.append(Spacer(1,10))

        # Optional: summarize notifications by type if available
        if "type" in notifications_df.columns:
            summary = notifications_df.groupby("type").size().reset_index(name="Count")
        else:
            summary = notifications_df.copy()

        elements.append(_build_table(summary, header_color=colors.pink))
        elements.append(PageBreak())

    # ---------------- BUILD ----------------
    doc.build(elements)

    if isinstance(buffer, io.BytesIO):
        buffer.seek(0)
