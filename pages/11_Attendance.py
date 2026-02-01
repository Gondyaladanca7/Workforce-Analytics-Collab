# pages/11_Attendance.py
"""
Employee Attendance Tracker — Workforce Intelligence System (FINAL + PDF GRAPH)
- Log attendance
- View history
- Analytics with clean graph
- Export Master PDF with graph
"""

import streamlit as st
import pandas as pd
import datetime
import matplotlib.pyplot as plt
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
except Exception:
    emp_df = pd.DataFrame(columns=["Emp_ID", "Name", "Status"])

try:
    attendance_df = db.fetch_attendance()
except Exception:
    attendance_df = pd.DataFrame(columns=["emp_id", "date", "check_in", "check_out", "status"])

emp_map = emp_df.set_index("Emp_ID")["Name"].to_dict() if not emp_df.empty else {}

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
            attendance_df = db.fetch_attendance()
            st.success("✅ Attendance logged successfully")
        except Exception as e:
            st.error("❌ Failed to log attendance")
            st.exception(e)

# -------------------------
# View Attendance History
# -------------------------
st.divider()
st.subheader("📅 Attendance History")

start = st.date_input("Start Date", datetime.date.today() - datetime.timedelta(days=30))
end = st.date_input("End Date", datetime.date.today())

att_df = attendance_df.copy()

if emp_id is not None:
    att_df = att_df[att_df["emp_id"] == emp_id]

att_df["Date"] = pd.to_datetime(att_df["date"], errors="coerce")

att_df = att_df[
    (att_df["Date"] >= pd.to_datetime(start)) &
    (att_df["Date"] <= pd.to_datetime(end))
]

attendance_png = None  # image for PDF

if not att_df.empty:
    att_df["Employee"] = att_df["emp_id"].map(emp_map).fillna(att_df["emp_id"].astype(str))
    display_df = att_df[["Employee", "Date", "check_in", "check_out", "status"]].sort_values("Date", ascending=False)

    st.dataframe(display_df, use_container_width=True)

    # -------------------------
    # Attendance Analytics (GRAPH)
    # -------------------------
    st.subheader("📊 Attendance Analytics")

    status_counts = att_df["status"].value_counts()

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(status_counts.index, status_counts.values)

    ax.set_title("Attendance Status Distribution")
    ax.set_xlabel("Status")
    ax.set_ylabel("Count")

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
    attendance_png = buf.read()

else:
    st.info("No attendance records found for the selected criteria.")

# -------------------------
# Master PDF Export (WITH GRAPH)
# -------------------------
st.divider()
st.subheader("📄 Master Workforce Report PDF")

allowed_roles_for_pdf = ["Admin", "Manager", "HR"]

if role in allowed_roles_for_pdf:
    if st.button("Download Master PDF"):
        pdf_buffer = io.BytesIO()
        try:
            generate_master_report(
                buffer=pdf_buffer,
                employees_df=emp_df,
                attendance_df=display_df if not att_df.empty else attendance_df,
                mood_df=db.fetch_mood_logs(),
                projects_df=db.fetch_projects(),
                notifications_df=pd.DataFrame(),
                mood_fig=attendance_png  # 👈 attendance graph added to PDF
            )

            pdf_buffer.seek(0)

            st.download_button(
                label="Download PDF",
                data=pdf_buffer,
                file_name="workforce_master_report.pdf",
                mime="application/pdf",
            )

        except Exception as e:
            st.error("❌ Failed to generate master PDF.")
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
            required_cols = ["emp_id", "date", "check_in", "check_out", "status"]

            if all(col in df_csv.columns for col in required_cols):
                db.bulk_add_attendance(df_csv)
                attendance_df = db.fetch_attendance()
                st.success("✅ Attendance imported successfully!")
            else:
                st.error(f"CSV missing required columns: {required_cols}")

        except Exception as e:
            st.error("❌ Failed to import CSV")
            st.exception(e)
