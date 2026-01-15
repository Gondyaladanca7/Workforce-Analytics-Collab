# utils/pdf_export.py

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import io
import matplotlib.pyplot as plt
import re
import pandas as pd

# --------------------------
# Sanitize text for PDF
# --------------------------
def _sanitize_text_for_pdf(s: str) -> str:
    """Replace emojis and non-ASCII chars to avoid PDF errors."""
    if s is None:
        return ""
    s = s.replace("😊", "Happy").replace("😐", "Neutral").replace("😔", "Sad").replace("😡", "Angry")
    s = s.replace("₹", "Rs.")
    s = re.sub(r"[^\x00-\x7F]+", " ", s)
    return s


# --------------------------
# Generate Workforce PDF
# --------------------------
def generate_summary_pdf(
    buffer,
    total,
    active,
    resigned,
    df,
    mood_df=None,
    dept_fig=None,
    gender_fig=None,
    salary_fig=None,
    title="Workforce Summary Report"
):
    """
    buffer: file path or BytesIO
    df: employee DataFrame
    mood_df: mood DataFrame
    dept_fig, gender_fig, salary_fig: matplotlib Figure objects
    """
    if isinstance(buffer, io.BytesIO):
        doc = SimpleDocTemplate(buffer, pagesize=A4)
    else:
        doc = SimpleDocTemplate(buffer, pagesize=A4)

    elements = []
    styles = getSampleStyleSheet()

    # Title
    title_style = ParagraphStyle(name="Title", fontSize=18, leading=22, alignment=1, spaceAfter=12)
    elements.append(Paragraph(title, title_style))

    # Metrics
    metrics_style = ParagraphStyle(name="Metrics", fontSize=11, leading=14, spaceAfter=6)
    elements.append(Paragraph(f"Total Employees: {int(total)}", metrics_style))
    elements.append(Paragraph(f"Active Employees: {int(active)}", metrics_style))
    elements.append(Paragraph(f"Resigned Employees: {int(resigned)}", metrics_style))
    elements.append(Spacer(1, 12))

    # Employee Table
    if df is not None and not df.empty:
        df_display = df.copy()
        cols_to_show = [c for c in ["Emp_ID","Name","Department","Role","Join_Date","Status"] if c in df_display.columns]
        df_display = df_display[cols_to_show]
        # Sanitize all string values
        for col in df_display.select_dtypes(include=["object"]).columns:
            df_display[col] = df_display[col].astype(str).apply(_sanitize_text_for_pdf)
        data = [cols_to_show] + df_display.values.tolist()

        pastel_blue = colors.Color(173/255,216/255,230/255)
        pastel_grey = colors.Color(240/255,240/255,240/255)
        t = Table(data, hAlign='LEFT', repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),pastel_blue),
            ('TEXTCOLOR',(0,0),(-1,0),colors.black),
            ('ALIGN',(0,0),(-1,-1),'LEFT'),
            ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
            ('FONTSIZE',(0,0),(-1,-1),9),
            ('BACKGROUND',(0,1),(-1,-1),pastel_grey),
            ('GRID',(0,0),(-1,-1),0.25,colors.black)
        ]))
        elements.append(t)
        elements.append(Spacer(1,12))

    # Mood Table
    if mood_df is not None and not mood_df.empty:
        mood_df_copy = mood_df.copy()
        if "remarks" in mood_df_copy.columns:
            mood_df_copy["remarks"] = mood_df_copy["remarks"].fillna("").astype(str).apply(_sanitize_text_for_pdf)
        if "Name" not in mood_df_copy.columns and "Employee" in mood_df_copy.columns:
            mood_df_copy["Name"] = mood_df_copy["Employee"]
        mood_cols = [c for c in ["Name","log_date","mood","remarks"] if c in mood_df_copy.columns]
        if len(mood_cols) > 0 and len(mood_df_copy) > 0:
            # Sanitize all string columns
            for col in mood_cols:
                mood_df_copy[col] = mood_df_copy[col].astype(str).apply(_sanitize_text_for_pdf)
            mood_data = [mood_cols] + mood_df_copy[mood_cols].values.tolist()
            t_mood = Table(mood_data,hAlign='LEFT',repeatRows=1)
            t_mood.setStyle(TableStyle([
                ('BACKGROUND',(0,0),(-1,0),colors.lightgreen),
                ('TEXTCOLOR',(0,0),(-1,0),colors.black),
                ('ALIGN',(0,0),(-1,-1),'LEFT'),
                ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
                ('FONTSIZE',(0,0),(-1,-1),9),
                ('GRID',(0,0),(-1,-1),0.25,colors.black)
            ]))
            elements.append(t_mood)
            elements.append(Spacer(1,12))

    # Figures
    for fig, heading in zip([dept_fig, gender_fig, salary_fig],
                            ["Department Distribution", "Gender Ratio", "Average Salary by Department"]):
        if fig is not None:
            buf = io.BytesIO()
            try:
                fig.savefig(buf, format='png', bbox_inches='tight')
                buf.seek(0)
                elements.append(Paragraph(heading, styles['Heading2']))
                elements.append(Image(buf, width=6*inch, height=3*inch))
                elements.append(Spacer(1,12))
            except Exception:
                continue
            finally:
                plt.close(fig)  # close figure to free memory

    doc.build(elements)
    if isinstance(buffer, io.BytesIO):
        buffer.seek(0)
