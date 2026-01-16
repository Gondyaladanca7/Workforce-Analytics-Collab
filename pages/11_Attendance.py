# pages/11_Attendance.py
"""
Employee Attendance Tracker — Workforce Intelligence System
Log attendance, view history, analytics, and export master PDF reports.
"""

import streamlit as st
import pandas as pd
import datetime
import io

from utils.auth import require_login, show_role_badge, logout_user
from utils import database as db
from utils.pdf_export import generate_master_report

# -------------------------
# Authentication
# -------------------------
require_login()
role = st.session_state.get("role", "Employee")
my_emp_id = st.session_state.get("my_emp_id")

st.title("📋 Employee Attendance Tracker")
show_role_badge()
logout_user()

# -------------------------
# Load Data
# -------------------------
try:
    emp_df = db.fetch_employees()
    attendance_df = db.fetch_attendance()
except Exception as e:
    st.error("Failed to load required data.")
    st.exception(e)
    st.stop()

emp_map = emp_df.set_index("Emp_ID")["Name"].to_dict()

# -------------------------
# Employee Selection
# -------------------------
if role in ["Admin", "Manager", "HR"]:
    emp_options = ["All"] + (emp_df["Emp_ID"].astype(str) + " - " + emp_df["Name"]).tolist()
    selected = st.selectbox("Select Employee", emp_options)
    emp_id = None if selected == "All" else int(selected.split(" - ")[0])
else:
    emp_id = my_emp_id

# -------------------------
# Log Attendance (Admin only)
# -------------------------
if role == "Admin":
    st.subheader("⏰ Log Attendance")

    today = datetime.date.today()
    check_in = st.time_input("Check-in", datetime.time(9, 0))
    check_out = st.time_input("Check-out", datetime.time(18, 0))
    status = st.selectbox("Status", ["Present", "Absent", "Half-day", "Remote"])

    if st.button("Log Attendance"):
        try:
            db.add_attendance(
                emp_id=emp_id,
                date=today.strftime("%Y-%m-%d"),
                check_in=check_in.strftime("%H:%M:%S"),
                check_out=check_out.strftime("%H:%M:%S"),
                status=status
            )
            # ✅ Safe refresh without rerun
            attendance_df = db.fetch_attendance()
            st.success("Attendance logged successfully ✅")
        except Exception as e:
            st.error("Failed to log attendance")
            st.exception(e)

# -------------------------
# View Attendance History
# -------------------------
st.divider()
st.subheader("📅 Attendance History")

start = st.date_input(
    "Start Date", datetime.date.today() - datetime.timedelta(days=30)
)
end = st.date_input("End Date", datetime.date.today())

att_df = attendance_df.copy()
if emp_id is not None:
    att_df = att_df[att_df["emp_id"] == emp_id]

att_df = att_df[
    (att_df["date"] >= pd.to_datetime(start)) &
    (att_df["date"] <= pd.to_datetime(end))
]

if att_df.empty:
    st.info("No attendance records found.")
else:
    att_df["Employee"] = att_df["emp_id"].map(emp_map)
    att_df["Date"] = pd.to_datetime(att_df["date"])

    st.dataframe(
        att_df[["Employee", "Date", "check_in", "check_out", "status"]]
        .sort_values("Date", ascending=False),
        use_container_width=True
    )

    st.subheader("📊 Attendance Analytics")
    st.bar_chart(att_df["status"].value_counts())

# -------------------------
# Master PDF Export
# -------------------------
st.divider()
st.subheader("📄 Master Workforce Report PDF")

allowed_roles_for_pdf = ["Admin", "Manager", "HR"]

if role in allowed_roles_for_pdf:
    pdf_buffer = io.BytesIO()
    if st.button("Download Master PDF"):
        try:
            generate_master_report(
                buffer=pdf_buffer,
                employees_df=emp_df,
                attendance_df=attendance_df,
                mood_df=db.fetch_mood_logs(),
                projects_df=db.fetch_projects(),
                notifications_df=pd.DataFrame()
            )
            pdf_buffer.seek(0)
            st.download_button(
                label="Download PDF",
                data=pdf_buffer,
                file_name="workforce_master_report.pdf",
                mime="application/pdf",
            )
        except Exception as e:
            st.error("Failed to generate master PDF.")
            st.exception(e)
else:
    st.info("PDF download available for Admin, Manager, HR only.")
# -------------------------
# Import CSV (Admin Only)
# -------------------------
if role in ["Admin", "Manager", "HR"]:
    st.sidebar.subheader("📥 Import Attendance CSV")
    uploaded_file = st.sidebar.file_uploader("Upload CSV", type=["csv"])
    if uploaded_file:
        try:
            df_csv = pd.read_csv(uploaded_file)
            # Validate required columns
            required_cols = ["emp_id","date","check_in","check_out","status"]
            if all(col in df_csv.columns for col in required_cols):
                db.bulk_add_attendance(df_csv)  # You need to create this in db.py
                st.success("✅ Attendance imported successfully!")
            else:
                st.error(f"CSV missing required columns: {required_cols}")
        except Exception as e:
            st.error("❌ Failed to import CSV")
            st.exception(e)
