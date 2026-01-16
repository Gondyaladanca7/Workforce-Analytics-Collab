# pages/10_Projects.py
import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import io

from utils.auth import require_login, show_role_badge, logout_user
from utils import database as db
from utils.pdf_export import generate_master_report

# -------------------------
# AUTH (ROLE BASED)
# -------------------------
require_login(roles_allowed=["Admin", "Manager", "HR"])

st.title("📈 Project Health Tracker")

# -------------------------
# Load Data
# -------------------------
try:
    project_df = db.fetch_projects()
    emp_df = db.fetch_employees()
    attendance_df = db.fetch_attendance()
    mood_df = db.fetch_mood_logs()
    notifications_df = pd.DataFrame()
    for emp in emp_df["Emp_ID"]:
        notif = db.fetch_notifications(emp)
        if not notif.empty:
            notifications_df = pd.concat([notifications_df, notif], ignore_index=True)
except Exception as e:
    st.error("Failed to load required data.")
    st.exception(e)
    st.stop()

if project_df.empty:
    st.info("No project data available.")
    st.stop()

# Map owner names
emp_map = emp_df.set_index("Emp_ID")["Name"].to_dict()
project_df["Owner"] = project_df["owner_emp_id"].map(emp_map).fillna(
    project_df["owner_emp_id"].astype(str)
)

# -------------------------
# Filters
# -------------------------
st.sidebar.header("Filters")
status_filter = st.sidebar.selectbox(
    "Project Status", ["All"] + sorted(project_df["status"].unique())
)
owner_filter = st.sidebar.selectbox(
    "Project Owner", ["All"] + sorted(project_df["Owner"].unique())
)
date_range = st.sidebar.date_input("End Before Date", value=datetime.date.today())

filtered_df = project_df.copy()
if status_filter != "All":
    filtered_df = filtered_df[filtered_df["status"] == status_filter]
if owner_filter != "All":
    filtered_df = filtered_df[filtered_df["Owner"] == owner_filter]
filtered_df = filtered_df[
    pd.to_datetime(filtered_df["due_date"]) <= pd.to_datetime(date_range)
]

# -------------------------
# Overview
# -------------------------
st.subheader("🗂️ Projects Overview")
st.dataframe(
    filtered_df[
        ["project_id", "project_name", "Owner", "status", "progress", "start_date", "due_date"]
    ],
    height=400,
    use_container_width=True
)

# -------------------------
# Analytics
# -------------------------
st.subheader("📊 Project Completion Analytics")
if not filtered_df.empty:
    fig = px.bar(
        filtered_df,
        x="project_name",
        y="progress",
        color="status",
        text="progress",
        title="Project Progress (%)"
    )
    fig.update_layout(yaxis=dict(range=[0, 100]))
    st.plotly_chart(fig, use_container_width=True)

# -------------------------
# Master PDF Export (ROLE BASED)
# -------------------------
st.divider()
st.subheader("📄 Master Workforce Report PDF")
allowed_roles_for_pdf = ["Admin", "Manager", "HR"]
if st.session_state.get("role") in allowed_roles_for_pdf:
    if st.button("Download Master PDF"):
        pdf_buffer = io.BytesIO()
        try:
            # Pass all sections to master PDF
            generate_master_report(
                buffer=pdf_buffer,
                employees_df=emp_df,
                attendance_df=attendance_df,
                mood_df=mood_df,
                projects_df=filtered_df,  # pass filtered projects
                notifications_df=notifications_df,
                project_fig=fig.to_image(format="png")
            )
            st.download_button(
                "Download PDF",
                pdf_buffer,
                "workforce_master_report.pdf",
                "application/pdf",
            )
        except Exception as e:
            st.error("Failed to generate master PDF.")
            st.exception(e)
else:
    st.info("PDF download available for Admin, Manager, and HR only.")
