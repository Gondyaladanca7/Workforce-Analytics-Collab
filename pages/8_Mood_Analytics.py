# pages/8_Mood_Analytics.py
import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import io

from utils.auth import require_login, show_role_badge, logout_user
from utils import database as db
from utils.pdf_export import generate_summary_pdf

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
        mood_df = db.fetch_mood_logs()  # emp_id, mood, log_date, remarks
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
        "Select Mood(s)", options=mood_df["mood"].unique(), default=mood_df["mood"].unique()
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
        labels={"avg_mood": "Average Mood", "date":"Date"}
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
        y=filtered_df["mood"].map({"😊 Happy": 4, "😐 Neutral": 3, "😔 Sad": 2, "😡 Angry": 1}),
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
    # Export PDF
    # -------------------------
    st.subheader("📄 Export Mood Analytics PDF")
    pdf_buffer = io.BytesIO()
    if st.button("Generate Mood Analytics PDF"):
        try:
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates

            # Trend chart
            fig_trend, ax1 = plt.subplots(figsize=(6,3))
            ax1.plot(trend_df["date"], trend_df["avg_mood"], marker='o', color='blue')
            ax1.set_title("Average Mood Over Time")
            ax1.set_xlabel("Date")
            ax1.set_ylabel("Avg Mood (1-4)")
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            fig_trend.autofmt_xdate()

            # Weekly stacked
            fig_weekly, ax2 = plt.subplots(figsize=(6,3))
            weekly_df.plot(kind="bar", stacked=True, ax=ax2)
            ax2.set_title("Weekly Mood Counts")
            ax2.set_xlabel("Week")
            ax2.set_ylabel("Count")

            # Employee-wise Boxplot
            fig_box, ax3 = plt.subplots(figsize=(6,3))
            emp_mood_map = filtered_df.copy()
            emp_mood_map["mood_val"] = emp_mood_map["mood"].map({"😊 Happy":4,"😐 Neutral":3,"😔 Sad":2,"😡 Angry":1})
            emp_mood_map.boxplot(column="mood_val", by="Employee", ax=ax3)
            ax3.set_ylabel("Mood (1-4)")
            ax3.set_title("Mood Comparison by Employee")
            plt.suptitle("")

            generate_summary_pdf(
                buffer=pdf_buffer,
                total=filtered_df["Employee"].nunique(),
                active=len(filtered_df),
                resigned=0,
                df=filtered_df,
                mood_df=filtered_df,
                dept_fig=fig_trend,
                gender_fig=fig_weekly,
                salary_fig=fig_box,
                title="Filtered Mood Analytics Report"
            )

            st.download_button(
                label="Download PDF",
                data=pdf_buffer,
                file_name="mood_analytics_report.pdf",
                mime="application/pdf"
            )

            plt.close(fig_trend)
            plt.close(fig_weekly)
            plt.close(fig_box)

        except Exception as e:
            st.error("Failed to generate PDF.")
            st.exception(e)
