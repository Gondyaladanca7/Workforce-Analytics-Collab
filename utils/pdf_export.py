from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import io
import pandas as pd
import re

# --------------------------------------------------
# SANITIZE TEXT
# --------------------------------------------------
def _sanitize(s):
    if s is None:
        return ""
    s = str(s)
    s = s.replace("😊", "Happy").replace("😐", "Neutral")
    s = s.replace("😔", "Sad").replace("😡", "Angry")
    s = re.sub(r"[^\x00-\x7F]+", " ", s)
    return s


# --------------------------------------------------
# CONVERT MATPLOTLIB FIG TO IMAGE
# --------------------------------------------------
def _fig_to_image(fig, width=6, height=3):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    return Image(buf, width=width * inch, height=height * inch)


# --------------------------------------------------
# MAIN PDF GENERATOR (UNIFIED)
# --------------------------------------------------
def generate_summary_pdf(
    buffer,
    total,
    active,
    resigned,
    df=None,
    mood_df=None,
    dept_fig=None,
    gender_fig=None,
    salary_fig=None,
    title="Workforce Report"
):
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    # ---------------- TITLE ----------------
    title_style = ParagraphStyle(
        name="Title",
        fontSize=18,
        alignment=1,
        spaceAfter=14
    )
    elements.append(Paragraph(title, title_style))

    # ---------------- METRICS ----------------
    elements.append(Paragraph(f"<b>Total:</b> {total}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Active:</b> {active}", styles["Normal"]))
    elements.append(Paragraph(f"<b>Resigned:</b> {resigned}", styles["Normal"]))
    elements.append(Spacer(1, 12))

    # ---------------- TABLE ----------------
    if df is not None and not df.empty:
        df_copy = df.copy()
        for col in df_copy.columns:
            df_copy[col] = df_copy[col].apply(_sanitize)

        table_data = [list(df_copy.columns)] + df_copy.values.tolist()
        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightblue),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 0.25, colors.black),
            ('FONTSIZE', (0,0), (-1,-1), 8),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 14))

    # ---------------- MOOD TABLE ----------------
    if mood_df is not None and not mood_df.empty:
        elements.append(Paragraph("Mood Records", styles["Heading2"]))
        mood_copy = mood_df.copy()
        for col in mood_copy.columns:
            mood_copy[col] = mood_copy[col].apply(_sanitize)

        mood_data = [list(mood_copy.columns)] + mood_copy.values.tolist()
        mood_table = Table(mood_data, repeatRows=1)
        mood_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgreen),
            ('GRID', (0,0), (-1,-1), 0.25, colors.black),
            ('FONTSIZE', (0,0), (-1,-1), 8),
        ]))
        elements.append(mood_table)
        elements.append(Spacer(1, 14))

    # ---------------- FIGURES ----------------
    if dept_fig:
        elements.append(Paragraph("Analytics", styles["Heading2"]))
        elements.append(_fig_to_image(dept_fig))
        elements.append(Spacer(1, 10))

    if gender_fig:
        elements.append(_fig_to_image(gender_fig))
        elements.append(Spacer(1, 10))

    if salary_fig:
        elements.append(_fig_to_image(salary_fig))
        elements.append(Spacer(1, 10))

    # ---------------- BUILD ----------------
    doc.build(elements)

    if isinstance(buffer, io.BytesIO):
        buffer.seek(0)
