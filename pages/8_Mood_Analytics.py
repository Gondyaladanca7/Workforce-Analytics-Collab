"""
Employee Mood Analytics Dashboard — Workforce Analytics System
Visualize trends, compare moods, and export master workforce PDF WITH GRAPHS.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import io
import matplotlib.pyplot as plt

from utils.auth import require_login, show_role_badge, logout_user
from utils import database as db
from utils.pdf_export import generate_master_report

# -----------------------
# Authentication
# -----------------------
require_login()
show_role_badge()
logout_user()

role = st.session_state.get("role", "Employee")

st.title("📊 Mood Analytics Dashboard")

# -----------------------
# Load Data
# -----------------------
mood_df = db.fetch_mood_logs()
emp_df = db.fetch_employees()
attendance_df = db.fetch_attendance()
projects_df = db.fetch_projects()

notifications_df = pd.DataFrame()
if not emp_df.empty:
    for emp in emp_df["Emp_ID"]:
        n = db.fetch_notifications(emp)
        if not n.empty:
            notifications_df = pd.concat([notifications_df, n], ignore_index=True)

# -----------------------
# Prepare data
# -----------------------
emp_map = emp_df.set_index("Emp_ID")["Name"].to_dict()
mood_df["Employee"] = mood_df["emp_id"].map(emp_map)
mood_df["DateTime"] = pd.to_datetime(mood_df["log_date"], errors="coerce")
mood_df["date"] = mood_df["DateTime"].dt.date

mood_score_map = {"😊 Happy": 4, "😐 Neutral": 3, "😔 Sad": 2, "😡 Angry": 1}

# -----------------------
# Filters
# -----------------------
st.sidebar.header("Filters")
users = sorted(mood_df["Employee"].dropna().unique())
selected_user = st.sidebar.selectbox("Employee", ["All"] + users)

start_date = st.sidebar.date_input("Start Date", mood_df["date"].min())
end_date = st.sidebar.date_input("End Date", mood_df["date"].max())

filtered_df = mood_df.copy()
if selected_user != "All":
    filtered_df = filtered_df[filtered_df["Employee"] == selected_user]

filtered_df = filtered_df[
    (filtered_df["date"] >= start_date) &
    (filtered_df["date"] <= end_date)
]

# -----------------------
# Trend Graph (Dashboard)
# -----------------------
trend_df = filtered_df.groupby("date")["mood"].apply(
    lambda x: x.map(mood_score_map).mean()
).reset_index(name="avg_mood")

trend_fig = px.line(
    trend_df,
    x="date",
    y="avg_mood",
    markers=True,
    title="Average Mood Over Time"
)
trend_fig.update_yaxes(tickmode="array", tickvals=[1,2,3,4])
st.plotly_chart(trend_fig, use_container_width=True)

# -----------------------
# Distribution Graph (Dashboard)
# -----------------------
dist_df = filtered_df["mood"].value_counts().reset_index()
dist_df.columns = ["Mood", "Count"]

dist_fig = px.bar(
    dist_df,
    x="Mood",
    y="Count",
    text="Count",
    title="Mood Distribution"
)
st.plotly_chart(dist_fig, use_container_width=True)

# -----------------------
# Comparison Graph (Dashboard)
# -----------------------
filtered_df["MoodScore"] = filtered_df["mood"].map(mood_score_map)

compare_fig = px.strip(
    filtered_df,
    x="Employee",
    y="MoodScore",
    title="Mood Comparison by Employee"
)
compare_fig.update_yaxes(tickmode="array", tickvals=[1,2,3,4])
st.plotly_chart(compare_fig, use_container_width=True)

# -----------------------
# Table
# -----------------------
st.dataframe(filtered_df[["Employee","mood","remarks","DateTime"]])

# -----------------------
# PDF EXPORT (MATPLOTLIB — NO KALEIDO)
# -----------------------
st.subheader("📄 Master Workforce PDF")

if role in ["Admin","Manager","HR"]:

    if st.button("Generate PDF with Graphs"):
        pdf_buffer = io.BytesIO()

        try:
            # -------- GRAPH 1 (Trend)
            fig1, ax1 = plt.subplots()
            ax1.plot(trend_df["date"], trend_df["avg_mood"], marker="o")
            ax1.set_title("Average Mood Over Time")
            ax1.set_ylabel("Mood (1–4)")
            ax1.set_xlabel("Date")
            ax1.set_yticks([1,2,3,4])
            fig1.autofmt_xdate()
            buf1 = io.BytesIO()
            fig1.savefig(buf1, format="png")
            plt.close(fig1)
            buf1.seek(0)

            # -------- GRAPH 2 (Distribution)
            fig2, ax2 = plt.subplots()
            ax2.bar(dist_df["Mood"], dist_df["Count"])
            ax2.set_title("Mood Distribution")
            ax2.set_ylabel("Count")
            buf2 = io.BytesIO()
            fig2.savefig(buf2, format="png")
            plt.close(fig2)
            buf2.seek(0)

            generate_master_report(
                buffer=pdf_buffer,
                employees_df=emp_df,
                attendance_df=attendance_df,
                mood_df=filtered_df,
                projects_df=projects_df,
                notifications_df=notifications_df,
                mood_fig=buf1.getvalue(),     # ✅ PNG BYTES
                project_fig=buf2.getvalue()  # ✅ PNG BYTES
            )

            pdf_buffer.seek(0)

            st.download_button(
                "Download PDF",
                pdf_buffer,
                "workforce_master_report.pdf",
                "application/pdf"
            )

        except Exception as e:
            st.error("PDF generation failed")
            st.exception(e)
else:
    st.info("Only Admin / Manager / HR can download PDF.")
