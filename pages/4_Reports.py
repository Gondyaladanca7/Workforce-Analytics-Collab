# pages/4_Reports.py
"""
Workforce Analytics Reports — Workforce Intelligence System
Displays metrics, charts, and generates MASTER PDF reports with workforce data.
"""

import streamlit as st
import pandas as pd
import io
import matplotlib.pyplot as plt
import seaborn as sns

from utils import database as db
from utils.auth import require_login, show_role_badge, logout_user
from utils.pdf_export import generate_master_report
from utils.analytics import get_summary, department_distribution, gender_ratio, average_salary_by_dept

sns.set_style("whitegrid")
st.set_page_config(page_title="Reports", page_icon="📊", layout="wide")

# -------------------------
# Authentication & Role
# -------------------------
require_login()
show_role_badge()
logout_user()

role = st.session_state.get("role", "Employee")
username = st.session_state.get("user", "unknown")

if role not in ["Admin", "Manager", "HR"]:
    st.warning("⚠️ Access denied. Admin/Manager/HR only.")
    st.stop()

st.title("📊 Workforce Reports")

# -------------------------
# Fetch data safely
# -------------------------
def safe_fetch(func):
    try:
        return func()
    except Exception:
        return pd.DataFrame()

df_employees = safe_fetch(db.fetch_employees)
df_mood = safe_fetch(db.fetch_mood_logs)
df_attendance = safe_fetch(db.fetch_attendance)
df_notifications = safe_fetch(lambda: db.fetch_notifications(emp_id=st.session_state.get("my_emp_id")))
df_projects = safe_fetch(db.fetch_projects)

# -------------------------
# Filters (Safe)
# -------------------------
st.sidebar.header("🔍 Filter Options")

dept_options = ["All"]
role_options = ["All"]
status_options = ["All"]

if not df_employees.empty:
    dept_options += sorted(df_employees["Department"].dropna().unique().tolist())
    role_options += sorted(df_employees["Role"].dropna().unique().tolist())
    status_options += sorted(df_employees["Status"].dropna().unique().tolist())

dept_filter = st.sidebar.selectbox("Department", dept_options)
role_filter = st.sidebar.selectbox("Role", role_options)
status_filter = st.sidebar.selectbox("Status", status_options)

filtered_employees = df_employees.copy()
if dept_filter != "All":
    filtered_employees = filtered_employees[filtered_employees["Department"] == dept_filter]
if role_filter != "All":
    filtered_employees = filtered_employees[filtered_employees["Role"] == role_filter]
if status_filter != "All":
    filtered_employees = filtered_employees[filtered_employees["Status"] == status_filter]

# -------------------------
# Summary Metrics
# -------------------------
summary = get_summary(filtered_employees)
col1, col2, col3 = st.columns(3)
col1.metric("Total Employees", summary.get("total", 0))
col2.metric("Active Employees", summary.get("active", 0))
col3.metric("Resigned Employees", summary.get("resigned", 0))
st.markdown("---")

# -------------------------
# Charts (Matplotlib + Seaborn)
# -------------------------
dept_fig = None
if not filtered_employees.empty and "Department" in filtered_employees.columns:
    dept_ser = department_distribution(filtered_employees)
    fig, ax = plt.subplots(figsize=(8,5))
    sns.barplot(x=dept_ser.index, y=dept_ser.values, palette="pastel", ax=ax)
    ax.set_xlabel("Department")
    ax.set_ylabel("Number of Employees")
    ax.set_title("Department-wise Employee Distribution")
    plt.xticks(rotation=45)
    st.pyplot(fig, use_container_width=True)
    dept_fig = fig

gender_fig = None
if not filtered_employees.empty and "Gender" in filtered_employees.columns:
    gender_counts = gender_ratio(filtered_employees)
    fig, ax = plt.subplots(figsize=(6,6))
    ax.pie(gender_counts.values, labels=gender_counts.index,
           autopct="%1.1f%%", startangle=90,
           colors=sns.color_palette("pastel"))
    ax.axis("equal")
    ax.set_title("Gender Distribution")
    st.pyplot(fig, use_container_width=True)

salary_fig = None
if not filtered_employees.empty and all(x in filtered_employees.columns for x in ["Salary","Department"]):
    avg_salary = average_salary_by_dept(filtered_employees)
    fig, ax = plt.subplots(figsize=(8,5))
    sns.barplot(x=avg_salary.index, y=avg_salary.values, palette="pastel", ax=ax)
    ax.set_xlabel("Department")
    ax.set_ylabel("Average Salary")
    ax.set_title("Average Salary by Department")
    plt.xticks(rotation=45)
    st.pyplot(fig, use_container_width=True)

# -------------------------
# Download Master PDF
# -------------------------
st.subheader("📄 Download Workforce Master PDF")

if role in ["Admin", "Manager", "HR"]:
    pdf_buffer = io.BytesIO()
    if st.button("Generate PDF"):
        try:
            generate_master_report(
                buffer=pdf_buffer,
                employees_df=filtered_employees,
                attendance_df=df_attendance,
                mood_df=df_mood,
                projects_df=df_projects,
                notifications_df=df_notifications,
                mood_fig=dept_fig,
                project_fig=None,
                title="Workforce Master Report"
            )
            st.download_button(
                label="Download PDF",
                data=pdf_buffer,
                file_name="workforce_master_report.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error("❌ Failed to generate PDF.")
            st.exception(e)
else:
    st.info("PDF download available for Admin / Manager / HR only.")
