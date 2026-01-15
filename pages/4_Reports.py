# pages/4_Reports.py
"""
Workforce Analytics Reports — Workforce Intelligence System
Displays metrics, charts, and generates PDF reports with workforce data.
"""

import streamlit as st
import pandas as pd
from utils import database as db
from utils.auth import require_login, show_role_badge, logout_user
from utils.pdf_export import generate_summary_pdf
from utils.analytics import get_summary, department_distribution, gender_ratio, average_salary_by_dept
import matplotlib.pyplot as plt
import seaborn as sns
import io

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

if role not in ["Admin", "Manager"]:
    st.warning("⚠️ Access denied. Admin/Manager only.")
    st.stop()

st.title("📊 Workforce Reports")

# -------------------------
# Fetch data
# -------------------------
try:
    df = db.fetch_employees()
except Exception:
    df = pd.DataFrame()

try:
    mood_df = db.fetch_mood_logs()
except Exception:
    mood_df = pd.DataFrame()

# -------------------------
# Filters
# -------------------------
st.sidebar.header("🔍 Filter Options")
dept_filter = st.sidebar.selectbox("Department", ["All"] + sorted(df["Department"].dropna().unique().tolist()))
status_filter = st.sidebar.selectbox("Status", ["All"] + sorted(df["Status"].dropna().unique().tolist()))
role_filter = st.sidebar.selectbox("Role", ["All"] + sorted(df["Role"].dropna().unique().tolist()))

filtered_df = df.copy()
if dept_filter != "All":
    filtered_df = filtered_df[filtered_df["Department"] == dept_filter]
if status_filter != "All":
    filtered_df = filtered_df[filtered_df["Status"] == status_filter]
if role_filter != "All":
    filtered_df = filtered_df[filtered_df["Role"] == role_filter]

# -------------------------
# Summary Metrics
# -------------------------
summary = get_summary(filtered_df)
col1, col2, col3 = st.columns(3)
col1.metric("Total Employees", summary["total"])
col2.metric("Active Employees", summary["active"])
col3.metric("Resigned Employees", summary["resigned"])

st.markdown("---")

# -------------------------
# Charts
# -------------------------
dept_fig = None
if not filtered_df.empty and "Department" in filtered_df.columns:
    dept_ser = department_distribution(filtered_df)
    fig, ax = plt.subplots(figsize=(8,5))
    sns.barplot(x=dept_ser.index, y=dept_ser.values, palette="pastel", ax=ax)
    ax.set_xlabel("Department")
    ax.set_ylabel("Number of Employees")
    ax.set_title("Department-wise Employee Distribution")
    plt.xticks(rotation=45)
    st.pyplot(fig, use_container_width=True)
    dept_fig = fig

gender_fig = None
if not filtered_df.empty and "Gender" in filtered_df.columns:
    gender_counts = gender_ratio(filtered_df)
    fig, ax = plt.subplots(figsize=(6,6))
    ax.pie(gender_counts.values, labels=gender_counts.index, autopct="%1.1f%%",
           startangle=90, colors=sns.color_palette("pastel"))
    ax.axis("equal")
    ax.set_title("Gender Distribution")
    st.pyplot(fig, use_container_width=True)
    gender_fig = fig

salary_fig = None
if not filtered_df.empty and "Salary" in filtered_df.columns and "Department" in filtered_df.columns:
    avg_salary = average_salary_by_dept(filtered_df)
    fig, ax = plt.subplots(figsize=(8,5))
    sns.barplot(x=avg_salary.index, y=avg_salary.values, palette="pastel", ax=ax)
    ax.set_xlabel("Department")
    ax.set_ylabel("Average Salary")
    ax.set_title("Average Salary by Department")
    plt.xticks(rotation=45)
    st.pyplot(fig, use_container_width=True)
    salary_fig = fig

# -------------------------
# Download PDF
# -------------------------
st.subheader("📄 Download Workforce Summary PDF")
pdf_buffer = io.BytesIO()
if st.button("Generate PDF"):
    try:
        generate_summary_pdf(
            buffer=pdf_buffer,
            total=summary["total"],
            active=summary["active"],
            resigned=summary["resigned"],
            df=filtered_df,
            mood_df=mood_df,
            dept_fig=dept_fig,
            gender_fig=gender_fig,
            salary_fig=salary_fig,
            title="Workforce Summary Report"
        )
        st.download_button(
            label="Download PDF",
            data=pdf_buffer,
            file_name="workforce_summary_report.pdf",
            mime="application/pdf"
        )
    except Exception as e:
        st.error("Failed to generate PDF.")
        st.exception(e)
