# pages/8_Mood_Analytics.py
import streamlit as st
import pandas as pd
import plotly.express as px
import datetime

from utils.auth import require_login, show_role_badge, logout_user
from utils import database as db

def show():
    # -------------------------
    # Login & Role
    # -------------------------
    require_login()
    show_role_badge()
    logout_user()

    st.title("📊 Mood Analytics Dashboard")

    # -------------------------
    # Load Mood Data
    # -------------------------
    try:
        mood_df = db.fetch_mood_logs()  # fetch_mood_logs() returns emp_id, mood, log_date
        emp_df = db.fetch_employees()
    except Exception as e:
        st.error("Failed to load mood data or employees.")
        st.exception(e)
        return

    if mood_df.empty or emp_df.empty:
        st.info("No mood entries or employee data available.")
        return

    # Map employee names
    emp_map = emp_df.set_index("Emp_ID")["Name"].to_dict()
    mood_df["Employee"] = mood_df["emp_id"].map(emp_map).fillna(mood_df["emp_id"].astype(str))

    # Parse dates
    mood_df["log_date_parsed"] = pd.to_datetime(mood_df["log_date"], errors="coerce")
    mood_df["date"] = mood_df["log_date_parsed"].dt.date

    # -------------------------
    # Filters
    # -------------------------
    st.sidebar.header("Filters")
    users = sorted(mood_df["Employee"].unique())
    selected_user = st.sidebar.selectbox("Select Employee", ["All"] + users)
    start_date = st.sidebar.date_input("Start Date", value=mood_df["date"].min())
    end_date = st.sidebar.date_input("End Date", value=mood_df["date"].max())
    selected_mood = st.sidebar.multiselect(
        "Select Mood(s)", options=mood_df["mood"].unique(), default=mood_df["mood"].unique()
    )

    filtered_df = mood_df.copy()
    if selected_user != "All":
        filtered_df = filtered_df[filtered_df["Employee"] == selected_user]
    filtered_df = filtered_df[
        (filtered_df["date"] >= start_date) & (filtered_df["date"] <= end_date)
    ]
    filtered_df = filtered_df[filtered_df["mood"].isin(selected_mood)]

    if filtered_df.empty:
        st.warning("No mood entries match the selected filters.")
        return

    # -------------------------
    # Key Metrics
    # -------------------------
    st.subheader("📌 Key Metrics")
    total_entries = len(filtered_df)
    avg_mood = filtered_df["mood"].map({"😊 Happy": 4, "😐 Neutral": 3, "😔 Sad": 2, "😡 Angry": 1}).mean()
    mood_counts = filtered_df["mood"].value_counts()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Entries", total_entries)
    c2.metric("Average Mood (1-4)", f"{avg_mood:.2f}")
    c3.metric("Unique Employees", filtered_df["Employee"].nunique())

    # -------------------------
    # Mood Trend Over Time
    # -------------------------
    st.markdown("### 📅 Mood Trend Over Time")
    trend_df = filtered_df.groupby(["date"])["mood"].apply(
        lambda x: x.map({"😊 Happy": 4, "😐 Neutral": 3, "😔 Sad": 2, "😡 Angry": 1}).mean()
    ).reset_index(name="avg_mood")
    trend_fig = px.line(
        trend_df,
        x="date",
        y="avg_mood",
        markers=True,
        title="Average Mood Over Time",
        labels={"avg_mood": "Average Mood"}
    )
    st.plotly_chart(trend_fig, use_container_width=True)

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
        color_discrete_map={
            "😊 Happy": "green",
            "😐 Neutral": "gray",
            "😔 Sad": "orange",
            "😡 Angry": "red"
        }
    )
    st.plotly_chart(dist_fig, use_container_width=True)

    # -------------------------
    # Employee-wise Comparison
    # -------------------------
    st.markdown("### 🧍 Employee-wise Mood Comparison")
    emp_avg_df = filtered_df.groupby("Employee")["mood"].apply(
        lambda x: x.map({"😊 Happy": 4, "😐 Neutral": 3, "😔 Sad": 2, "😡 Angry": 1}).mean()
    ).reset_index(name="avg_mood")
    box_fig = px.box(
        filtered_df,
        x="Employee",
        y=filtered_df["mood"].map({"😊 Happy": 4, "😐 Neutral": 3, "😔 Sad": 2, "😡 Angry": 1}),
        points="all",
        title="Mood Comparison by Employee",
        labels={"y": "Mood (1-4)"}
    )
    st.plotly_chart(box_fig, use_container_width=True)

    # -------------------------
    # Display Raw Data
    # -------------------------
    st.markdown("---")
    st.subheader("🔍 Filtered Mood Data")
    st.dataframe(
        filtered_df[["Employee", "mood", "remarks", "log_date_parsed"]].sort_values("log_date_parsed", ascending=False).rename(
            columns={"log_date_parsed": "DateTime"}
        ),
        height=400
    )
