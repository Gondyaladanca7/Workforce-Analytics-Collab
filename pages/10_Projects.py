# pages/10_Projects.py
"""
Project Health Tracker (FINAL + PDF GRAPH)
Calculates project health using:
- Progress
- Employee Mood
- Attendance
Includes graph and PDF export with graph
"""

import streamlit as st
import pandas as pd
import datetime
import matplotlib.pyplot as plt
import io

from utils.auth import require_login, show_role_badge, logout_user
from utils import database as db
from utils.pdf_export import generate_master_report

# -------------------------
# Authentication
# -------------------------
require_login(roles_allowed=["Admin", "Manager", "HR"])
show_role_badge()
logout_user()

st.title("📈 Project Health Tracker")

# -------------------------
# Load Data
# -------------------------
try:
    project_df = db.fetch_projects()
    emp_df = db.fetch_employees()
    attendance_df = db.fetch_attendance()
    mood_df = db.fetch_mood_logs()
except Exception as e:
    st.error("Failed to load required data.")
    st.exception(e)
    st.stop()

if project_df.empty:
    st.info("No project data available.")
    st.stop()

# -------------------------
# Map Employee Names
# -------------------------
if not emp_df.empty:
    emp_map = emp_df.set_index("Emp_ID")["Name"].to_dict()
    project_df["Owner"] = project_df["owner_emp_id"].map(emp_map).fillna(
        project_df["owner_emp_id"].astype(str)
    )
else:
    project_df["Owner"] = project_df["owner_emp_id"]

# -------------------------
# Helper: Attendance Score
# -------------------------
def attendance_score(emp_id):
    emp_att = attendance_df[attendance_df["emp_id"] == emp_id]
    if emp_att.empty:
        return 0
    present = emp_att[emp_att["status"] == "Present"]
    ratio = len(present) / len(emp_att) * 100
    if ratio > 80:
        return 20
    elif ratio >= 50:
        return 10
    else:
        return 0

# -------------------------
# Helper: Mood Score
# -------------------------
def mood_score(emp_id):
    emp_mood = mood_df[mood_df["emp_id"] == emp_id]
    if emp_mood.empty:
        return 0
    last = emp_mood.sort_values("log_date").iloc[-1]
    remark = str(last["remarks"])
    if "Happy" in remark:
        return 20
    elif "Neutral" in remark:
        return 10
    else:
        return 0

# -------------------------
# Compute Health
# -------------------------
health_rows = []

for _, row in project_df.iterrows():
    progress = int(row.get("progress", 0))
    owner_id = row.get("owner_emp_id")

    mood = mood_score(owner_id)
    att = attendance_score(owner_id)

    health_score = progress + mood + att

    if health_score >= 70:
        health_status = "Healthy"
    elif health_score >= 40:
        health_status = "At Risk"
    else:
        health_status = "Critical"

    health_rows.append({
        "Project ID": row["project_id"],
        "Project": row["project_name"],
        "Owner": row["Owner"],
        "Progress (%)": progress,
        "Health Score": health_score,
        "Health Status": health_status,
        "Start Date": row["start_date"],
        "Due Date": row["due_date"]
    })

health_df = pd.DataFrame(health_rows)

# -------------------------
# Display Table
# -------------------------
st.subheader("📋 Project Health Overview")
st.dataframe(health_df, use_container_width=True)

# -------------------------
# Health Analytics Graph (MATPLOTLIB)
# -------------------------
st.subheader("📊 Project Health Analytics")

health_counts = health_df["Health Status"].value_counts()

fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.bar(health_counts.index, health_counts.values, color=["green", "orange", "red"])

ax.set_title("Projects by Health Status")
ax.set_xlabel("Health Status")
ax.set_ylabel("Count")

for bar in bars:
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height(),
        str(int(bar.get_height())),
        ha="center",
        va="bottom",
        fontsize=9
    )

plt.tight_layout()
st.pyplot(fig)

# -------------------------
# Convert Graph to PNG (for PDF)
# -------------------------
buf = io.BytesIO()
fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
buf.seek(0)
project_png = buf.read()

# -------------------------
# Export Master PDF (WITH GRAPH)
# -------------------------
st.divider()
st.subheader("📄 Download Master Workforce PDF")

if st.button("Download Master PDF"):
    pdf_buffer = io.BytesIO()
    try:
        generate_master_report(
            buffer=pdf_buffer,
            employees_df=emp_df,
            attendance_df=attendance_df,
            mood_df=mood_df,
            projects_df=health_df,
            notifications_df=pd.DataFrame(),
            project_fig=project_png  # ✅ graph included
        )

        pdf_buffer.seek(0)

        st.download_button(
            "Download PDF",
            pdf_buffer,
            "workforce_project_health_report.pdf",
            "application/pdf"
        )

    except Exception as e:
        st.error("Failed to generate master PDF.")
        st.exception(e)
