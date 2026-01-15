# pages/11_Attendance.py
import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import io

from utils.auth import require_login, show_role_badge, logout_user
from utils import database as db
from utils.pdf_export import generate_summary_pdf

def show():
    # -------------------------
    # Auth
    # -------------------------
    require_login()
    show_role_badge()
    logout_user()

    role = st.session_state.get("role", "Employee")
    username = st.session_state.get("user", "Unknown")
    my_emp_id = st.session_state.get("my_emp_id")

    st.title("📋 Employee Attendance Tracker")

    # -------------------------
    # Load Employees
    # -------------------------
    try:
        emp_df = db.fetch_employees()
    except Exception as e:
        st.error("Failed to load employees.")
        st.exception(e)
        return

    emp_map = emp_df.set_index("Emp_ID")["Name"].to_dict()

    # -------------------------
    # Employee Selection
    # -------------------------
    st.subheader("👤 Employee Selection")

    if role in ["Admin", "HR", "Manager"]:
        emp_options = ["All"] + (emp_df["Emp_ID"].astype(str) + " - " + emp_df["Name"]).tolist()
        selected_emp = st.selectbox("Select Employee", emp_options)
        emp_id = None if selected_emp == "All" else int(selected_emp.split(" - ")[0])
    else:
        if not my_emp_id:
            st.error("Employee ID not linked with this account.")
            return
        emp_id = my_emp_id
        selected_emp = f"{emp_id} - {emp_map.get(emp_id,'Unknown')}"

    # -------------------------
    # Log Attendance
    # -------------------------
    st.subheader("⏰ Log Attendance")
    today = datetime.date.today()

    check_in = st.time_input("Check-in Time", value=datetime.time(9, 0))
    check_out = st.time_input("Check-out Time", value=datetime.time(18, 0))
    status = st.selectbox("Status", ["Present", "Absent", "Half-day", "Remote"])

    if st.button("Log Attendance"):
        if not emp_id:
            st.warning("Please select an employee.")
        else:
            try:
                db.add_attendance(
                    emp_id=emp_id,
                    date=today.strftime("%Y-%m-%d"),
                    check_in=check_in.strftime("%H:%M:%S"),
                    check_out=check_out.strftime("%H:%M:%S"),
                    status=status
                )
                st.success(f"Attendance logged for {selected_emp} ✅")
                st.experimental_rerun()
            except Exception as e:
                st.error("Failed to log attendance.")
                st.exception(e)

    st.markdown("---")

    # -------------------------
    # View Attendance
    # -------------------------
    st.subheader("📅 Attendance History")

    start_date = st.date_input("Start Date", today - datetime.timedelta(days=30))
    end_date = st.date_input("End Date", today)

    try:
        att_df = db.fetch_attendance(emp_id=emp_id, start_date=start_date, end_date=end_date)
    except Exception as e:
        st.error("Failed to fetch attendance.")
        st.exception(e)
        return

    if att_df.empty:
        st.info("No attendance records found.")
        return

    att_df["Employee"] = att_df["emp_id"].map(emp_map)
    att_df["Date"] = pd.to_datetime(att_df["date"])

    st.dataframe(
        att_df[["Employee", "Date", "check_in", "check_out", "status"]]
        .sort_values("Date", ascending=False),
        height=380
    )

    # -------------------------
    # Analytics
    # -------------------------
    st.subheader("📊 Attendance Analytics")

    status_counts = att_df["status"].value_counts()
    st.bar_chart(status_counts)

    daily_trend = att_df.groupby("Date").size().reset_index(name="count")
    fig_trend_plotly = px.line(
        daily_trend,
        x="Date",
        y="count",
        markers=True,
        title="Daily Attendance Trend"
    )
    st.plotly_chart(fig_trend_plotly, use_container_width=True)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Records", len(att_df))
    col2.metric("Present", (att_df["status"] == "Present").sum())
    col3.metric("Absent", (att_df["status"] == "Absent").sum())
    col4.metric("Half-day", (att_df["status"] == "Half-day").sum())

    # -------------------------
    # Export PDF
    # -------------------------
    st.markdown("---")
    st.subheader("📄 Export Attendance PDF")

    pdf_buffer = io.BytesIO()
    if st.button("Generate Attendance PDF"):
        try:
            import matplotlib.pyplot as plt

            # Status Chart
            fig_status, ax1 = plt.subplots(figsize=(6,3))
            status_counts.plot(kind="bar", ax=ax1)
            ax1.set_title("Attendance Status Counts")
            ax1.set_ylabel("Count")

            # Daily Trend
            fig_daily, ax2 = plt.subplots(figsize=(6,3))
            ax2.plot(daily_trend["Date"], daily_trend["count"], marker="o")
            ax2.set_title("Daily Attendance Trend")
            ax2.set_ylabel("Entries")
            fig_daily.autofmt_xdate()

            # Employee-wise Present Count
            fig_emp, ax3 = plt.subplots(figsize=(6,3))
            emp_summary = att_df.groupby("Employee")["status"].apply(lambda x: (x=="Present").sum())
            emp_summary.plot(kind="bar", ax=ax3)
            ax3.set_title("Employee-wise Present Days")
            ax3.set_ylabel("Days")

            generate_summary_pdf(
                buffer=pdf_buffer,
                total=len(att_df),
                active=(att_df["status"]=="Present").sum(),
                resigned=(att_df["status"]=="Absent").sum(),
                df=att_df,
                mood_df=None,
                dept_fig=fig_status,
                gender_fig=fig_daily,
                salary_fig=fig_emp,
                title="Employee Attendance Report"
            )

            st.download_button(
                "Download Attendance PDF",
                data=pdf_buffer,
                file_name="attendance_report.pdf",
                mime="application/pdf"
            )

            plt.close(fig_status)
            plt.close(fig_daily)
            plt.close(fig_emp)

        except Exception as e:
            st.error("Failed to generate PDF.")
            st.exception(e)
