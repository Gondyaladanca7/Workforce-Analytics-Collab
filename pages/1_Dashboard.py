# pages/1_Dashboard.py
"""
Dashboard — Workforce Analytics System (FINAL + PDF GRAPH SUPPORT)
- Proper label alignment
- Numbers on bars
- No overlapping text
- Graph included in PDF
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io

from utils import database as db
from utils.analytics import (
    get_summary,
    department_distribution,
    gender_ratio,
    average_salary_by_dept
)
from utils.pdf_export import generate_master_report

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
st.title("📊 Workforce Dashboard")

# -------------------------
# Load employee data
# -------------------------
try:
    df = db.fetch_employees()
except Exception as e:
    st.error("Failed to fetch employee data.")
    st.exception(e)
    df = pd.DataFrame()

# -------------------------
# Key Metrics
# -------------------------
st.header("1️⃣ Key Metrics")

if not df.empty:
    total, active, resigned = get_summary(df)
else:
    total, active, resigned = 0, 0, 0

col1, col2, col3 = st.columns(3)
col1.metric("Total Employees", total)
col2.metric("Active Employees", active)
col3.metric("Resigned Employees", resigned)

# -------------------------
# Department Distribution (GRAPH FOR PDF)
# -------------------------
st.header("2️⃣ Department Distribution")

dashboard_png = None  # image for PDF

if not df.empty and "Department" in df.columns:
    dept_counts = department_distribution(df)

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(dept_counts.index, dept_counts.values)

    ax.set_title("Employees by Department")
    ax.set_xlabel("Department")
    ax.set_ylabel("Count")
    plt.xticks(rotation=45, ha="right")

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

    # ✅ Convert graph to PNG for PDF
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    dashboard_png = buf.read()

    plt.close(fig)
else:
    st.info("No department data available.")

# -------------------------
# Skill Distribution
# -------------------------
st.header("3️⃣ Skill Distribution")

if not df.empty and "Skills" in df.columns:
    skill_list = []
    for s in df["Skills"].dropna():
        parts = s.replace(";", ",").split(",")
        skill_list.extend([p.strip() for p in parts if p.strip()])

    if skill_list:
        skill_counts = pd.Series(skill_list).value_counts().head(15)

        fig, ax = plt.subplots(figsize=(12, 6))
        bars = ax.bar(skill_counts.index, skill_counts.values)

        ax.set_title("Skill Distribution")
        ax.set_xlabel("Skills")
        ax.set_ylabel("Count")
        plt.xticks(rotation=45, ha="right")

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
        plt.close(fig)
    else:
        st.info("No skill data available.")
else:
    st.info("No skill data available.")

# -------------------------
# Gender Ratio
# -------------------------
st.header("4️⃣ Gender Ratio")

if not df.empty and "Gender" in df.columns:
    gender_counts = gender_ratio(df)

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(
        gender_counts,
        labels=gender_counts.index,
        autopct="%1.1f%%",
        startangle=90
    )
    ax.axis("equal")
    ax.set_title("Gender Distribution")

    st.pyplot(fig)
    plt.close(fig)
else:
    st.info("No gender data available.")

# -------------------------
# Average Salary by Department
# -------------------------
st.header("5️⃣ Average Salary by Department")

if not df.empty and "Department" in df.columns and "Salary" in df.columns:
    avg_salary = average_salary_by_dept(df)

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(avg_salary.index, avg_salary.values)

    ax.set_title("Average Salary by Department")
    ax.set_xlabel("Department")
    ax.set_ylabel("Average Salary")
    plt.xticks(rotation=45, ha="right")

    for bar in bars:
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{int(bar.get_height())}",
            ha="center",
            va="bottom",
            fontsize=9
        )

    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)
else:
    st.info("No salary data available.")

# -------------------------
# Recent Employees
# -------------------------
st.header("6️⃣ Recent Employees")

if not df.empty and "Join_Date" in df.columns:
    recent_df = df.sort_values(by="Join_Date", ascending=False).head(10).reset_index(drop=True)
    recent_df.insert(0, "Sr No", range(1, len(recent_df) + 1))

    st.dataframe(
        recent_df[["Sr No", "Emp_ID", "Name", "Department", "Role", "Join_Date", "Status"]],
        use_container_width=True
    )
else:
    st.info("No employee data available.")

# -------------------------
# PDF EXPORT (WITH GRAPH)
# -------------------------
st.divider()
st.subheader("📄 Download Dashboard PDF")

if st.button("Download Dashboard PDF"):
    if dashboard_png is None:
        st.error("No graph available to export.")
    else:
        pdf_buffer = io.BytesIO()
        try:
            generate_master_report(
                buffer=pdf_buffer,
                employees_df=df,
                attendance_df=None,
                mood_df=None,
                projects_df=None,
                notifications_df=None,
                dashboard_fig=dashboard_png  # ✅ CORRECT PARAMETER
            )

            pdf_buffer.seek(0)

            st.download_button(
                "Download PDF",
                pdf_buffer,
                "dashboard_report.pdf",
                "application/pdf"
            )
        except Exception as e:
            st.error("Failed to generate PDF.")
            st.exception(e)

