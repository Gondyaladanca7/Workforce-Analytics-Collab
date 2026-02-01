# pages/12_Notifications.py
"""
Notifications Center — Workforce Intelligence System (FINAL FIXED)
- View & filter notifications
- Mark read / delete
- Notification analytics graph
- Graph ALWAYS included in PDF export
"""

import streamlit as st
import pandas as pd
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
emp_id = st.session_state.get("my_emp_id")

st.title("🔔 Notifications Center")
show_role_badge()
logout_user()

# -------------------------
# Load Data
# -------------------------
try:
    notif_df = db.fetch_notifications(emp_id)
    emp_df = db.fetch_employees()
    attendance_df = db.fetch_attendance()
    mood_df = db.fetch_mood_logs()
    project_df = db.fetch_projects()
except Exception as e:
    st.error("Failed to load notifications or other data.")
    st.exception(e)
    st.stop()

if notif_df.empty:
    st.info("No notifications found.")

# -------------------------
# Filters (ONLY FOR DISPLAY)
# -------------------------
st.subheader("🔎 Filters")

status_filter = st.selectbox("Status", ["All", "Unread", "Read"])

if "type" in notif_df.columns:
    type_options = ["All"] + sorted(notif_df["type"].dropna().unique())
else:
    type_options = ["All"]

type_filter = st.selectbox("Type", type_options)

filtered = notif_df.copy()

if status_filter != "All" and "is_read" in filtered.columns:
    filtered = filtered[
        filtered["is_read"] == (1 if status_filter == "Read" else 0)
    ]

if type_filter != "All" and "type" in filtered.columns:
    filtered = filtered[filtered["type"] == type_filter]

# -------------------------
# Display Notifications
# -------------------------
st.subheader("📢 Notifications")

if filtered.empty:
    st.info("No notifications to display.")
else:
    for _, row in filtered.iterrows():
        status_text = "✅ Read" if row.get("is_read", 1) == 1 else "🟡 Unread"

        st.markdown(
            f"""
            **{status_text}**  
            {row.get('message', '')}  
            _{row.get('created_at', '')}_
            """
        )

        col1, col2 = st.columns(2)

        if row.get("is_read", 1) == 0:
            if col1.button("Mark Read", key=f"read_{row['id']}"):
                db.mark_notification_read(row["id"])
                st.success("Marked as read")
                st.rerun()

        if col2.button("Delete", key=f"del_{row['id']}"):
            db.delete_notification(row["id"])
            st.success("Notification deleted")
            st.rerun()

# -------------------------
# Notification Analytics (ALWAYS FROM notif_df)
# -------------------------
st.divider()
st.subheader("📊 Notification Analytics")

notif_png = None  # image for PDF

if not notif_df.empty:

    analytics_df = notif_df.copy()

    if "is_read" in analytics_df.columns:
        analytics_df["Status"] = analytics_df["is_read"].map({0: "Unread", 1: "Read"})
    else:
        analytics_df["Status"] = "Unknown"

    status_counts = analytics_df["Status"].value_counts()

    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar(status_counts.index, status_counts.values)

    ax.set_title("Notification Status Distribution")
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

    # ✅ convert to PNG for PDF
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    notif_png = buf.read()
    plt.close(fig)

else:
    st.info("No analytics data available.")

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
                attendance_df=attendance_df,
                mood_df=mood_df,
                projects_df=project_df,
                notifications_df=filtered,
                notification_fig=notif_png  # ✅ ALWAYS PASSED
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
            required_cols = ["emp_id", "message", "type", "is_read", "created_at"]

            if all(col in df_csv.columns for col in required_cols):
                db.bulk_add_notifications(df_csv)
                st.success("✅ Notifications imported successfully!")
                st.rerun()
            else:
                st.error(f"CSV must contain: {required_cols}")

        except Exception as e:
            st.error("❌ Failed to import CSV")
            st.exception(e)
