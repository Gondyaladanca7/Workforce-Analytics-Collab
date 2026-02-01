# pages/4_Reports.py
"""
Workforce Reports (FIXED)
- Clean graphs
- Numbers shown on bars
- Real metrics
- Proper PDF export
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io

from utils import database as db
from utils.auth import require_login, show_role_badge, logout_user
from utils.pdf_export import generate_master_report
from utils.analytics import department_distribution, gender_ratio, average_salary_by_dept

st.set_page_config(page_title="Reports", page_icon="📊", layout="wide")

# -------------------------
# Authentication
# -------------------------
require_login()
show_role_badge()
logout_user()

role = st.session_state.get("role", "Employee")

if role not in ["Admin", "Manager", "HR"]:
    st.warning("⚠️ Access denied. Admin / Manager / HR only.")
    st.stop()

st.title("📊 Workforce Reports")

# -------------------------
# Load data safely
# -------------------------
def safe_fetch(func):
    try:
        return func()
    except Exception:
        return pd.DataFrame()

df_employees = safe_fetch(db.fetch_employees)
df_mood = safe_fetch(db.fetch_mood_logs)
df_attendance = safe_fetch(db.fetch_attendance)
df_projects = safe_fetch(db.fetch_projects)

# -------------------------
# Filters
# -------------------------
st.sidebar.header("🔍 Filters")

dept_filter = st.sidebar.selectbox(
    "Department",
    ["All"] + sorted(df_employees["Department"].dropna().unique())
    if not df_employees.empty else ["All"]
)

status_filter = st.sidebar.selectbox(
    "Status",
    ["All"] + sorted(df_employees["Status"].dropna().unique())
    if not df_employees.empty else ["All"]
)

filtered_df = df_employees.copy()

if dept_filter != "All":
    filtered_df = filtered_df[filtered_df["Department"] == dept_filter]
if status_filter != "All":
    filtered_df = filtered_df[filtered_df["Status"] == status_filter]

# -------------------------
# Summary Metrics
# -------------------------
st.subheader("📌 Summary")

total_employees = len(filtered_df)
active_employees = len(filtered_df[filtered_df["Status"] == "Active"]) if "Status" in filtered_df.columns else 0
resigned_employees = len(filtered_df[filtered_df["Status"] == "Resigned"]) if "Status" in filtered_df.columns else 0

c1, c2, c3 = st.columns(3)
c1.metric("Total Employees", total_employees)
c2.metric("Active Employees", active_employees)
c3.metric("Resigned Employees", resigned_employees)

st.divider()

# -------------------------
# Department Distribution
# -------------------------
st.subheader("🏢 Department-wise Distribution")

if not filtered_df.empty:
    dept_counts = department_distribution(filtered_df)

    fig, ax = plt.subplots()
    bars = ax.bar(dept_counts.index, dept_counts.values)
    ax.set_title("Employees per Department")
    ax.set_ylabel("Count")

    for bar in bars:
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            str(int(bar.get_height())),
            ha="center",
            va="bottom"
        )

    st.pyplot(fig)
else:
    st.info("No data for department chart.")

# -------------------------
# Gender Ratio
# -------------------------
st.subheader("👥 Gender Distribution")

if not filtered_df.empty and "Gender" in filtered_df.columns:
    gender_counts = gender_ratio(filtered_df)

    fig, ax = plt.subplots()
    ax.pie(
        gender_counts.values,
        labels=gender_counts.index,
        autopct="%1.1f%%",
        startangle=90
    )
    ax.axis("equal")
    st.pyplot(fig)
else:
    st.info("No gender data available.")

# -------------------------
# Average Salary
# -------------------------
st.subheader("💰 Average Salary by Department")

if not filtered_df.empty and "Salary" in filtered_df.columns:
    avg_salary = average_salary_by_dept(filtered_df)

    fig, ax = plt.subplots()
    bars = ax.bar(avg_salary.index, avg_salary.values)
    ax.set_title("Average Salary by Department")
    ax.set_ylabel("Salary")

    for bar in bars:
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{int(bar.get_height())}",
            ha="center",
            va="bottom"
        )

    st.pyplot(fig)
else:
    st.info("No salary data available.")

# -------------------------
# Mood Report
# -------------------------
st.subheader("😊 Mood Report")

if not df_mood.empty:
    mood_counts = df_mood["remarks"].str.extract(r"(😊 Happy|😐 Neutral|😟 Stressed)")[0].value_counts()

    fig, ax = plt.subplots()
    bars = ax.bar(mood_counts.index, mood_counts.values)
    ax.set_title("Mood Distribution")
    ax.set_ylabel("Count")

    for bar in bars:
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            str(int(bar.get_height())),
            ha="center",
            va="bottom"
        )

    st.pyplot(fig)
else:
    st.info("No mood data available.")

# -------------------------
# Project Report
# -------------------------
st.subheader("📈 Project Health Report")

if not df_projects.empty:
    proj_status = df_projects["status"].value_counts()

    fig, ax = plt.subplots()
    bars = ax.bar(proj_status.index, proj_status.values)
    ax.set_title("Projects by Status")
    ax.set_ylabel("Count")

    for bar in bars:
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            str(int(bar.get_height())),
            ha="center",
            va="bottom"
        )

    st.pyplot(fig)
else:
    st.info("No project data available.")

# -------------------------
# Export Master PDF
# -------------------------
st.divider()
st.subheader("📄 Download Master Workforce PDF")

if st.button("Generate PDF"):
    pdf_buffer = io.BytesIO()
    try:
        generate_master_report(
            buffer=pdf_buffer,
            employees_df=filtered_df,
            attendance_df=df_attendance,
            mood_df=df_mood,
            projects_df=df_projects,
            notifications_df=pd.DataFrame()
        )

        st.download_button(
            "Download PDF",
            pdf_buffer,
            "workforce_report.pdf",
            "application/pdf"
        )
    except Exception as e:
        st.error("Failed to generate PDF.")
        st.exception(e)
