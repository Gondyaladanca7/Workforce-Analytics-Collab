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
role = st.session_state.get("role","Employee")
username = st.session_state.get("user")

st.title("🔔 Notifications Center")
show_role_badge()
logout_user()

# -------------------------
# Load Data
# -------------------------
try:
    notif_df = db.fetch_notifications(username=username, role=role)
    emp_df = db.fetch_employees()
    attendance_df = db.fetch_attendance()
    mood_df = db.fetch_mood_logs()
    project_df = db.fetch_projects()
except Exception as e:
    st.error("Failed to load notifications or other data.")
    st.exception(e)
    st.stop()

if notif_df.empty:
    st.info("No notifications.")
    st.stop()

# -------------------------
# Filters
# -------------------------
status_filter = st.selectbox("Status", ["All","Unread","Read"])
type_filter = st.selectbox("Type", ["All","Task","Feedback","Mood","Attendance"])

filtered = notif_df.copy()
if status_filter != "All":
    filtered = filtered[filtered["is_read"] == (1 if status_filter=="Read" else 0)]
if type_filter != "All":
    filtered = filtered[filtered["type"] == type_filter]

# -------------------------
# Display Notifications
# -------------------------
for _, row in filtered.iterrows():
    st.markdown(f"**{row['title']}**  \n{row['message']}  \n_{row['created_at']}_")
    col1, col2 = st.columns(2)
    
    if row["is_read"] == 0:
        if col1.button("Mark Read", key=f"r{row['id']}"):
            try:
                db.mark_notification_read(row["id"])
                st.success("Marked as read")
                st.experimental_rerun()
            except Exception as e:
                st.error("Failed to mark notification read")
                st.exception(e)
                
    if col2.button("Delete", key=f"d{row['id']}"):
        try:
            db.delete_notification(row["id"])
            st.success("Notification deleted")
            st.experimental_rerun()
        except Exception as e:
            st.error("Failed to delete notification")
            st.exception(e)

# -------------------------
# Master PDF Export
# -------------------------
st.divider()
st.subheader("📄 Master Workforce Report PDF")
allowed_roles_for_pdf = ["Admin","Manager","HR"]

if role in allowed_roles_for_pdf:
    if st.button("Download Master PDF"):
        pdf_buffer = io.BytesIO()
        try:
            generate_master_report(
                buffer=pdf_buffer,
                employees_df=emp_df,
                attendance_df=attendance_df,
                mood_df=mood_df,
                projects_df=project_df,
                notifications_df=filtered
            )
            st.download_button(
                "Download PDF",
                pdf_buffer,
                "workforce_master_report.pdf",
                "application/pdf"
            )
        except Exception as e:
            st.error("Failed to generate master PDF.")
            st.exception(e)
else:
    st.info("PDF download available for Admin, Manager, HR only.")
