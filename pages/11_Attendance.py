# pages/11_Attendance.py

import streamlit as st
import pandas as pd
import datetime
import plotly.express as px

from utils.auth import require_login, show_role_badge, logout_user
from utils import database as db


def show():
    require_login()
    show_role_badge()
    logout_user()

    role = st.session_state.get("role", "Employee")
    username = st.session_state.get("user", "Unknown")

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

    # -------------------------
    # Employee Selection
    # -------------------------
    st.subheader("👤 Employee Selection")

    if role in ["Admin", "HR", "Manager"]:
        emp_options = ["All"] + (emp_df["Emp_ID"].astype(str) + " - " + emp_df["Name"]).tolist()
        selected_emp = st.selectbox("Select Employee", emp_options)
        emp_id = None if selected_emp == "All" else int(selected_emp.split(" - ")[0])
    else:
        emp_id = st.session_state.get("my_emp_id")
        selected_emp = f"{emp_id} - {username}" if emp_id else "Unknown"

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

    emp_map = emp_df.set_index("Emp_ID")["Name"].to_dict()
    att_df["Employee"] = att_df["emp_id"].map(emp_map)
    att_df["Date"] = pd.to_datetime(att_df["date"])

    st.dataframe(
        att_df[["Employee", "Date", "check_in", "check_out", "status"]],
        height=380
    )

    # -------------------------
    # Analytics
    # -------------------------
    st.subheader("📊 Attendance Analytics")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Total Records", len(att_df))

    with col2:
        st.metric("Absents", (att_df["status"] == "Absent").sum())

    status_counts = att_df["status"].value_counts()
    st.bar_chart(status_counts)

    daily_trend = att_df.groupby("Date")["status"].count().reset_index()
    fig = px.line(
        daily_trend,
        x="Date",
        y="status",
        markers=True,
        title="Daily Attendance Trend"
    )
    st.plotly_chart(fig, use_container_width=True)
