# pages/10_Projects.py
"""
Project Health Tracker — Workforce Intelligence System
View project status, analytics, and generate master PDF reports.
"""

import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import io

from utils.auth import require_login, show_role_badge, logout_user
from utils import database as db
from utils.pdf_export import generate_master_report

# -------------------------
# Authentication
# -------------------------
require_login(roles_allowed=["Admin", "Manager", "HR"])

st.title("📈 Project Health Tracker")
show_role_badge()
logout_user()

# -------------------------
# Load Data (SAFE)
# -------------------------
try:
    project_df = db.fetch_projects()
    emp_df = db.fetch_employees()
    attendance_df = db.fetch_attendance()
    mood_df = db.fetch_mood_logs()

    # Collect notifications safely
    notifications_df = pd.DataFrame()
    if not emp_df.empty:
        for emp_id in emp_df["Emp_ID"].dropna().unique():
            try:
                notif = db.fetch_notifications(emp_id)
                if not notif.empty:
                    notifications_df = pd.concat(
                        [notifications_df, notif],
                        ignore_index=True
                    )
            except Exception:
                # Ignore notification failure for one employee
                pass

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
emp_map = emp_df.set_index("Emp_ID")["Name"].to_dict()

project_df["Owner"] = (
    project_df["owner_emp_id"]
    .map(emp_map)
    .fillna(project_df["owner_emp_id"].astype(str))
)

# -------------------------
# Filters
# -------------------------
st.sidebar.header("Filters")

status_filter = st.sidebar.selectbox(
    "Project Status",
    ["All"] + sorted(project_df["status"].dropna().unique().tolist())
)

owner_filter = st.sidebar.selectbox(
    "Project Owner",
    ["All"] + sorted(project_df["Owner"].dropna().unique().tolist())
)

date_range = st.sidebar.date_input(
    "End Before Date",
    value=datetime.date.today()
)

filtered_df = project_df.copy()

if status_filter != "All":
    filtered_df = filtered_df[filtered_df["status"] == status_filter]

if owner_filter != "All":
    filtered_df = filtered_df[filtered_df["Owner"] == owner_filter]

filtered_df["due_date"] = pd.to_datetime(
    filtered_df["due_date"],
    errors="coerce"
)

filtered_df = filtered_df[
    filtered_df["due_date"] <= pd.to_datetime(date_range)
]

# -------------------------
# Projects Overview
# -------------------------
st.subheader("🗂️ Projects Overview")

st.dataframe(
    filtered_df[
        [
            "project_id",
            "project_name",
            "Owner",
            "status",
            "progress",
            "start_date",
            "due_date",
        ]
    ],
    height=400,
    use_container_width=True,
)

# -------------------------
# Project Completion Analytics
# -------------------------
st.subheader("📊 Project Completion Analytics")

project_chart_png = None

if not filtered_df.empty:
    fig = px.bar(
        filtered_df,
        x="project_name",
        y="progress",
        color="status",
        text="progress",
        title="Project Progress (%)",
    )
    fig.update_layout(yaxis=dict(range=[0, 100]))
    st.plotly_chart(fig, use_container_width=True)

    # Convert chart to PNG BYTES (CRITICAL FIX)
    try:
        project_chart_png = fig.to_image(format="png")
    except Exception:
        project_chart_png = None

# -------------------------
# Master PDF Export
# -------------------------
st.divider()
st.subheader("📄 Master Workforce Report PDF")

allowed_roles_for_pdf = ["Admin", "Manager", "HR"]

if st.session_state.get("role") in allowed_roles_for_pdf:
    if st.button("Download Master PDF"):
        pdf_buffer = io.BytesIO()

        try:
            generate_master_report(
                buffer=pdf_buffer,
                employees_df=emp_df,
                attendance_df=attendance_df,
                mood_df=mood_df,
                projects_df=filtered_df,
                notifications_df=notifications_df,
                project_fig=project_chart_png,
            )

            pdf_buffer.seek(0)

            st.download_button(
                label="Download PDF",
                data=pdf_buffer,
                file_name="workforce_master_report.pdf",
                mime="application/pdf",
            )

        except Exception as e:
            st.error("Failed to generate master PDF.")
            st.exception(e)
else:
    st.info("PDF download available for Admin, Manager, HR only.")
