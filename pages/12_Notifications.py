# pages/12_Notifications.py
"""
Notifications Center — Workforce Intelligence System
View, filter, manage notifications and export master PDF reports.
"""

import streamlit as st
import pandas as pd
import io

from utils.auth import require_login, show_role_badge, logout_user
from utils import database as db
from utils.pdf_export import generate_master_report

# -------------------------
# Authentication
# -------------------------
require_login()

role = st.session_state.get("role", "Employee")
emp_id = st.session_state.get("my_emp_id")

st.title("🔔 Notifications Center")
show_role_badge()
logout_user()

# -------------------------
# Load Data (SAFE)
# -------------------------
def load_data():
    try:
        notif_df = db.fetch_notifications(emp_id)
        emp_df = db.fetch_employees()
        attendance_df = db.fetch_attendance()
        mood_df = db.fetch_mood_logs()
        project_df = db.fetch_projects()
        return notif_df, emp_df, attendance_df, mood_df, project_df
    except Exception as e:
        st.error("Failed to load notifications or other data.")
        st.exception(e)
        st.stop()

notif_df, emp_df, attendance_df, mood_df, project_df = load_data()

# -------------------------
# Filters
# -------------------------
st.subheader("Filters")
status_filter = st.selectbox("Status", ["All", "Unread", "Read"])

# Safe handling if 'type' column missing
if "type" in notif_df.columns:
    type_options = ["All"] + sorted(notif_df["type"].dropna().unique().tolist())
else:
    type_options = ["All"]

type_filter = st.selectbox("Type", type_options)

filtered = notif_df.copy()

if status_filter != "All":
    filtered = filtered[filtered["is_read"] == (1 if status_filter == "Read" else 0)]

if type_filter != "All" and "type" in filtered.columns:
    filtered = filtered[filtered["type"] == type_filter]

# -------------------------
# Display Notifications
# -------------------------
st.subheader("Notifications")

if filtered.empty:
    st.info("No notifications to display.")
else:
    for idx, row in filtered.iterrows():
        st.markdown(
            f"""
            **{row.get('title', 'Notification')}**  
            {row.get('message', '')}  
            _{row.get('created_at', '')}_
            """
        )

        col1, col2 = st.columns(2)

        # Mark Read
        if row.get("is_read", 1) == 0:
            if col1.button("Mark Read", key=f"read_{row.get('id', idx)}"):
                try:
                    db.mark_notification_read(row["id"])
                    # Safe refresh
                    notif_df = db.fetch_notifications(emp_id)
                    st.success("Marked as read")
                except Exception as e:
                    st.error("Failed to mark notification as read")
                    st.exception(e)

        # Delete
        if col2.button("Delete", key=f"del_{row.get('id', idx)}"):
            try:
                db.delete_notification(row["id"])
                notif_df = db.fetch_notifications(emp_id)
                st.success("Notification deleted")
            except Exception as e:
                st.error("Failed to delete notification")
                st.exception(e)

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
                mood_df=mood_df,
                projects_df=project_df,
                notifications_df=filtered,
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
    st.sidebar.subheader("📥 Import Notifications CSV")
    uploaded_file = st.sidebar.file_uploader("Upload CSV", type=["csv"])
    if uploaded_file:
        try:
            df_csv = pd.read_csv(uploaded_file)
            # Validate required columns
            required_cols = ["title","message","type","is_read","created_at"]
            if all(col in df_csv.columns for col in required_cols):
                db.bulk_add_notifications(df_csv)  # You need to implement in db.py
                st.success("✅ Notifications imported successfully!")
            else:
                st.error(f"CSV missing required columns: {required_cols}")
        except Exception as e:
            st.error("❌ Failed to import CSV")
            st.exception(e)
