# pages/8_Mood_Analytics.py
import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import io

from utils.auth import require_login, show_role_badge, logout_user
from utils import database as db
from utils.pdf_export import generate_master_report

def show():
    # -------------------------
    # Login & Role
    # -------------------------
    require_login()
    show_role_badge()
    logout_user()

    st.title("📊 Mood Analytics Dashboard")

    # -------------------------
    # Load Data
    # -------------------------
    try:
        mood_df = db.fetch_mood_logs()
        emp_df = db.fetch_employees()
        attendance_df = db.fetch_attendance()
        projects_df = db.fetch_projects()
        notifications_df = pd.DataFrame()
        for emp in emp_df["Emp_ID"]:
            notif = db.fetch_notifications(emp)
            if not notif.empty:
                notifications_df = pd.concat([notifications_df, notif], ignore_index=True)
    except Exception as e:
        st.error("Failed to load required data.")
        st.exception(e)
        return

    if mood_df.empty or emp_df.empty:
        st.info("No mood or employee data available.")
        return

    # Map employee names
    emp_map = emp_df.set_index("Emp_ID")["Name"].to_dict()
    mood_df["Employee"] = mood_df["emp_id"].map(emp_map).fillna(mood_df["emp_id"].astype(str))

    # Parse dates
    mood_df["DateTime"] = pd.to_datetime(mood_df["log_date"], errors="coerce")
    mood_df["date"] = mood_df["DateTime"].dt.date

    # -------------------------
    # Filters
    # -------------------------
    st.sidebar.header("Filters")
    users = sorted(mood_df["Employee"].unique())
    selected_user = st.sidebar.selectbox("Select Employee", ["All"] + users)
    start_date = st.sidebar.date_input("Start Date", value=mood_df["date"].min())
    end_date = st.sidebar.date_input("End Date", value=mood_df["date"].max())
    selected_mood = st.sidebar.multiselect(
        "Select Mood(s)", options=sorted(mood_df["mood"].unique()), default=sorted(mood_df["mood"].unique())
    )

    filtered_df = mood_df.copy()
    if selected_user != "All":
        filtered_df = filtered_df[filtered_df["Employee"] == selected_user]
    filtered_df = filtered_df[(filtered_df["date"] >= start_date) & (filtered_df["date"] <= end_date)]
    filtered_df = filtered_df[filtered_df["mood"].isin(selected_mood)]

    if filtered_df.empty:
        st.warning("No mood entries match the selected filters.")
        return

    # -------------------------
    # Key Metrics
    # -------------------------
    st.subheader("📌 Key Metrics")
    total_entries = len(filtered_df)
    mood_score_map = {"😊 Happy": 4, "😐 Neutral": 3, "😔 Sad": 2, "😡 Angry": 1}
    avg_mood = filtered_df["mood"].map(mood_score_map).mean()
    mood_counts = filtered_df["mood"].value_counts()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Entries", total_entries)
    c2.metric("Average Mood (1-4)", f"{avg_mood:.2f}")
    c3.metric("Unique Employees", filtered_df["Employee"].nunique())

    # -------------------------
    # Mood Trend Over Time
    # -------------------------
    st.markdown("### 📅 Mood Trend Over Time")
    trend_df = filtered_df.groupby(["date"])["mood"].apply(lambda x: x.map(mood_score_map).mean()).reset_index(name="avg_mood")
    trend_fig = px.line(
        trend_df,
        x="date",
        y="avg_mood",
        markers=True,
        title="Average Mood Over Time",
        labels={"avg_mood": "Average Mood", "date": "Date"}
    )
    st.plotly_chart(trend_fig, use_container_width=True)

    # Weekly stacked mood chart
    weekly_df = filtered_df.groupby([pd.Grouper(key="DateTime", freq="W"), "mood"]).size().unstack(fill_value=0)
    weekly_fig = px.bar(
        weekly_df, x=weekly_df.index, y=weekly_df.columns,
        title="Weekly Mood Counts", labels={"value":"Count","DateTime":"Week"}
    )
    st.plotly_chart(weekly_fig, use_container_width=True)

    # -------------------------
    # Mood Distribution
    # -------------------------
    st.markdown("### 📊 Mood Distribution")
    dist_fig = px.bar(
        mood_counts.reset_index().rename(columns={"index": "Mood", "mood": "Count"}),
        x="Mood",
        y="Count",
        text="Count",
        title="Mood Distribution",
        color="Mood",
        color_discrete_map={"😊 Happy":"green","😐 Neutral":"gray","😔 Sad":"orange","😡 Angry":"red"}
    )
    st.plotly_chart(dist_fig, use_container_width=True)

    # -------------------------
    # Employee-wise Comparison
    # -------------------------
    st.markdown("### 🧍 Employee-wise Mood Comparison")
    box_fig = px.box(
        filtered_df,
        x="Employee",
        y=filtered_df["mood"].map(mood_score_map),
        points="all",
        title="Mood Comparison by Employee",
        labels={"y":"Mood (1-4)"}
    )
    st.plotly_chart(box_fig, use_container_width=True)

    # -------------------------
    # Display Raw Data
    # -------------------------
    st.markdown("---")
    st.subheader("🔍 Filtered Mood Data")
    st.dataframe(
        filtered_df[["Employee","mood","remarks","DateTime"]].sort_values("DateTime", ascending=False),
        height=400
    )

    # -------------------------
    # Master PDF Export (ROLE BASED)
    # -------------------------
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
                    mood_df=filtered_df,  # pass filtered mood only
                    projects_df=projects_df,
                    notifications_df=notifications_df,
                    dept_fig=None,
                    mood_fig=None,
                    project_fig=None,
                    title="Master Workforce Report"
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
